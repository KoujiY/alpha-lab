import { useState } from "react";

import type { Portfolio, PortfolioStyle } from "@/api/types";

import { HoldingsTable } from "./HoldingsTable";

interface PortfolioTabsProps {
  portfolios: Portfolio[];
}

const STYLE_ORDER: PortfolioStyle[] = [
  "conservative",
  "balanced",
  "aggressive",
];

export function PortfolioTabs({ portfolios }: PortfolioTabsProps) {
  const sorted = STYLE_ORDER.map((s) =>
    portfolios.find((p) => p.style === s),
  ).filter((p): p is Portfolio => p !== undefined);

  const defaultStyle =
    sorted.find((p) => p.is_top_pick)?.style ?? sorted[0]?.style ?? "balanced";
  const [active, setActive] = useState<PortfolioStyle>(defaultStyle);

  const current = sorted.find((p) => p.style === active);

  return (
    <div>
      <div className="mb-4 flex gap-2 border-b border-slate-800">
        {sorted.map((p) => (
          <button
            type="button"
            key={p.style}
            onClick={() => setActive(p.style)}
            className={`px-4 py-2 ${
              active === p.style
                ? "border-b-2 border-sky-400 font-semibold text-sky-300"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {p.label}
            {p.is_top_pick && (
              <span className="ml-2 rounded bg-sky-500/20 px-2 py-0.5 text-xs text-sky-300">
                最推薦
              </span>
            )}
          </button>
        ))}
      </div>
      {current && (
        <div>
          <div className="mb-3 flex gap-6 text-sm text-slate-400">
            <span>
              預期殖利率：{current.expected_yield?.toFixed(2) ?? "—"}%
            </span>
            <span>
              風險分數：{current.risk_score?.toFixed(1) ?? "—"}
            </span>
          </div>
          <HoldingsTable holdings={current.holdings} />
        </div>
      )}
    </div>
  );
}
