# Feature Specification: AgentDesk AI — Human-in-the-loop AI SupportOps Platform

**Feature Branch**: `001-agentdesk-mvp`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "AgentDesk AI — plataforma SaaS multi-tenant donde una empresa gestiona tickets de soporte usando agentes IA con RAG, aprobaciones humanas, métricas, auditoría y webhooks."

## Clarifications

### Session 2026-06-02

- Q: Default confidence threshold for waiting-for-approval vs escalated? → A: 0.7 (configurable)
- Q: Default semantic-search similarity threshold (cosine 0..1)? → A: 0.5 (configurable)
- Q: Webhook delivery retry policy? → A: 5 retries, exponential backoff with jitter
- Q: JWT token model? → A: Short-lived access token (~30 min) + refresh token (~7 days)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator triages a ticket with AI assistance and approves a grounded reply (Priority: P1)

A support operator opens an incoming ticket, runs the AI workflow, reviews the AI-drafted reply
together with the knowledge-base context it used, and either approves, edits, or rejects it before
anything is considered final. The drafted reply is never delivered automatically — a human always
decides.

**Why this priority**: This is the core value of the product — accountable, human-supervised AI
support. Without it, the platform is just a ticketing tool. It is the smallest slice that
demonstrates the full differentiator end-to-end.

**Independent Test**: Seed an organization with one knowledge-base document and one ticket. Run the
AI workflow on the ticket; confirm a draft is produced with cited context and the ticket moves to
"waiting for approval". Approve the draft; confirm the ticket becomes "approved" and the action is
attributed to the operator. This delivers value on its own.

**Acceptance Scenarios**:

1. **Given** a ticket in state "new" and a populated knowledge base, **When** an operator runs the
   AI workflow, **Then** the system produces a suggested reply with the supporting context and moves
   the ticket to "waiting for approval".
2. **Given** a ticket awaiting approval, **When** the operator approves the draft, **Then** the
   ticket becomes "approved" and the system records who approved it and when.
3. **Given** a ticket awaiting approval, **When** the operator edits the draft and then approves,
   **Then** the edited content is stored as the final reply and the edit and approval are both
   attributed to the operator.
4. **Given** a ticket awaiting approval, **When** the operator rejects the draft, **Then** the ticket
   becomes "rejected" and the rejection is recorded with the operator's identity.

---

### User Story 2 - Low-confidence cases are escalated, not auto-answered (Priority: P1)

When the AI cannot produce a sufficiently grounded answer (low confidence), the case is escalated to
a human queue instead of presenting a risky draft as if it were trustworthy.

**Why this priority**: Safe failure is as important as success for an AI support product; it prevents
the system from confidently delivering wrong answers and reinforces the human-in-the-loop guarantee.

**Independent Test**: Run the workflow on a ticket whose topic has no relevant knowledge-base content;
confirm the ticket is marked "escalated" and an escalation event is recorded.

**Acceptance Scenarios**:

1. **Given** a ticket whose question has no relevant supporting context, **When** the AI workflow
   runs, **Then** the ticket is marked "escalated" rather than "waiting for approval".
2. **Given** an escalated ticket, **When** an operator views it, **Then** they can see why it was
   escalated (low confidence / insufficient grounding).

---

### User Story 3 - Admin manages the knowledge base that grounds AI replies (Priority: P2)

An administrator adds internal documents (uploaded or entered directly) to the organization's
knowledge base. The system makes their content searchable so the AI can ground its drafts in the
organization's own material.

**Why this priority**: The quality of grounded answers depends entirely on the knowledge base; it is
a prerequisite for Story 1 to produce useful drafts, but the approval loop can be demonstrated with
minimal seed data, so it ranks just below P1.

**Independent Test**: Add a document, then run a semantic search for a phrase contained in it;
confirm the relevant passage is returned above the configured similarity threshold.

**Acceptance Scenarios**:

1. **Given** an admin with a document, **When** they add it to the knowledge base, **Then** its
   content becomes searchable within their organization.
2. **Given** a populated knowledge base, **When** a semantic search is performed, **Then** only
   passages at or above the configured similarity threshold are returned, ranked by relevance.
3. **Given** documents belonging to another organization, **When** a user searches, **Then** results
   from other organizations are never returned.

---

### User Story 4 - Roles control who can do what (Priority: P2)

The platform distinguishes administrators, operators, and viewers. Each role can perform only the
actions appropriate to it, and every login attempt is recorded.

**Why this priority**: Multi-tenant SaaS credibility requires real access control, but it supports
rather than constitutes the core AI loop.

**Acceptance Scenarios**:

1. **Given** a viewer, **When** they attempt to approve a draft, **Then** the action is denied.
2. **Given** an operator, **When** they approve a draft, **Then** the action succeeds.
3. **Given** any user, **When** they attempt to access another organization's tickets or documents,
   **Then** the request is denied.
4. **Given** a login attempt, **When** it succeeds or fails, **Then** the outcome is recorded in the
   audit log.

