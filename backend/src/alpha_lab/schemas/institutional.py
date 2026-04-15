"""三大法人買賣超 Pydantic 模型。

來源：TWSE T86（每日三大法人買賣超日報）
單位：股數（未換算為張數）；net = buy - sell。
"""

from datetime import date

from pydantic import BaseModel, Field


class InstitutionalTrade(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    foreign_net: int = Field(..., description="外資買賣超（股）")
    trust_net: int = Field(..., description="投信買賣超（股）")
    dealer_net: int = Field(..., description="自營商買賣超（股，自行買賣+避險合計）")
    total_net: int = Field(..., description="三大法人合計買賣超（股）")
