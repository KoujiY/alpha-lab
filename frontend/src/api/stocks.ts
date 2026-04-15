import { apiGet } from "./client";
import type { StockMeta, StockOverview } from "./types";

export function fetchStockOverview(symbol: string): Promise<StockOverview> {
  return apiGet<StockOverview>(
    `/api/stocks/${encodeURIComponent(symbol)}/overview`
  );
}

export function searchStocks(q: string, limit = 20): Promise<StockMeta[]> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", String(limit));
  return apiGet<StockMeta[]>(`/api/stocks?${params.toString()}`);
}
