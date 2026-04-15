import { useParams } from "react-router-dom";

import { StockHeader } from "@/components/stock/StockHeader";
import { useStockOverview } from "@/hooks/useStockOverview";

export function StockPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const { data, isLoading, error } = useStockOverview(symbol);

  if (!symbol) {
    return <p className="text-slate-400">找不到股票代號。</p>;
  }
  if (isLoading) {
    return <p className="text-slate-400">載入中...</p>;
  }
  if (error || !data) {
    return (
      <p className="text-red-400">
        載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
      </p>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <StockHeader meta={data.meta} />
      {/* section 元件將於 Task F2-F4 插入此區 */}
      <p className="text-slate-500 text-sm">
        共 {data.prices.length} 筆股價、{data.revenues.length} 筆月營收、
        {data.financials.length} 季財報。
      </p>
    </div>
  );
}
