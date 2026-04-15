"""融資融券 Pydantic 模型。

來源：TWSE MI_MARGN（每日信用交易統計）
單位：張數；yoy/mom 無（盤中無此指標）。
"""

from datetime import date

from pydantic import BaseModel, Field


class MarginTrade(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    margin_balance: int = Field(..., ge=0, description="融資餘額（張）")
    margin_buy: int = Field(..., ge=0, description="融資買進（張）")
    margin_sell: int = Field(..., ge=0, description="融資賣出（張）")
    short_balance: int = Field(..., ge=0, description="融券餘額（張）")
    short_sell: int = Field(..., ge=0, description="融券賣出（張）")
    short_cover: int = Field(..., ge=0, description="融券買進回補（張）")
