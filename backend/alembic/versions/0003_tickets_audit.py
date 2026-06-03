"""tickets, ticket_events, audit_logs

Revision ID: 0003_tickets_audit
Revises: 0002_org_user
Create Date: 2026-06-02
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_tickets_audit"
down_revision: str | None = "0002_org_user"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ticket_status = sa.Enum(
    "new", "triaged", "draft_ready", "waiting_approval",
    "approved", "rejected", "escalated", "closed",
    name="ticket_status",
)
ticket_priority = sa.Enum("low", "medium", "high", "urgent", name="ticket_priority")
audit_event = sa.Enum(
    "ticket_created", "agent_run_started", "retrieval_completed", "draft_generated",
    "response_approved", "response_rejected", "ticket_escalated", "webhook_sent",
    "login_success", "login_failed",
    name="audit_event",
)


def upgrade() -> None:
    bind = op.get_bind()
    ticket_status.create(bind, checkfirst=True)
    ticket_priority.create(bind, checkfirst=True)
    audit_event.create(bind, checkfirst=True)

    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", ticket_priority, nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("suggested_type", sa.String(length=100), nullable=True),
        sa.Column("suggested_priority", ticket_priority, nullable=True),
        sa.Column("draft_response", sa.Text(), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tickets_organization_id", "tickets", ["organization_id"])
    op.create_index("ix_tickets_org_status", "tickets", ["organization_id", "status"])

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_status", ticket_status, nullable=True),
        sa.Column("to_status", ticket_status, nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])
    op.create_index("ix_ticket_events_organization_id", "ticket_events", ["organization_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event", audit_event, nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("meta", sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_event", "audit_logs", ["event"])
    op.create_index("ix_audit_logs_org_created", "audit_logs", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ticket_events")
    op.drop_table("tickets")
    bind = op.get_bind()
    audit_event.drop(bind, checkfirst=True)
    ticket_priority.drop(bind, checkfirst=True)
    ticket_status.drop(bind, checkfirst=True)
