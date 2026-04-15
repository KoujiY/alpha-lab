import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import type { FactorBreakdown } from "@/api/types";

interface ScoreRadarProps {
  breakdown: FactorBreakdown;
}

export function ScoreRadar({ breakdown }: ScoreRadarProps) {
  const data = [
    { factor: "價值", score: breakdown.value_score ?? 0 },
    { factor: "成長", score: breakdown.growth_score ?? 0 },
    { factor: "股息", score: breakdown.dividend_score ?? 0 },
    { factor: "品質", score: breakdown.quality_score ?? 0 },
  ];

  const totalLabel =
    breakdown.total_score !== null ? breakdown.total_score.toFixed(1) : "—";

  return (
    <section aria-label="多因子評分" className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xl font-semibold">多因子評分</h2>
        <span className="text-sm text-slate-400">總分 {totalLabel}</span>
      </div>
      <div className="flex-1 rounded border border-slate-800 bg-slate-900 p-3">
        <ResponsiveContainer width="100%" height={160}>
          <RadarChart data={data}>
            <PolarGrid stroke="#334155" />
            <PolarAngleAxis
              dataKey="factor"
              tick={{ fill: "#cbd5e1", fontSize: 12 }}
            />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              dataKey="score"
              stroke="#60a5fa"
              fill="#3b82f6"
              fillOpacity={0.4}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
