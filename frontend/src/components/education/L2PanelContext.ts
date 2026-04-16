import { createContext, useContext } from "react";

export interface L2PanelContextValue {
  activeTopicId: string | null;
  openTopic: (topicId: string) => void;
  closePanel: () => void;
}

export const L2PanelContext = createContext<L2PanelContextValue | null>(null);

const NOOP_CONTEXT: L2PanelContextValue = {
  activeTopicId: null,
  openTopic: () => {},
  closePanel: () => {},
};

export function useL2Panel(): L2PanelContextValue {
  // 若元件未被 L2PanelProvider 包住（例如於局部測試），回 noop 避免 crash
  return useContext(L2PanelContext) ?? NOOP_CONTEXT;
}