---

### User Story 5 - Downstream systems are notified of resolved and escalated cases (Priority: P3)

When a ticket reaches "approved" or "escalated", the organization's configured external endpoint is
notified with a verifiable, signed message, and delivery attempts are tracked.

**Why this priority**: Integration is valuable for a real enterprise system and for the portfolio
narrative, but the platform is usable without it.

**Acceptance Scenarios**:

1. **Given** an organization with a configured notification endpoint, **When** a ticket becomes
   "approved" or "escalated", **Then** a signed notification is sent and the attempt is recorded.
2. **Given** a notification that fails to deliver, **When** the failure occurs, **Then** delivery is
   retried a bounded number of times and each attempt is recorded.
3. **Given** a received notification, **When** the recipient verifies its signature, **Then** they
   can confirm it genuinely originated from the platform and was not tampered with.

---

### User Story 6 - Managers observe operational and AI health via metrics (Priority: P3)

An administrator views aggregate metrics about ticket volume, AI workflow performance, approval and
escalation behavior, and job health.

**Why this priority**: Observability rounds out the "real system" story and is expected in the
portfolio, but it depends on the other stories generating data first.

**Acceptance Scenarios**:

1. **Given** activity in the system, **When** an admin opens the metrics view, **Then** they see
   total tickets, tickets by status, average AI run latency, average estimated cost per run, approval
   rate, escalation rate, retrieval hit rate, and failed-job count.
2. **Given** a viewer or operator, **When** they request admin metrics, **Then** access is governed
   by role.

---

### Edge Cases

- A ticket with no matching knowledge-base content → escalated with a recorded reason.
- The AI workflow is run twice on the same ticket → the latest run's draft and run record are
  retained; prior runs remain visible in history.
- An operator edits a draft to empty content → the edit is rejected (a final reply must be non-empty).
- A notification endpoint is unreachable for all retries → the ticket state is unaffected; the
  exhausted delivery is recorded as failed and counts toward failed-job metrics.
- A user's token is missing, expired, or for another organization → request denied without leaking
  whether the target resource exists.
- A document is added with empty or whitespace-only content → rejected with a clear validation error.
- Concurrent approval and rejection of the same ticket → the first action wins; the second sees the
  already-resolved state and is rejected.

## Requirements *(mandatory)*

### Functional Requirements

**Tenancy, Identity & Access**

- **FR-001**: System MUST scope every ticket, document, knowledge-base entry, notification config, and
  audit record to a single organization, and MUST never expose one organization's data to another.
- **FR-002**: System MUST authenticate users with a credential-based login that issues a
  short-lived access token (default ~30 minutes) plus a longer-lived refresh token (default ~7 days),
  with a token-refresh capability. Token lifetimes MUST be configurable.
- **FR-003**: System MUST support three roles — administrator, operator, viewer — and MUST enforce
  per-action authorization (e.g., only operators/admins approve, reject, or edit drafts; only admins
  manage users, notification config, and view admin metrics; viewers are read-only).
- **FR-004**: System MUST record every login attempt outcome (success and failure).

**Knowledge Base**

- **FR-005**: Authorized users MUST be able to add documents to their organization's knowledge base,
  either by uploading a file or by entering content directly.
- **FR-006**: System MUST divide document content into retrievable passages and make them searchable
  by meaning, not just keywords.
- **FR-007**: System MUST provide semantic search that returns only passages meeting or exceeding a
  configurable similarity threshold (default cosine similarity 0.5), ranked by relevance, scoped to the
  caller's organization.

**Tickets**

- **FR-008**: Authorized users MUST be able to create a ticket with a title, description, and priority,
  and MUST be able to list tickets and view a single ticket's detail.
- **FR-009**: System MUST track ticket state through: new, triaged, draft ready, waiting for approval,
  approved, rejected, escalated, and closed.
- **FR-010**: System MUST maintain a chronological history of state changes and significant actions for
  each ticket, including who performed each action.

**AI Workflow**

- **FR-011**: System MUST provide a workflow that, for a given ticket, classifies it (type and suggested
  priority), retrieves relevant knowledge-base context, drafts a suggested reply, evaluates how well the
  draft is grounded in the retrieved context, and decides an outcome.
- **FR-012**: System MUST route the outcome by confidence: at or above a configurable threshold
  (default 0.7) the ticket goes to "waiting for approval"; below it, the ticket is "escalated".
- **FR-013**: System MUST run the AI workflow without blocking the requester (asynchronously) and MUST
  record, per run, its duration and an estimated processing cost.
- **FR-014**: System MUST keep AI/embedding capability behind an interchangeable interface and MUST
  default to a deterministic, offline capability so the product runs and is tested without external
  paid services.

**Human-in-the-Loop**

- **FR-015**: System MUST NOT deliver or finalize an AI-drafted reply automatically; a human MUST
  approve, edit-then-approve, or reject it.
