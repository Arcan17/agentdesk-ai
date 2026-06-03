import { clearTokens, getAccessToken } from "./auth";
import type {
  AgentRun,
  DocumentItem,
  Metrics,
  Ticket,
  TicketEvent,
  TokenPair,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (auth) {
    const token = getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (resp.status === 401) {
    clearTokens();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  // auth
  register: (organization_name: string, email: string, password: string) =>
    request<TokenPair>(
      "/auth/register",
      { method: "POST", body: JSON.stringify({ organization_name, email, password }) },
      false,
    ),
  login: (email: string, password: string) =>
    request<TokenPair>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    ),

  // tickets
  listTickets: (status?: string) =>
    request<Ticket[]>(`/tickets${status ? `?status=${status}` : ""}`),
  getTicket: (id: string) => request<Ticket>(`/tickets/${id}`),
  createTicket: (title: string, description: string, priority: string) =>
    request<Ticket>("/tickets", {
      method: "POST",
      body: JSON.stringify({ title, description, priority }),
    }),
  ticketEvents: (id: string) => request<TicketEvent[]>(`/tickets/${id}/events`),

  // agent + HITL
  runWorkflow: (id: string) =>
    request<AgentRun>(`/tickets/${id}/run`, { method: "POST" }),
  approve: (id: string, edited_response?: string) =>
    request<Ticket>(`/tickets/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ edited_response: edited_response ?? null }),
    }),
  reject: (id: string, reason?: string) =>
    request<Ticket>(`/tickets/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null }),
    }),
  editDraft: (id: string, content: string) =>
    request<Ticket>(`/tickets/${id}/edit-draft`, {
      method: "PATCH",
      body: JSON.stringify({ content }),
    }),

  // documents
  listDocuments: () => request<DocumentItem[]>("/documents"),
  createDocument: (title: string, content: string) =>
    request<DocumentItem>("/documents", {
      method: "POST",
      body: JSON.stringify({ title, content }),
    }),

  // metrics
  metrics: () => request<Metrics>("/admin/metrics"),
};
