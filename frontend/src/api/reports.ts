import { apiGet } from "./client";
import type { ReportDetail, ReportMeta, ReportType } from "./types";

export interface ListReportsParams {
  type?: ReportType;
  tag?: string;
}

export function listReports(params?: ListReportsParams): Promise<ReportMeta[]> {
  const query = new URLSearchParams();
  if (params?.type) query.set("type", params.type);
  if (params?.tag) query.set("tag", params.tag);
  const qs = query.toString();
  return apiGet<ReportMeta[]>(`/api/reports${qs ? `?${qs}` : ""}`);
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return apiGet<ReportDetail>(`/api/reports/${encodeURIComponent(reportId)}`);
}
