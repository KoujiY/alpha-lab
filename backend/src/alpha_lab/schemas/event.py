"""重大訊息 Pydantic 模型。

來源：MOPS t146sb05（即時重大訊息）
event_type：MOPS 原始「主旨」或公司自填事件類型；content：訊息全文。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Event(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    event_datetime: datetime = Field(..., description="發言時間（含時分）")
    event_type: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1)
    content: str = Field(default="")