- **FR-016**: System MUST record, for every approval, rejection, and edit, the acting user, the
  timestamp, and the resulting state.

**Audit & Observability**

- **FR-017**: System MUST write an immutable audit entry for each significant event: ticket created,
  AI run started, retrieval completed, draft generated, response approved, response rejected, ticket
  escalated, notification sent, login success, and login failure.
- **FR-018**: System MUST expose aggregate metrics: total tickets, tickets by status, average AI run
  latency, average estimated cost per run, approval rate, escalation rate, retrieval hit rate, and
  failed-job count.
- **FR-019**: System MUST emit structured operational logs and MUST NOT expose secrets or internal
  stack traces to clients.

**Notifications / Webhooks**

- **FR-020**: Administrators MUST be able to configure a notification endpoint per organization.
- **FR-021**: System MUST send a notification when a ticket transitions to "approved" or "escalated".
- **FR-022**: System MUST sign each notification so recipients can verify authenticity and integrity.
- **FR-023**: System MUST record each delivery attempt and MUST retry failed deliveries a bounded
  number of times (default 5 attempts, exponential backoff with jitter) before marking the delivery
  failed; the retry limit and backoff MUST be configurable.

**Dashboard**

- **FR-024**: System MUST provide a web dashboard allowing users to log in, view the ticket list and a
  ticket's detail, trigger the AI workflow, view the generated draft, approve/reject/edit it, view a
  ticket's audit history, view metrics, and view/manage the knowledge base — each gated by role.

**Security & Configuration**

- **FR-025**: System MUST NOT contain hardcoded secrets and MUST document all configuration via an
  example environment file; cross-origin access MUST be configurable; basic request rate limiting MUST
  be applied where feasible; all external inputs MUST be validated.

### Key Entities *(include if feature involves data)*

- **Organization**: A tenant. Owns users, documents, tickets, notification configuration, and audit
  records. The isolation boundary for all data.
- **User**: A member of one organization with a role (administrator, operator, viewer) and login
  credentials.
- **Document**: Source material added to an organization's knowledge base; holds original content and
  metadata; decomposed into passages.
- **Knowledge Passage (Chunk)**: A retrievable segment of a document with a semantic representation used
  for similarity search.
- **Ticket**: A support case with title, description, priority, current state, and links to its history,
  AI runs, and final reply.
- **Ticket Event / History Entry**: A timestamped record of a state change or action on a ticket,
  attributed to a user or to the AI workflow.
- **AI Run**: A record of one execution of the workflow for a ticket, capturing classification,
  retrieved context, draft, grounding/confidence assessment, outcome, duration, and estimated cost.
- **Audit Log Entry**: An immutable record of a significant security or business event, scoped to an
  organization.
- **Notification Configuration**: An organization's external endpoint and signing secret for outbound
  notifications.
- **Notification Delivery**: A record of one attempt to deliver a notification, including outcome and
  attempt count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can take an incoming ticket from "new" to an approved, grounded reply in
  under 3 minutes of interaction (excluding background processing).
- **SC-002**: 100% of AI-drafted replies require an explicit human decision before they are finalized;
  zero replies are auto-delivered.
- **SC-003**: For a question whose answer exists in the knowledge base, the supporting passage appears
  in the AI's retrieved context in at least 90% of cases.
- **SC-004**: Tickets without relevant knowledge-base content are escalated rather than presented as
  confident drafts in 100% of cases.
- **SC-005**: 100% of the listed significant events produce a corresponding audit entry attributable to
  an actor (user or AI workflow).
- **SC-006**: 100% of cross-organization data access attempts are denied.
- **SC-007**: Every outbound notification can be verified as authentic by its recipient, and 100% of
  delivery attempts (success or final failure) are recorded.
- **SC-008**: The entire system can be started locally and its automated test suite can be run to
  completion with no external paid services and no real AI calls.
- **SC-009**: A first-time reader can understand the problem, solution, and architecture from the
  project documentation in under 2 minutes.

## Assumptions

- Document content is primarily text or text-extractable; rich binary parsing (e.g., scanned images,
  complex PDFs) is out of scope for the MVP.
- A single, deterministic offline AI/embedding capability is sufficient to demonstrate and test the
  full workflow; real providers are optional, opt-in, and never required to run or test the system.
- Default similarity (0.5) and confidence (0.7) thresholds are configuration values with sensible
  defaults, settled during clarification and overridable via configuration.
- Estimated processing cost is a computed approximation for observability, not a billing-grade figure.
- The dashboard targets desktop browsers; mobile-optimized layouts are out of scope for the MVP.
- A single shared knowledge base per organization is sufficient; per-team or per-product knowledge
  partitions are out of scope for the MVP.
- Notification delivery targets HTTP-style endpoints provided by the organization.
- End customers do not log in; the platform's direct users are the organization's support staff
  (admin/operator/viewer). How approved replies reach end customers is out of scope (handled by
  downstream systems via notifications).
