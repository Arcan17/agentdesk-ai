# Tasks: AgentDesk AI — Human-in-the-loop AI SupportOps Platform

**Feature**: `001-agentdesk-mvp` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests are **required** (Constitution Principle III). Each task lists exact file paths. `[P]` = can run
in parallel (different files, no incomplete dependency). Story labels map to spec user stories:
US1 = AI-assisted approval, US2 = escalation, US3 = knowledge base, US4 = roles/RBAC, US5 = webhooks,
US6 = metrics.

Delivery is **phase by phase with a pause** after each implementation phase (summary + tests + review).

---

## Phase 1 — Setup & Infrastructure (Implementation Phase 1)

- [ ] T001 Create backend project skeleton (`backend/app/{core,db,models,schemas,api/v1,services,providers,agent,workers}` packages with `__init__.py`) and `backend/pyproject.toml` (FastAPI, SQLAlchemy 2.0, asyncpg, pydantic v2, pydantic-settings, alembic, celery, redis, python-jose, passlib[bcrypt], httpx, structlog, slowapi, langgraph; dev: pytest, pytest-asyncio, ruff, mypy)
- [ ] T002 [P] Implement settings in `backend/app/core/config.py` (pydantic-settings: DATABASE_URL, REDIS_URL, JWT_SECRET, ACCESS_TOKEN_MINUTES=30, REFRESH_TOKEN_DAYS=7, LLM_PROVIDER=mock, EMBEDDING_PROVIDER=mock, EMBEDDING_DIM=384, CONFIDENCE_THRESHOLD=0.7, SIMILARITY_THRESHOLD=0.5, WEBHOOK_MAX_RETRIES=5, CORS_ORIGINS, RATE_LIMIT_PER_MINUTE)
- [ ] T003 [P] Implement structured logging in `backend/app/core/logging.py` (structlog JSON, request-id)
- [ ] T004 [P] Implement async DB engine/session in `backend/app/db/engine.py` and `backend/app/db/session.py`; declarative base in `backend/app/db/base.py` (UUID + timestamp mixins)
- [ ] T005 Create FastAPI app factory in `backend/app/main.py` (CORS from settings, slowapi rate limit, exception handlers that never leak stack traces, `/api/v1` router include) and `GET /api/v1/health` returning DB+Redis status in `backend/app/api/v1/health.py`
- [ ] T006 [P] Initialize Alembic in `backend/alembic/` + `backend/alembic.ini`; first migration enables pgvector (`CREATE EXTENSION IF NOT EXISTS vector`)
- [ ] T007 [P] Author `backend/Dockerfile`, `frontend/Dockerfile` (placeholder), root `docker-compose.yml` (postgres `pgvector/pgvector:pg16`, redis, backend, worker, frontend), and `.env.example` with every variable
- [ ] T008 [P] Add `backend/tests/conftest.py` (async test client via httpx ASGITransport, test DB fixtures, env forcing `LLM_PROVIDER=mock`/`EMBEDDING_PROVIDER=mock`) and a smoke `test_health` in `backend/tests/test_health.py`

**Checkpoint / pause**: `docker compose up` boots; `GET /api/v1/health` is 200; `pytest -q` green.

---

## Phase 2 — Auth, Users, Organizations, RBAC (Implementation Phase 2 · US4)

- [ ] T009 [P] [US4] Organization model in `backend/app/models/organization.py`
- [ ] T010 [P] [US4] User model + Role enum in `backend/app/models/user.py` (hashed_password, role, organization_id)
- [ ] T011 [US4] Alembic migration for organization + user tables in `backend/alembic/versions/`
- [ ] T012 [P] [US4] Security helpers in `backend/app/core/security.py` (bcrypt hash/verify, JWT encode/decode for access + refresh)
- [ ] T013 [P] [US4] Auth/RBAC dependencies in `backend/app/core/deps.py` and `backend/app/rbac.py` (`get_current_user`, `require_role(*roles)`, tenant scoping helper)
- [ ] T014 [P] [US4] Pydantic schemas in `backend/app/schemas/auth.py` and `backend/app/schemas/user.py` (RegisterRequest, LoginRequest, TokenPair, UserCreate, UserOut)
- [ ] T015 [US4] AuthService in `backend/app/services/auth_service.py` (register org+admin, authenticate, refresh) and UserService in `backend/app/services/user_service.py`
- [ ] T016 [US4] Auth router in `backend/app/api/v1/auth.py` (`/register`, `/login`, `/refresh`) and users router in `backend/app/api/v1/users.py` (admin-only list/create)
- [ ] T017 [US4] Tests: `backend/tests/test_auth.py` (register/login/refresh, bad creds) and `backend/tests/test_rbac.py` (role enforcement + cross-org denial)

