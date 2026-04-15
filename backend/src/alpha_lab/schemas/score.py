"""多因子評分 Pydantic schemas。"""

from datetime import date

from pydantic import BaseModel, Field


class FactorBreakdown(BaseModel):
    """單檔的四因子分數與總分。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    calc_date: date
    value_score: float | None = None
    growth_score: float | None = None
    dividend_score: float | None = None
    quality_score: float | None = None
    total_score: float | None = None


class ScoreResponse(BaseModel):
    """`GET /api/stocks/{symbol}/score` 回應。"""

    symbol: str
    latest: FactorBreakdown | None = None
