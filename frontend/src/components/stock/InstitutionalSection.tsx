import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { InstitutionalPoint } from "@/api/types";

interface InstitutionalSectionProps {
  points: InstitutionalPoint[];
}

export function InstitutionalSection({ points }: InstitutionalSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="三大法人">
        <h2 className="text-xl font-semibold mb-3">三大法人買賣超</h2>
        <p className="text-slate-500">尚無三大法人資料</p>
      </section>
    );
  }
  const data = points.map((p) => ({
    date: p.trade_date,
    foreign: p.foreign_net / 1000,
    trust: p.trust_net / 1000,
    dealer: p.dealer_net / 1000,
  }));
  return (
    <section aria-label="三大法人">
      <h2 className="text-xl font-semibold mb-3">三大法人買賣超（近 20 日，單位：張）</h2>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Legend />
            <Bar dataKey="foreign" name="外資" fill="#38bdf8" />
            <Bar dataKey="trust" name="投信" fill="#a78bfa" />
            <Bar dataKey="dealer" name="自營商" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
