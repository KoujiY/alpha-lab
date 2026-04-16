import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { L2PanelContext } from "./L2PanelContext";

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
    [activeTopicId, openTopic, closePanel],
  );

  return (
    <L2PanelContext.Provider value={value}>{children}</L2PanelContext.Provider>
  );
}
