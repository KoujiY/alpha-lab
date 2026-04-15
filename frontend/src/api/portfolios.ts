import { apiPost } from "./client";
import type { PortfolioStyle, RecommendResponse } from "./types";

export function recommendPortfolios(
  style?: PortfolioStyle,
  options?: { saveReport?: boolean },
): Promise<RecommendResponse> {
  const params: Record<string, string> = {};
  if (style) params.style = style;
  if (options?.saveReport) params.save_report = "true";
  return apiPost<RecommendResponse>(
    "/api/portfolios/recommend",
    Object.keys(params).length > 0 ? params : undefined,
  );
}
