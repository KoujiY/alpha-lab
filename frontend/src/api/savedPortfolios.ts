import { apiDelete, apiGet, apiPost } from "@/api/client";
import type {
  BaseDateProbe,
  PerformanceResponse,
  SavedPortfolioCreate,
  SavedPortfolioDetail,
  SavedPortfolioMeta,
} from "@/api/types";

export function listSavedPortfolios(): Promise<SavedPortfolioMeta[]> {
  return apiGet<SavedPortfolioMeta[]>("/api/portfolios/saved");
}

export function getSavedPortfolio(id: number): Promise<SavedPortfolioDetail> {
  return apiGet<SavedPortfolioDetail>(`/api/portfolios/saved/${id}`);
}

export function saveRecommendedPortfolio(
  payload: SavedPortfolioCreate,
  options?: { allowFallback?: boolean },
): Promise<SavedPortfolioMeta> {
  const params = options?.allowFallback ? { allow_fallback: "true" } : undefined;
  return apiPost<SavedPortfolioMeta>("/api/portfolios/saved", params, payload);
}

export function deleteSavedPortfolio(id: number): Promise<void> {
  return apiDelete(`/api/portfolios/saved/${id}`);
}

export function fetchPerformance(id: number): Promise<PerformanceResponse> {
  return apiGet<PerformanceResponse>(`/api/portfolios/saved/${id}/performance`);
}

export function probeBaseDate(symbols: string[]): Promise<BaseDateProbe> {
  const query = encodeURIComponent(symbols.join(","));
  return apiGet<BaseDateProbe>(`/api/portfolios/saved/probe?symbols=${query}`);
}
