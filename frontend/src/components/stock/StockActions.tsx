import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import {
  getSavedPortfolio,
  listSavedPortfolios,
  probeBaseDate,
  saveRecommendedPortfolio,
} from "@/api/savedPortfolios";
import type { BaseDateProbe, SavedPortfolioDetail, StockMeta } from "@/api/types";
import { BaseDateConfirmDialog } from "@/components/portfolio/BaseDateConfirmDialog";
import { isFavorite, toggleFavorite } from "@/lib/favorites";
import { buildMergedHoldings } from "@/lib/portfolioMerge";

interface StockActionsProps {
  meta: StockMeta;
}

type ConfirmDialogState =
  | { open: false }
  | { open: true; detail: SavedPortfolioDetail; probe: BaseDateProbe };

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

export function StockActions({ meta }: StockActionsProps) {
  const [fav, setFav] = useState(false);
  useEffect(() => {
    setFav(isFavorite(meta.symbol));
  }, [meta.symbol]);

  const queryClient = useQueryClient();
  const { data: savedList } = useQuery({
    queryKey: ["saved-portfolios"],
    queryFn: listSavedPortfolios,
  });
  const [pickerOpen, setPickerOpen] = useState(false);
  const [weightPct, setWeightPct] = useState("10");
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
  });

  async function persistMerged(
    detail: SavedPortfolioDetail,
    allowFallback: boolean,
  ): Promise<void> {
    const delta = Number(weightPct) / 100;
    const merged = buildMergedHoldings({
      existing: detail.holdings,
      symbol: meta.symbol,
      name: meta.name,
      delta,
    });
    await saveRecommendedPortfolio(
      {
        style: detail.style,
        label: `${detail.label} + ${meta.symbol}`,
        holdings: merged,
        parent_id: detail.id,
      },
      { allowFallback },
    );
  }

  const addToExistingMutation = useMutation({
    mutationFn: async ({ portfolioId }: { portfolioId: number }) => {
      const target = savedList?.find((p) => p.id === portfolioId);
      if (!target) throw new Error("組合不存在");

      const detail = await getSavedPortfolio(portfolioId);

      // probe base date：若 meta.symbol 今日無價 或 既有持股今日任一無價，
      // 跳 BaseDateConfirmDialog 讓使用者選「取消去更新」或「用歷史日期繼續」
      const symbolsToCheck = Array.from(
        new Set([
          meta.symbol,
          ...detail.holdings.map((h) => h.symbol),
        ]),
      );
      const probe = await probeBaseDate(symbolsToCheck);
      if (!probe.today_available) {
        setConfirmDialog({ open: true, detail, probe });
        return { dialogOpened: true as const };
      }

      await persistMerged(detail, false);
      return { dialogOpened: false as const };
    },
    onSuccess: async (result) => {
      if (result?.dialogOpened) return;
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      setPickerOpen(false);
    },
  });

  const confirmFallbackMutation = useMutation({
    mutationFn: async (detail: SavedPortfolioDetail) => {
      await persistMerged(detail, true);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      setConfirmDialog({ open: false });
      setPickerOpen(false);
    },
  });

  const weightNum = Number(weightPct);
  const remainderPct =
    Number.isFinite(weightNum) && weightNum > 0 && weightNum < 100
      ? 100 - weightNum
      : null;

  const addPending =
    addToExistingMutation.isPending || confirmFallbackMutation.isPending;
  const addError =
    addToExistingMutation.error ?? confirmFallbackMutation.error ?? null;

  return (
    <div
      className="relative flex items-center gap-2"
      data-testid="stock-actions"
    >
      <button
        type="button"
        onClick={() => {
          toggleFavorite(meta.symbol);
          setFav((v) => !v);
        }}
        className="rounded border border-slate-700 bg-slate-900/60 px-2.5 py-1 text-sm"
        data-testid="favorite-toggle"
        aria-pressed={fav}
      >
        {fav ? "★ 已收藏" : "☆ 收藏"}
      </button>
      <button
        type="button"
        onClick={() => setPickerOpen((o) => !o)}
        className="rounded border border-indigo-500 bg-indigo-500/10 px-2.5 py-1 text-sm text-indigo-300 hover:bg-indigo-500/20"
        data-testid="add-to-portfolio"
        aria-expanded={pickerOpen}
      >
        加入組合
      </button>
      {pickerOpen ? (
        <div
          className="absolute right-0 top-10 z-20 w-64 rounded border border-slate-700 bg-slate-900 p-3 shadow-lg"
          data-testid="portfolio-picker"
        >
          <p className="mb-2 text-xs text-slate-400">選擇組合</p>
          <ul className="mb-2 max-h-40 space-y-1 overflow-y-auto">
            {(savedList ?? []).map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() =>
                    addToExistingMutation.mutate({ portfolioId: p.id })
                  }
                  className="w-full rounded px-2 py-1 text-left text-sm hover:bg-slate-800"
                  data-testid={`pick-portfolio-${p.id}`}
                  disabled={addPending}
                >
                  {p.label}
                </button>
              </li>
            ))}
            {(savedList ?? []).length === 0 ? (
              <li className="text-xs text-slate-500">
                尚無組合，先到 /portfolios 儲存
              </li>
            ) : null}
          </ul>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            新持股權重
            <input
              type="number"
              min="1"
              max="99"
              value={weightPct}
              onChange={(e) => setWeightPct(e.target.value)}
              className="w-16 rounded border border-slate-700 bg-slate-800 px-1 py-0.5"
            />
            %
          </label>
          <p className="mt-1 text-[10px] text-slate-500">
            其他持股會等比例稀釋到{" "}
            {remainderPct !== null ? `${remainderPct}%` : "—"}
          </p>
          {addError ? (
            <p className="mt-2 text-xs text-red-400">
              加入失敗：{humanizeAddError(addError)}
            </p>
          ) : null}
        </div>
      ) : null}
      <BaseDateConfirmDialog
        open={confirmDialog.open}
        probe={confirmDialog.open ? confirmDialog.probe : null}
        onCancel={() => setConfirmDialog({ open: false })}
        onProceed={() => {
          if (confirmDialog.open) {
            confirmFallbackMutation.mutate(confirmDialog.detail);
          }
        }}
      />
    </div>
  );
}
