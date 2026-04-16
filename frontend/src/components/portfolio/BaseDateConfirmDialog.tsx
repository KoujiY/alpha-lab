import type { BaseDateProbe } from "@/api/types";

/**
 * 「今日報價不齊」確認視窗。
 *
 * 觸發場景：使用者要儲存 / 加入組合時，前端先呼叫 `probeBaseDate(symbols)` 檢查
 * 所有持股今日是否都有 PriceDaily。若任一檔缺價（`today_available === false`），
 * 彈此視窗讓使用者選擇：
 * - 取消 → 什麼都不做（通常搭配去點 nav 的「更新報價」補抓）
 * - 以 `resolved_date`（最近全檔都有報價的歷史日期）為基準繼續 → 走 allow_fallback 路徑
 *
 * 若後端連 `resolved_date` 都算不出（歷史上沒有任何一天所有 symbols 都有報價），
 * 「繼續」按鈕 disabled，只能取消。
 */
export interface BaseDateConfirmDialogProps {
  open: boolean;
  probe: BaseDateProbe | null;
  onCancel: () => void;
  onProceed: () => void;
}

export function BaseDateConfirmDialog({
  open,
  probe,
  onCancel,
  onProceed,
}: BaseDateConfirmDialogProps) {
  if (!open || !probe) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      data-testid="save-confirm-dialog"
    >
      <div className="max-w-md rounded border border-slate-700 bg-slate-900 p-5 shadow-xl">
        <h3 className="mb-2 text-base font-semibold text-amber-300">
          今日報價不齊
        </h3>
        <p className="mb-2 text-sm text-slate-300">
          下列持股在 {probe.target_date} 還沒有收盤價：
        </p>
        <p className="mb-3 text-xs text-slate-500">
          提醒：TWSE 通常於交易日 14:00 後公告當日收盤價，盤中或非交易日可能尚未有資料。
        </p>
        <p className="mb-3 break-all text-sm font-mono text-amber-200">
          {probe.missing_today_symbols.join("、")}
        </p>
        {probe.resolved_date ? (
          <p className="mb-4 text-sm text-slate-300">
            可以以最近所有持股都有報價的日期{" "}
            <strong className="text-slate-100">{probe.resolved_date}</strong>{" "}
            為基準儲存；或先「取消」再點 nav「更新報價」補抓。
          </p>
        ) : (
          <p className="mb-4 text-sm text-red-300">
            找不到任何「全持股都有報價」的歷史日期，請先點 nav「更新報價」補抓。
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            data-testid="save-confirm-cancel"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onProceed}
            disabled={probe.resolved_date === null}
            className="rounded border border-amber-500 bg-amber-500/10 px-3 py-1.5 text-sm text-amber-200 hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            data-testid="save-confirm-proceed"
          >
            以 {probe.resolved_date ?? "—"} 為基準繼續
          </button>
        </div>
      </div>
    </div>
  );
}