**Checkpoint / pause**: auth flow + RBAC + tenant isolation tests pass.

---

## Phase 3 — Tickets & Audit Logs (Implementation Phase 3 · US1 foundation)

- [ ] T018 [P] [US1] Ticket model + status/priority enums + state-machine helper in `backend/app/models/ticket.py`
- [ ] T019 [P] [US1] TicketEvent model in `backend/app/models/ticket_event.py`
- [ ] T020 [P] [US1] AuditLog model + event enum in `backend/app/models/audit_log.py`
- [ ] T021 [US1] Alembic migration for ticket, ticket_event, audit_log tables
- [ ] T022 [P] [US1] Ticket schemas in `backend/app/schemas/ticket.py` (TicketCreate, TicketOut, TicketEventOut)
- [ ] T023 [P] [US1] AuditService in `backend/app/services/audit_service.py` (write event helper used everywhere)
- [ ] T024 [US1] TicketService in `backend/app/services/ticket_service.py` (create, list-by-org, get, validated status transitions, history append)
- [ ] T025 [US1] Tickets router in `backend/app/api/v1/tickets.py` (`POST /`, `GET /`, `GET /{id}`, `GET /{id}/events`); emits `ticket_created`
- [ ] T026 [US1] Tests: `backend/tests/test_tickets.py` (create/list/detail/history, illegal transition → 409) and `backend/tests/test_audit.py` (ticket_created + login events recorded)

**Checkpoint / pause**: ticket CRUD + history + audit logging green.

---

## Phase 4 — Documents, Chunking, Retrieval (Implementation Phase 4 · US3)

- [ ] T027 [P] [US3] Provider interfaces in `backend/app/providers/base.py` (`LLMProvider.complete`, `EmbeddingProvider.embed`, `LLMResult` with token usage)
- [ ] T028 [P] [US3] Deterministic `MockProvider` in `backend/app/providers/mock.py` (hash→L2-normalized 384-d vector; templated completion with token counts)
- [ ] T029 [P] [US3] Anthropic + OpenAI adapters in `backend/app/providers/anthropic.py` and `backend/app/providers/openai.py` (vendor SDK imports isolated here) + selector in `backend/app/providers/factory.py`
- [ ] T030 [P] [US3] Document + DocumentChunk models (`embedding vector(384)`) in `backend/app/models/document.py` and `backend/app/models/document_chunk.py`
- [ ] T031 [US3] Alembic migration for document + document_chunk (incl. pgvector cosine index)
- [ ] T032 [P] [US3] Document schemas in `backend/app/schemas/document.py` (DocumentCreate, DocumentOut, SearchRequest, SearchHit)
- [ ] T033 [US3] DocumentService in `backend/app/services/document_service.py` (validate non-empty, chunk text, embed via provider, persist chunks) and RetrievalService in `backend/app/services/retrieval_service.py` (cosine search scoped by org, threshold + top_k)
- [ ] T034 [US3] Documents router in `backend/app/api/v1/documents.py` (`POST /`, `GET /`, `POST /search`)
- [ ] T035 [US3] Tests: `backend/tests/test_documents.py` (ingest + empty-content 422 + cross-org isolation) and `backend/tests/test_retrieval.py` (deterministic mock retrieval respects threshold/ordering)

**Checkpoint / pause**: ingestion + semantic search deterministic and tenant-scoped.

---

