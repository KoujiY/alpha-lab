import { Link, useParams } from "react-router-dom";

import { MarkdownRender } from "@/components/MarkdownRender";
import { useReport } from "@/hooks/useReports";

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { data, isLoading, error } = useReport(reportId ?? null);

  if (isLoading) {
    return <p className="text-slate-400">載入中...</p>;
  }
  if (error) {
    return (
      <div className="space-y-2">
        <Link to="/reports" className="text-sm text-sky-300 hover:underline">
          ← 回列表
        </Link>
        <p className="text-red-400">
          載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
        </p>
      </div>
    );
  }
  if (!data) {
    return null;
  }

  return (
    <article
      className="w-full max-w-3xl space-y-4"
      data-testid="report-detail"
    >
      <Link to="/reports" className="text-sm text-sky-300 hover:underline">
        ← 回列表
      </Link>
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="rounded bg-slate-800 px-2 py-0.5">{data.type}</span>
          <span>{data.date}</span>
          {data.symbols.length > 0 ? <span>{data.symbols.join(", ")}</span> : null}
        </div>
        <h1 className="text-2xl font-bold">{data.title}</h1>
        {data.summary_line ? (
          <p className="text-sm text-slate-400">{data.summary_line}</p>
        ) : null}
      </header>
      <MarkdownRender source={data.body_markdown} />
    </article>
  );
}
