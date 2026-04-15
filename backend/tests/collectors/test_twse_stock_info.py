"""TWSE 上市公司基本資料 collector 單元測試。"""

import json
from datetime import date
from pathlib import Path

import respx

from alpha_lab.collectors.twse_stock_info import fetch_stock_info
from alpha_lab.schemas.stock_info import StockInfo

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "twse_t187ap03_L_sample.json"
)


def _load_fixture() -> list[dict[str, object]]:
    with FIXTURE_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list)
    return data


async def test_fetch_stock_info_parses_sample_all() -> None:
    sample = _load_fixture()
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap03_L").respond(json=sample)
        rows = await fetch_stock_info(symbols=None)

    assert len(rows) == 4
    by_symbol = {r.symbol: r for r in rows}
    assert isinstance(by_symbol["2330"], StockInfo)
    assert by_symbol["2330"].name == "台積電"
    # TWSE 產業別實際回傳代碼字串（24 = 半導體業）
    assert by_symbol["2330"].industry == "24"
    # 8 碼西元日期
    assert by_symbol["2330"].listed_date == date(1994, 9, 5)
    assert by_symbol["2317"].listed_date == date(1991, 2, 6)
    assert by_symbol["2454"].industry == "24"
    assert by_symbol["2603"].name == "長榮"


async def test_fetch_stock_info_filters_by_symbols() -> None:
    sample = _load_fixture()
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap03_L").respond(json=sample)
        rows = await fetch_stock_info(symbols=["2330", "2454"])

    assert {r.symbol for r in rows} == {"2330", "2454"}


async def test_fetch_stock_info_skips_rows_with_missing_fields() -> None:
    payload = [
        {
            "公司代號": "2330",
            "公司簡稱": "台積電",
            "產業別": "24",
            "上市日期": "19940905",
        },
        {
            # 缺 symbol -> 略過
            "公司簡稱": "無代號公司",
            "產業別": "99",
            "上市日期": "20110101",
        },
        {
            # 缺 name -> 略過
            "公司代號": "9999",
            "產業別": "99",
            "上市日期": "20110101",
        },
        {
            # industry 為空字串 / listed_date 為 "-" 應保留並轉 None
            "公司代號": "1234",
            "公司簡稱": "測試",
            "產業別": "",
            "上市日期": "-",
        },
    ]
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap03_L").respond(json=payload)
        rows = await fetch_stock_info(symbols=None)

    by_symbol = {r.symbol: r for r in rows}
    assert set(by_symbol) == {"2330", "1234"}
    assert by_symbol["1234"].industry is None
    assert by_symbol["1234"].listed_date is None


async def test_fetch_stock_info_empty_payload() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap03_L").respond(json=[])
        rows = await fetch_stock_info(symbols=["2330"])

    assert rows == []
