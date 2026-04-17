import { createStore, del, entries, get, set } from "idb-keyval";
import type { ReportDetail } from "@/api/types";

const store = createStore("alpha-lab-reports", "report-cache");

function key(reportId: string): string {
  return `report:${reportId}`;
}

export async function getCachedReport(
  reportId: string,
): Promise<ReportDetail | undefined> {
  return get<ReportDetail>(key(reportId), store);
}

export async function setCachedReport(report: ReportDetail): Promise<void> {
  await set(key(report.id), report, store);
}

export async function listCachedReportIds(): Promise<string[]> {
  const all = await entries<string, ReportDetail>(store);
  return all.map(([k]) => k.replace(/^report:/, ""));
}

export async function clearReportCache(): Promise<void> {
  const all = await entries<string, ReportDetail>(store);
  for (const [k] of all) {
    await del(k, store);
  }
}
