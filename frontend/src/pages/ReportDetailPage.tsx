import { Link, useNavigate, useParams } from "react-router-dom";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteReport, updateReport } from "@/api/reports";
import { MarkdownRender } from "@/components/MarkdownRender";
import { useReport } from "@/hooks/useReports";

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useReport(reportId ?? null);

  const starMutation = useMutation({
    mutationFn: (starred: boolean) =>
      updateReport(reportId ?? "", { starred }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteReport(reportId ?? ""),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
      void navigate("/reports");
    },
  });

  function handleDelete() {
    if (window.confirm(`刪除「${data?.title ?? reportId ?? ""}」？`)) {
      deleteMutation.mutate();
    }
  }

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
      <div className="flex items-center justify-between">
        <Link to="/reports" className="text-sm text-sky-300 hover:underline">
          ← 回列表
        </Link>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => starMutation.mutate(!data.starred)}
            data-testid="detail-star-toggle"
            aria-label={data.starred ? "取消加星" : "加星"}
            className="text-base"
          >
            {data.starred ? "★" : "☆"}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            data-testid="detail-delete"
            className="text-xs text-red-400 hover:text-red-300"
          >
            刪除
          </button>
        </div>
      </div>
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
