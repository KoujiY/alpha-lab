import type { StockMeta } from "@/api/types";

interface StockHeaderProps {
  meta: StockMeta;
}

export function StockHeader({ meta }: StockHeaderProps) {
  return (
    <header className="border-b border-slate-800 pb-4 mb-6">
      <h1 className="text-3xl font-bold">
        {meta.symbol} {meta.name}
      </h1>
      <p className="text-slate-400 text-sm mt-1">
        {meta.industry ?? "產業未分類"}
        {meta.listed_date ? ` · 上市於 ${meta.listed_date}` : null}
      </p>
    </header>
  );
}
