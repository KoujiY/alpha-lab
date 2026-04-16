import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { recommendPortfolios } from "@/api/portfolios";
import { saveRecommendedPortfolio } from "@/api/savedPortfolios";
import type { Portfolio, SavedPortfolioMeta } from "@/api/types";
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

  const saveOneMutation = useMutation<SavedPortfolioMeta, Error, Portfolio>({
    mutationFn: (p: Portfolio) =>
      saveRecommendedPortfolio({
        style: p.style,
        label: `${p.label} ${data?.calc_date ?? ""}`.trim(),
        holdings: p.holdings.map((h) => ({
          symbol: h.symbol,
          name: h.name,
          weight: h.weight,
          base_price: 0,
        })),
      }),
    onMutate: () => {
      setSaveOneState({ status: "pending" });
    },
    onSuccess: async (resp) => {
      setSaveOneState({ status: "success", label: resp.label });
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
    },
    onError: (err) => {
      setSaveOneState({
        status: "error",
        message: err instanceof Error ? err.message : "未知錯誤",
      });
    },
  });

  if (isLoading) {
    return <p className="text-slate-400">載入中...</p>;
  }
  if (error) {
    return (
      <p className="text-red-400">
        載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
      </p>
    );
  }
  if (!data) {
    return null;
  }

  return (
    <div className="w-full space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">投資組合推薦</h1>
          <p className="mt-1 text-sm text-slate-500">計算日：{data.calc_date}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveState.status === "pending"}
            className="rounded border border-indigo-500 bg-indigo-500/10 px-3 py-1.5 text-sm text-indigo-300 hover:bg-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            data-testid="save-portfolio-report"
          >
            {saveState.status === "pending" ? "儲存中…" : "儲存此次推薦為報告"}
          </button>
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

      <PortfolioTabs
        portfolios={data.portfolios}
        onSave={(p) => saveOneMutation.mutate(p)}
      />
    </div>
  );
}
