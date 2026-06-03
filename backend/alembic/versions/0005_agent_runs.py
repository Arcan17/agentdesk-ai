"""agent_runs

Revision ID: 0005_agent_runs
Revises: 0004_documents
Create Date: 2026-06-02
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_agent_runs"
down_revision: str | None = "0004_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

run_status = sa.Enum("running", "completed", "failed", name="agent_run_status")
run_outcome = sa.Enum("waiting_approval", "escalated", name="agent_run_outcome")
json_type = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    run_status.create(bind, checkfirst=True)
    run_outcome.create(bind, checkfirst=True)

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("classification", json_type, nullable=True),
        sa.Column("retrieved_chunk_ids", json_type, nullable=True),
        sa.Column("retrieval_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("draft", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("outcome", run_outcome, nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_runs_ticket_id", "agent_runs", ["ticket_id"])
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])
    op.create_index("ix_agent_runs_org_created", "agent_runs", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    bind = op.get_bind()
    run_outcome.drop(bind, checkfirst=True)
    run_status.drop(bind, checkfirst=True)