## Phase 5 — LangGraph Agentic Workflow (Implementation Phase 5 · US1, US2)

- [ ] T036 [P] [US1] AgentRun model in `backend/app/models/agent_run.py` (classification, retrieval_hit, draft, confidence, outcome, latency_ms, cost, tokens) + Alembic migration
- [ ] T037 [P] [US1] Cost estimator in `backend/app/agent/cost.py` (tokens → estimated_cost_usd per provider price table)
- [ ] T038 [P] [US1] Typed `AgentState` in `backend/app/agent/state.py`
- [ ] T039 [US1] Nodes in `backend/app/agent/nodes.py`: classifier, retriever (uses RetrievalService), draft (uses LLMProvider), critic (grounding confidence 0..1), decision (≥0.7 → waiting_approval else escalated; no hits → escalate)
- [ ] T040 [US1] Assemble graph `classifier→retriever→draft→critic→decision` in `backend/app/agent/graph.py`
- [ ] T041 [US1] AgentRunService in `backend/app/services/agent_run_service.py` (create run, invoke graph, persist run + audit events agent_run_started/retrieval_completed/draft_generated, update ticket status & draft, accumulate latency/cost)
- [ ] T042 [US1] Celery app in `backend/app/workers/celery_app.py` and `run_agent(ticket_id)` task in `backend/app/workers/tasks.py`; worker service in docker-compose
- [ ] T043 [US1] Agent router in `backend/app/api/v1/agent.py` (`POST /tickets/{id}/run` → 202, enqueues task; synchronous fallback path for tests)
- [ ] T044 [US1] [US2] Tests: `backend/tests/test_agent_workflow.py` (mock provider: grounded ticket → waiting_approval with draft + cited chunks; no-context ticket → escalated; run records latency/cost; ticket_escalated audited)

**Checkpoint / pause**: full workflow runs on mock provider; escalation path verified.

---

## Phase 6 — Approvals (HITL), Metrics, Webhooks (Implementation Phase 6 · US1, US5, US6)

- [ ] T045 [US1] Approval methods in `backend/app/services/ticket_service.py` (approve → final_response required non-empty, reject, edit-draft) recording actor + state in TicketEvent + audit (response_approved/response_rejected)
- [ ] T046 [US1] Approvals router in `backend/app/api/v1/approvals.py` (`POST /tickets/{id}/approve`, `/reject`, `PATCH /tickets/{id}/edit-draft`) with state guards (409) and empty-content guard (422)
- [ ] T047 [US1] Tests: `backend/tests/test_approvals.py` (approve/edit-then-approve/reject, empty edit 422, wrong-state 409, actor recorded)
- [ ] T048 [P] [US5] Webhook + WebhookDelivery models in `backend/app/models/webhook.py` and `backend/app/models/webhook_delivery.py` + Alembic migration
- [ ] T049 [P] [US5] Webhook schemas in `backend/app/schemas/webhook.py` (WebhookConfig, WebhookDeliveryOut)
- [ ] T050 [US5] WebhookService in `backend/app/services/webhook_service.py` (HMAC-SHA256 sign, build payload, create delivery) and `deliver_webhook(delivery_id)` Celery task with max_retries=5 exponential backoff + jitter, marks success/failed, audits webhook_sent
- [ ] T051 [US5] Hook approval/escalation transitions to enqueue webhooks (ticket.approved / ticket.escalated) in ticket/agent services
- [ ] T052 [US5] Webhooks router in `backend/app/api/v1/webhooks.py` (`GET`/`PUT /webhooks` admin config, `GET /webhooks/deliveries`)
- [ ] T053 [US5] Tests: `backend/tests/test_webhooks.py` (HMAC signature correctness, delivery enqueued on approve/escalate, retry→failed marks status, no network via httpx mock)
- [ ] T054 [P] [US6] MetricsService in `backend/app/services/metrics_service.py` (aggregate SQL: totals, by-status, avg latency, avg cost, approval/escalation rate, retrieval hit rate, failed jobs)
- [ ] T055 [US6] Metrics router in `backend/app/api/v1/metrics.py` (`GET /admin/metrics`, admin-only) + schema in `backend/app/schemas/metrics.py`
- [ ] T056 [US6] Tests: `backend/tests/test_metrics.py` (deterministic metrics over seeded data; RBAC on endpoint)

