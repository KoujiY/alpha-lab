import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  getSavedPortfolio,
  listSavedPortfolios,
  probeBaseDate,
  saveRecommendedPortfolio,
} from "@/api/savedPortfolios";
import type {
  BaseDateProbe,
  SavedHolding,
  SavedPortfolioDetail,
  SavedPortfolioMeta,
  StockMeta,
} from "@/api/types";
import { BaseDateConfirmDialog } from "@/components/portfolio/BaseDateConfirmDialog";
import { SoftLimitWarningList } from "@/components/portfolio/SoftLimitWarningList";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { buildMergedHoldings } from "@/lib/portfolioMerge";
import { checkSoftLimits } from "@/lib/softLimits";
import {
  isWeightSumValid,
  normalizeToOne,
  rebalanceAfterEdit,
} from "@/lib/weightAdjust";

export interface AddToPortfolioWizardProps {
  meta: StockMeta;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type WizardStep = "pick" | "preview";

type ConfirmDialogState =
  | { open: false }
  | { open: true; probe: BaseDateProbe };

function humanizeAddError(err: unknown): string {
  if (!(err instanceof Error)) return "未知錯誤";
  const msg = err.message;
  const priceMatch = msg.match(/no price for ([\w.]+) on (\d{4}-\d{2}-\d{2})/);
  if (priceMatch) {
    return `${priceMatch[1]} 在 ${priceMatch[2]} 無收盤價，請先點 nav「更新報價」補抓後重試`;
  }
  if (msg.includes("no common trade_date")) {
    return "組合內部分持股在基準日無報價，請先點 nav「更新報價」補齊";
  }
  return msg;
}

export function AddToPortfolioWizard({
  meta,
  open,
  onOpenChange,
}: AddToPortfolioWizardProps) {
  const queryClient = useQueryClient();
  const { data: savedList } = useQuery({
    queryKey: ["saved-portfolios"],
    queryFn: listSavedPortfolios,
    enabled: open,
  });

  const [step, setStep] = useState<WizardStep>("pick");
  const [baseDetail, setBaseDetail] = useState<SavedPortfolioDetail | null>(
    null,
  );
  const [previewHoldings, setPreviewHoldings] = useState<SavedHolding[]>([]);
  // 編輯中的單格：只維護「目前正在打字的那一列」raw string；
  // 其他列直接從 previewHoldings 格式化顯示，避免兩份 state 漂移。
  const [editing, setEditing] = useState<{ symbol: string; raw: string } | null>(
    null,
  );
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
  });
  const [fetchError, setFetchError] = useState<string | null>(null);

  // 每次打開 wizard 都要回 step 1；關閉時清理 state
  useEffect(() => {
    if (!open) {
      setStep("pick");
      setBaseDetail(null);
      setPreviewHoldings([]);
      setEditing(null);
      setConfirmDialog({ open: false });
      setFetchError(null);
    }
  }, [open]);

  async function handlePickBase(base: SavedPortfolioMeta) {
    setFetchError(null);
    try {
      const detail = await getSavedPortfolio(base.id);
      const merged = buildMergedHoldings({
        existing: detail.holdings,
        symbol: meta.symbol,
        name: meta.name,
        delta: 0.1,
      });
      setBaseDetail(detail);
      setPreviewHoldings(merged);
      setEditing(null);
      setStep("preview");
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "讀取組合失敗");
    }
  }

  function handleWeightChange(symbol: string, raw: string) {
    setEditing({ symbol, raw });
    const trimmed = raw.trim();
    if (trimmed === "") return; // 空字串：保留 raw 顯示、暫不 re-normalize
    const pct = Number(trimmed);
    if (!Number.isFinite(pct)) return; // 非數字（例如「.」）：保留顯示、不更新數值
    setPreviewHoldings((prev) => rebalanceAfterEdit(prev, symbol, pct / 100));
  }

  function handleWeightBlur() {
    setEditing(null);
  }

  function displayWeight(h: SavedHolding): string {
    if (editing && editing.symbol === h.symbol) return editing.raw;
    return (h.weight * 100).toFixed(2);
  }

  function isEditingInvalid(): boolean {
    if (!editing) return false;
    const trimmed = editing.raw.trim();
    if (trimmed === "") return true;
    return !Number.isFinite(Number(trimmed));
  }

  function handleAutoNormalize() {
    setPreviewHoldings((prev) => normalizeToOne(prev));
    setEditing(null);
  }

  const warnings = useMemo(
    () => checkSoftLimits(previewHoldings),
    [previewHoldings],
  );
  const sumValid = isWeightSumValid(previewHoldings);
  const canAutoNormalize =
    !sumValid &&
    previewHoldings.reduce((s, h) => s + h.weight, 0) > 0;

  async function persistHoldings(allowFallback: boolean) {
    if (!baseDetail) return;
    await saveRecommendedPortfolio(
      {
        style: baseDetail.style,
        label: `${baseDetail.label} + ${meta.symbol}`,
        holdings: previewHoldings.map((h) => ({
          symbol: h.symbol,
          name: h.name,
          weight: h.weight,
          base_price: 0,
        })),
        parent_id: baseDetail.id,
      },
      { allowFallback },
    );
  }

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (!baseDetail) throw new Error("尚未選擇基底組合");
      const symbolsToCheck = Array.from(
        new Set(previewHoldings.map((h) => h.symbol)),
      );
      const probe = await probeBaseDate(symbolsToCheck);
      if (!probe.today_available) {
        setConfirmDialog({ open: true, probe });
        return { dialogOpened: true as const };
      }
      await persistHoldings(false);
      return { dialogOpened: false as const };
    },
    onSuccess: async (result) => {
      if (result?.dialogOpened) return;
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      onOpenChange(false);
    },
  });

  const fallbackMutation = useMutation({
    mutationFn: () => persistHoldings(true),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      setConfirmDialog({ open: false });
      onOpenChange(false);
    },
  });

  const pending = confirmMutation.isPending || fallbackMutation.isPending;
  const error = confirmMutation.error ?? fallbackMutation.error ?? null;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent
          className="max-w-xl"
          data-testid={step === "pick" ? "wizard-step-1" : "wizard-step-2"}
        >
          <DialogHeader>
            <DialogTitle>
              {step === "pick"
                ? `加入組合：${meta.symbol} ${meta.name}`
                : `預覽權重：${baseDetail?.label ?? ""} + ${meta.symbol}`}
            </DialogTitle>
            <DialogDescription>
              {step === "pick"
                ? "選一個既有組合作為基底；加入後會複製它並加上新股票。"
                : "每列可手動覆寫權重，其餘持股會等比縮放保持合計 100%。"}
            </DialogDescription>
          </DialogHeader>

          {step === "pick" ? (
            <div className="max-h-80 overflow-y-auto">
              {fetchError ? (
                <p className="mb-2 text-xs text-red-400">{fetchError}</p>
              ) : null}
              {(savedList ?? []).length === 0 ? (
                <p className="text-sm text-slate-400">
                  尚無組合，先到 /portfolios 儲存
                </p>
              ) : (
                <ul className="space-y-1">
                  {(savedList ?? []).map((p) => (
                    <li key={p.id}>
                      <Button
                        variant="outline"
                        onClick={() => void handlePickBase(p)}
                        data-testid={`pick-portfolio-${p.id}`}
                        className="h-auto w-full justify-between py-2 text-left"
                      >
                        <span className="text-slate-100">{p.label}</span>
                        <span className="text-xs text-slate-500">
                          {p.holdings_count} 檔 · 起始 {p.base_date}
                        </span>
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="max-h-72 overflow-y-auto rounded border border-slate-800">
                <table className="w-full text-sm">
                  <thead className="bg-slate-900 text-left text-xs text-slate-400">
                    <tr>
                      <th className="px-2 py-1.5">代號</th>
                      <th className="px-2 py-1.5">名稱</th>
                      <th className="px-2 py-1.5 text-right">權重 %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewHoldings.map((h) => (
                      <tr
                        key={h.symbol}
                        className="border-t border-slate-800"
                        data-testid={`wizard-row-${h.symbol}`}
                      >
                        <td className="px-2 py-1 font-mono text-slate-200">
                          {h.symbol}
                        </td>
                        <td className="px-2 py-1">{h.name}</td>
                        <td className="px-2 py-1 text-right">
                          <Input
                            type="number"
                            inputMode="decimal"
                            min={0}
                            max={100}
                            step={0.1}
                            value={displayWeight(h)}
                            onChange={(e) =>
                              handleWeightChange(h.symbol, e.target.value)
                            }
                            onBlur={handleWeightBlur}
                            data-testid={`wizard-weight-input-${h.symbol}`}
                            className="h-7 w-20 px-2 py-0.5 text-right"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-900 text-xs text-slate-400">
                    <tr>
                      <td className="px-2 py-1" colSpan={2}>
                        合計
                      </td>
                      <td
                        className="px-2 py-1 text-right"
                        data-testid="wizard-sum"
                      >
                        {(
                          previewHoldings.reduce((s, h) => s + h.weight, 0) *
                          100
                        ).toFixed(2)}
                        %
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              <SoftLimitWarningList warnings={warnings} />

              {isEditingInvalid() ? (
                <p
                  className="flex items-center gap-1.5 text-xs text-amber-300"
                  data-testid="wizard-input-invalid"
                >
                  <AlertTriangle className="size-3.5" />
                  請輸入 0~100 的數字；其他列暫未重新分配。
                </p>
              ) : null}

              {!sumValid ? (
                <div
                  className="flex items-center justify-between gap-2 rounded border border-red-700/50 bg-red-500/10 px-2 py-1.5 text-xs text-red-300"
                  data-testid="wizard-sum-invalid"
                >
                  <span>權重合計不是 100%，請調整或一鍵自動補正。</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleAutoNormalize}
                    disabled={!canAutoNormalize}
                    data-testid="wizard-auto-normalize"
                  >
                    <Wand2 />
                    自動補正
                  </Button>
                </div>
              ) : null}
              {error ? (
                <p className="text-xs text-red-400">
                  加入失敗：{humanizeAddError(error)}
                </p>
              ) : null}
            </div>
          )}

          <DialogFooter>
            {step === "preview" ? (
              <Button
                variant="outline"
                onClick={() => setStep("pick")}
                data-testid="wizard-back"
              >
                <ArrowLeft />
                返回上一步
              </Button>
            ) : null}
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              data-testid="wizard-cancel"
            >
              取消
            </Button>
            {step === "preview" ? (
              <Button
                variant="primary"
                onClick={() => confirmMutation.mutate()}
                disabled={pending || !sumValid}
                data-testid="wizard-confirm"
              >
                {pending ? "儲存中…" : "確定建立"}
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <BaseDateConfirmDialog
        open={confirmDialog.open}
        probe={confirmDialog.open ? confirmDialog.probe : null}
        onCancel={() => setConfirmDialog({ open: false })}
        onProceed={() => fallbackMutation.mutate()}
      />
    </>
  );
}
