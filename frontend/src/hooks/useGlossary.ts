import { useQuery } from "@tanstack/react-query";

import { fetchAllGlossary } from "@/api/glossary";
import type { GlossaryTerm } from "@/api/types";

export function useGlossary() {
  return useQuery<Record<string, GlossaryTerm>>({
    queryKey: ["glossary"],
    queryFn: fetchAllGlossary,
    staleTime: 10 * 60_000,
  });
}
