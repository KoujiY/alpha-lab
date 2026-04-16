"""Yahoo Finance Chart API collector 測試。"""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.yahoo import YahooFetchError, fetch_yahoo_daily_prices

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_daily_prices_parses_chart_payload():
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "2330.TW"},
                    "timestamp": [1711929600, 1712016000],  # 2024-04-01, 2024-04-02 UTC
                    "indicators": {
                        "quote": [
                            {
                                "open": [720.0, 725.0],
                                "high": [728.0, 730.0],
                                "low": [718.0, 723.0],
                                "close": [725.0, 728.0],
                                "volume": [30000000, 28000000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))

    rows = await fetch_yahoo_daily_prices(
        symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
    )
    assert len(rows) == 2
    assert rows[0].symbol == "2330"
    assert rows[0].source == "yahoo"
    assert rows[0].close == pytest.approx(725.0)
    assert rows[0].volume == 30000000
    assert rows[0].trade_date == date(2024, 4, 1)
    assert rows[1].trade_date == date(2024, 4, 2)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_drops_rows_with_null_fields():
    """Yahoo 偶爾在某些交易日回 null（盤中斷訊）— 應過濾整列。"""
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "2330.TW"},
                    "timestamp": [1711929600, 1712016000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [720.0, None],
                                "high": [728.0, 730.0],
                                "low": [718.0, 723.0],
                                "close": [725.0, None],
                                "volume": [30000000, 28000000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))

    rows = await fetch_yahoo_daily_prices(
        symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
    )
    assert len(rows) == 1
    assert rows[0].trade_date == date(2024, 4, 1)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_raises_on_error_envelope():
    payload = {
        "chart": {
            "result": None,
            "error": {"code": "Not Found", "description": "No data"},
        }
    }
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))
    with pytest.raises(YahooFetchError, match="Not Found"):
        await fetch_yahoo_daily_prices(
            symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
        )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_raises_on_http_5xx():
    respx.get(CHART_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(YahooFetchError):
        await fetch_yahoo_daily_prices(
            symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
        )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_returns_empty_on_no_results():
    payload = {"chart": {"result": [], "error": None}}
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))
    rows = await fetch_yahoo_daily_prices(
        symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
    )
    assert rows == []
