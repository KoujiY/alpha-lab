"""Report 儲存 / 讀取 Pydantic schemas（Phase 4）。

對齊 CLAUDE.md §「Claude Code 分析 SOP」中的 frontmatter 與四種報告類型。
"""

from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

ReportType = Literal["stock", "portfolio", "events", "research"]


class ReportMeta(BaseModel):
    """`index.json` 中單筆 meta；不含 body。"""

    id: str = Field(..., min_length=1)
    type: ReportType
    title: str = Field(..., min_length=1)
    symbols: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    date: date_type
    path: str = Field(..., min_length=1)
    summary_line: str = Field(default="")
    starred: bool = False


class ReportDetail(ReportMeta):
    body_markdown: str = Field(..., min_length=1)


class ReportCreate(BaseModel):
    """新增報告時的輸入；id 可省略，由 service 依 type + subject 組出來。"""

    type: ReportType
    title: str = Field(..., min_length=1)
    body_markdown: str = Field(..., min_length=1)
    summary_line: str = Field(default="")
    symbols: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    date: date_type | None = None
    subject: str | None = Field(
        default=None,
        description="stock 用 symbol、research 用 topic；portfolio / events 不使用",
    )


class ReportIndex(BaseModel):
    updated_at: str
    reports: list[ReportMeta]


class ReportUpdate(BaseModel):
    """`PATCH /api/reports/{id}` 可改的欄位。None = 不變。"""

    title: str | None = None
    tags: list[str] | None = None
    summary_line: str | None = None
    starred: bool | None = None
