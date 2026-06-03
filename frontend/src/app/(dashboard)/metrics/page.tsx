"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { MetricsCards } from "@/components/MetricsCards";

export default function MetricsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => api.metrics(),
  });

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">Metrics</h1>
      {isLoading && <p className="text-slate-500">Loading…</p>}
      {error && (
        <p className="text-rose-600">
          {error instanceof ApiError && error.status === 403
            ? "Admin access required to view metrics."
            : "Could not load metrics."}
        </p>
      )}
      {data && <MetricsCards metrics={data} />}
    </div>
  );
}
