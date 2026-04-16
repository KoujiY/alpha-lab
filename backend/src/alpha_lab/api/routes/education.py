"""/api/education 路由（Phase 4 — L2 詳解）。"""

from fastapi import APIRouter, HTTPException

from alpha_lab.education.loader import get_l2_topic, load_l2_topics
from alpha_lab.schemas.education import L2Topic, L2TopicMeta

router = APIRouter(prefix="/education", tags=["education"])


@router.get("/l2", response_model=list[L2TopicMeta])
async def list_l2_topics() -> list[L2TopicMeta]:
    topics = load_l2_topics()
    return [
        L2TopicMeta(id=t.id, title=t.title, related_terms=t.related_terms)
        for t in topics.values()
    ]


@router.get("/l2/{topic_id}", response_model=L2Topic)
async def get_l2_topic_by_id(topic_id: str) -> L2Topic:
    topic = get_l2_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail=f"L2 topic {topic_id} not found")
    return topic
