"""MOPS collector 單元測試。"""

import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.runner import upsert_monthly_revenues
from alpha_lab.schemas.revenue import MonthlyRevenue
from alpha_lab.storage.models import Base, RevenueMonthly, Stock

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


def test_upsert_monthly_revenues_inserts_new_rows() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            MonthlyRevenue(
                symbol="2330", year=2026, month=3,
                revenue=300000000, yoy_growth=20.0, mom_growth=7.14,
            ),
            MonthlyRevenue(
                symbol="2317", year=2026, month=3,
                revenue=500000000, yoy_growth=11.11, mom_growth=-1.96,
            ),
        ]
        inserted = upsert_monthly_revenues(session, rows)
        session.commit()

        assert inserted == 2
        assert session.query(RevenueMonthly).count() == 2


def test_upsert_monthly_revenues_updates_existing_row() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            RevenueMonthly(
                symbol="2330", year=2026, month=3,
                revenue=1, yoy_growth=0.0, mom_growth=0.0,
            )
        )
        session.commit()

        updated = upsert_monthly_revenues(
            session,
            [MonthlyRevenue(
                symbol="2330", year=2026, month=3,
                revenue=300000000, yoy_growth=20.0, mom_growth=7.14,
            )],
        )
        session.commit()

        assert updated == 1
        row = session.get(
            RevenueMonthly,
            {"symbol": "2330", "year": 2026, "month": 3},
        )
        assert row is not None
        assert row.revenue == 300000000
        assert row.yoy_growth == 20.0


def test_upsert_monthly_revenues_auto_creates_stock() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        inserted = upsert_monthly_revenues(
            session,
            [MonthlyRevenue(
                symbol="2454", year=2026, month=3,
                revenue=100000000, yoy_growth=None, mom_growth=None,
            )],
        )
        session.commit()

        assert inserted == 1
        stock = session.get(Stock, "2454")
        assert stock is not None
