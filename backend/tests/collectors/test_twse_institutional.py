"""TWSE 三大法人 collector 單元測試。"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
from alpha_lab.schemas.institutional import InstitutionalTrade

SAMPLE_FIELDS = [
    "證券代號", "證券名稱",
    "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
    "外陸資買賣超股數(不含外資自營商)",
    "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
    "投信買進股數", "投信賣出股數", "投信買賣超股數",
    "自營商買賣超股數",
    "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)", "自營商買賣超股數(自行買賣)",
    "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
    "三大法人買賣超股數",
]

SAMPLE_RESPONSE = {
    "stat": "OK",
    "date": "20260401",
    "fields": SAMPLE_FIELDS,
    "data": [
        [
            "2330", "台積電",
            "1,000,000", "0", "1,000,000",
            "0", "0", "0",
            "0", "500,000", "-500,000",
            "100,000",
            "0", "0", "0",
            "0", "0", "0",
            "600,000",
        ],
    ],
}


@pytest.mark.asyncio
async def test_fetch_institutional_trades_parses_sample() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json=SAMPLE_RESPONSE)

        rows = await fetch_institutional_trades(trade_date=date(2026, 4, 1))

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, InstitutionalTrade)
    assert r.symbol == "2330"
    assert r.trade_date == date(2026, 4, 1)
    assert r.foreign_net == 1_000_000  # 外陸資 + 外資自營商
    assert r.trust_net == -500_000
    assert r.dealer_net == 100_000
    assert r.total_net == 600_000


@pytest.mark.asyncio
async def test_fetch_institutional_trades_filters_symbols() -> None:
    payload = {
        "stat": "OK",
        "fields": SAMPLE_FIELDS,
        "data": [
            ["2330", "台積電"] + ["0"] * 16 + ["100"],
            ["2317", "鴻海"] + ["0"] * 16 + ["200"],
        ],
    }
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json=payload)
        rows = await fetch_institutional_trades(
            trade_date=date(2026, 4, 1), symbols=["2330"]
        )
    assert [r.symbol for r in rows] == ["2330"]


@pytest.mark.asyncio
async def test_fetch_institutional_trades_non_ok_stat_raises() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json={"stat": "查詢無資料", "data": []})
        with pytest.raises(ValueError, match="查詢無資料"):
            await fetch_institutional_trades(trade_date=date(2026, 4, 1))


@pytest.mark.asyncio
async def test_fetch_institutional_trades_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_institutional_trades(trade_date=date(2026, 4, 1))
