import type { Holding } from "@/api/types";

interface HoldingsTableProps {
  holdings: Holding[];
}

export function HoldingsTable({ holdings }: HoldingsTableProps) {
  if (holdings.length === 0) {
    return <p className="text-slate-500">此組合無持股候選。</p>;
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-slate-800 text-left text-slate-400">
          <th className="py-2">代號</th>
          <th className="py-2">名稱</th>
          <th className="py-2 text-right">權重</th>
          <th className="py-2 text-right">總分</th>
        </tr>
      </thead>
      <tbody>
        {holdings.map((h) => (
          <tr key={h.symbol} className="border-b border-slate-800">
            <td className="py-2">{h.symbol}</td>
            <td className="py-2">{h.name}</td>
            <td className="py-2 text-right">
              {(h.weight * 100).toFixed(1)}%
            </td>
            <td className="py-2 text-right">
              {h.score_breakdown.total_score?.toFixed(1) ?? "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
