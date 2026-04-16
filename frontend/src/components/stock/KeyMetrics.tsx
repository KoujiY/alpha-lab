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
    <section aria-label="關鍵指標" className="flex h-full flex-col">
      <h2 className="text-xl font-semibold mb-3">關鍵指標</h2>
      <div className="grid flex-1 grid-cols-2 gap-3">
        <Metric
          label="最新收盤"
          value={latestPrice ? latestPrice.close.toFixed(2) : "—"}
        />
        <Metric
          label={<TermTooltip term="EPS">最新 EPS</TermTooltip>}
          value={eps != null ? eps.toFixed(2) : "—"}
        />
        <Metric
          label={
            <TermTooltip term="PE" l2TopicId="PE">
              本益比 (PE)
            </TermTooltip>
          }
          value={pe != null ? pe.toFixed(1) : "—"}
        />
        <Metric
          label="最新期別"
          value={latestFinancial?.period ?? "—"}
        />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: ReactNode; value: string }) {
  return (
    <div className="relative bg-slate-900 rounded p-2 border border-slate-800 flex items-center justify-center min-h-[60px]">
      <div className="absolute top-2 left-2 text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}
