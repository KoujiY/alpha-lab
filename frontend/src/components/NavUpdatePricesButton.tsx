import { useMatch } from "react-router-dom";

import {
  getSavedPortfolio,
  listSavedPortfolios,
} from "@/api/savedPortfolios";
import { readFavorites } from "@/lib/favorites";
import { useUpdatePricesJob } from "@/hooks/useUpdatePricesJob";

/**
 * nav 全局「更新報價」按鈕。
 *
 * 收集要更新的 symbols（union 取集合避免重複）：
 * - 所有 saved portfolios 的持股
 * - localStorage 收藏清單
 * - 當前 URL 為 /stocks/:symbol 時，加入該 symbol（讓使用者在個股頁按一下就覆蓋到瀏覽中的檔）
 *
 * 為什麼不打「更新全部」的 job：後端目前沒有這個 job type，而且也沒意義 —
 * 使用者只關心自己追蹤的標的，batch symbols 較精準也較快。
 *
 * 狀態回饋：按下按鈕後在 nav 下方彈出狀態面板（running 進度 / done 摘要 / error 錯誤），
 * 有關閉按鈕讓使用者手動解除。不用 `title=` 原生 tooltip 因為跨平台行為不一致
 * （macOS / 部分瀏覽器不會顯示或 hover 延遲過長）。
 */
export function NavUpdatePricesButton() {
  const stockMatch = useMatch("/stocks/:symbol");
  const currentStockSymbol = stockMatch?.params.symbol ?? null;

  const { state, run, reset } = useUpdatePricesJob({
    getSymbols: async () => {
      const saved = await listSavedPortfolios();
      const details = await Promise.all(
        saved.map((p) => getSavedPortfolio(p.id)),
      );
      const fromPortfolios = details.flatMap((d) =>
        d.holdings.map((h) => h.symbol),
      );
      const favorites = readFavorites();
      const extras = currentStockSymbol ? [currentStockSymbol] : [];
      return Array.from(
        new Set([...fromPortfolios, ...favorites, ...extras]),
      );
    },
    invalidateKeys: [
      ["saved-portfolios"],
      ["portfolios-recommend"],
      ["stock-overview"],
    ],
  });

  const running = state.status === "running";
  const showPanel = state.status !== "idle";

  let label = "更新報價";
  if (running) label = "更新中…";
  else if (state.status === "done") label = "更新報價 ✓";
  else if (state.status === "error") label = "更新報價 ✗";

  let panelText = "";
  let panelToneClass = "text-slate-300";
  if (state.status === "running") {
    panelText = state.message;
    panelToneClass = "text-amber-300";
  } else if (state.status === "done") {
    panelText = state.summary;
    panelToneClass = "text-emerald-400";
  } else if (state.status === "error") {
    panelText = `失敗：${state.message}`;
    panelToneClass = "text-red-400";
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          void run();
        }}
        disabled={running}
        className="rounded border border-amber-500 bg-amber-500/10 px-2.5 py-1 text-sm text-amber-300 hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
        data-testid="nav-update-prices"
      >
        {label}
      </button>
      {showPanel ? (
        <div
          className="absolute right-0 top-10 z-30 w-80 rounded border border-slate-700 bg-slate-900 p-3 shadow-lg"
          data-testid="nav-update-prices-panel"
        >
          <div className="flex items-start justify-between gap-2">
            <p className={`flex-1 wrap-break-word text-xs ${panelToneClass}`}>
              {panelText}
            </p>
            {!running ? (
              <button
                type="button"
                onClick={reset}
                className="rounded px-1 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                aria-label="關閉狀態"
                data-testid="nav-update-prices-dismiss"
              >
                ✕
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
