import { apiPost } from "./client";
import type { PortfolioStyle, RecommendResponse } from "./types";

export function recommendPortfolios(
  style?: PortfolioStyle,
): Promise<RecommendResponse> {
  return apiPost<RecommendResponse>(
    "/api/portfolios/recommend",
    style ? { style } : undefined,
  );
}
