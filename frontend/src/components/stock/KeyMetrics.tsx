import type { DailyPricePoint, FinancialPoint } from "@/api/types";

interface KeyMetricsProps {
  latestPrice: DailyPricePoint | undefined;
  latestFinancial: FinancialPoint | undefined;
}

export function KeyMetrics({ latestPrice, latestFinancial }: KeyMetricsProps) {
  const eps = latestFinancial?.eps;
  const pe =
    latestPrice && eps && eps > 0 ? latestPrice.close / eps : null;

  return (
    <section
      aria-label="關鍵指標"
      className="grid grid-cols-2 md:grid-cols-4 gap-4"
    >
      <Metric
        label="最新收盤"
        value={latestPrice ? latestPrice.close.toFixed(2) : "—"}
      />
      <Metric
        label="最新 EPS"
        value={eps != null ? eps.toFixed(2) : "—"}
      />
      <Metric
        label="本益比 (PE)"
        value={pe != null ? pe.toFixed(1) : "—"}
      />
      <Metric
        label="最新期別"
        value={latestFinancial?.period ?? "—"}
      />
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900 rounded p-3 border border-slate-800">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}
