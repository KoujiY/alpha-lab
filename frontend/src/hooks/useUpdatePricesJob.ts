import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { createCollectJob, getJobStatus } from "@/api/jobs";

/**
 * 更新今日報價（daily_collect batch）用的共用狀態機 + 輪詢邏輯。
 *
 * 為什麼抽 hook：
 * - 原本只有 /portfolios 頁面有這個按鈕，但「今日沒跑 daily_collect → 想加入組合會撞
 *   no-price 錯」的情境在個股頁、screener、events 都會發生
 * - 共用 hook 可以讓 nav 全域按鈕 / 各頁 inline 按鈕複用同一套狀態機，不重複
 *
 * `getSymbols` 由呼叫端決定要更新哪些 symbols：
 * - nav 版本：聚合所有 saved portfolios 的 holdings + favorites
 * - /portfolios 頁：該次推薦結果的 allSymbols
 */
export type UpdatePricesState =
  | { status: "idle" }
  | { status: "running"; jobId: number; message: string }
  | { status: "done"; summary: string }
  | { status: "error"; message: string };

export interface UseUpdatePricesJobArgs {
  getSymbols: () => Promise<string[]> | string[];
  /** 成功後要 invalidate 的 query keys，用於觸發頁面重新抓資料 */
  invalidateKeys?: readonly (readonly string[])[];
}

const POLL_INTERVAL_MS = 2000;

export function useUpdatePricesJob(args: UseUpdatePricesJobArgs): {
  state: UpdatePricesState;
  run: () => Promise<void>;
  reset: () => void;
} {
  const queryClient = useQueryClient();
  const [state, setState] = useState<UpdatePricesState>({ status: "idle" });

  async function pollUntilDone(jobId: number): Promise<void> {
    while (true) {
      const job = await getJobStatus(jobId);
      if (job.status === "completed") {
        setState({ status: "done", summary: job.result_summary ?? "完成" });
        if (args.invalidateKeys) {
          await Promise.all(
            args.invalidateKeys.map((key) =>
              queryClient.invalidateQueries({ queryKey: [...key] }),
            ),
          );
        }
        return;
      }
      if (job.status === "failed") {
        setState({
          status: "error",
          message: job.error_message ?? "未知錯誤",
        });
        return;
      }
      setState({
        status: "running",
        jobId,
        message: `更新中…（${job.status}）`,
      });
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
  }

  async function run(): Promise<void> {
    try {
      const symbols = await args.getSymbols();
      if (symbols.length === 0) {
        setState({ status: "error", message: "沒有要更新的 symbols" });
        return;
      }
      setState({
        status: "running",
        jobId: 0,
        message: `啟動中…共 ${symbols.length} 檔`,
      });
      const job = await createCollectJob({
        type: "twse_prices_batch",
        params: { symbols },
      });
      setState({
        status: "running",
        jobId: job.id,
        message: `已派出 job #${job.id}，更新 ${symbols.length} 檔`,
      });
      await pollUntilDone(job.id);
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "未知錯誤",
      });
    }
  }

  function reset(): void {
    setState({ status: "idle" });
  }

  return { state, run, reset };
}
