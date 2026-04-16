import { apiDelete, apiGet, apiPatch } from "./client";
import type { ReportDetail, ReportMeta, ReportType, ReportUpdate } from "./types";

export interface ListReportsParams {
  type?: ReportType;
  tag?: string;
  symbol?: string;
  query?: string;
}

export function listReports(params?: ListReportsParams): Promise<ReportMeta[]> {
  const query = new URLSearchParams();
  if (params?.type) query.set("type", params.type);
  if (params?.tag) query.set("tag", params.tag);
  if (params?.symbol) query.set("symbol", params.symbol);
  if (params?.query) query.set("q", params.query);
  const qs = query.toString();
  return apiGet<ReportMeta[]>(`/api/reports${qs ? `?${qs}` : ""}`);
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return apiGet<ReportDetail>(`/api/reports/${encodeURIComponent(reportId)}`);
}

export function updateReport(
  reportId: string,
  patch: ReportUpdate,
): Promise<ReportMeta> {
  return apiPatch<ReportMeta>(`/api/reports/${encodeURIComponent(reportId)}`, patch);
}

export function deleteReport(reportId: string): Promise<void> {
  return apiDelete(`/api/reports/${encodeURIComponent(reportId)}`);
}
