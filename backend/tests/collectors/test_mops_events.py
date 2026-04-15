"""MOPS events collector 單元測試。"""

from datetime import datetime

import httpx
import pytest
import respx

from alpha_lab.collectors.mops_events import fetch_latest_events
from alpha_lab.schemas.event import Event

SAMPLE_RESPONSE = [
    {
        "出表日期": "1150411",
        "發言日期": "1150410",
        "發言時間": "143020",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "主旨": "公告本公司董事會決議配息案",
        "符合條款": "第五款",
        "說明": "擬配發現金股利每股 11 元",
    },
    {
        "出表日期": "1150411",
        "發言日期": "1150410",
        "發言時間": "090000",
        "公司代號": "2317",
        "公司名稱": "鴻海",
        "主旨": "代子公司公告重訊",
        "符合條款": "第二款",
        "說明": "內容",
    },
]


@pytest.mark.asyncio
async def test_fetch_latest_events_parses_sample() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=SAMPLE_RESPONSE)

        events = await fetch_latest_events()

    assert len(events) == 2
    e = next(x for x in events if x.symbol == "2330")
    assert isinstance(e, Event)
    assert e.event_datetime == datetime(2026, 4, 10, 14, 30, 20)
    assert e.event_type == "第五款"
    assert "配息案" in e.title
    assert "11 元" in e.content


@pytest.mark.asyncio
async def test_fetch_latest_events_filters_symbols() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=SAMPLE_RESPONSE)
        events = await fetch_latest_events(symbols=["2330"])
    assert [e.symbol for e in events] == ["2330"]


@pytest.mark.asyncio
async def test_fetch_latest_events_empty_list_ok() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=[])
        events = await fetch_latest_events()
    assert events == []


@pytest.mark.asyncio
async def test_fetch_latest_events_http_error() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_latest_events()


@pytest.mark.asyncio
async def test_fetch_latest_events_tolerates_whitespace_keys() -> None:
    """TWSE OpenAPI 實測回傳帶「主旨 」(trailing space) 等不規則 key，collector 應能 strip。"""
    payload = [
        {
            "出表日期": "1150415",
            "發言日期": "1150414",
            "發言時間": "70003",
            "公司代號": "1463",
            "公司名稱": "強盛新",
            "主旨 ": "公告公司更名",  # 注意 key 尾端有空白
            "符合條款": "第51款",
            "說明": "詳細說明",
        }
    ]
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=payload)
        events = await fetch_latest_events()

    assert len(events) == 1
    assert events[0].symbol == "1463"
    assert events[0].title == "公告公司更名"
    # 發言時間 "70003" 左補 0 → 07:00:03
    assert events[0].event_datetime == datetime(2026, 4, 14, 7, 0, 3)


@pytest.mark.asyncio
async def test_fetch_latest_events_accepts_gregorian_date() -> None:
    """日期若為 8 碼西元格式亦應被支援。"""
    payload = [
        {
            "發言日期": "20260410",
            "發言時間": "143020",
            "公司代號": "2330",
            "主旨": "test",
            "符合條款": "第五款",
            "說明": "x",
        }
    ]
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=payload)
        events = await fetch_latest_events()

    assert len(events) == 1
    assert events[0].event_datetime == datetime(2026, 4, 10, 14, 30, 20)
