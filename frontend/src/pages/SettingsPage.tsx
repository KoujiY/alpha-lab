import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

import { listAllStocks } from "@/api/stocks";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useFavorites } from "@/hooks/useFavorites";
import {
  useTutorialMode,
  type TutorialMode,
} from "@/contexts/TutorialModeContext";
import { clearReportCache, listCachedReportIds } from "@/lib/reportCache";

const TUTORIAL_OPTIONS: { value: TutorialMode; label: string; desc: string }[] =
  [
    { value: "full", label: "完整教學", desc: "顯示所有 L1 tooltip 與 L2 面板" },
    { value: "compact", label: "精簡", desc: "僅在首次出現時提示" },
    { value: "off", label: "關閉", desc: "不顯示教學提示" },
  ];

export function SettingsPage() {
  const { mode, setMode } = useTutorialMode();
  const { favorites, toggle } = useFavorites();
  // 只有使用者有收藏時才觸發 /api/stocks 全量載入，避免空收藏情境白白下載 3000 檔
  const stocksEnabled = favorites.length > 0;
  const { data: stocks, isLoading: stocksLoading } = useQuery({
    queryKey: ["stocks", "list", ""],
    queryFn: () => listAllStocks(),
    staleTime: 5 * 60 * 1000,
    enabled: stocksEnabled,
  });
  const [cachedCount, setCachedCount] = useState<number | null>(null);
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);

  useEffect(() => {
    void listCachedReportIds().then((ids) => setCachedCount(ids.length));
  }, []);

  const nameMap = new Map((stocks ?? []).map((s) => [s.symbol, s.name]));
  function displayName(symbol: string): string {
    if (!stocksEnabled) return "";
    if (stocksLoading) return "（載入中…）";
    return nameMap.get(symbol) ?? "（查無資料，可能已下市）";
  }

  async function executeClearCache() {
    await clearReportCache();
    setCachedCount(0);
    setClearConfirmOpen(false);
  }

  return (
    <div className="w-full space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-bold">設定</h1>
        <p className="mt-1 text-sm text-slate-500">
          使用者偏好（存於瀏覽器 localStorage，不同瀏覽器 / 裝置不共用）
        </p>
      </div>

      <section
        className="rounded border border-slate-800 bg-slate-900/40 p-4"
        data-testid="settings-tutorial"
      >
        <h2 className="text-lg font-semibold">教學密度</h2>
        <p className="mt-1 text-xs text-slate-500">
          影響 L1 術語 tooltip 與 L2 詳解面板的呈現程度
        </p>
        <RadioGroup
          value={mode}
          onValueChange={(v) => setMode(v as TutorialMode)}
          className="mt-3 space-y-2"
        >
          {TUTORIAL_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className="flex cursor-pointer items-start gap-3 rounded p-2 hover:bg-slate-800/40"
            >
              <RadioGroupItem
                value={opt.value}
                data-testid={`tutorial-option-${opt.value}`}
                className="mt-1"
              />
              <div>
                <div className="text-sm text-slate-200">{opt.label}</div>
                <div className="text-xs text-slate-500">{opt.desc}</div>
              </div>
            </label>
          ))}
        </RadioGroup>
      </section>

      <section
        className="rounded border border-slate-800 bg-slate-900/40 p-4"
        data-testid="settings-favorites"
      >
        <h2 className="text-lg font-semibold">收藏股票</h2>
        <p className="mt-1 text-xs text-slate-500">
          從個股頁或股票列表加入；共 {favorites.length} 檔
        </p>
        {favorites.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">
            目前沒有收藏。到{" "}
            <a href="/stocks" className="text-sky-300 hover:text-sky-200">
              股票列表
            </a>{" "}
            加星收藏。
          </p>
        ) : (
          <ul className="mt-3 space-y-1">
            {favorites.map((symbol) => (
              <li
                key={symbol}
                className="flex items-center justify-between rounded bg-slate-950/40 px-3 py-2 text-sm"
                data-testid={`favorite-row-${symbol}`}
              >
                <span>
                  <span className="font-mono text-slate-200">{symbol}</span>
                  <span className="ml-2 text-slate-400">
                    {displayName(symbol)}
                  </span>
                </span>
                <IconButton
                  label="移除收藏"
                  onClick={() => toggle(symbol)}
                  data-testid={`favorite-remove-${symbol}`}
                  className="text-red-400 hover:text-red-300"
                >
                  <X />
                </IconButton>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        className="rounded border border-slate-800 bg-slate-900/40 p-4"
        data-testid="settings-cache"
      >
        <h2 className="text-lg font-semibold">離線報告快取</h2>
        <p className="mt-1 text-xs text-slate-500">
          報告打開時會存到 IndexedDB，離線時可回放；清空不影響伺服器端的檔案
        </p>
        <div className="mt-3 flex items-center justify-between">
          <span className="text-sm text-slate-300" data-testid="cache-count">
            已快取 {cachedCount ?? "…"} 篇報告
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setClearConfirmOpen(true)}
            disabled={cachedCount === 0}
            data-testid="cache-clear"
          >
            清空快取
          </Button>
        </div>
      </section>

      <AlertDialog
        open={clearConfirmOpen}
        onOpenChange={setClearConfirmOpen}
      >
        <AlertDialogContent data-testid="cache-clear-confirm">
          <AlertDialogHeader>
            <AlertDialogTitle>清空離線報告快取？</AlertDialogTitle>
            <AlertDialogDescription>
              清除後下次開啟報告會重新向伺服器抓取，但不影響伺服器端檔案。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="cache-clear-cancel">
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              data-testid="cache-clear-proceed"
              onClick={() => void executeClearCache()}
            >
              清空
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
