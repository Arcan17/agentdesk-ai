# Phase 1 Data Model: AgentDesk AI

All tenant-scoped tables carry `organization_id` (FK → `organization.id`) and are always filtered by
the authenticated user's organization. Primary keys are UUIDs. Timestamps (`created_at`, `updated_at`)
are timezone-aware. `EMBEDDING_DIM = 384`.

## Entities

### Organization
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | str | unique, required |
| created_at | datetime | |

Relationships: has many `User`, `Document`, `Ticket`, `AuditLog`; has zero/one `Webhook` config.

### User
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | required |
| email | str | unique per organization, validated |
| hashed_password | str | bcrypt; never serialized |
| role | enum(`admin`,`operator`,`viewer`) | required |
| is_active | bool | default true |
| created_at | datetime | |

### Document
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | required |
| title | str | required |
| source_type | enum(`manual`,`upload`) | |
| content | text | required, non-empty (validated) |
| created_by | UUID FK→User | |
| created_at | datetime | |

Relationships: has many `DocumentChunk` (cascade delete).

### DocumentChunk
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | denormalized for tenant-scoped vector search |
| document_id | UUID FK | required |
| chunk_index | int | order within document |
| content | text | the passage text |
| embedding | vector(384) | pgvector; cosine distance index |

### Ticket
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | required |
| title | str | required |
| description | text | required |
| priority | enum(`low`,`medium`,`high`,`urgent`) | default `medium` |
| status | enum (see state machine) | default `new` |
| suggested_type | str nullable | set by classifier |
| suggested_priority | enum nullable | set by classifier |
| draft_response | text nullable | latest AI draft |
| final_response | text nullable | set on approval (possibly edited) |
| created_by | UUID FK→User | |
| created_at / updated_at | datetime | |

Relationships: has many `TicketEvent`, `AgentRun`.

**Status state machine**:
```
new → triaged → draft_ready → waiting_approval → approved → closed
                            ↘ escalated
waiting_approval → rejected → (draft_ready on re-run)
any non-closed → closed
```
Allowed transitions are enforced in `ticket_service`; illegal transitions raise a domain error
(supports the concurrent approve/reject edge case — first writer wins).

### TicketEvent  (history)
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| ticket_id | UUID FK | required |
| organization_id | UUID FK | |
| event_type | str | e.g. `created`,`agent_run`,`approved`,`rejected`,`edited`,`escalated`,`status_change` |
| from_status / to_status | enum nullable | for transitions |
| actor_user_id | UUID FK nullable | null when actor is the AI workflow |
| message | text nullable | |
| created_at | datetime | |

### AgentRun
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| ticket_id | UUID FK | required |
| organization_id | UUID FK | |
| status | enum(`running`,`completed`,`failed`) | |
| classification | json nullable | type + suggested priority |
| retrieved_chunk_ids | json nullable | list of chunk ids used |
| retrieval_hit | bool | true if ≥1 chunk above similarity threshold |
| draft | text nullable | |
| confidence | float nullable | critic grounding score 0..1 |
| outcome | enum(`waiting_approval`,`escalated`) nullable | |
| latency_ms | int nullable | |
| estimated_cost_usd | float nullable | from token usage |
| prompt_tokens / completion_tokens | int nullable | |
| error | text nullable | when failed |
| created_at / finished_at | datetime | |

### AuditLog  (append-only)
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK nullable | nullable for failed logins w/o resolved org |
| actor_user_id | UUID FK nullable | |
| event | enum | ticket_created, agent_run_started, retrieval_completed, draft_generated, response_approved, response_rejected, ticket_escalated, webhook_sent, login_success, login_failed |
| target_type / target_id | str/UUID nullable | e.g. ticket:<id> |
| metadata | json nullable | |
| created_at | datetime | |

No update/delete operations exposed (immutability by convention).

### Webhook  (per-organization config)
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | unique (one config per org) |
| url | str | validated http(s) URL |
| secret | str | HMAC signing key; never serialized in full |
| is_active | bool | default true |
| created_at / updated_at | datetime | |

### WebhookDelivery
| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| webhook_id | UUID FK | |
| organization_id | UUID FK | |
| event | str | `ticket.approved` / `ticket.escalated` |
| payload | json | signed body |
| status | enum(`pending`,`success`,`failed`) | |
| attempts | int | default 0 |
| last_status_code | int nullable | |
| last_error | text nullable | |
| created_at / updated_at | datetime | |

## Validation rules (from requirements)

- Document `content` MUST be non-empty/non-whitespace (edge case).
- Ticket `final_response` MUST be non-empty when approving (edit-to-empty rejected).
- Webhook `url` MUST be a valid http(s) URL.
- All list/detail queries MUST filter by `organization_id` of the current user (FR-001/SC-006).
- Status transitions MUST follow the state machine; violations raise `409 Conflict`.

## Indexes

- `document_chunk`: vector index on `embedding` (cosine) + btree on `organization_id`.
- `ticket`: composite `(organization_id, status)` for metrics & listing.
- `audit_log`: `(organization_id, created_at)`; `agent_run`: `(organization_id, created_at)`.
