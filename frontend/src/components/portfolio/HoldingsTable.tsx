import { Fragment, useState } from "react";

import type { Holding } from "@/api/types";
import { useTutorialMode } from "@/contexts/TutorialModeContext";

interface HoldingsTableProps {
  holdings: Holding[];
}

export function HoldingsTable({ holdings }: HoldingsTableProps) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const { mode } = useTutorialMode();
  const showReasons = mode !== "off";

  if (holdings.length === 0) {
    return <p className="text-slate-500">此組合無持股候選。</p>;
  }

  const toggle = (symbol: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  };

  const columnCount = showReasons ? 5 : 4;

  return (
    <table className="w-full text-sm" data-testid="holdings-table">
      <thead>
        <tr className="border-b border-slate-800 text-left text-slate-400">
          <th className="py-2">代號</th>
          <th className="py-2">名稱</th>
          <th className="py-2 text-right">權重</th>
          <th className="py-2 text-right">總分</th>
          {showReasons && <th className="py-2 text-right">理由</th>}
        </tr>
      </thead>
      <tbody>
        {holdings.map((h) => {
          const isOpen = showReasons && expanded.has(h.symbol);
          return (
            <Fragment key={h.symbol}>
              <tr className="border-b border-slate-800">
                <td className="py-2">{h.symbol}</td>
                <td className="py-2">{h.name}</td>
                <td className="py-2 text-right">
                  {(h.weight * 100).toFixed(1)}%
                </td>
                <td className="py-2 text-right">
                  {h.score_breakdown.total_score?.toFixed(1) ?? "—"}
                </td>
                {showReasons && (
                  <td className="py-2 text-right">
                    {h.reasons && h.reasons.length > 0 ? (
                      <button
                        type="button"
                        onClick={() => toggle(h.symbol)}
                        className="text-sky-400 hover:text-sky-300"
                        aria-expanded={isOpen}
                        aria-controls={`reasons-${h.symbol}`}
                        data-testid={`reasons-toggle-${h.symbol}`}
                      >
                        {isOpen ? "收起" : "查看理由"}
                      </button>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                )}
              </tr>
              {isOpen && (
                <tr
                  id={`reasons-${h.symbol}`}
                  className="border-b border-slate-800 bg-slate-900/50"
                >
                  <td colSpan={columnCount} className="py-3 px-2">
                    <ul className="list-disc pl-6 space-y-1 text-slate-300">
                      {h.reasons.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
