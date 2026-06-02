# Webhook Contract (outbound)

AgentDesk AI sends an HTTP POST to the organization's configured `url` when a ticket transitions to
`approved` or `escalated`.

## Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `X-AgentDesk-Event` | `ticket.approved` \| `ticket.escalated` |
| `X-AgentDesk-Timestamp` | unix seconds at send time |
| `X-AgentDesk-Signature` | `sha256=<hex>` — HMAC-SHA256 of the **raw request body** using the org's webhook `secret` |

## Body

```json
{
  "event": "ticket.approved",
  "delivery_id": "uuid",
  "organization_id": "uuid",
  "ticket": {
    "id": "uuid",
    "title": "string",
    "status": "approved",
    "priority": "medium",
    "final_response": "string|null",
    "updated_at": "ISO-8601"
  },
  "sent_at": "ISO-8601"
}
```

## Signature verification (recipient side)

```python
import hmac, hashlib
expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, received_signature_header)
```

## Delivery & retries

- A `WebhookDelivery` row is created `pending`, then a Celery task `deliver_webhook` posts the body.
- Success = HTTP 2xx → status `success`, `webhook_sent` audit event written.
- Failure (non-2xx, timeout, connection error) → retried with exponential backoff + jitter,
  `max_retries=5` (delays ≈ 2s, 4s, 8s, 16s, 32s). After exhaustion → status `failed`, counts toward
  the `failed_jobs` metric.
- Each attempt increments `attempts` and records `last_status_code` / `last_error`.
