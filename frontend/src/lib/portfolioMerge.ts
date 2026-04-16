import type { SavedHolding } from "@/api/types";

/**
 * 把一檔新股票以 delta-weight 稀釋語意加入既有持股清單。
 *
 * 規則：
 * 1. 所有既有持股權重 *= (1 - delta)（等比例稀釋，挪出 delta 的空間）
 * 2. 若 symbol 已存在：該筆 += delta（合併，不重複出現）
 * 3. 若 symbol 不存在：append 一筆 weight=delta
 * 4. 所有 `base_price` 設 0，讓後端用新組合的 `base_date` 重新查收盤價 rebase，
 *    避免舊 base_date 的價格混入導致 NAV 公式分母不自洽。
 *
 * 拒絕條件：
 * - delta 不在 (0, 1) 開區間
 * - 既有為「單一 symbol 100% 全倉」且加碼同一 symbol（加不進去，因為稀釋後仍是自己）
 */
export interface MergeArgs {
  existing: SavedHolding[];
  symbol: string;
  name: string;
  delta: number;
}

export function buildMergedHoldings(args: MergeArgs): SavedHolding[] {
  const { existing, symbol, name, delta } = args;

  if (!Number.isFinite(delta) || delta <= 0 || delta >= 1) {
    throw new Error("權重需介於 1% 到 99%");
  }

  const hasExisting = existing.some((h) => h.symbol === symbol);
  const othersCount = existing.filter((h) => h.symbol !== symbol).length;

  if (hasExisting && othersCount === 0) {
    throw new Error(`此組合已為 ${symbol} 全倉，無法再加碼`);
  }

  const scaled: SavedHolding[] = existing.map((h) => ({
    ...h,
    weight: h.weight * (1 - delta),
    base_price: 0,
  }));

  if (hasExisting) {
    return scaled.map((h) =>
      h.symbol === symbol ? { ...h, weight: h.weight + delta } : h,
    );
  }
  return [...scaled, { symbol, name, weight: delta, base_price: 0 }];
}
