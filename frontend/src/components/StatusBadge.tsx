import type { TicketStatus } from "@/lib/types";

const STYLES: Record<TicketStatus, string> = {
  new: "bg-slate-100 text-slate-700",
  triaged: "bg-blue-100 text-blue-700",
  draft_ready: "bg-indigo-100 text-indigo-700",
  waiting_approval: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-rose-100 text-rose-700",
  escalated: "bg-orange-100 text-orange-800",
  closed: "bg-slate-200 text-slate-600",
};

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {status.replace("_", " ")}
    </span>
  );
}
