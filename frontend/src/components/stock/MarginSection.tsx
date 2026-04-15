import type { MarginPoint } from "@/api/types";

interface MarginSectionProps {
  points: MarginPoint[];
}

export function MarginSection({ points }: MarginSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="融資融券">
        <h2 className="text-xl font-semibold mb-3">融資融券</h2>
        <p className="text-slate-500">尚無融資融券資料</p>
      </section>
    );
  }
  const latest = points[points.length - 1];
  return (
    <section aria-label="融資融券">
      <h2 className="text-xl font-semibold mb-3">融資融券（最新一日）</h2>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <Stat label="融資餘額" value={latest.margin_balance} />
        <Stat label="融資買進" value={latest.margin_buy} />
        <Stat label="融資賣出" value={latest.margin_sell} />
        <Stat label="融券餘額" value={latest.short_balance} />
        <Stat label="融券賣出" value={latest.short_sell} />
        <Stat label="融券回補" value={latest.short_cover} />
      </dl>
      <p className="text-xs text-slate-500 mt-2">日期：{latest.trade_date}（單位：張）</p>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-900 rounded p-3 border border-slate-800">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-lg font-semibold mt-1">{value.toLocaleString("zh-TW")}</dd>
    </div>
  );
}
