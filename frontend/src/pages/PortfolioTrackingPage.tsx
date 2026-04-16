import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { deleteSavedPortfolio, fetchPerformance } from "@/api/savedPortfolios";
import { PerformanceChart } from "@/components/portfolio/PerformanceChart";

export function PortfolioTrackingPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["portfolio-performance", portfolioId],
    queryFn: () => fetchPerformance(portfolioId),
    enabled: !Number.isNaN(portfolioId),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSavedPortfolio(portfolioId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      navigate("/portfolios");
    },
  });

  if (Number.isNaN(portfolioId)) {
    return <p className="text-red-400">非法的組合 id</p>;
  }
  if (isLoading) return <p className="text-slate-400">載入中…</p>;
  if (error || !data) {
    return <p className="text-red-400">載入失敗</p>;
  }

  const {
    portfolio,
    points,
    latest_nav,
    total_return,
    parent_points,
    parent_nav_at_fork,
  } = data;
  const returnPct = (total_return * 100).toFixed(2);
  const returnColor = total_return >= 0 ? "text-emerald-400" : "text-red-400";

  const hasLineage =
    portfolio.parent_id != null && portfolio.parent_nav_at_fork != null;
  const continuousReturn = hasLineage
    ? (portfolio.parent_nav_at_fork as number) * latest_nav - 1.0
    : null;
  const continuousPct =
    continuousReturn != null ? (continuousReturn * 100).toFixed(2) : null;
  const continuousColor =
    continuousReturn != null && continuousReturn >= 0
      ? "text-emerald-400"
      : "text-red-400";

  return (
    <div className="space-y-4" data-testid="portfolio-tracking-page">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{portfolio.label}</h1>
          <p className="text-sm text-slate-500">
            {portfolio.style} · 起始 {portfolio.base_date} ·{" "}
            {portfolio.holdings_count} 檔
          </p>
          {hasLineage ? (
            <p
              className="mt-1 text-xs text-amber-300"
              data-testid="lineage-info"
            >
              由{" "}
              <Link
                to={`/portfolios/${portfolio.parent_id}`}
                className="underline hover:text-amber-200"
                data-testid="lineage-parent-link"
              >
                組合 #{portfolio.parent_id}
              </Link>{" "}
              分裂 · fork NAV {portfolio.parent_nav_at_fork?.toFixed(4)}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => {
            if (window.confirm(`確定刪除組合「${portfolio.label}」？`)) {
              deleteMutation.mutate();
            }
          }}
          className="rounded border border-red-500 bg-red-500/10 px-3 py-1.5 text-sm text-red-300 hover:bg-red-500/20"
          data-testid="delete-portfolio"
        >
          刪除
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
          <p className="text-xs text-slate-500">目前 NAV</p>
          <p className="text-lg font-semibold">{latest_nav.toFixed(4)}</p>
        </div>
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
          <p className="text-xs text-slate-500">累積報酬</p>
          <p className={`text-lg font-semibold ${returnColor}`}>{returnPct}%</p>
        </div>
        {continuousPct != null ? (
          <div
            className="rounded border border-amber-700 bg-amber-900/20 p-3"
            data-testid="continuous-return-card"
          >
            <p className="text-xs text-amber-300">自母組合起報酬</p>
            <p className={`text-lg font-semibold ${continuousColor}`}>
              {continuousPct}%
            </p>
          </div>
        ) : null}
      </div>

      <section className="rounded border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">NAV 走勢</h2>
        <PerformanceChart
          points={points}
          parentPoints={parent_points}
          parentNavAtFork={parent_nav_at_fork}
          childBaseDate={portfolio.base_date}
        />
      </section>

      <section className="rounded border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">持股明細</h2>
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1 text-left">代號</th>
              <th className="py-1 text-left">名稱</th>
              <th className="py-1 text-right">權重</th>
              <th className="py-1 text-right">基準價</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map((h) => (
              <tr key={h.symbol} className="border-t border-slate-800">
                <td className="py-1">{h.symbol}</td>
                <td className="py-1">{h.name}</td>
                <td className="py-1 text-right">
                  {(h.weight * 100).toFixed(1)}%
                </td>
                <td className="py-1 text-right">{h.base_price.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
