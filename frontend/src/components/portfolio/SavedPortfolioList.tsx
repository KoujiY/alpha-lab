import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listSavedPortfolios } from "@/api/savedPortfolios";

export function SavedPortfolioList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["saved-portfolios"],
    queryFn: listSavedPortfolios,
  });

  if (isLoading) return <p className="text-sm text-slate-400">載入已儲存組合…</p>;
  if (error) return <p className="text-sm text-red-400">載入失敗</p>;
  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        尚未儲存任何組合。點下方「儲存此組合」開始追蹤。
      </p>
    );
  }
  return (
    <ul className="space-y-2" data-testid="saved-portfolio-list">
      {data.map((p) => (
        <li
          key={p.id}
          className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/60 px-3 py-2"
        >
          <div>
            <Link
              to={`/portfolios/${p.id}`}
              className="text-sm text-sky-300 hover:underline"
            >
              {p.label}
            </Link>
            <p className="text-xs text-slate-500">
              {p.style} · {p.holdings_count} 檔 · 起始 {p.base_date}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
