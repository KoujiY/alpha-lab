"""月營收 Pydantic 模型。

資料來源：MOPS 公開資訊觀測站，每月 10 日後各公司公告前一月營收。
單位：revenue 為「千元」（MOPS 原始欄位單位），yoy/mom 為百分比（%）。
"""

from pydantic import BaseModel, Field


class MonthlyRevenue(BaseModel):
    """單一股票單月營收。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    year: int = Field(..., ge=1990, le=2100, description="西元年")
    month: int = Field(..., ge=1, le=12)
    revenue: int = Field(..., ge=0, description="當月營收（千元）")
    yoy_growth: float | None = Field(None, description="去年同月比，%")
    mom_growth: float | None = Field(None, description="上月比，%")
