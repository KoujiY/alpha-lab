import type { BaseDateProbe, SymbolPriceStatus } from "@/api/types";

export interface BaseDateConfirmDialogProps {
  open: boolean;
  probe: BaseDateProbe | null;
  onCancel: () => void;
  onProceed: () => void;
}

const STATUS_LABELS: Record<
  SymbolPriceStatus,
  { label: string; hint: string; color: string }
> = {
  no_data: {
    label: "無任何報價紀錄",
    hint: "此股票尚未抓取過資料，請先點 nav「更新報價」執行資料蒐集。",
    color: "text-red-300",
  },
  stale: {
    label: "報價已過時（可能停牌 / 下市）",
    hint: "最近的報價已超過 7 天，該股票可能停牌或下市。",
    color: "text-orange-300",
  },
  today_missing: {
    label: "今日尚未有收盤價",
    hint: "TWSE 通常於交易日 14:00 後公告，盤中或非交易日可能尚未有資料。",
    color: "text-amber-300",
  },
};

function groupByStatus(
  symbols: string[],
  statuses: Record<string, SymbolPriceStatus>,
): Record<SymbolPriceStatus, string[]> {
  const groups: Record<SymbolPriceStatus, string[]> = {
    no_data: [],
    stale: [],
    today_missing: [],
  };
  for (const sym of symbols) {
    const status = statuses[sym] ?? "today_missing";
    groups[status].push(sym);
  }
  return groups;
}

export function BaseDateConfirmDialog({
  open,
  probe,
  onCancel,
  onProceed,
}: BaseDateConfirmDialogProps) {
  if (!open || !probe) return null;

  const groups = groupByStatus(
    probe.missing_today_symbols,
    probe.symbol_statuses,
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      data-testid="save-confirm-dialog"
    >
      <div className="max-w-md rounded border border-slate-700 bg-slate-900 p-5 shadow-xl">
        <h3 className="mb-2 text-base font-semibold text-amber-300">
          部分持股報價不齊
        </h3>

        {(["no_data", "stale", "today_missing"] as const).map((status) => {
          const syms = groups[status];
          if (syms.length === 0) return null;
          const info = STATUS_LABELS[status];
          return (
            <div
              key={status}
              className="mb-3"
              data-testid={`status-group-${status}`}
            >
              <p className={`text-sm font-medium ${info.color}`}>
                {info.label}
              </p>
              <p className="break-all font-mono text-sm text-slate-200">
                {syms.join("、")}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">{info.hint}</p>
            </div>
          );
        })}

        {probe.resolved_date ? (
          <p className="mb-4 text-sm text-slate-300">
            可以以最近所有持股都有報價的日期{" "}
            <strong className="text-slate-100">{probe.resolved_date}</strong>{" "}
            為基準儲存；或先「取消」再補抓報價。
          </p>
        ) : (
          <p className="mb-4 text-sm text-red-300">
            找不到任何「全持股都有報價」的歷史日期，請先補抓報價後再試。
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
