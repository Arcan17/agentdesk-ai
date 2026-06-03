import type { TicketEvent } from "@/lib/types";

export function AuditTimeline({ events }: { events: TicketEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">No history yet.</p>;
  }
  return (
    <ol className="relative space-y-4 border-l border-slate-200 pl-4">
      {events.map((e) => (
        <li key={e.id} className="relative">
          <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-brand" />
          <p className="text-sm font-medium">
            {e.event_type}
            {e.from_status && e.to_status && (
              <span className="font-normal text-slate-500">
                {" "}
                · {e.from_status} → {e.to_status}
              </span>
            )}
          </p>
          {e.message && <p className="text-sm text-slate-600">{e.message}</p>}
          <p className="text-xs text-slate-400">
            {new Date(e.created_at).toLocaleString()}
            {e.actor_user_id ? " · by operator" : " · by AI workflow"}
          </p>
        </li>
      ))}
    </ol>
  );
}
