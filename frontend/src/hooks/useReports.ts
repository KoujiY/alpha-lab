import { useQuery } from "@tanstack/react-query";

import { getReport, listReports, type ListReportsParams } from "@/api/reports";

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

export function useReport(reportId: string | null) {
  return useQuery({
    queryKey: ["reports", "detail", reportId],
    queryFn: () => {
      if (reportId === null) {
        throw new Error("reportId is required");
      }
      return getReport(reportId);
    },
    enabled: reportId !== null,
    staleTime: 60 * 1000,
  });
}
