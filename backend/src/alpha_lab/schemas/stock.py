"""Stocks API 回應 Pydantic 模型。

overview 端點回傳 `StockOverview`，聚合個股頁首屏所需資料。
細端點回傳單一 section 的 list（如 `list[DailyPricePoint]`）。
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class StockMeta(BaseModel):
    """個股基本資料。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    name: str
    industry: str | None = None
    listed_date: date | None = None


class DailyPricePoint(BaseModel):
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class RevenuePoint(BaseModel):
    year: int
    month: int
    revenue: int
    yoy_growth: float | None = None
    mom_growth: float | None = None


class FinancialPoint(BaseModel):
    """單季財報摘要（income + balance 合併視圖）。"""

    period: str  # "2026Q1"
    revenue: int | None = None
    gross_profit: int | None = None
    operating_income: int | None = None
    net_income: int | None = None
    eps: float | None = None
    total_assets: int | None = None
    total_liabilities: int | None = None
    total_equity: int | None = None


class InstitutionalPoint(BaseModel):
    trade_date: date
    foreign_net: int
    trust_net: int
    dealer_net: int
    total_net: int


class MarginPoint(BaseModel):
    trade_date: date
    margin_balance: int
    margin_buy: int
    margin_sell: int
    short_balance: int
    short_sell: int
    short_cover: int


class EventPoint(BaseModel):
    id: int
    event_datetime: datetime
    event_type: str
    title: str
    content: str


class StockOverview(BaseModel):
    """個股頁首屏聚合資料。

    - prices：近 60 個交易日
    - revenues：近 12 個月
    - financials：近 4 季（合併 income + balance）
    - institutional / margin：近 20 個交易日
    - events：近 20 筆
    """

    meta: StockMeta
    prices: list[DailyPricePoint]
    revenues: list[RevenuePoint]
    financials: list[FinancialPoint]
    institutional: list[InstitutionalPoint]
    margin: list[MarginPoint]
    events: list[EventPoint]
