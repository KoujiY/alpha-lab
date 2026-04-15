import { useParams } from "react-router-dom";

import { EventsSection } from "@/components/stock/EventsSection";
import { FinancialsSection } from "@/components/stock/FinancialsSection";
import { InstitutionalSection } from "@/components/stock/InstitutionalSection";
import { KeyMetrics } from "@/components/stock/KeyMetrics";
import { MarginSection } from "@/components/stock/MarginSection";
import { PriceChart } from "@/components/stock/PriceChart";
import { RevenueSection } from "@/components/stock/RevenueSection";
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
    <div className="w-full space-y-4">
      <StockHeader meta={data.meta} />
      <KeyMetrics
        latestPrice={data.prices[data.prices.length - 1]}
        latestFinancial={data.financials[data.financials.length - 1]}
      />
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 space-y-4">
          <PriceChart points={data.prices} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <RevenueSection points={data.revenues} />
            <InstitutionalSection points={data.institutional} />
          </div>
          <FinancialsSection points={data.financials} />
        </div>
        <aside className="space-y-4 lg:max-h-[calc(100vh-12rem)] lg:overflow-y-auto lg:pr-1">
          <MarginSection points={data.margin} />
          <EventsSection events={data.events} />
        </aside>
      </div>
    </div>
  );
}
