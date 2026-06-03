"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DraftPanel } from "@/components/DraftPanel";
import { AuditTimeline } from "@/components/AuditTimeline";
import { StatusBadge } from "@/components/StatusBadge";

export default function TicketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const ticketQ = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api.getTicket(id),
  });
  const eventsQ = useQuery({
    queryKey: ["events", id],
    queryFn: () => api.ticketEvents(id),
  });

  if (ticketQ.isLoading) return <p className="text-slate-500">Loading…</p>;
  if (ticketQ.isError || !ticketQ.data)
    return <p className="text-rose-600">Ticket not found.</p>;

  const ticket = ticketQ.data;

  return (
    <div>
      <Link href="/tickets" className="text-sm text-slate-500 hover:text-slate-900">
        ← Back to tickets
      </Link>

      <div className="mt-2 flex items-center justify-between">
        <h1 className="text-xl font-semibold">{ticket.title}</h1>
        <StatusBadge status={ticket.status} />
      </div>
      <p className="mt-1 whitespace-pre-wrap text-slate-600">{ticket.description}</p>
      <p className="mt-2 text-sm text-slate-500">
        Priority: {ticket.priority}
        {ticket.suggested_type && ` · AI type: ${ticket.suggested_type}`}
      </p>

      <div className="mt-6 grid gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2 rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-lg font-semibold">AI response</h2>
          <DraftPanel ticket={ticket} />
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-lg font-semibold">History</h2>
          <AuditTimeline events={eventsQ.data ?? []} />
        </section>
      </div>
    </div>
  );
}
