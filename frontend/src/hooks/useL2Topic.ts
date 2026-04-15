import { useQuery } from "@tanstack/react-query";

import { getL2Topic } from "@/api/education";

export function useL2Topic(topicId: string | null) {
  return useQuery({
    queryKey: ["education", "l2", topicId],
    queryFn: () => {
      if (topicId === null) {
        throw new Error("topicId is required");
      }
      return getL2Topic(topicId);
    },
    enabled: topicId !== null,
    staleTime: 10 * 60 * 1000,
  });
}
