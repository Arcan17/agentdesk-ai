<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Bump rationale: Initial ratification of the AgentDesk AI constitution (first concrete
                version replacing the unfilled template).
Modified principles: N/A (initial definition)
Added sections:
  - Core Principles (I–VII)
  - Additional Constraints: Technology & Security Standards
  - Development Workflow & Quality Gates
  - Governance
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ reviewed (Constitution Check gate aligns)
  - .specify/templates/spec-template.md ✅ reviewed (no mandated section conflicts)
  - .specify/templates/tasks-template.md ✅ reviewed (testing/observability task types covered)
Deferred TODOs: none
-->

# AgentDesk AI Constitution

AgentDesk AI is a human-in-the-loop AI SupportOps platform. This constitution defines the
non-negotiable engineering principles for the project. It exists to keep the codebase clean,
secure, deterministic, and demonstrably production-grade for a professional portfolio.

## Core Principles

### I. Clean, Modular Architecture
The system MUST maintain strict separation of concerns across layers:
`api` (HTTP routing + I/O schemas) → `services` (business logic) → `models` (persistence) with
cross-cutting `providers` (LLM/embeddings), `agent` (LangGraph workflow), and `workers` (async
jobs). Business logic MUST NOT live in route handlers. Modules MUST depend inward only; a model
never imports a router. Rationale: a recruiter or engineer must navigate the codebase and locate
any responsibility in seconds, and layers must be independently testable.

### II. Providers Behind Interfaces (NON-NEGOTIABLE)
All LLM and embedding access MUST go through abstract interfaces (`LLMProvider`,
`EmbeddingProvider`). Concrete adapters (Anthropic, OpenAI, Mock) are selected by environment
variable. A deterministic `MockProvider` is the default and the ONLY provider exercised in tests
and CI. No business or agent code may import a vendor SDK directly. Rationale: vendor lock-in is
avoided, costs are controlled, and the system is testable without network or paid APIs.

### III. Deterministic Tests, No Paid APIs in CI (NON-NEGOTIABLE)
Tests MUST be deterministic and reproducible. There MUST be zero real LLM/embedding calls in CI;
the mock provider is forced via `LLM_PROVIDER=mock` and `EMBEDDING_PROVIDER=mock`. Every feature
ships with tests covering its happy path and key failure modes. Required coverage areas:
auth/RBAC, ticket lifecycle, document ingestion, retrieval, the LangGraph workflow (mock),
human approval, webhook HMAC signing, audit logging, and metrics. Rationale: CI must be free,
fast, and never flaky due to external services.

### IV. Security & Secret Hygiene (NON-NEGOTIABLE)
Secrets MUST NEVER be hardcoded or committed; a complete `.env.example` documents every variable.
All external inputs MUST be validated with Pydantic v2. Authentication uses JWT; authorization
uses role-based access control (admin/operator/viewer) enforced per endpoint. Errors MUST be
handled and never leak stack traces or secrets to clients. CORS is configurable; basic rate
limiting is applied where feasible. Rationale: the platform handles multi-tenant support data and
must model real enterprise security posture.

### V. Observability & Auditability
The system MUST emit structured logs. Security- and business-critical events MUST be written to
an immutable audit log (e.g. `ticket_created`, `agent_run_started`, `retrieval_completed`,
`draft_generated`, `response_approved`, `response_rejected`, `ticket_escalated`, `webhook_sent`,
`login_success`, `login_failed`). A metrics endpoint exposes ticket counts by status, agent-run
latency, estimated cost per run, approval/escalation rates, retrieval hit rate, and failed-job
counts. Rationale: support operations and AI workflows are only trustworthy when measurable and
traceable.

### VI. Multi-Tenant Isolation
Every tenant-scoped entity MUST belong to an `Organization`. Queries MUST be scoped by the
authenticated user's organization; no endpoint may return another organization's data. Webhook
configuration, documents, tickets, and audit logs are all tenant-scoped. Rationale: a SaaS
platform must guarantee tenants never see each other's data.

### VII. Human-in-the-Loop Control
AI-generated responses MUST NOT be sent to end users automatically. A drafted response enters
`waiting_approval` (or `escalated` when confidence is below threshold) and requires an operator to
approve, reject, or edit it. Every such action MUST record the actor, timestamp, and resulting
state transition. Rationale: the product's core value and differentiator is accountable human
oversight of AI output.

## Additional Constraints: Technology & Security Standards

- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic migrations.
- Data: PostgreSQL 16 with the pgvector extension as the vector store (single database).
- Async/jobs: Celery with Redis as broker/result backend; webhook retries are bounded with backoff.
- Agentic workflow: LangGraph (`classifier → retriever → draft → critic → decision`).
- Frontend: Next.js 15 with TypeScript.
- Infrastructure: Docker Compose MUST bring up the full stack locally (postgres+pgvector, redis,
  backend, worker, frontend).
- CI/CD: GitHub Actions running lint, type-check, and pytest with mock providers only.
- Webhooks MUST be signed with HMAC-SHA256 and record delivery attempts.

## Development Workflow & Quality Gates

- Spec-driven development is mandatory: specify → clarify → plan → tasks → analyze → implement.
- Implementation proceeds in phases; a phase MUST NOT advance while critical errors remain.
- Each phase closes with: a summary of changes, the list of files created/modified, how to test
  it, and a passing test run for the affected modules.
- New behavior requires accompanying deterministic tests (Principle III).
- Code MUST be reasonably typed and endpoints documented (FastAPI/OpenAPI).
- No change may introduce a direct vendor SDK import outside the `providers` layer (Principle II)
  or a hardcoded secret (Principle IV).

## Governance

This constitution supersedes ad-hoc practices for AgentDesk AI. Amendments MUST be made by editing
this file, accompanied by a Sync Impact Report and a semantic version bump:
- MAJOR: removal or backward-incompatible redefinition of a principle.
- MINOR: a new principle or materially expanded guidance.
- PATCH: clarifications and wording fixes.

All implementation work and reviews MUST verify compliance with these principles. Any deviation
MUST be justified in writing within the relevant spec or plan. Runtime development guidance for AI
agents lives in the project `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-06-02 | **Last Amended**: 2026-06-02
