import { useCallback, useEffect, useState } from "react";

import { readFavorites, toggleFavorite } from "@/lib/favorites";

const STORAGE_KEY = "alpha-lab:favorites";

export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>(() => readFavorites());

  useEffect(() => {
    function handleStorage(event: StorageEvent) {
      // event.key === null 表示 localStorage.clear() 整個清掉；其餘情況只處理我們的 key
      if (event.key !== null && event.key !== STORAGE_KEY) return;
      setFavorites(readFavorites());
    }
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const toggle = useCallback((symbol: string) => {
    setFavorites(toggleFavorite(symbol));
  }, []);

  const isFavorite = useCallback(
    (symbol: string) => favorites.includes(symbol),
    [favorites],
  );

  return { favorites, isFavorite, toggle };
}
