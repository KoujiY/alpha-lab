import type { SavedHolding } from "@/api/types";

/**
 * 當使用者把 `editedSymbol` 的權重手動改為 `editedWeight`（0~1），
 * 其他 holding 以「原權重占其他檔總和的比例」等比縮放到剩餘空間 1 - editedWeight。
 *
 * 回傳新的 holdings 陣列；若 editedSymbol 不在 holdings 內就原樣回傳。
 * Guard：
 *  - editedWeight < 0 → 夾到 0
 *  - editedWeight > 1 → 夾到 1
 *  - 只有單一 holding → 強制 editedWeight = 1，`weight` 設 1
 *  - 其他 holdings 權重總和為 0（理論不會發生，但守一下）→ 把 remainder 平分
 */
export function rebalanceAfterEdit(
  holdings: SavedHolding[],
  editedSymbol: string,
  editedWeight: number,
): SavedHolding[] {
  if (holdings.length === 0) return holdings;
  const target = holdings.find((h) => h.symbol === editedSymbol);
  if (!target) return holdings;

  const clamped = Math.max(0, Math.min(1, editedWeight));

  if (holdings.length === 1) {
    return [{ ...target, weight: 1 }];
  }

  const others = holdings.filter((h) => h.symbol !== editedSymbol);
  const otherSum = others.reduce((s, h) => s + h.weight, 0);
  const remainder = 1 - clamped;

  const scaled =
    otherSum > 0
      ? others.map((h) => ({
          ...h,
          weight: (h.weight / otherSum) * remainder,
        }))
      : others.map((h) => ({ ...h, weight: remainder / others.length }));

  return holdings.map((h) =>
    h.symbol === editedSymbol
      ? { ...h, weight: clamped }
      : (scaled.find((s) => s.symbol === h.symbol) ?? h),
  );
}

/**
 * 權重加總是否在 1 附近（容忍 1e-6）。
 */
export function isWeightSumValid(holdings: SavedHolding[]): boolean {
  const sum = holdings.reduce((s, h) => s + h.weight, 0);
  return Math.abs(sum - 1) < 1e-6;
}

/**
 * 把 holdings 等比縮放到合計 1。
 * - sum = 0（極端退化 state，使用者把所有權重打成 0）→ 原樣回傳（呼叫方負責顯示錯誤）
 * - 其他情況 → 每筆 weight /= sum，保證 Σ = 1
 *
 * 用途：當 `isWeightSumValid` 因連續手動編輯累積誤差而回 false，
 * 提供「自動補正」按鈕給使用者一鍵修復，而不是卡死 confirm button。
 */
export function normalizeToOne(holdings: SavedHolding[]): SavedHolding[] {
  const sum = holdings.reduce((s, h) => s + h.weight, 0);
  if (sum === 0) return holdings;
  return holdings.map((h) => ({ ...h, weight: h.weight / sum }));
}
