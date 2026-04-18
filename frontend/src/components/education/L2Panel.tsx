import { X } from "lucide-react";

import { MarkdownRender } from "@/components/MarkdownRender";
import { IconButton } from "@/components/ui/icon-button";
import { useL2Topic } from "@/hooks/useL2Topic";

import { useL2Panel } from "./L2PanelContext";

export function L2Panel() {
  const { activeTopicId, closePanel } = useL2Panel();
  const { data, isLoading, error } = useL2Topic(activeTopicId);

  if (activeTopicId === null) {
    return null;
  }

  return (
    <aside
      role="complementary"
      aria-label="詳解面板"
      className="fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col border-l border-slate-800 bg-slate-950 shadow-2xl"
    >
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <h2 className="text-lg font-semibold text-slate-100">
          {data?.title ?? "載入中…"}
        </h2>
        <IconButton label="關閉詳解面板" onClick={closePanel}>
          <X />
        </IconButton>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isLoading && <p className="text-slate-400">載入中…</p>}
        {error && (
          <p className="text-red-400">
            載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
          </p>
        )}
        {data && <MarkdownRender source={data.body_markdown} />}
        {data && data.related_terms.length > 0 && (
          <div className="mt-6 border-t border-slate-800 pt-3 text-sm text-slate-400">
            相關術語：{data.related_terms.join("、")}
          </div>
        )}
      </div>
    </aside>
  );
}
