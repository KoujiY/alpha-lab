import { useQuery } from "@tanstack/react-query";

import { listAllStocks } from "@/api/stocks";

export function useStocks(q?: string) {
  return useQuery({
    queryKey: ["stocks", "list", q ?? ""],
    queryFn: () => listAllStocks(q),
    staleTime: 5 * 60 * 1000,
  });
}
