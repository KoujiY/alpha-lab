import { apiGet } from "./client";
import type { ScoreResponse } from "./types";

export function fetchStockScore(symbol: string): Promise<ScoreResponse> {
  return apiGet<ScoreResponse>(
    `/api/stocks/${encodeURIComponent(symbol)}/score`
  );
}
