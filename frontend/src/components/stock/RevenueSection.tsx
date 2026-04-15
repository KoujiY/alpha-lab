import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RevenuePoint } from "@/api/types";

interface RevenueSectionProps {
  points: RevenuePoint[];
}

export function RevenueSection({ points }: RevenueSectionProps) {
  const data = points.map((p) => ({
    label: `${p.year}-${String(p.month).padStart(2, "0")}`,
    revenue: p.revenue / 1_000_000,
    yoy: p.yoy_growth != null ? p.yoy_growth * 100 : null,
  }));
  return (
    <section aria-label="月營收">
      <h2 className="text-xl font-semibold mb-3">月營收（近 12 個月）</h2>
      {data.length === 0 ? (
        <p className="text-slate-500">尚無月營收資料</p>
      ) : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid stroke="#1e293b" />
              <XAxis dataKey="label" stroke="#64748b" fontSize={12} />
              <YAxis
                stroke="#64748b"
                fontSize={12}
                label={{ value: "百萬", angle: -90, position: "insideLeft" }}
              />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
              />
              <Bar dataKey="revenue" fill="#38bdf8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
