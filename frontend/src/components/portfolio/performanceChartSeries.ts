import type { PerformancePoint } from "@/api/types";

export interface ChartRow {
  date: string;
  parent: number | null;
  self: number | null;
}

export interface BuildArgs {
  points: PerformancePoint[];
  parentPoints: PerformancePoint[] | null | undefined;
  parentNavAtFork: number | null | undefined;
  childBaseDate: string | null | undefined;
}

export interface BuildResult {
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
