import { apiGet } from "./client";
import type { GlossaryTerm } from "./types";

export function fetchGlossaryTerm(key: string): Promise<GlossaryTerm> {
  return apiGet<GlossaryTerm>(
    `/api/glossary/${encodeURIComponent(key)}`
  );
}

export function fetchAllGlossary(): Promise<Record<string, GlossaryTerm>> {
  return apiGet<Record<string, GlossaryTerm>>("/api/glossary");
}
