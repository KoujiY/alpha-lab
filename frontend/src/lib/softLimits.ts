import type { SavedHolding } from "@/api/types";

export type SoftLimitCode =
  | "too_many_holdings"
  | "single_weight_too_high"
  | "weight_too_small";

export interface SoftLimitWarning {
  code: SoftLimitCode;
  message: string;
  symbols?: string[];
}

export const SOFT_LIMITS = {
  MAX_HOLDINGS: 20,
  MAX_SINGLE_WEIGHT: 0.4,
  MIN_SINGLE_WEIGHT: 0.005,
} as const;

export function checkSoftLimits(
  holdings: readonly SavedHolding[],
): SoftLimitWarning[] {
  const warnings: SoftLimitWarning[] = [];

  if (holdings.length > SOFT_LIMITS.MAX_HOLDINGS) {
    warnings.push({
      code: "too_many_holdings",
      message: `持股數 ${holdings.length} 檔 > ${SOFT_LIMITS.MAX_HOLDINGS} 檔，分散度偏高可能稀釋選股能力`,
    });
  }

  const heavy = holdings.filter((h) => h.weight > SOFT_LIMITS.MAX_SINGLE_WEIGHT);
  if (heavy.length > 0) {
    warnings.push({
      code: "single_weight_too_high",
      message: `單檔權重 > ${Math.round(SOFT_LIMITS.MAX_SINGLE_WEIGHT * 100)}%，集中風險偏高`,
      symbols: heavy.map((h) => h.symbol),
    });
  }

  const tiny = holdings.filter(
    (h) => h.weight > 0 && h.weight < SOFT_LIMITS.MIN_SINGLE_WEIGHT,
  );
  if (tiny.length > 0) {
    warnings.push({
      code: "weight_too_small",
      message: `單檔權重 < ${(SOFT_LIMITS.MIN_SINGLE_WEIGHT * 100).toFixed(1)}%，對整體 NAV 幾乎無影響`,
      symbols: tiny.map((h) => h.symbol),
    });
  }

  return warnings;
}
