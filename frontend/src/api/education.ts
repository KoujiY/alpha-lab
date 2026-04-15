import { apiGet } from "./client";
import type { L2Topic, L2TopicMeta } from "./types";

export function listL2Topics(): Promise<L2TopicMeta[]> {
  return apiGet<L2TopicMeta[]>("/api/education/l2");
}

export function getL2Topic(topicId: string): Promise<L2Topic> {
  return apiGet<L2Topic>(`/api/education/l2/${encodeURIComponent(topicId)}`);
}