**Checkpoint / pause**: approvals, signed webhooks with retries, and metrics all green.

---

## Phase 7 — Frontend Dashboard (Implementation Phase 7)

- [ ] T057 Scaffold Next.js 15 + TS app in `frontend/` (App Router, Tailwind, TanStack Query) + `frontend/package.json`, `frontend/tsconfig.json`
- [ ] T058 [P] API client + auth/token storage + shared types in `frontend/src/lib/`
- [ ] T059 [P] [US4] Login page in `frontend/src/app/login/page.tsx`
- [ ] T060 [P] [US1] Tickets list page + `useTickets` hook in `frontend/src/app/tickets/page.tsx`
- [ ] T061 [US1] Ticket detail page in `frontend/src/app/tickets/[id]/page.tsx` with `DraftPanel` (Run AI workflow button, approve/reject/edit) and `AuditTimeline` components in `frontend/src/components/`
- [ ] T062 [P] [US6] Metrics page in `frontend/src/app/metrics/page.tsx` with `MetricsCards`
- [ ] T063 [P] [US3] Documents/KB page in `frontend/src/app/documents/page.tsx` (list + add document)
- [ ] T064 Wire `frontend` service in `docker-compose.yml` (API base URL env) and verify dashboard against running backend

**Checkpoint / pause**: dashboard supports login → ticket → run → review → approve/reject/edit → audit → metrics → KB.

---

## Phase 8 — Tests hardening, CI/CD, README (Implementation Phase 8)

- [ ] T065 Add `.github/workflows/ci.yml` (services: postgres pgvector + redis; steps: ruff, mypy, pytest with LLM_PROVIDER=mock/EMBEDDING_PROVIDER=mock)
- [ ] T066 [P] Configure ruff + mypy in `backend/pyproject.toml`; fix lint/type issues across backend
- [ ] T067 [P] Ensure full suite determinism and coverage of all required areas; run `pytest -q` end to end
- [ ] T068 Write professional `README.md` (problem, solution, architecture + Mermaid diagram, stack, features, screenshot placeholders, docker-compose run, test run, env vars, technical decisions, "What this project demonstrates", "Why this matters for Applied AI / Backend roles")
- [ ] T069 Final end-to-end verification via `docker compose up` following [quickstart.md](./quickstart.md); confirm signed webhook + audit + metrics

---

## Dependencies & Execution Order

- Phase 1 (Setup) → blocks everything.
- Phase 2 (Auth/RBAC) → blocks all authenticated endpoints (Phases 3–7).
- Phase 3 (Tickets/Audit) → required by Phases 5, 6.
- Phase 4 (Documents/Retrieval) → required by Phase 5 (retriever node).
- Phase 5 (Workflow) → required by Phase 6 approvals/metrics/webhooks.
- Phase 6 → required by Phase 7 detail/metrics pages.
- Phase 7 → frontend; Phase 8 → CI/README/verification (last).
- Provider interfaces (T027–T029) may start as early as Phase 1 if desired (no DB dependency).

## Parallelization examples

- Phase 1: T002, T003, T004, T006, T007, T008 in parallel after T001.
- Phase 4: T027, T028, T029 (providers) parallel with T030/T032 (models/schemas).
- Phase 6: webhook stack (T048–T053) parallel with metrics stack (T054–T056) once approvals land.

## MVP scope

US1 + US2 (Phases 1–5 plus approvals from Phase 6) deliver the core human-in-the-loop AI loop and are
the demonstrable MVP. US3 supports US1; US4 underpins access; US5/US6 complete the enterprise story.

## Suggested implementation strategy

Deliver strictly phase by phase (matches user's plan). After each phase: summarize changes, list files
created/modified, state how to test, run the affected `pytest` modules, and pause for review. Do not
advance a phase while critical errors remain (Constitution Workflow gate).
