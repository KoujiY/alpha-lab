import type { FinancialPoint } from "@/api/types";
import { TermTooltip } from "@/components/TermTooltip";

interface FinancialsSectionProps {
  points: FinancialPoint[];
}

function fmt(value: number | null, scale = 1): string {
  if (value == null) return "—";
  return (value / scale).toLocaleString("zh-TW", { maximumFractionDigits: 2 });
}

export function FinancialsSection({ points }: FinancialsSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="季報摘要">
        <h2 className="text-xl font-semibold mb-3">季報摘要</h2>
        <p className="text-slate-500">尚無季報資料</p>
      </section>
    );
  }
  return (
    <section aria-label="季報摘要">
      <h2 className="text-xl font-semibold mb-3">季報摘要（近 4 季，單位：百萬）</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-slate-800">
          <thead className="bg-slate-900">
            <tr>
              <th className="text-left px-3 py-2">期別</th>
              <th className="text-right px-3 py-2">營收</th>
              <th className="text-right px-3 py-2">毛利</th>
              <th className="text-right px-3 py-2">營業利益</th>
              <th className="text-right px-3 py-2">淨利</th>
              <th className="text-right px-3 py-2">
                <TermTooltip term="EPS">EPS</TermTooltip>
              </th>
              <th className="text-right px-3 py-2">股東權益</th>
            </tr>
          </thead>
          <tbody>
            {points.slice().reverse().map((p) => (
              <tr key={p.period} className="border-t border-slate-800">
                <td className="px-3 py-2">{p.period}</td>
                <td className="text-right px-3 py-2">{fmt(p.revenue, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.gross_profit, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.operating_income, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.net_income, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.eps)}</td>
                <td className="text-right px-3 py-2">{fmt(p.total_equity, 1_000_000)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
