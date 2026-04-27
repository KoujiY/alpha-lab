import { Star, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteReport, updateReport } from "@/api/reports";
import { MarkdownRender } from "@/components/MarkdownRender";
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
import { IconButton } from "@/components/ui/icon-button";
import { useReport } from "@/hooks/useReports";
import { getCachedReport } from "@/lib/reportCache";

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useReport(reportId ?? null);

  const [isCached, setIsCached] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  useEffect(() => {
    if (!reportId) return;
    getCachedReport(reportId).then((c) => setIsCached(c !== undefined));
  }, [reportId, data]);

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
        <div className="flex items-center gap-1">
          <IconButton
            label={data.starred ? "取消加星" : "加星"}
            data-testid="detail-star-toggle"
            aria-pressed={data.starred}
            onClick={() => starMutation.mutate(!data.starred)}
          >
            <Star
              className={
                data.starred
                  ? "fill-amber-300 text-amber-300"
                  : "text-slate-400"
              }
            />
          </IconButton>
          <IconButton
            label="刪除"
            data-testid="detail-delete"
            className="text-red-400 hover:text-red-300"
            onClick={() => setConfirmDelete(true)}
          >
            <Trash2 />
          </IconButton>
        </div>
      </div>
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="rounded bg-slate-800 px-2 py-0.5">{data.type}</span>
          <span>{data.date}</span>
          {data.symbols.length > 0 ? <span>{data.symbols.join(", ")}</span> : null}
        </div>
        <h1 className="text-2xl font-bold">
          {data.title}
          {isCached && (
            <span
              className="ml-2 align-middle rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-normal text-emerald-300"
              data-testid="cache-badge"
            >
              已快取
            </span>
          )}
        </h1>
        {data.summary_line ? (
          <p className="text-sm text-slate-400">{data.summary_line}</p>
        ) : null}
      </header>
      <MarkdownRender source={data.body_markdown} />

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent data-testid="detail-delete-confirm">
          <AlertDialogHeader>
            <AlertDialogTitle>確定刪除這份報告？</AlertDialogTitle>
            <AlertDialogDescription>
              「{data.title}」刪除後無法復原。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="detail-delete-cancel">
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              data-testid="detail-delete-proceed"
              onClick={() => deleteMutation.mutate()}
            >
              刪除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </article>
  );
}
