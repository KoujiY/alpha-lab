"""Stocks API 回應 Pydantic 模型。

overview 端點回傳 `StockOverview`，聚合個股頁首屏所需資料。
細端點回傳單一 section 的 list（如 `list[DailyPricePoint]`）。

注意：這些是回應 DTO，資料來自已驗證的 storage 層，因此省略 OHLC / 買賣超等
數值範圍檢查（`ge=0` 類），避免與 collector 端 schemas 重複。單位與範圍描述
透過 `Field(description=...)` 帶到 OpenAPI，供前端參考。
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class StockMeta(BaseModel):
    """個股基本資料。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=64)
    industry: str | None = None
    listed_date: date | None = None


class DailyPricePoint(BaseModel):
    """單日 OHLCV。"""

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int = Field(..., description="成交股數")


class RevenuePoint(BaseModel):
    """單月營收 + YoY/MoM 成長率。"""

    year: int
    month: int
    revenue: int = Field(..., description="當月營收（新台幣元）")
    yoy_growth: float | None = Field(default=None, description="年增率（小數，例 0.15 = 15%）")
    mom_growth: float | None = Field(default=None, description="月增率（小數）")


class FinancialPoint(BaseModel):
    """單季財報摘要（income + balance 合併視圖）。"""

    period: str = Field(..., pattern=r"^\d{4}Q[1-4]$", description="季別，格式 YYYYQ[1-4]，例：2026Q1")
    revenue: int | None = Field(default=None, description="當季營收（新台幣元）")
    gross_profit: int | None = Field(default=None, description="毛利（新台幣元）")
    operating_income: int | None = Field(default=None, description="營業利益（新台幣元）")
    net_income: int | None = Field(default=None, description="稅後淨利（新台幣元）")
    eps: float | None = Field(default=None, description="每股盈餘（新台幣元）")
    total_assets: int | None = Field(default=None, description="資產總額（新台幣元）")
    total_liabilities: int | None = Field(default=None, description="負債總額（新台幣元）")
    total_equity: int | None = Field(default=None, description="權益總額（新台幣元）")


class InstitutionalPoint(BaseModel):
    """單日三大法人買賣超（單位：股）。"""

    trade_date: date
    foreign_net: int = Field(..., description="外資買賣超（股）")
    trust_net: int = Field(..., description="投信買賣超（股）")
    dealer_net: int = Field(..., description="自營商買賣超（股）")
    total_net: int = Field(..., description="三大法人合計買賣超（股）")


class MarginPoint(BaseModel):
    """單日融資融券餘額與進出（單位：張）。"""

    trade_date: date
    margin_balance: int = Field(..., description="融資餘額（張）")
    margin_buy: int = Field(..., description="融資買進（張）")
    margin_sell: int = Field(..., description="融資賣出（張）")
    short_balance: int = Field(..., description="融券餘額（張）")
    short_sell: int = Field(..., description="融券賣出（張）")
    short_cover: int = Field(..., description="融券回補（張）")


class EventPoint(BaseModel):
    """單筆重大訊息。"""

    id: int
    event_datetime: datetime
    event_type: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1)
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
