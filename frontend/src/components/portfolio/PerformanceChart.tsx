import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PerformancePoint } from "@/api/types";

interface PerformanceChartProps {
  points: PerformancePoint[];
  parentPoints?: PerformancePoint[] | null;
  parentNavAtFork?: number | null;
}

interface ChartRow {
  date: string;
  parent: number | null;
  self: number | null;
}

interface BuildArgs {
  points: PerformancePoint[];
  parentPoints: PerformancePoint[] | null | undefined;
  parentNavAtFork: number | null | undefined;
}

interface BuildResult {
  rows: ChartRow[];
  forkDate: string | null;
}

export function buildChartSeries(args: BuildArgs): BuildResult {
  const { points, parentPoints, parentNavAtFork } = args;
  const hasParent =
    parentPoints != null &&
    parentPoints.length > 0 &&
    parentNavAtFork != null &&
    Number.isFinite(parentNavAtFork);
  const scale = hasParent ? (parentNavAtFork as number) : 1;

  const rows: ChartRow[] = [];
  if (hasParent) {
    for (const p of parentPoints as PerformancePoint[]) {
      rows.push({ date: p.date, parent: p.nav, self: null });
    }
  }

  if (points.length === 0) {
    return { rows, forkDate: null };
  }

  const forkDate = hasParent ? points[0].date : null;
  for (let i = 0; i < points.length; i += 1) {
    const p = points[i];
    const selfNav = p.nav * scale;
    if (i === 0 && hasParent) {
      rows.push({ date: p.date, parent: scale, self: selfNav });
    } else {
      rows.push({ date: p.date, parent: null, self: selfNav });
    }
  }
  return { rows, forkDate };
}

export function PerformanceChart({
  points,
  parentPoints = null,
  parentNavAtFork = null,
}: PerformanceChartProps) {
  if (points.length === 0 && (!parentPoints || parentPoints.length === 0)) {
    return <p className="text-slate-400 text-sm">尚無績效資料</p>;
  }
  const { rows, forkDate } = buildChartSeries({
    points,
    parentPoints,
    parentNavAtFork,
  });
  return (
    <div className="h-64 w-full" data-testid="performance-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" stroke="#94a3b8" />
          <YAxis domain={["auto", "auto"]} stroke="#94a3b8" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
            }}
          />
          {forkDate ? (
            <ReferenceLine
              x={forkDate}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: "fork", fill: "#f59e0b", position: "top" }}
            />
          ) : null}
          {parentPoints && parentPoints.length > 0 ? (
            <Line
              type="monotone"
              dataKey="parent"
              stroke="#94a3b8"
              strokeDasharray="4 4"
              dot={false}
              strokeWidth={2}
              connectNulls={false}
              name="parent"
            />
          ) : null}
          <Line
            type="monotone"
            dataKey="self"
            stroke="#38bdf8"
            dot={false}
            strokeWidth={2}
            connectNulls={false}
            name="self"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
