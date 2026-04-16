"""Saved Portfolio 相關 schemas（Phase 6）。"""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field

from alpha_lab.analysis.weights import Style


class SavedHolding(BaseModel):
    symbol: str
    name: str
    weight: float
    base_price: float


class SavedPortfolioCreate(BaseModel):
    """把某個風格的推薦結果存成追蹤組合。

    前端從 `RecommendResponse` 取一個 Portfolio 組合成這個 payload。
    """

    style: Style
    label: str = Field(..., min_length=1, max_length=32)
    note: str | None = None
    holdings: list[SavedHolding] = Field(..., min_length=1)


class SavedPortfolioMeta(BaseModel):
    id: int
    style: Style
    label: str
    note: str | None
    base_date: date_type
    created_at: datetime
    holdings_count: int


class SavedPortfolioDetail(SavedPortfolioMeta):
    holdings: list[SavedHolding]


class PerformancePoint(BaseModel):
    date: date_type
    nav: float
    daily_return: float | None = None


class PerformanceResponse(BaseModel):
    portfolio: SavedPortfolioDetail
    points: list[PerformancePoint]
    latest_nav: float
    total_return: float  # nav_last - 1.0


class BaseDateProbe(BaseModel):
    """`GET /api/portfolios/saved/probe` 回傳。

    `today_available` 為 True 時前端可直接 strict save；否則前端應跳 dialog
    顯示 `resolved_date` 與 `missing_today_symbols`，讓使用者決定要先補抓
    報價還是同意以 `resolved_date` 為基準儲存。
    """

    target_date: date_type
    resolved_date: date_type | None
    today_available: bool
    missing_today_symbols: list[str]
