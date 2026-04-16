"""Education L2 詳解 Pydantic schemas。"""

from pydantic import BaseModel, Field


class L2TopicMeta(BaseModel):
    """L2 詳解 meta（供列表頁使用，不含 body）。"""

    id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1)
    related_terms: list[str] = Field(default_factory=list)


class L2Topic(L2TopicMeta):
    """L2 詳解完整內容。"""

    body_markdown: str = Field(..., min_length=1)
