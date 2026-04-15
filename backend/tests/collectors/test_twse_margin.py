"""TWSE 融資融券 collector 單元測試。"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.twse_margin import fetch_margin_trades
from alpha_lab.schemas.margin import MarginTrade

SAMPLE_FIELDS = [
    "股票代號", "股票名稱",
    "融資買進", "融資賣出", "現金償還", "融資前日餘額", "融資今日餘額", "融資限額", "融資使用率(%)",
    "融券買進", "融券賣出", "現券償還", "融券前日餘額", "融券今日餘額", "融券限額", "融券使用率(%)",
    "資券互抵", "註記",
]

SAMPLE_RESPONSE = {
    "stat": "OK",
    "tables": [
        {
            "fields": SAMPLE_FIELDS,
            "data": [
                [
                    "2330", "台積電",
                    "500", "400", "0", "10100", "10200", "999999", "0.5",
                    "30", "50", "0", "220", "200", "99999", "0.1",
                    "0", "",
                ],
            ],
        }
    ],
}


@pytest.mark.asyncio
async def test_fetch_margin_trades_parses_sample() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=SAMPLE_RESPONSE)

        rows = await fetch_margin_trades(trade_date=date(2026, 4, 1))

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, MarginTrade)
    assert r.symbol == "2330"
    assert r.trade_date == date(2026, 4, 1)
    assert r.margin_buy == 500
    assert r.margin_sell == 400
    assert r.margin_balance == 10200
    assert r.short_sell == 50
    assert r.short_cover == 30
    assert r.short_balance == 200


@pytest.mark.asyncio
async def test_fetch_margin_trades_filters_symbols() -> None:
    payload = {
        "stat": "OK",
        "tables": [
            {
                "fields": SAMPLE_FIELDS,
                "data": [
                    ["2330", "台積電"] + ["0"] * 16,
                    ["2317", "鴻海"] + ["0"] * 16,
                ],
            }
        ],
    }
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=payload)
        rows = await fetch_margin_trades(
            trade_date=date(2026, 4, 1), symbols=["2317"]
        )
    assert [r.symbol for r in rows] == ["2317"]


@pytest.mark.asyncio
async def test_fetch_margin_trades_non_ok_raises() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(
            json={"stat": "查詢無資料"}
        )
        with pytest.raises(ValueError, match="查詢無資料"):
            await fetch_margin_trades(trade_date=date(2026, 4, 1))


@pytest.mark.asyncio
async def test_fetch_margin_trades_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_margin_trades(trade_date=date(2026, 4, 1))
