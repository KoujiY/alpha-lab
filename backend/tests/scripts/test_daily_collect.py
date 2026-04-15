"""daily_collect CLI 單元測試。"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage.models import Base, Event, InstitutionalTrade, MarginTrade, PriceDaily

# 匯入 backend/scripts/daily_collect.py
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "daily_collect.py"
spec = importlib.util.spec_from_file_location("daily_collect", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
daily_collect = importlib.util.module_from_spec(spec)
sys.modules["daily_collect"] = daily_collect
spec.loader.exec_module(daily_collect)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def test_parse_args_defaults() -> None:
    ns = daily_collect._parse_args([])
    assert ns.date is None
    assert ns.symbols is None


def test_parse_args_with_values() -> None:
    ns = daily_collect._parse_args(["--date", "2026-04-11", "--symbols", "2330,2317"])
    assert ns.date == "2026-04-11"
    assert ns.symbols == "2330,2317"


def test_parse_date_none_returns_today() -> None:
    assert daily_collect._parse_date(None) == date.today()


def test_parse_date_with_value() -> None:
    assert daily_collect._parse_date("2026-04-11") == date(2026, 4, 11)


@pytest.mark.asyncio
async def test_run_daily_collect_all_jobs_complete(session_factory, capsys) -> None:
    # 給 prices 用的 TWSE 回應
    stock_day_payload = {
        "stat": "OK",
        "fields": [
            "日期", "成交股數", "成交金額", "開盤價", "最高價",
            "最低價", "收盤價", "漲跌價差", "成交筆數",
        ],
        "data": [
            ["115/04/11", "1000", "0", "100", "110", "99", "105", "+5", "1"],
        ],
    }
    institutional_payload = {
        "stat": "OK",
        "fields": [
            "證券代號", "證券名稱",
            "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
            "外陸資買賣超股數(不含外資自營商)",
            "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
            "投信買進股數", "投信賣出股數", "投信買賣超股數",
            "自營商買賣超股數",
            "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)",
            "自營商買賣超股數(自行買賣)",
            "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
            "三大法人買賣超股數",
        ],
        "data": [["2330", "台積電"] + ["0"] * 16 + ["1000"]],
    }
    margin_fields = [
        "代號", "名稱",
        "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額", "可用額度",
        "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額", "可用額度",
        "資券互抵", "註記",
    ]
    margin_groups = [
        {"title": "股票", "span": 2},
        {"title": "融資", "span": 6},
        {"title": "融券", "span": 6},
        {"title": "", "span": 1},
        {"title": "", "span": 1},
    ]
    margin_payload = {
        "stat": "OK",
        "tables": [
            {"title": "信用交易總計", "fields": ["項目"], "data": []},
            {
                "title": "信用交易彙總",
                "groups": margin_groups,
                "fields": margin_fields,
                "data": [
                    [
                        "2330", "台積電",
                        "500", "400", "0", "10,100", "10,200", "999,999",
                        "30", "50", "0", "220", "200", "99,999",
                        "0", "",
                    ],
                ],
            },
        ],
    }
    events_payload = [
        {
            "出表日期": "1150411",
            "發言日期": "1150411",
            "發言時間": "143020",
            "公司代號": "2330",
            "公司名稱": "台積電",
            "主旨": "配息案",
            "符合條款": "第五款",
            "說明": "每股 11 元",
        },
    ]

    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY").respond(
            json=stock_day_payload
        )
        mock.get("https://www.twse.com.tw/rwd/zh/fund/T86").respond(json=institutional_payload)
        mock.get("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN").respond(
            json=margin_payload
        )
        mock.get("https://openapi.twse.com.tw/v1/opendata/t187ap04_L").respond(json=events_payload)

        results = await daily_collect.run_daily_collect(
            trade_date=date(2026, 4, 11),
            symbols=["2330"],
            session_factory=session_factory,
        )

    labels = [r[0] for r in results]
    statuses = [r[1] for r in results]
    assert labels == ["TWSE prices 2330", "TWSE institutional", "TWSE margin", "MOPS events"]
    assert all(s == "completed" for s in statuses), results

    with session_factory() as session:
        assert session.query(PriceDaily).count() == 1
        assert session.query(InstitutionalTrade).count() == 1
        assert session.query(MarginTrade).count() == 1
        assert session.query(Event).count() == 1

    out = capsys.readouterr().out
    assert "daily_collect trade_date=2026-04-11" in out
    assert "summary" in out


@pytest.mark.asyncio
async def test_run_daily_collect_skips_prices_when_no_symbols(
    session_factory, capsys
) -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.twse.com.tw/rwd/zh/fund/T86").respond(
            json={"stat": "OK", "fields": [], "data": []}
        )
        mock.get("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN").respond(
            json={
                "stat": "OK",
                "tables": [
                    {"title": "信用交易彙總", "groups": [], "fields": [], "data": []},
                ],
            }
        )
        mock.get("https://openapi.twse.com.tw/v1/opendata/t187ap04_L").respond(json=[])

        results = await daily_collect.run_daily_collect(
            trade_date=date(2026, 4, 11),
            symbols=None,
            session_factory=session_factory,
        )

    labels = [r[0] for r in results]
    assert labels == ["TWSE institutional", "TWSE margin", "MOPS events"]
    out = capsys.readouterr().out
    assert "[TWSE prices] skipped" in out
