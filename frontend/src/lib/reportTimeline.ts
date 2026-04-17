import type { ReportMeta } from "@/api/types";

export interface ReportMonthGroup {
  month: string;
  items: ReportMeta[];
}

export function groupReportsByMonth(
  reports: ReportMeta[],
): ReportMonthGroup[] {
  const map = new Map<string, ReportMeta[]>();
  for (const r of reports) {
    const month = r.date.slice(0, 7);
    const bucket = map.get(month) ?? [];
    bucket.push(r);
    map.set(month, bucket);
  }
  return [...map.entries()]
    .sort(([a], [b]) => (a < b ? 1 : a > b ? -1 : 0))
    .map(([month, items]) => ({ month, items }));
}
