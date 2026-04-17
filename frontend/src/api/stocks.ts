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

// /stocks 瀏覽列表頁用：一次載入全市場（上限 3000）。
// 與 searchStocks 分開以保留 HeaderSearch 的 top-N 預設。
export function listAllStocks(q?: string): Promise<StockMeta[]> {
  return searchStocks(q ?? "", 3000);
}
