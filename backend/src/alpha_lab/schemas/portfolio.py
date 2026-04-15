"""組合推薦 Pydantic schemas。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from alpha_lab.schemas.score import FactorBreakdown

Style = Literal["conservative", "balanced", "aggressive"]


class Holding(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str
    weight: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: FactorBreakdown
    reasons: list[str] = Field(default_factory=list)


class Portfolio(BaseModel):
    style: Style
    label: str
    is_top_pick: bool = False
    holdings: list[Holding]
    expected_yield: float | None = None
    risk_score: float | None = None
    reasoning_ref: str | None = None


class RecommendResponse(BaseModel):
    generated_at: datetime
    calc_date: str
    portfolios: list[Portfolio]
