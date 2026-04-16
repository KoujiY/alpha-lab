import { useState } from "react";

import type { ReportType } from "@/api/types";
import { ReportCard } from "@/components/reports/ReportCard";
import { useReports } from "@/hooks/useReports";

const TYPE_OPTIONS: { value: ReportType | "all"; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "stock", label: "個股" },
  { value: "portfolio", label: "組合" },
  { value: "events", label: "事件" },
  { value: "research", label: "研究" },
];

export function ReportsPage() {
  const [typeFilter, setTypeFilter] = useState<ReportType | "all">("all");
  const { data, isLoading, error } = useReports(
    typeFilter === "all" ? undefined : { type: typeFilter },
  );

  return (
    <div className="w-full space-y-4" data-testid="reports-page">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">分析回顧</h1>
          <p className="mt-1 text-sm text-slate-500">
            歷次分析報告（由 Claude Code / 推薦儲存功能寫入 `data/reports/`）
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {TYPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => setTypeFilter(opt.value)}
            aria-pressed={typeFilter === opt.value}
            className={`rounded border px-3 py-1 text-sm ${
              typeFilter === opt.value
                ? "border-sky-500 bg-sky-500/20 text-sky-200"
                : "border-slate-700 text-slate-400 hover:border-slate-500"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {isLoading ? <p className="text-slate-400">載入中...</p> : null}
      {error ? (
        <p className="text-red-400">
          載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
        </p>
      ) : null}
      {data ? (
        data.length === 0 ? (
          <p className="text-slate-500">目前沒有符合條件的報告。</p>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {data.map((meta) => (
              <ReportCard key={meta.id} meta={meta} />
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}
