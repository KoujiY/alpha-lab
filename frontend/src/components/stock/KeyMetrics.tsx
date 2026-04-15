import type { ReactNode } from "react";

import type { DailyPricePoint, FinancialPoint } from "@/api/types";
import { TermTooltip } from "@/components/TermTooltip";

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
        label={<TermTooltip term="EPS">最新 EPS</TermTooltip>}
        value={eps != null ? eps.toFixed(2) : "—"}
      />
      <Metric
        label={<TermTooltip term="PE">本益比 (PE)</TermTooltip>}
        value={pe != null ? pe.toFixed(1) : "—"}
      />
      <Metric
        label="最新期別"
        value={latestFinancial?.period ?? "—"}
      />
    </section>
  );
}

function Metric({ label, value }: { label: ReactNode; value: string }) {
  return (
    <div className="bg-slate-900 rounded p-3 border border-slate-800">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}
