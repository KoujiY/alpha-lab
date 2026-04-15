import { useQuery } from "@tanstack/react-query";

import { recommendPortfolios } from "@/api/portfolios";
import { PortfolioTabs } from "@/components/portfolio/PortfolioTabs";

export function PortfoliosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["portfolios-recommend"],
    queryFn: () => recommendPortfolios(),
  });

  if (isLoading) {
    return <p className="text-slate-400">載入中...</p>;
  }
  if (error) {
    return (
      <p className="text-red-400">
        載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
      </p>
    );
  }
  if (!data) {
    return null;
  }

  return (
    <div className="w-full space-y-4">
      <div>
        <h1 className="text-2xl font-bold">投資組合推薦</h1>
        <p className="mt-1 text-sm text-slate-500">計算日：{data.calc_date}</p>
      </div>
      <PortfolioTabs portfolios={data.portfolios} />
    </div>
  );
}
