"""TWSE 融資融券 collector 單元測試。

Mock payload 反映真實 TWSE MI_MARGN（2025 年版）：
- `tables[0]` 為整體買賣總計（summary）
- `tables[1]` 為個股信用交易彙總，有 `groups` 與 `fields`，融資/融券兩群組
"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors._twse_common import TWSERateLimitError
from alpha_lab.collectors.twse_margin import fetch_margin_trades
from alpha_lab.schemas.margin import MarginTrade

# 真實結構：融資 group 佔 2..7、融券 group 佔 8..13、資券互抵/註記在尾端。
# 融資與融券子欄位名稱相同（買進/賣出/現金(券)償還/前日餘額/今日餘額/可用額度）。
SAMPLE_FIELDS = [
    "代號", "名稱",
    # 融資群組 (index 2..7)
    "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額", "可用額度",
    # 融券群組 (index 8..13)
    "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額", "可用額度",
    "資券互抵", "註記",
]

# 真實 TWSE groups 不含 `start`，靠 span 累加推導；前面會有股票識別群組。
SAMPLE_GROUPS = [
    {"title": "股票", "span": 2},
    {"title": "融資", "span": 6},
    {"title": "融券", "span": 6},
    {"title": "", "span": 1},
    {"title": "", "span": 1},
]

SUMMARY_TABLE = {
    "title": "信用交易總計",
    "fields": ["項目", "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額"],
    "data": [["融資(交易單位)", "1,000", "800", "0", "20,000", "20,200"]],
}


def _credit_table(data: list[list[str]]) -> dict[str, object]:
    return {
        "title": "信用交易彙總",
        "groups": SAMPLE_GROUPS,
        "fields": SAMPLE_FIELDS,
        "data": data,
    }


SAMPLE_RESPONSE = {
    "stat": "OK",
    "tables": [
        SUMMARY_TABLE,
        _credit_table(
            [
                [
                    "2330", "台積電",
                    # 融資：買進=500、賣出=400、現金償還=0、前日=10,100、今日=10,200、限額
                    "500", "400", "0", "10,100", "10,200", "999,999",
                    # 融券：買進(回補)=30、賣出=50、現券償還=0、前日=220、今日=200、限額
                    "30", "50", "0", "220", "200", "99,999",
                    "0", "",
                ],
            ]
        ),
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
            SUMMARY_TABLE,
            _credit_table(
                [
                    ["2330", "台積電"] + ["0"] * 12 + ["0", ""],
                    ["2317", "鴻海"] + ["0"] * 12 + ["0", ""],
                ]
            ),
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
async def test_fetch_margin_trades_returns_empty_when_no_data() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        route = mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(
            json={"stat": "很抱歉，沒有符合條件的資料"},
        )
        result = await fetch_margin_trades(trade_date=date(2026, 4, 15))
    assert result == []
    assert route.called


@pytest.mark.asyncio
async def test_fetch_margin_trades_raises_on_other_non_ok_stat() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(
            json={"stat": "系統忙線中"},
        )
        with pytest.raises(ValueError, match="系統忙線中"):
            await fetch_margin_trades(trade_date=date(2026, 4, 15))


@pytest.mark.asyncio
async def test_fetch_margin_trades_handles_numeric_cells() -> None:
    """TWSE 有時把數字欄位直接以 int 回傳。"""
    # 以 int 取代 "1,000" 等字串
    row = [
        "2330", "台積電",
        100, 50, 0, 20000, 20050, 0,
        20, 10, 0, 2000, 2010, 0,
        0, "",
    ]
    payload = {
        "stat": "OK",
        "tables": [SUMMARY_TABLE, _credit_table([row])],
    }
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=payload)
        result = await fetch_margin_trades(trade_date=date(2026, 4, 15))
    assert len(result) == 1
    assert result[0].margin_buy == 100
    assert result[0].margin_balance == 20050


@pytest.mark.asyncio
async def test_fetch_margin_trades_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_margin_trades(trade_date=date(2026, 4, 1))


@pytest.mark.asyncio
async def test_fetch_margin_trades_raises_rate_limit_on_waf_307() -> None:
    waf_body = "<html>THE PAGE CANNOT BE ACCESSED! FOR SECURITY REASONS...</html>"
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(
            307,
            headers={"content-type": "text/html; charset=UTF-8"},
            content=waf_body.encode("utf-8"),
        )
        with pytest.raises(TWSERateLimitError):
            await fetch_margin_trades(trade_date=date(2026, 4, 1))
