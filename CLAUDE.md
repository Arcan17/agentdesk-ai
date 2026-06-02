<!-- SPECKIT START -->
Active feature: **001-agentdesk-mvp** (AgentDesk AI — Human-in-the-loop AI SupportOps Platform).

For technologies, project structure, data model, and decisions, read:
- Plan: `specs/001-agentdesk-mvp/plan.md`
- Spec: `specs/001-agentdesk-mvp/spec.md`
- Data model: `specs/001-agentdesk-mvp/data-model.md`
- Contracts: `specs/001-agentdesk-mvp/contracts/`
- Constitution: `.specify/memory/constitution.md`

Stack: Python 3.11 / FastAPI / SQLAlchemy 2.0 async / Pydantic v2 / PostgreSQL 16 + pgvector /
Celery + Redis / LangGraph / Next.js 15 + TS. LLM & embedding providers are behind interfaces with a
deterministic Mock default; never call real LLMs in tests/CI.
<!-- SPECKIT END -->
