"""Model package — import all models so SQLAlchemy metadata and Alembic see them."""
from app.models.agent_run import AgentRun, AgentRunOutcome, AgentRunStatus
from app.models.audit_log import AuditEvent, AuditLog
from app.models.document import Document, DocumentSource
from app.models.document_chunk import DocumentChunk
from app.models.organization import Organization
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.ticket_event import TicketEvent
from app.models.user import Role, User

__all__ = [
    "Organization",
    "User",
    "Role",
    "Ticket",
    "TicketStatus",
    "TicketPriority",
    "TicketEvent",
    "AuditLog",
    "AuditEvent",
    "Document",
    "DocumentSource",
    "DocumentChunk",
    "AgentRun",
    "AgentRunStatus",
    "AgentRunOutcome",
]
