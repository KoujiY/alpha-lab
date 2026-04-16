import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { fetchFactors, filterStocks } from "@/api/screener";
import type { FactorRange, ScreenerStock } from "@/api/types";

export function ScreenerPage() {
  const { data: factorsData, isLoading: factorsLoading } = useQuery({
    queryKey: ["screener-factors"],
    queryFn: fetchFactors,
  });

  const [ranges, setRanges] = useState<Record<string, number>>({});
  const [sortBy, setSortBy] = useState("total_score");
  const [sortDesc, setSortDesc] = useState(true);

  const filterMutation = useMutation({
    mutationFn: (params: {
      filters: FactorRange[];
      sort_by: string;
      sort_desc: boolean;
    }) => filterStocks(params),
  });

  const handleFilter = useCallback(() => {
    if (!factorsData) return;
    const filters: FactorRange[] = factorsData.factors
      .filter((f) => (ranges[f.key] ?? 0) > 0)
      .map((f) => ({
        key: f.key,
        min_value: ranges[f.key] ?? 0,
        max_value: 100,
      }));
    filterMutation.mutate({ filters, sort_by: sortBy, sort_desc: sortDesc });
  }, [factorsData, ranges, sortBy, sortDesc, filterMutation]);

  const handleSliderChange = useCallback(
    (key: string, value: number) => {
      setRanges((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleSort = useCallback(
    (key: string) => {
      if (sortBy === key) {
        setSortDesc((prev) => !prev);
      } else {
        setSortBy(key);
        setSortDesc(true);
      }
    },
    [sortBy],
  );

  if (factorsLoading) {
    return <p className="text-slate-400">載入因子資訊…</p>;
  }

  if (!factorsData) {
    return null;
  }

  return (
    <div className="w-full space-y-6">
      <h1 className="text-2xl font-bold">選股篩選器</h1>

      {/* 因子滑桿區 */}
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-4">
        <h2 className="text-sm font-semibold text-slate-400">
          篩選條件（最低分數）
        </h2>
        {factorsData.factors
          .filter((f) => f.key !== "total_score")
          .map((factor) => (
            <div key={factor.key} className="flex items-center gap-4">
              <label
                className="w-32 text-sm text-slate-300"
                htmlFor={`slider-${factor.key}`}
              >
                {factor.label}
              </label>
              <input
                id={`slider-${factor.key}`}
                type="range"
                min={0}
                max={100}
                step={5}
                value={ranges[factor.key] ?? 0}
                onChange={(e) =>
                  handleSliderChange(factor.key, Number(e.target.value))
                }
                className="flex-1 accent-sky-500"
                data-testid={`slider-${factor.key}`}
              />
              <span className="w-10 text-right text-sm tabular-nums text-slate-300">
                {ranges[factor.key] ?? 0}
              </span>
            </div>
          ))}
        <button
          type="button"
          onClick={handleFilter}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
          data-testid="screener-filter-btn"
        >
          篩選
        </button>
      </div>

      {/* 結果區 */}
      {filterMutation.isPending && (
        <p className="text-slate-400">篩選中…</p>
      )}

      {filterMutation.isError && (
        <div className="rounded-lg border border-amber-700 bg-amber-900/30 p-4">
          <p className="text-amber-300">
            {filterMutation.error instanceof Error &&
            filterMutation.error.message.includes("409")
              ? "尚無評分資料。請先執行評分計算（POST /api/jobs/collect，job_type='score'）。"
              : `篩選失敗：${filterMutation.error instanceof Error ? filterMutation.error.message : "未知錯誤"}`}
          </p>
        </div>
      )}

      {filterMutation.data && (
        <div className="space-y-2">
          <p className="text-sm text-slate-500">
            計算日：{filterMutation.data.calc_date} | 共{" "}
            {filterMutation.data.total_count} 檔符合
          </p>
          {filterMutation.data.stocks.length === 0 ? (
            <p className="text-slate-400">
              沒有符合條件的股票，請調低篩選門檻。
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="screener-results">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-slate-400">
                    <th className="py-2 pr-4">代號</th>
                    <th className="py-2 pr-4">名稱</th>
                    <th className="py-2 pr-4">產業</th>
                    <SortHeader
                      label="價值"
                      sortKey="value_score"
                      current={sortBy}
                      desc={sortDesc}
                      onClick={handleSort}
                    />
                    <SortHeader
                      label="成長"
                      sortKey="growth_score"
                      current={sortBy}
                      desc={sortDesc}
                      onClick={handleSort}
                    />
                    <SortHeader
                      label="股息"
                      sortKey="dividend_score"
                      current={sortBy}
                      desc={sortDesc}
                      onClick={handleSort}
                    />
                    <SortHeader
                      label="品質"
                      sortKey="quality_score"
                      current={sortBy}
                      desc={sortDesc}
                      onClick={handleSort}
                    />
                    <SortHeader
                      label="總分"
                      sortKey="total_score"
                      current={sortBy}
                      desc={sortDesc}
                      onClick={handleSort}
                    />
                  </tr>
                </thead>
                <tbody>
                  {filterMutation.data.stocks.map((stock) => (
                    <StockRow key={stock.symbol} stock={stock} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SortHeaderProps {
  label: string;
  sortKey: string;
  current: string;
  desc: boolean;
  onClick: (key: string) => void;
}

function SortHeader({
  label,
  sortKey,
  current,
  desc,
  onClick,
}: SortHeaderProps) {
  const arrow = current === sortKey ? (desc ? " ▼" : " ▲") : "";
  return (
    <th
      className="cursor-pointer py-2 pr-4 select-none hover:text-sky-300"
      onClick={() => onClick(sortKey)}
    >
      {label}
      {arrow}
    </th>
  );
}

function StockRow({ stock }: { stock: ScreenerStock }) {
  const fmt = (v: number | null) => (v !== null ? v.toFixed(1) : "—");
  return (
    <tr className="border-b border-slate-800 hover:bg-slate-800/50">
      <td className="py-2 pr-4">
        <Link
          to={`/stocks/${stock.symbol}`}
          className="text-sky-400 hover:underline"
        >
          {stock.symbol}
        </Link>
      </td>
      <td className="py-2 pr-4">{stock.name}</td>
      <td className="py-2 pr-4 text-slate-400">{stock.industry ?? "—"}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.value_score)}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.growth_score)}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.dividend_score)}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.quality_score)}</td>
      <td className="py-2 pr-4 tabular-nums font-medium">
        {fmt(stock.total_score)}
      </td>
    </tr>
  );
}
