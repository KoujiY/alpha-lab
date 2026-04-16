import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { createCollectJob, getJobStatus } from "@/api/jobs";
import { recommendPortfolios } from "@/api/portfolios";
import { probeBaseDate, saveRecommendedPortfolio } from "@/api/savedPortfolios";
import type {
  BaseDateProbe,
  Portfolio,
  SavedPortfolioMeta,
} from "@/api/types";
import { PortfolioTabs } from "@/components/portfolio/PortfolioTabs";
import { SavedPortfolioList } from "@/components/portfolio/SavedPortfolioList";

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

type UpdatePricesState =
  | { status: "idle" }
  | { status: "running"; jobId: number; message: string }
  | { status: "done"; summary: string }
  | { status: "error"; message: string };

type ConfirmDialogState =
  | { open: false }
  | { open: true; portfolio: Portfolio; probe: BaseDateProbe };

const POLL_INTERVAL_MS = 2000;

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
  const [updateState, setUpdateState] = useState<UpdatePricesState>({
    status: "idle",
  });
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
  });

  const allSymbols = data
    ? Array.from(
        new Set(
          data.portfolios.flatMap((p) => p.holdings.map((h) => h.symbol)),
        ),
      )
    : [];

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

  async function pollJobUntilDone(jobId: number): Promise<void> {
    while (true) {
      const job = await getJobStatus(jobId);
      if (job.status === "completed") {
        setUpdateState({
          status: "done",
          summary: job.result_summary ?? "完成",
        });
        await queryClient.invalidateQueries({
          queryKey: ["portfolios-recommend"],
        });
        return;
      }
      if (job.status === "failed") {
        setUpdateState({
          status: "error",
          message: job.error_message ?? "未知錯誤",
        });
        return;
      }
      setUpdateState({
        status: "running",
        jobId,
        message: `更新中…（${job.status}，輪詢中）`,
      });
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
  }

  async function handleUpdatePrices(): Promise<void> {
    if (allSymbols.length === 0) return;
    setUpdateState({
      status: "running",
      jobId: 0,
      message: `啟動中…共 ${allSymbols.length} 檔`,
    });
    try {
      const job = await createCollectJob({
        type: "twse_prices_batch",
        params: { symbols: allSymbols },
      });
      setUpdateState({
        status: "running",
        jobId: job.id,
        message: `已派出 job #${job.id}，更新 ${allSymbols.length} 檔報價`,
      });
      await pollJobUntilDone(job.id);
    } catch (err) {
      setUpdateState({
        status: "error",
        message: err instanceof Error ? err.message : "未知錯誤",
      });
    }
  }

  const updateRunning = updateState.status === "running";

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
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleUpdatePrices}
              disabled={updateRunning || !data || allSymbols.length === 0}
              className="rounded border border-amber-500 bg-amber-500/10 px-3 py-1.5 text-sm text-amber-300 hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              data-testid="update-today-prices"
            >
              {updateRunning ? "更新中…" : "更新今日報價"}
            </button>
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveState.status === "pending" || !data}
              className="rounded border border-indigo-500 bg-indigo-500/10 px-3 py-1.5 text-sm text-indigo-300 hover:bg-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              data-testid="save-portfolio-report"
            >
              {saveState.status === "pending" ? "儲存中…" : "儲存此次推薦為報告"}
            </button>
          </div>
          <p className="text-xs text-slate-500">
            今日收盤價約於交易日 14:00 後由 TWSE 公告（週末/假日不交易）
          </p>
          {updateState.status === "running" ? (
            <p className="text-xs text-amber-300">{updateState.message}</p>
          ) : null}
          {updateState.status === "done" ? (
            <p className="text-xs text-emerald-400">{updateState.summary}</p>
          ) : null}
          {updateState.status === "error" ? (
            <p className="text-xs text-red-400">
              更新失敗：{updateState.message}
            </p>
          ) : null}
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

      {confirmDialog.open ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          data-testid="save-confirm-dialog"
        >
          <div className="max-w-md rounded border border-slate-700 bg-slate-900 p-5 shadow-xl">
            <h3 className="mb-2 text-base font-semibold text-amber-300">
              今日報價不齊
            </h3>
            <p className="mb-2 text-sm text-slate-300">
              下列持股在 {confirmDialog.probe.target_date} 還沒有收盤價：
            </p>
            <p className="mb-3 text-xs text-slate-500">
              提醒：TWSE 通常於交易日 14:00 後公告當日收盤價，盤中或非交易日可能尚未有資料。
            </p>
            <p className="mb-3 break-all text-sm font-mono text-amber-200">
              {confirmDialog.probe.missing_today_symbols.join("、")}
            </p>
            {confirmDialog.probe.resolved_date ? (
              <p className="mb-4 text-sm text-slate-300">
                可以以最近所有持股都有報價的日期{" "}
                <strong className="text-slate-100">
                  {confirmDialog.probe.resolved_date}
                </strong>{" "}
                為基準儲存；或先「取消」再點上方「更新今日報價」補抓。
              </p>
            ) : (
              <p className="mb-4 text-sm text-red-300">
                找不到任何「全持股都有報價」的歷史日期，請先點「更新今日報價」補抓。
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCancelDialog}
                className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
                data-testid="save-confirm-cancel"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => {
                  void handleConfirmFallback();
                }}
                disabled={confirmDialog.probe.resolved_date === null}
                className="rounded border border-amber-500 bg-amber-500/10 px-3 py-1.5 text-sm text-amber-200 hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                data-testid="save-confirm-proceed"
              >
                以 {confirmDialog.probe.resolved_date ?? "—"} 為基準繼續
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
