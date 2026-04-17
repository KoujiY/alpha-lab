import { useQuery } from "@tanstack/react-query";

import { getReport, listReports, type ListReportsParams } from "@/api/reports";
import type { ReportDetail } from "@/api/types";
import { getCachedReport, setCachedReport } from "@/lib/reportCache";

export function useReports(params?: ListReportsParams) {
  return useQuery({
    queryKey: [
      "reports",
      "list",
      params?.type ?? null,
      params?.tag ?? null,
      params?.symbol ?? null,
      params?.query ?? null,
    ],
    queryFn: () => listReports(params),
    staleTime: 30 * 1000,
  });
}

export async function getReportWithCache(
  reportId: string,
  fetchFn: (id: string) => Promise<ReportDetail> = getReport,
): Promise<ReportDetail> {
  try {
    const report = await fetchFn(reportId);
    await setCachedReport(report).catch(() => {});
    return report;
  } catch (err) {
    const cached = await getCachedReport(reportId);
    if (cached) return cached;
    throw err;
  }
}

export function useReport(reportId: string | null) {
  return useQuery({
    queryKey: ["reports", "detail", reportId],
    queryFn: () => {
      if (reportId === null) {
        throw new Error("reportId is required");
      }
      return getReportWithCache(reportId);
    },
    enabled: reportId !== null,
    staleTime: 60 * 1000,
  });
}
