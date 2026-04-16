import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  MODE_ORDER,
  STORAGE_KEY,
  TutorialModeContext,
  type TutorialMode,
} from "./TutorialModeContext";

function readInitialMode(): TutorialMode {
  if (typeof window === "undefined") return "full";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === "full" || raw === "compact" || raw === "off") return raw;
  return "full";
}

interface TutorialModeProviderProps {
  children: ReactNode;
}

export function TutorialModeProvider({ children }: TutorialModeProviderProps) {
  const [mode, setModeState] = useState<TutorialMode>(readInitialMode);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const setMode = useCallback((next: TutorialMode) => {
    setModeState(next);
  }, []);

  const cycle = useCallback(() => {
    setModeState((prev) => {
      const idx = MODE_ORDER.indexOf(prev);
      return MODE_ORDER[(idx + 1) % MODE_ORDER.length];
    });
  }, []);

  const value = useMemo(
    () => ({ mode, setMode, cycle }),
    [mode, setMode, cycle],
  );
  return (
    <TutorialModeContext.Provider value={value}>
      {children}
    </TutorialModeContext.Provider>
  );
}
