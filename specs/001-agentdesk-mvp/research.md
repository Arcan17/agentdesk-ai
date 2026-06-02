# Phase 0 Research: AgentDesk AI

All Technical Context items are resolved (no NEEDS CLARIFICATION remain). This document records the
key decisions, their rationale, and rejected alternatives.

## 1. Vector store: pgvector vs. external (Chroma)

- **Decision**: PostgreSQL 16 + `pgvector` extension; embeddings stored on `document_chunk.embedding`
  (`vector(N)`), similarity via cosine distance (`<=>`) with an IVFFlat/HNSW-capable column.
- **Rationale**: Single datastore (relational + vector) simplifies ops, transactions, and multi-tenant
  scoping (the `organization_id` filter and the vector search live in one query). More "enterprise"
  and impressive for a backend portfolio. Docker image `pgvector/pgvector:pg16`.
- **Alternatives rejected**: ChromaDB (extra service/container, separate consistency story, weaker
  tenant-scoped joins). Kept as a documented fallback only.

## 2. Embedding dimension & mock determinism

- **Decision**: Fixed embedding dimension `EMBEDDING_DIM=384` for all providers. `MockProvider.embed`
  produces a deterministic unit vector from a hash of the text (token-frequency hashing → L2-normalized
  float vector), so equal text → equal vector and similar text → higher cosine similarity.
- **Rationale**: Determinism makes retrieval tests stable and threshold (0.5) calibratable without any
  network. Real Anthropic/OpenAI adapters project/truncate to the same dimension (documented).
- **Alternatives rejected**: Random embeddings (non-reproducible); per-provider variable dimensions
  (would require schema/migration changes when switching providers).

## 3. LLM/embedding provider abstraction

- **Decision**: `providers/base.py` defines `LLMProvider.complete(prompt, **opts) -> LLMResult` and
  `EmbeddingProvider.embed(texts) -> list[vector]`. `factory.py` selects implementation from
  `LLM_PROVIDER` / `EMBEDDING_PROVIDER` env (`mock` | `anthropic` | `openai`). `LLMResult` carries text
  + token usage so cost can be estimated. Vendor SDKs imported only inside `anthropic.py` / `openai.py`.
- **Rationale**: Satisfies Constitution Principle II; enables CI with `mock`; no vendor lock-in.
- **Alternatives rejected**: Direct SDK calls in services (violates II, untestable in CI).

## 4. Agentic workflow runtime (LangGraph)

- **Decision**: A `StateGraph` with nodes `classifier → retriever → draft → critic → decision`. State is
  a typed dict (`AgentState`) holding ticket fields, classification, retrieved chunks, draft, critic
  confidence, decision, and accumulated latency/cost. The graph is invoked inside a Celery task; each
  node appends an audit event and updates the `AgentRun` record.
- **Rationale**: LangGraph models the explicit node/edge flow the spec describes and is the named stack.
  Running inside Celery keeps the HTTP request non-blocking (FR-013).
- **Alternatives rejected**: Hand-rolled function pipeline (loses the graph/observability story);
  running synchronously in the request (blocks, violates FR-013).

## 5. Critic / confidence scoring

- **Decision**: The critic node computes a grounding confidence in [0,1] from overlap between the draft
  and retrieved context plus retrieval similarity (deterministic with the mock provider). `decision`:
  `confidence >= CONFIDENCE_THRESHOLD (0.7)` → `waiting_approval`; else `escalated`. If retrieval
  returns no chunks above `SIMILARITY_THRESHOLD (0.5)`, confidence is forced low → escalation.
- **Rationale**: Deterministic, testable, and faithful to FR-011/FR-012; guarantees the "no relevant
  context → escalate" edge case (SC-004).

## 6. Async jobs: Celery + Redis

- **Decision**: Celery app with Redis broker/result backend. Two task types: `run_agent(ticket_id)` and
  `deliver_webhook(delivery_id)`. Webhook retries: `max_retries=5`, exponential backoff base 2s with
  jitter (2,4,8,16,32s ±jitter); on exhaustion mark delivery `failed`.
- **Rationale**: Named stack; bounded retries satisfy FR-023; failed deliveries feed failed-job metric.
- **Alternatives rejected**: FastAPI BackgroundTasks (no retries/durability/observability);
  RQ/Dramatiq (Celery is the specified stack).

## 7. Auth & RBAC

- **Decision**: JWT via python-jose. Access token ~30 min, refresh token ~7 days, `/auth/refresh`
  endpoint. Passwords hashed with bcrypt (passlib). RBAC via a FastAPI dependency `require_role(*roles)`
  reading the current user; tenant scope enforced by always filtering on the user's `organization_id`.
- **Rationale**: Matches clarified FR-002/FR-003; standard, well-understood, testable.
- **Alternatives rejected**: Session cookies (less typical for a SPA+API portfolio); single long-lived
  token (rejected during clarification).

## 8. Webhook signing

- **Decision**: HMAC-SHA256 over the raw JSON body using the org's webhook secret; signature sent in an
  `X-AgentDesk-Signature: sha256=<hex>` header plus an `X-AgentDesk-Timestamp`. Recipients recompute to
  verify (FR-022). Tests assert signature correctness without any network using httpx mocking.

## 9. Observability

- **Decision**: structlog JSON logs with request id; `AuditLog` rows for all FR-017 events; metrics
  computed on read in `metrics_service` via aggregate SQL over tickets, agent_runs, audit_logs, and
  webhook_deliveries.
- **Rationale**: Simple, dependency-light, deterministic for tests. (Prometheus export is a documented
  future extension, out of MVP scope.)

## 10. Frontend data layer

- **Decision**: Next.js 15 App Router + TanStack Query against the REST API; JWT stored in memory with
  refresh; Tailwind for a clean professional look.
- **Rationale**: Modern, recruiter-recognizable stack; keeps the dashboard thin over the documented API.

## Resolved unknowns summary

| Item | Resolution |
|------|------------|
| Vector store | pgvector (single DB) |
| Embedding dim | 384, fixed across providers |
| Mock determinism | hash→normalized vector; templated completions |
| Confidence threshold | 0.7 (env-configurable) |
| Similarity threshold | 0.5 (env-configurable) |
| Webhook retries | 5, exponential backoff + jitter |
| Token model | access ~30m + refresh ~7d |
