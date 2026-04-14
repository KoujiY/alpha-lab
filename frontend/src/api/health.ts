import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";

export type HealthResponse = {
  status: string;
  version: string;
  timestamp: string;
};

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/api/health"),
    refetchInterval: 30_000,
  });
}
