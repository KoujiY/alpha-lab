"""選股篩選器 Pydantic schemas。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FactorMeta(BaseModel):
    """單一因子的 meta 資訊。"""

    key: str
    label: str
    min_value: float = 0.0
    max_value: float = 100.0
    default_min: float = 0.0
    description: str = ""


class FactorsResponse(BaseModel):
    """GET /api/screener/factors 回應。"""

    factors: list[FactorMeta]


class FactorRange(BaseModel):
    """單一因子的篩選範圍。"""

    key: str
    min_value: float = Field(0.0, ge=0.0, le=100.0)
    max_value: float = Field(100.0, ge=0.0, le=100.0)


class FilterRequest(BaseModel):
    """POST /api/screener/filter 請求。"""

    filters: list[FactorRange] = Field(default_factory=list)
    sort_by: str = "total_score"
    sort_desc: bool = True
    limit: int = Field(50, ge=1, le=200)


class ScreenerStock(BaseModel):
    """篩選結果中的單檔股票。"""

    symbol: str
    name: str
    industry: str | None
    value_score: float | None
    growth_score: float | None
    dividend_score: float | None
    quality_score: float | None
    total_score: float | None


class FilterResponse(BaseModel):
    """POST /api/screener/filter 回應。"""

    calc_date: str
    total_count: int
    stocks: list[ScreenerStock]
