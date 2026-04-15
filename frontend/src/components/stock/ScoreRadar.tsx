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
    <div className="rounded-lg border p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold">多因子評分</h3>
        <span className="text-sm text-gray-600">總分 {totalLabel}</span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="factor" />
          <PolarRadiusAxis domain={[0, 100]} tick={false} />
          <Radar
            dataKey="score"
            stroke="#2563eb"
            fill="#3b82f6"
            fillOpacity={0.3}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
