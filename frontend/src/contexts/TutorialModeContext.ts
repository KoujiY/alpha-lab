import { createContext, useContext } from "react";

export type TutorialMode = "full" | "compact" | "off";

export interface TutorialModeContextValue {
  mode: TutorialMode;
  setMode: (mode: TutorialMode) => void;
  cycle: () => void;
}

export const STORAGE_KEY = "alpha-lab:tutorial-mode";
export const MODE_ORDER: TutorialMode[] = ["full", "compact", "off"];

export const TutorialModeContext =
  createContext<TutorialModeContextValue | null>(null);

export function useTutorialMode(): TutorialModeContextValue {
  const ctx = useContext(TutorialModeContext);
  if (!ctx) {
    throw new Error("useTutorialMode must be used within TutorialModeProvider");
  }
  return ctx;
}
