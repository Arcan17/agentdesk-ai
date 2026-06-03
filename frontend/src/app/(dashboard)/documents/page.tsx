"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";

export default function DocumentsPage() {
  const qc = useQueryClient();
  const { data: docs, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
  });

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const create = useMutation({
    mutationFn: () => api.createDocument(title, content),
    onSuccess: () => {
      setTitle("");
      setContent("");
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return (
    <div className="grid gap-8 lg:grid-cols-3">
      <section className="lg:col-span-2">
        <h1 className="mb-4 text-xl font-semibold">Knowledge Base</h1>
        {isLoading ? (
          <p className="text-slate-500">Loading…</p>
        ) : docs && docs.length > 0 ? (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {docs.map((d: DocumentItem) => (
              <li key={d.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium">{d.title}</p>
                  <p className="text-sm text-slate-500">
                    {d.source_type} · {new Date(d.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-sm text-slate-500">{d.chunk_count ?? 0} chunks</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">
            No documents yet. Add internal docs to ground AI replies.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold">Add document</h2>
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
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Document content…"
            required
            rows={6}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={create.isPending}
            className="w-full rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
          >
            {create.isPending ? "Adding…" : "Add document"}
          </button>
          {create.isError && (
            <p className="text-sm text-rose-600">Could not add document.</p>
          )}
        </form>
      </section>
    </div>
  );
}
