import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { recommendPortfolios } from "@/api/portfolios";
import { probeBaseDate, saveRecommendedPortfolio } from "@/api/savedPortfolios";
import type {
  BaseDateProbe,
  Portfolio,
  SavedPortfolioMeta,
} from "@/api/types";
import { BaseDateConfirmDialog } from "@/components/portfolio/BaseDateConfirmDialog";
import { PortfolioTabs } from "@/components/portfolio/PortfolioTabs";
import { SavedPortfolioList } from "@/components/portfolio/SavedPortfolioList";
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
import { checkSoftLimits } from "@/lib/softLimits";

type SaveState =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "success"; savedAt: string }
  | { status: "error"; message: string };

type SaveOneState =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "success"; label: string }
  | { status: "error"; message: string };

type ConfirmDialogState =
  | { open: false }
  | { open: true; portfolio: Portfolio; probe: BaseDateProbe };

type SoftLimitDialogState =
  | { open: false }
  | { open: true; portfolio: Portfolio };

export function PortfoliosPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["portfolios-recommend"],
    queryFn: () => recommendPortfolios(),
  });

  const [saveState, setSaveState] = useState<SaveState>({ status: "idle" });
  const [saveOneState, setSaveOneState] = useState<SaveOneState>({
    status: "idle",
  });
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
  });
  const [softLimitDialog, setSoftLimitDialog] = useState<SoftLimitDialogState>({
    open: false,
  });

  const saveMutation = useMutation({
    mutationFn: () => recommendPortfolios(undefined, { saveReport: true }),
    onMutate: () => {
      setSaveState({ status: "pending" });
    },
    onSuccess: (resp) => {
      setSaveState({ status: "success", savedAt: resp.calc_date });
    },
    onError: (err) => {
      setSaveState({
        status: "error",
        message: err instanceof Error ? err.message : "未知錯誤",
      });
    },
  });

  async function executeSave(
    portfolio: Portfolio,
    allowFallback: boolean,
  ): Promise<SavedPortfolioMeta> {
    return saveRecommendedPortfolio(
      {
        style: portfolio.style,
        label: `${portfolio.label} ${data?.calc_date ?? ""}`.trim(),
        holdings: portfolio.holdings.map((h) => ({
          symbol: h.symbol,
          name: h.name,
          weight: h.weight,
          base_price: 0,
        })),
      },
      { allowFallback },
    );
  }

  async function handleSaveClick(portfolio: Portfolio): Promise<void> {
    const warnings = checkSoftLimits(
      portfolio.holdings.map((h) => ({
        symbol: h.symbol,
        name: h.name,
        weight: h.weight,
        base_price: 0,
      })),
    );
    if (warnings.length > 0) {
      setSoftLimitDialog({ open: true, portfolio });
      return;
    }
    await executeSaveFlow(portfolio);
  }

  async function executeSaveFlow(portfolio: Portfolio): Promise<void> {
    setSaveOneState({ status: "pending" });
    try {
      const symbols = portfolio.holdings.map((h) => h.symbol);
      const probe = await probeBaseDate(symbols);
      if (probe.today_available) {
        const resp = await executeSave(portfolio, false);
        setSaveOneState({ status: "success", label: resp.label });
        await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      } else {
        setSaveOneState({ status: "idle" });
        setConfirmDialog({ open: true, portfolio, probe });
      }
    } catch (err) {
      setSaveOneState({
        status: "error",
        message: err instanceof Error ? err.message : "未知錯誤",
      });
    }
  }

  async function handleConfirmFallback(): Promise<void> {
    if (!confirmDialog.open) return;
    const { portfolio } = confirmDialog;
    setConfirmDialog({ open: false });
    setSaveOneState({ status: "pending" });
    try {
      const resp = await executeSave(portfolio, true);
      setSaveOneState({ status: "success", label: resp.label });
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
    } catch (err) {
      setSaveOneState({
        status: "error",
        message: err instanceof Error ? err.message : "未知錯誤",
      });
    }
  }

  function handleCancelDialog(): void {
    setConfirmDialog({ open: false });
    setSaveOneState({ status: "idle" });
  }

  return (
    <div className="w-full space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">投資組合推薦</h1>
          {data ? (
            <p className="mt-1 text-sm text-slate-500">
              計算日：{data.calc_date}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col items-end gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={saveState.status === "pending" || !data}
            data-testid="save-portfolio-report"
          >
            {saveState.status === "pending" ? "儲存中…" : "儲存此次推薦為報告"}
          </Button>
          <p className="text-xs text-slate-500">
            今日收盤價約於交易日 14:00 後由 TWSE 公告；若需補抓請用 nav「更新報價」
          </p>
          {saveState.status === "success" ? (
            <p className="text-xs text-emerald-400">
              已儲存 portfolio-{saveState.savedAt}
            </p>
          ) : null}
          {saveState.status === "error" ? (
            <p className="text-xs text-red-400">儲存失敗：{saveState.message}</p>
          ) : null}
        </div>
      </div>

      <section className="rounded border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">已儲存組合</h2>
        <SavedPortfolioList />
      </section>

      <div className="flex flex-col items-end gap-1">
        {saveOneState.status === "pending" ? (
          <p className="text-xs text-slate-400">儲存組合中…</p>
        ) : null}
        {saveOneState.status === "success" ? (
          <p className="text-xs text-emerald-400">
            已儲存「{saveOneState.label}」
          </p>
        ) : null}
        {saveOneState.status === "error" ? (
          <p className="text-xs text-red-400">
            儲存組合失敗：{saveOneState.message}
          </p>
        ) : null}
      </div>

      {isLoading ? (
        <p className="text-slate-400">推薦載入中...</p>
      ) : error ? (
        <p className="text-red-400">
          推薦載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
        </p>
      ) : data ? (
        <PortfolioTabs
          portfolios={data.portfolios}
          onSave={(p) => {
            void handleSaveClick(p);
          }}
        />
      ) : null}

      <BaseDateConfirmDialog
        open={confirmDialog.open}
        probe={confirmDialog.open ? confirmDialog.probe : null}
        onCancel={handleCancelDialog}
        onProceed={() => {
          void handleConfirmFallback();
        }}
      />

      <Dialog
        open={softLimitDialog.open}
        onOpenChange={(o) => {
          if (!o) setSoftLimitDialog({ open: false });
        }}
      >
        <DialogContent data-testid="soft-limit-dialog" showClose={false}>
          <DialogHeader>
            <DialogTitle>組合結構提醒</DialogTitle>
            <DialogDescription>
              這個組合觸發了幾個非阻擋的建議，仍可儲存。
            </DialogDescription>
          </DialogHeader>
          {softLimitDialog.open ? (
            <SoftLimitWarningList
              warnings={checkSoftLimits(
                softLimitDialog.portfolio.holdings.map((h) => ({
                  symbol: h.symbol,
                  name: h.name,
                  weight: h.weight,
                  base_price: 0,
                })),
              )}
            />
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSoftLimitDialog({ open: false })}
              data-testid="soft-limit-cancel"
            >
              取消
            </Button>
            <Button
              variant="warn"
              onClick={() => {
                if (softLimitDialog.open) {
                  const { portfolio } = softLimitDialog;
                  setSoftLimitDialog({ open: false });
                  void executeSaveFlow(portfolio);
                }
              }}
              data-testid="soft-limit-proceed"
            >
              仍要儲存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
