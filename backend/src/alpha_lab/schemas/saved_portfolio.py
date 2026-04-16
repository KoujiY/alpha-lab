"""Saved Portfolio 相關 schemas（Phase 6 + Phase 7 血緣）。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from alpha_lab.analysis.weights import Style

WEIGHT_SUM_TOLERANCE = 1e-6


class SavedHolding(BaseModel):
    symbol: str
    name: str
    weight: float
    base_price: float


class SavedPortfolioCreate(BaseModel):
    """把某個風格的推薦結果存成追蹤組合。

    `parent_id`：若此組合由另一個已儲存組合「加入個股」而來，帶上母組合 id；
    後端會自動查 parent latest_nav 並填 `parent_nav_at_fork`。
    """

    style: Style
    label: str = Field(..., min_length=1, max_length=32)
    note: str | None = None
    holdings: list[SavedHolding] = Field(..., min_length=1)
    parent_id: int | None = None

    @model_validator(mode="after")
    def _validate_holdings(self) -> SavedPortfolioCreate:
        symbols = [h.symbol for h in self.holdings]
        if len(symbols) != len(set(symbols)):
            dup = sorted({s for s in symbols if symbols.count(s) > 1})
            raise ValueError(f"duplicate symbol in holdings: {dup}")
        total = sum(h.weight for h in self.holdings)
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"weights must sum to 1.0 (got {total:.8f}, "
                f"tolerance {WEIGHT_SUM_TOLERANCE})"
            )
        return self


class SavedPortfolioMeta(BaseModel):
    id: int
    style: Style
    label: str
    note: str | None
    base_date: date_type
    created_at: datetime
    holdings_count: int
    parent_id: int | None = None
    parent_nav_at_fork: float | None = None


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
    total_return: float  # self 段：nav_last - 1.0
    parent_points: list[PerformancePoint] | None = None
    parent_nav_at_fork: float | None = None


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
