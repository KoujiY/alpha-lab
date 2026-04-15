"""Glossary term Pydantic 模型。"""

from pydantic import BaseModel, Field


class GlossaryTerm(BaseModel):
    """術語庫單筆條目。"""

    term: str = Field(..., min_length=1, description="正式中文術語名")
    short: str = Field(..., min_length=1, max_length=200, description="一句話解釋（Tooltip L1 用）")
    detail: str = Field(default="", description="完整說明（Markdown，L2 詳解面板 Phase 4 才用）")
    related: list[str] = Field(default_factory=list, description="相關術語 key 列表")
