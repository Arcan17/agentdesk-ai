"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { Ticket } from "@/lib/types";

export function DraftPanel({ ticket }: { ticket: Ticket }) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState(ticket.draft_response ?? "");
  const [error, setError] = useState<string | null>(null);

  const onSuccess = () => {
    setError(null);
    qc.invalidateQueries({ queryKey: ["ticket", ticket.id] });
    qc.invalidateQueries({ queryKey: ["events", ticket.id] });
    qc.invalidateQueries({ queryKey: ["tickets"] });
  };
  const onError = (e: unknown) =>
    setError(e instanceof ApiError ? e.message : "Action failed");

  const run = useMutation({ mutationFn: () => api.runWorkflow(ticket.id), onSuccess, onError });
  const approve = useMutation({
    mutationFn: () => api.approve(ticket.id, draft || undefined),
    onSuccess,
    onError,
  });
  const reject = useMutation({ mutationFn: () => api.reject(ticket.id), onSuccess, onError });
  const saveEdit = useMutation({
    mutationFn: () => api.editDraft(ticket.id, draft),
    onSuccess,
    onError,
  });

  const canApprove = ticket.status === "waiting_approval";
  const canRun = ticket.status !== "closed" && ticket.status !== "approved";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => run.mutate()}
          disabled={run.isPending || !canRun}
          className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-40"
        >
          {run.isPending ? "Running…" : "Run AI workflow"}
        </button>
      </div>

      {ticket.final_response ? (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <p className="mb-1 text-sm font-semibold text-green-800">Approved response</p>
          <p className="whitespace-pre-wrap text-sm text-slate-700">
            {ticket.final_response}
          </p>
        </div>
      ) : (
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            AI draft {canApprove && "(editable before approval)"}
          </label>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={8}
            placeholder="Run the AI workflow to generate a draft…"
            disabled={!canApprove}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50"
          />
          {canApprove && (
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                onClick={() => approve.mutate()}
                disabled={approve.isPending || !draft.trim()}
                className="rounded-md bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-40"
              >
                Approve
              </button>
              <button
                onClick={() => saveEdit.mutate()}
                disabled={saveEdit.isPending || !draft.trim()}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Save edit
              </button>
              <button
                onClick={() => reject.mutate()}
                disabled={reject.isPending}
                className="rounded-md bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-40"
              >
                Reject
              </button>
            </div>
          )}
        </div>
      )}

      {error && <p className="text-sm text-rose-600">{error}</p>}
    </div>
  );
}
