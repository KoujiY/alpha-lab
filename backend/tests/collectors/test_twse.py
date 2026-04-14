"""TWSE collector 單元測試（使用 respx mock httpx）。"""

from datetime import date

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_daily_prices
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.storage.models import Base, PriceDaily, Stock

SAMPLE_RESPONSE = {
    "stat": "OK",
    "date": "20260401",
    "fields": [
        "日期", "成交股數", "成交金額", "開盤價", "最高價",
        "最低價", "收盤價", "漲跌價差", "成交筆數",
    ],
    "data": [
        ["115/04/01", "12,345,678", "6,234,567,890", "500.00",
         "510.00", "499.00", "505.00", "+2.00", "45,678"],
    ],
}


async def test_fetch_daily_prices_parses_sample() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=SAMPLE_RESPONSE)

        results = await fetch_daily_prices(symbol="2330", year_month=date(2026, 4, 1))

    assert len(results) == 1
    p = results[0]
    assert isinstance(p, DailyPrice)
    assert p.symbol == "2330"
    assert p.trade_date == date(2026, 4, 1)
    assert p.open == 500.0
    assert p.close == 505.0
    assert p.volume == 12345678


async def test_fetch_daily_prices_raises_on_non_ok_stat() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(
            json={"stat": "查詢無資料", "data": []}
        )

        with pytest.raises(ValueError, match="查詢無資料"):
            await fetch_daily_prices(symbol="9999", year_month=date(2026, 4, 1))


async def test_fetch_daily_prices_raises_on_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(500)

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_daily_prices(symbol="2330", year_month=date(2026, 4, 1))


def test_upsert_daily_prices_inserts_new_rows() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                open=500.0, high=510.0, low=499.0, close=505.0, volume=1000,
            ),
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 2),
                open=505.0, high=512.0, low=504.0, close=510.0, volume=2000,
            ),
        ]
        inserted = upsert_daily_prices(session, rows)
        session.commit()

        assert inserted == 2
        assert session.query(PriceDaily).count() == 2


def test_upsert_daily_prices_updates_existing_row() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            PriceDaily(
                symbol="2330", trade_date=date(2026, 4, 1),
                open=100.0, high=100.0, low=100.0, close=100.0, volume=1,
            )
        )
        session.commit()

        updated = upsert_daily_prices(
            session,
            [DailyPrice(
                symbol="2330", trade_date=date(2026, 4, 1),
                open=500.0, high=510.0, low=499.0, close=505.0, volume=1000,
            )],
        )
        session.commit()

        assert updated == 1
        row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
        assert row is not None
        assert row.close == 505.0
