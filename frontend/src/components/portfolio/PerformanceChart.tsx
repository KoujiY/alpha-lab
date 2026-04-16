import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
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
  childBaseDate?: string | null;
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
  childBaseDate: string | null | undefined;
}

interface BuildResult {
  rows: ChartRow[];
  forkDate: string | null;
}

export function buildChartSeries(args: BuildArgs): BuildResult {
  const { points, parentPoints, parentNavAtFork, childBaseDate } = args;
  const hasParent =
    parentPoints != null &&
    parentPoints.length > 0 &&
    parentNavAtFork != null &&
    Number.isFinite(parentNavAtFork) &&
    childBaseDate != null &&
    childBaseDate.length > 0;
  const scale = hasParent ? (parentNavAtFork as number) : 1;

  const rows: ChartRow[] = [];
  if (hasParent) {
    for (const p of parentPoints as PerformancePoint[]) {
      rows.push({ date: p.date, parent: p.nav, self: null });
    }
    rows.push({
      date: childBaseDate as string,
      parent: scale,
      self: scale,
    });
  }

  for (const p of points) {
    if (hasParent && p.date === childBaseDate) continue;
    rows.push({ date: p.date, parent: null, self: p.nav * scale });
  }

  const forkDate = hasParent ? (childBaseDate as string) : null;
  return { rows, forkDate };
}

export function PerformanceChart({
  points,
  parentPoints = null,
  parentNavAtFork = null,
  childBaseDate = null,
}: PerformanceChartProps) {
  if (points.length === 0 && (!parentPoints || parentPoints.length === 0)) {
    return <p className="text-slate-400 text-sm">尚無績效資料</p>;
  }
  const { rows, forkDate } = buildChartSeries({
    points,
    parentPoints,
    parentNavAtFork,
    childBaseDate,
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
          {forkDate && parentNavAtFork != null ? (
            <ReferenceDot
              x={forkDate}
              y={parentNavAtFork}
              r={4}
              fill="#38bdf8"
              stroke="#0f172a"
              strokeWidth={2}
              ifOverflow="visible"
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
