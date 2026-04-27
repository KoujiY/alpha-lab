import { X } from "lucide-react";
import { useMatch } from "react-router-dom";

import {
  getSavedPortfolio,
  listSavedPortfolios,
} from "@/api/savedPortfolios";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from "@/components/ui/popover";
import { useUpdatePricesJob } from "@/hooks/useUpdatePricesJob";
import { readFavorites } from "@/lib/favorites";

/**
 * nav 全局「更新報價」按鈕。
 *
 * 收集要更新的 symbols（union 取集合避免重複）：
 * - 所有 saved portfolios 的持股
 * - localStorage 收藏清單
 * - 當前 URL 為 /stocks/:symbol 時，加入該 symbol
 *
 * 狀態回饋：按下後在 nav 下方彈出 shadcn Popover 狀態面板，
 * Popover 的 open 由 job state 驅動（而非 Radix trigger），所以用 open prop 控制
 * + PopoverAnchor 對齊按鈕。結束時可點 X 手動關閉。
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
    <Popover
      open={showPanel}
      onOpenChange={(o) => {
        if (!o && !running) reset();
      }}
    >
      <PopoverAnchor asChild>
        <Button
          variant="warn"
          size="sm"
          onClick={() => {
            void run();
          }}
          disabled={running}
          data-testid="nav-update-prices"
        >
          {label}
        </Button>
      </PopoverAnchor>
      <PopoverContent
        data-testid="nav-update-prices-panel"
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <div className="flex items-start justify-between gap-2">
          <p className={`flex-1 break-words text-xs ${panelToneClass}`}>
            {panelText}
          </p>
          {!running ? (
            <IconButton
              label="關閉狀態"
              size="sm"
              onClick={reset}
              data-testid="nav-update-prices-dismiss"
            >
              <X />
            </IconButton>
          ) : null}
        </div>
      </PopoverContent>
    </Popover>
  );
}
