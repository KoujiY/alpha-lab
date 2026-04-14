"""TWSE collector 單元測試（使用 respx mock httpx）。"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.schemas.price import DailyPrice

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
