import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { StockMeta } from "@/api/types";
import { useFavorites } from "@/hooks/useFavorites";
import { useStocks } from "@/hooks/useStocks";

const INDUSTRY_ALL = "__all__";

function sortRows(rows: StockMeta[], favoriteSet: Set<string>): StockMeta[] {
  const favFirst = [...rows];
  favFirst.sort((a, b) => {
    const aFav = favoriteSet.has(a.symbol) ? 0 : 1;
    const bFav = favoriteSet.has(b.symbol) ? 0 : 1;
    if (aFav !== bFav) return aFav - bFav;
    return a.symbol.localeCompare(b.symbol);
  });
  return favFirst;
}

export function StocksPage() {
  const [query, setQuery] = useState("");
  const [industry, setIndustry] = useState<string>(INDUSTRY_ALL);
  const { data, isLoading, error } = useStocks();
  const { favorites, isFavorite, toggle } = useFavorites();
  const favoriteSet = useMemo(() => new Set(favorites), [favorites]);

  const industries = useMemo(() => {
    if (!data) return [] as string[];
    const set = new Set<string>();
    for (const s of data) {
      if (s.industry) set.add(s.industry);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [] as StockMeta[];
    const q = query.trim().toLowerCase();
    const byQuery = q
      ? data.filter(
          (s) =>
            s.symbol.toLowerCase().includes(q) ||
            s.name.toLowerCase().includes(q),
        )
      : data;
    const byIndustry =
      industry === INDUSTRY_ALL
        ? byQuery
        : byQuery.filter((s) => s.industry === industry);
    return sortRows(byIndustry, favoriteSet);
  }, [data, query, industry, favoriteSet]);

  return (
    <div className="w-full space-y-4" data-testid="stocks-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">股票瀏覽</h1>
          <p className="mt-1 text-sm text-slate-500">
            全市場上市公司列表（資料源：TWSE `t187ap03_L` 公司基本資料）
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜尋代號或名稱"
            className="w-56 rounded border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm"
            data-testid="stocks-search"
          />
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="rounded border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm"
            data-testid="stocks-industry"
          >
            <option value={INDUSTRY_ALL}>全部產業</option>
            {industries.map((ind) => (
              <option key={ind} value={ind}>
                {ind}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? <p className="text-slate-400">載入中...</p> : null}
      {error ? (
        <p className="text-red-400">
          載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
        </p>
      ) : null}
      {data ? (
        <>
          <p className="text-xs text-slate-500" data-testid="stocks-summary">
            共 {filtered.length} 檔（已收藏 {favorites.length} 檔）
          </p>
          {filtered.length === 0 ? (
            <p className="text-slate-500">沒有符合條件的股票。</p>
          ) : (
            <div className="overflow-x-auto rounded border border-slate-800">
              <table className="w-full text-sm">
                <thead className="bg-slate-900 text-left text-slate-400">
                  <tr>
                    <th className="px-3 py-2 w-10"> </th>
                    <th className="px-3 py-2 w-24">代號</th>
                    <th className="px-3 py-2">名稱</th>
                    <th className="px-3 py-2">產業</th>
                    <th className="px-3 py-2 w-32">上市日期</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => {
                    const fav = isFavorite(s.symbol);
                    return (
                      <tr
                        key={s.symbol}
                        className="border-t border-slate-800 hover:bg-slate-900/40"
                        data-testid={`stock-row-${s.symbol}`}
                      >
                        <td className="px-3 py-2">
                          <button
                            type="button"
                            onClick={() => toggle(s.symbol)}
                            aria-label={fav ? "取消收藏" : "加入收藏"}
                            className="text-base"
                            data-testid={`fav-toggle-${s.symbol}`}
                          >
                            {fav ? "★" : "☆"}
                          </button>
                        </td>
                        <td className="px-3 py-2 font-mono text-slate-200">
                          {s.symbol}
                        </td>
                        <td className="px-3 py-2">
                          <Link
                            to={`/stocks/${encodeURIComponent(s.symbol)}`}
                            className="text-sky-300 hover:text-sky-200"
                          >
                            {s.name}
                          </Link>
                        </td>
                        <td className="px-3 py-2 text-slate-400">
                          {s.industry ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-slate-500">
                          {s.listed_date ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
