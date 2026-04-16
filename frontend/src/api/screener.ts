import { apiGet, apiPost } from "./client";
import type { FactorRange, FactorsResponse, FilterResponse } from "./types";

export function fetchFactors(): Promise<FactorsResponse> {
  return apiGet<FactorsResponse>("/api/screener/factors");
}

export interface FilterParams {
  filters: FactorRange[];
  sort_by?: string;
  sort_desc?: boolean;
  limit?: number;
}

export function filterStocks(params: FilterParams): Promise<FilterResponse> {
  return apiPost<FilterResponse>("/api/screener/filter", undefined, params);
}
