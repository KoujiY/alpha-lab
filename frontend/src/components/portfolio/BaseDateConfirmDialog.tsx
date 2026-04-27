import type { BaseDateProbe, SymbolPriceStatus } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
  if (!probe) return null;

  const groups = groupByStatus(
    probe.missing_today_symbols,
    probe.symbol_statuses,
  );

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) onCancel();
      }}
    >
      <DialogContent data-testid="save-confirm-dialog" showClose={false}>
        <DialogHeader>
          <DialogTitle className="text-amber-300">部分持股報價不齊</DialogTitle>
          {probe.resolved_date ? (
            <DialogDescription>
              可以以最近所有持股都有報價的日期{" "}
              <strong className="text-slate-100">{probe.resolved_date}</strong>{" "}
              為基準儲存；或先「取消」再補抓報價。
            </DialogDescription>
          ) : (
            <DialogDescription className="text-red-300">
              找不到任何「全持股都有報價」的歷史日期，請先補抓報價後再試。
            </DialogDescription>
          )}
        </DialogHeader>

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

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
            data-testid="save-confirm-cancel"
          >
            取消
          </Button>
          <Button
            variant="warn"
            onClick={onProceed}
            disabled={probe.resolved_date === null}
            data-testid="save-confirm-proceed"
          >
            以 {probe.resolved_date ?? "—"} 為基準繼續
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
