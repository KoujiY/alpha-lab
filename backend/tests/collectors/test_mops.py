"""MOPS collector 單元測試。"""

import respx

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.schemas.revenue import MonthlyRevenue

SAMPLE_RESPONSE = [
    {
        "出表日期": "1150410",
        "資料年月": "11503",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "營業收入-當月營收": "300000000",
        "營業收入-上月營收": "280000000",
        "營業收入-去年當月營收": "250000000",
        "營業收入-上月比較增減(%)": "7.14",
        "營業收入-去年同月增減(%)": "20.00",
    },
    {
        "出表日期": "1150410",
        "資料年月": "11503",
        "公司代號": "2317",
        "公司名稱": "鴻海",
        "營業收入-當月營收": "500000000",
        "營業收入-上月營收": "510000000",
        "營業收入-去年當月營收": "450000000",
        "營業收入-上月比較增減(%)": "-1.96",
        "營業收入-去年同月增減(%)": "11.11",
    },
]


async def test_fetch_latest_monthly_revenues_parses_sample() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=SAMPLE_RESPONSE)

        results = await fetch_latest_monthly_revenues(symbols=["2330", "2317"])

    assert len(results) == 2
    tsmc = next(r for r in results if r.symbol == "2330")
    assert isinstance(tsmc, MonthlyRevenue)
    assert tsmc.year == 2026
    assert tsmc.month == 3
    assert tsmc.revenue == 300000000
    assert tsmc.yoy_growth == 20.00


async def test_fetch_latest_monthly_revenues_filters_symbols() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=SAMPLE_RESPONSE)

        results = await fetch_latest_monthly_revenues(symbols=["2330"])

    assert len(results) == 1
    assert results[0].symbol == "2330"


async def test_fetch_latest_monthly_revenues_all_when_symbols_none() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=SAMPLE_RESPONSE)

        results = await fetch_latest_monthly_revenues(symbols=None)

    assert len(results) == 2
