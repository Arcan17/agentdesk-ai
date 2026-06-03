"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import type { Ticket } from "@/lib/types";

export default function TicketsPage() {
  const qc = useQueryClient();
  const { data: tickets, isLoading } = useQuery({
    queryKey: ["tickets"],
    queryFn: () => api.listTickets(),
  });

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");

  const create = useMutation({
    mutationFn: () => api.createTicket(title, description, priority),
    onSuccess: () => {
      setTitle("");
      setDescription("");
      qc.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  return (
    <div className="grid gap-8 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <h1 className="mb-4 text-xl font-semibold">Tickets</h1>
        {isLoading ? (
          <p className="text-slate-500">Loading…</p>
        ) : tickets && tickets.length > 0 ? (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {tickets.map((t: Ticket) => (
              <li key={t.id}>
                <Link
                  href={`/tickets/${t.id}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-slate-50"
                >
                  <div>
                    <p className="font-medium">{t.title}</p>
                    <p className="text-sm text-slate-500">
                      {t.priority} · {new Date(t.created_at).toLocaleString()}
                    </p>
                  </div>
                  <StatusBadge status={t.status} />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">No tickets yet. Create one to get started.</p>
        )}
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold">New ticket</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
          className="space-y-3 rounded-lg border border-slate-200 bg-white p-4"
        >
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the issue…"
            required
            rows={4}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          <button
            type="submit"
            disabled={create.isPending}
            className="w-full rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {create.isPending ? "Creating…" : "Create ticket"}
          </button>
          {create.isError && (
            <p className="text-sm text-rose-600">Could not create ticket.</p>
          )}
        </form>
      </section>
    </div>
  );
}
