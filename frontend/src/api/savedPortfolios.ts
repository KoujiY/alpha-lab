import { apiDelete, apiGet, apiPost } from "@/api/client";
import type {
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
): Promise<SavedPortfolioMeta> {
  return apiPost<SavedPortfolioMeta>("/api/portfolios/saved", undefined, payload);
}

export function deleteSavedPortfolio(id: number): Promise<void> {
  return apiDelete(`/api/portfolios/saved/${id}`);
}

export function fetchPerformance(id: number): Promise<PerformanceResponse> {
  return apiGet<PerformanceResponse>(`/api/portfolios/saved/${id}/performance`);
}
