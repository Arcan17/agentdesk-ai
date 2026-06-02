# Implementation Plan: AgentDesk AI — Human-in-the-loop AI SupportOps Platform

**Branch**: `001-agentdesk-mvp` | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-agentdesk-mvp/spec.md`

## Summary

AgentDesk AI is a multi-tenant SaaS where support staff manage tickets assisted by an AI workflow
grounded in an organization's knowledge base (RAG). The AI never auto-answers: every drafted reply is
approved, edited, or rejected by a human, and low-confidence cases are escalated. The system records
audit events, exposes operational/AI metrics, and notifies external systems via HMAC-signed webhooks
with bounded retries.

**Technical approach**: An async FastAPI backend (SQLAlchemy 2.0 async, Pydantic v2) over PostgreSQL
16 + pgvector (single store for relational data and embeddings). The agentic workflow is a LangGraph
graph (`classifier → retriever → draft → critic → decision`) executed as a Celery task on Redis;
webhook delivery is a separate Celery task with bounded exponential-backoff retries. LLM and embedding
access sit behind `LLMProvider` / `EmbeddingProvider` interfaces with a deterministic `MockProvider`
default (Anthropic/OpenAI adapters optional, opt-in). A Next.js 15 + TypeScript dashboard consumes the
REST API. Everything runs via Docker Compose; CI runs ruff/mypy/pytest with mock providers only.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript / Node 20+ (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async) + asyncpg, Pydantic v2 + pydantic-settings,
Alembic, LangGraph, Celery, Redis client, python-jose (JWT), passlib[bcrypt], httpx, structlog,
slowapi (rate limiting); Next.js 15, React, TypeScript, TanStack Query, Tailwind CSS.

**Storage**: PostgreSQL 16 with the `pgvector` extension (relational + vector embeddings in one DB).
Redis as Celery broker/result backend.

**Testing**: pytest + pytest-asyncio; httpx ASGI transport for API tests; deterministic `MockProvider`
forced via `LLM_PROVIDER=mock` / `EMBEDDING_PROVIDER=mock`. No real LLM/embedding calls in CI.

**Target Platform**: Linux containers via Docker Compose (postgres, redis, backend, worker, frontend).

**Project Type**: Web application (separate `backend/` and `frontend/`).

**Performance Goals**: Interactive API endpoints responsive for a single-org demo workload; AI runs are
asynchronous (non-blocking) so request latency is independent of model latency. Not a high-throughput
benchmark — correctness, determinism, and clean architecture are prioritized for a portfolio.

**Constraints**: Zero real paid-API calls in tests/CI; no hardcoded secrets; multi-tenant isolation on
every query; full stack must boot from `docker compose up`; AI replies never auto-delivered.

**Scale/Scope**: Portfolio MVP — tens of organizations, thousands of tickets/documents. ~9 REST router
groups, ~10 persisted entities, one LangGraph workflow, two Celery task types, ~7 dashboard pages.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Plan compliance |
|-----------|-----------------|
| I. Clean, Modular Architecture | Layered `api → services → models`; cross-cutting `providers`, `agent`, `workers`. Routers hold no business logic. ✅ |
| II. Providers Behind Interfaces | `providers/base.py` interfaces; Mock default; vendor SDKs only inside their adapter modules. ✅ |
| III. Deterministic Tests, No Paid APIs | MockProvider deterministic (hash→vector, templated completion); CI forces mock; coverage spans all required areas. ✅ |
| IV. Security & Secret Hygiene | pydantic-settings + `.env.example`; JWT access+refresh; RBAC dependency; input validation; configurable CORS; slowapi rate limit. ✅ |
| V. Observability & Auditability | structlog structured logs; `AuditLog` for all listed events; `/admin/metrics` endpoint. ✅ |
| VI. Multi-Tenant Isolation | `organization_id` on all tenant entities; queries scoped via auth dependency; cross-org access denied. ✅ |
| VII. Human-in-the-Loop | Decision node sets `waiting_approval`/`escalated`; approve/reject/edit endpoints required before finalization. ✅ |

**Result**: PASS — no violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-agentdesk-mvp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (openapi.yaml, webhook.md)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                 # app factory, CORS, middleware, exception handlers, health
│   ├── core/                   # config.py, security.py (JWT/hashing), logging.py, ratelimit.py, deps.py
│   ├── db/                     # engine.py (async), session.py, base.py
│   ├── models/                 # organization, user, ticket, ticket_event, document,
│   │                           #   document_chunk, agent_run, audit_log, webhook, webhook_delivery
│   ├── schemas/                # Pydantic v2 request/response models per domain
│   ├── api/v1/                 # routers: auth, organizations, users, tickets, documents,
│   │                           #   agent, approvals, metrics, webhooks  + router.py aggregator
│   ├── services/               # auth, ticket, document, retrieval, agent_run, metrics, webhook, audit
│   ├── providers/              # base.py (interfaces), mock.py, anthropic.py, openai.py, factory.py
│   ├── agent/                  # state.py, nodes.py, graph.py, cost.py
│   ├── workers/                # celery_app.py, tasks.py (run_agent, deliver_webhook)
│   └── rbac.py                 # require_role(...) dependency + Role enum
├── alembic/                    # env.py + versions/ (incl. CREATE EXTENSION vector)
├── tests/                      # conftest.py + test_auth, test_rbac, test_tickets, test_documents,
│                               #   test_retrieval, test_agent_workflow, test_approvals,
│                               #   test_webhooks, test_audit, test_metrics
├── pyproject.toml
├── alembic.ini
└── Dockerfile

frontend/
├── src/
│   ├── app/                    # Next.js 15 App Router: login, tickets, tickets/[id], metrics, documents
│   ├── components/             # TicketList, TicketDetail, DraftPanel, AuditTimeline, MetricsCards, DocList
│   ├── lib/                    # api client, auth (token storage), types
│   └── hooks/                  # useTickets, useTicket, useMetrics, useDocuments
├── package.json
├── tsconfig.json
└── Dockerfile

docker-compose.yml              # postgres(pgvector), redis, backend, worker, frontend
.env.example
.github/workflows/ci.yml
README.md
```

**Structure Decision**: Web application (Option 2). Backend and frontend are separate top-level
directories with independent Dockerfiles, composed by `docker-compose.yml`. Backend internal layout
follows the constitution's layered architecture (Principle I).

## Complexity Tracking

> No constitution violations — section intentionally empty.
