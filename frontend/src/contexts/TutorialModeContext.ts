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

// 無 Provider 時提供預設 full mode + no-op setters；方便單元測試不用每個都包 Provider，
// 也避免 app 初始化順序問題。對齊 L2PanelContext 的 NOOP 預設模式。
const DEFAULT_CONTEXT: TutorialModeContextValue = {
  mode: "full",
  setMode: () => {},
  cycle: () => {},
};

export function useTutorialMode(): TutorialModeContextValue {
  return useContext(TutorialModeContext) ?? DEFAULT_CONTEXT;
}
