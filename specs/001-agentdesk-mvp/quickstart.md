# Quickstart: AgentDesk AI

## Run the full stack

```bash
cp .env.example .env          # defaults work out-of-the-box (mock providers)
docker compose up --build     # postgres+pgvector, redis, backend, worker, frontend
```

- Backend API + docs: http://localhost:8000/docs
- Frontend dashboard: http://localhost:3000
- Health: http://localhost:8000/api/v1/health

Migrations (Alembic, incl. `CREATE EXTENSION vector`) run automatically on backend start.

## End-to-end smoke flow

1. **Register** an organization + admin → `POST /api/v1/auth/register`.
2. **Login** → `POST /api/v1/auth/login` (use the access token as `Authorization: Bearer ...`).
3. **Add a document** → `POST /api/v1/documents` (chunked + embedded with the mock provider).
4. **Search** → `POST /api/v1/documents/search` to confirm retrieval works.
5. **Create a ticket** → `POST /api/v1/tickets`.
6. **Run the workflow** → `POST /api/v1/tickets/{id}/run` (async; poll the ticket).
7. **Review the draft** → `GET /api/v1/tickets/{id}`; ticket is `waiting_approval` or `escalated`.
8. **Approve / edit / reject** → `/approve`, `/edit-draft`, `/reject`.
9. On approval/escalation a **signed webhook** is sent (configure via `PUT /api/v1/webhooks`).
10. **Metrics** → `GET /api/v1/admin/metrics`; **audit** via ticket events / logs.

## Run tests (no network, no paid APIs)

```bash
cd backend
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock pytest -q
```

CI (`.github/workflows/ci.yml`) runs `ruff`, `mypy`, and `pytest` with the mock providers forced.

## Key env vars (see `.env.example`)

`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ACCESS_TOKEN_MINUTES` (30), `REFRESH_TOKEN_DAYS` (7),
`LLM_PROVIDER` (mock), `EMBEDDING_PROVIDER` (mock), `EMBEDDING_DIM` (384),
`CONFIDENCE_THRESHOLD` (0.7), `SIMILARITY_THRESHOLD` (0.5), `WEBHOOK_MAX_RETRIES` (5),
`CORS_ORIGINS`, `RATE_LIMIT_PER_MINUTE`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` (optional).
