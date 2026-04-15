import { useQuery } from "@tanstack/react-query";

import { fetchStockOverview } from "@/api/stocks";

export function useStockOverview(symbol: string | undefined) {
  return useQuery({
    queryKey: ["stock-overview", symbol],
    queryFn: () => fetchStockOverview(symbol!),
    enabled: !!symbol,
  });
}
