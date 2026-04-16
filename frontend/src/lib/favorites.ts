const KEY = "alpha-lab:favorites";

export function readFavorites(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === "string")
      : [];
  } catch {
    return [];
  }
}

export function isFavorite(symbol: string): boolean {
  return readFavorites().includes(symbol);
}

export function toggleFavorite(symbol: string): string[] {
  const current = readFavorites();
  const next = current.includes(symbol)
    ? current.filter((s) => s !== symbol)
    : [...current, symbol];
  window.localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
