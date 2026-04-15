"""Stocks schema 驗證測試。"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from alpha_lab.schemas.stock import (
    DailyPricePoint,
    EventPoint,
    StockMeta,
    StockOverview,
)


def test_stock_meta_rejects_empty_symbol() -> None:
    with pytest.raises(ValidationError):
        StockMeta(symbol="", name="測試")


def test_stock_overview_accepts_empty_lists() -> None:
    overview = StockOverview(
        meta=StockMeta(symbol="2330", name="台積電"),
        prices=[],
        revenues=[],
        financials=[],
        institutional=[],
        margin=[],
        events=[],
    )
    assert overview.meta.symbol == "2330"


def test_daily_price_point_round_trip() -> None:
    point = DailyPricePoint(
        trade_date=date(2026, 4, 14),
        open=600.0,
        high=610.0,
        low=595.0,
        close=605.0,
        volume=12345,
    )
    assert point.close == 605.0


def test_event_point_datetime_parsing() -> None:
    point = EventPoint(
        id=1,
        event_datetime=datetime(2026, 4, 14, 15, 30),
        event_type="財報",
        title="公布 Q1 財報",
        content="營收創新高",
    )
    assert point.event_datetime.year == 2026
