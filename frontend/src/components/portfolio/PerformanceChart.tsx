import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PerformancePoint } from "@/api/types";

interface PerformanceChartProps {
  points: PerformancePoint[];
}

export function PerformanceChart({ points }: PerformanceChartProps) {
  if (points.length === 0) {
    return <p className="text-slate-400 text-sm">尚無績效資料</p>;
  }
  return (
    <div className="h-64 w-full" data-testid="performance-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" stroke="#94a3b8" />
          <YAxis domain={["auto", "auto"]} stroke="#94a3b8" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
            }}
          />
          <Line
            type="monotone"
            dataKey="nav"
            stroke="#38bdf8"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
