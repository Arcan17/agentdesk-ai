import type { Metrics } from "@/lib/types";

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export function MetricsCards({ metrics }: { metrics: Metrics }) {
  const pct = (n: number) => `${(n * 100).toFixed(0)}%`;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Total tickets" value={String(metrics.total_tickets)} />
        <Card label="Approval rate" value={pct(metrics.approval_rate)} />
        <Card label="Escalation rate" value={pct(metrics.escalation_rate)} />
        <Card label="Retrieval hit rate" value={pct(metrics.retrieval_hit_rate)} />
        <Card label="Avg latency" value={`${metrics.avg_agent_latency_ms.toFixed(0)} ms`} />
        <Card
          label="Avg cost / run"
          value={`$${metrics.avg_estimated_cost_usd.toFixed(5)}`}
        />
        <Card label="Failed jobs" value={String(metrics.failed_jobs)} />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="mb-3 text-sm font-medium text-slate-700">Tickets by status</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(metrics.tickets_by_status).map(([k, v]) => (
            <span
              key={k}
              className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
            >
              {k.replace("_", " ")}: <strong>{v}</strong>
            </span>
          ))}
          {Object.keys(metrics.tickets_by_status).length === 0 && (
            <span className="text-sm text-slate-500">No data yet.</span>
          )}
        </div>
      </div>
    </div>
  );
}
