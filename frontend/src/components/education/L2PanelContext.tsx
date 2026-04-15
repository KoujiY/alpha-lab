import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

interface L2PanelContextValue {
  activeTopicId: string | null;
  openTopic: (topicId: string) => void;
  closePanel: () => void;
}

const L2PanelContext = createContext<L2PanelContextValue | null>(null);

export function L2PanelProvider({ children }: { children: ReactNode }) {
  const [activeTopicId, setActiveTopicId] = useState<string | null>(null);

  const openTopic = useCallback((topicId: string) => {
    setActiveTopicId(topicId);
  }, []);

  const closePanel = useCallback(() => {
    setActiveTopicId(null);
  }, []);

  const value = useMemo(
    () => ({ activeTopicId, openTopic, closePanel }),
    [activeTopicId, openTopic, closePanel]
  );

  return (
    <L2PanelContext.Provider value={value}>{children}</L2PanelContext.Provider>
  );
}

const NOOP_CONTEXT: L2PanelContextValue = {
  activeTopicId: null,
  openTopic: () => {},
  closePanel: () => {},
};

export function useL2Panel(): L2PanelContextValue {
  // 若元件未被 L2PanelProvider 包住（例如於局部測試），回 noop 避免 crash
  return useContext(L2PanelContext) ?? NOOP_CONTEXT;
}
