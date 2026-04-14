"""Models 結構測試：確保 declarative base 註冊所有表、欄位型別正確。"""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage.models import Base, Job, PriceDaily, RevenueMonthly, Stock


def test_base_registers_expected_tables() -> None:
    expected = {"stocks", "prices_daily", "revenues_monthly", "jobs"}
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_create_all_and_insert_stock() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    session_local = sessionmaker(bind=engine, future=True)
    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        session.commit()

        fetched = session.get(Stock, "2330")
        assert fetched is not None
        assert fetched.name == "台積電"


def test_price_daily_composite_primary_key() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        session.add(
            PriceDaily(
                symbol="2330",
                trade_date=datetime(2026, 4, 1, tzinfo=UTC).date(),
                open=500.0,
                high=510.0,
                low=499.0,
                close=505.0,
                volume=12345678,
            )
        )
        session.commit()


def test_job_defaults() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        job = Job(job_type="twse_prices", params_json="{}")
        session.add(job)
        session.commit()
        assert job.id is not None
        assert job.status == "pending"


def test_revenue_monthly_composite_key() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            RevenueMonthly(
                symbol="2330",
                year=2026,
                month=3,
                revenue=300000000,
                yoy_growth=20.0,
                mom_growth=7.14,
            )
        )
        session.commit()

        row = session.get(RevenueMonthly, {"symbol": "2330", "year": 2026, "month": 3})
        assert row is not None
        assert row.revenue == 300000000
