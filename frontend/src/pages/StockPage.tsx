import { useParams } from "react-router-dom";

import { KeyMetrics } from "@/components/stock/KeyMetrics";
import { PriceChart } from "@/components/stock/PriceChart";
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
    <div className="max-w-5xl mx-auto space-y-8">
      <StockHeader meta={data.meta} />
      <PriceChart points={data.prices} />
      <KeyMetrics
        latestPrice={data.prices[data.prices.length - 1]}
        latestFinancial={data.financials[data.financials.length - 1]}
      />
    </div>
  );
}
