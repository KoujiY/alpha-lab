import type { MarginPoint } from "@/api/types";

interface MarginSectionProps {
  points: MarginPoint[];
}

export function MarginSection({ points }: MarginSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="融資融券" className="flex h-full flex-col">
        <h2 className="text-xl font-semibold mb-3">融資融券</h2>
        <p className="text-slate-500">尚無融資融券資料</p>
      </section>
    );
  }
  const latest = points[points.length - 1];
  return (
    <section aria-label="融資融券" className="flex h-full flex-col">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-xl font-semibold">融資融券</h2>
        <span className="text-xs text-slate-500">{latest.trade_date}（單位：張）</span>
      </div>
      <dl className="grid flex-1 grid-cols-2 gap-2 text-sm">
        <Stat label="融資餘額" value={latest.margin_balance} />
        <Stat label="融資買進" value={latest.margin_buy} />
        <Stat label="融資賣出" value={latest.margin_sell} />
        <Stat label="融券餘額" value={latest.short_balance} />
        <Stat label="融券賣出" value={latest.short_sell} />
        <Stat label="融券回補" value={latest.short_cover} />
      </dl>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="relative bg-slate-900 rounded p-2 border border-slate-800 flex items-center justify-center min-h-[50px]">
      <dt className="absolute top-1 left-2 text-[11px] text-slate-500">{label}</dt>
      <dd className="text-lg font-semibold">{value.toLocaleString("zh-TW")}</dd>
    </div>
  );
}
