export type Role = "admin" | "operator" | "viewer";

export type TicketStatus =
  | "new"
  | "triaged"
  | "draft_ready"
  | "waiting_approval"
  | "approved"
  | "rejected"
  | "escalated"
  | "closed";

export type TicketPriority = "low" | "medium" | "high" | "urgent";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Ticket {
  id: string;
  organization_id: string;
  title: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  suggested_type: string | null;
  suggested_priority: TicketPriority | null;
  draft_response: string | null;
  final_response: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketEvent {
  id: string;
  ticket_id: string;
  event_type: string;
  from_status: TicketStatus | null;
  to_status: TicketStatus | null;
  actor_user_id: string | null;
  message: string | null;
  created_at: string;
}

export interface AgentRun {
  id: string;
  ticket_id: string;
  status: string;
  outcome: string | null;
  confidence: number | null;
  retrieval_hit: boolean;
  draft: string | null;
  latency_ms: number | null;
  estimated_cost_usd: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface DocumentItem {
  id: string;
  organization_id: string;
  title: string;
  source_type: "manual" | "upload";
  created_at: string;
  chunk_count: number | null;
}

export interface Metrics {
  total_tickets: number;
  tickets_by_status: Record<string, number>;
  avg_agent_latency_ms: number;
  avg_estimated_cost_usd: number;
  approval_rate: number;
  escalation_rate: number;
  retrieval_hit_rate: number;
  failed_jobs: number;
}
