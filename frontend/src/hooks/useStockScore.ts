import { useQuery } from "@tanstack/react-query";

import { fetchStockScore } from "@/api/scores";

export function useStockScore(symbol: string | undefined) {
  return useQuery({
    queryKey: ["stock-score", symbol],
    queryFn: () => fetchStockScore(symbol!),
    enabled: !!symbol,
  });
}
