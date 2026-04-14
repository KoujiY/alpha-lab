"""月營收 Pydantic 模型（Task B2 建立最小版，C1 會擴充註解/驗證）。"""

from pydantic import BaseModel, Field


class MonthlyRevenue(BaseModel):
    """單一股票單月營收（千元）。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    year: int = Field(..., ge=1990, le=2100)
    month: int = Field(..., ge=1, le=12)
    revenue: int = Field(..., ge=0)
    yoy_growth: float | None = None
    mom_growth: float | None = None
