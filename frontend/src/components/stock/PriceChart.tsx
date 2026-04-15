import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DailyPricePoint } from "@/api/types";

interface PriceChartProps {
  points: DailyPricePoint[];
}

export function PriceChart({ points }: PriceChartProps) {
  if (points.length === 0) {
    return (
      <section aria-label="股價走勢">
        <h2 className="text-xl font-semibold mb-3">股價走勢</h2>
        <div className="h-64 flex items-center justify-center text-slate-500">
          尚無股價資料
        </div>
      </section>
    );
  }
  return (
    <section aria-label="股價走勢">
      <h2 className="text-xl font-semibold mb-3">股價走勢</h2>
      <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis dataKey="trade_date" stroke="#64748b" fontSize={12} />
          <YAxis stroke="#64748b" fontSize={12} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
      </div>
    </section>
  );
}
