"""日股價 Pydantic 模型。"""

from datetime import date

from pydantic import BaseModel, Field


class DailyPrice(BaseModel):
    """單一股票單日 OHLCV。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: int = Field(..., ge=0)
