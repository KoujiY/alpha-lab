"""Stocks overview 端點整合測試。"""

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import (
    Base,
    Event,
    FinancialStatement,
    InstitutionalTrade,
    MarginTrade,
    PriceDaily,
    RevenueMonthly,
    Stock,
)


def _make_test_engine() -> Engine:
    """建立共享記憶體 SQLite 引擎（StaticPool 確保所有連線共用同一個 in-memory DB）。"""
    return create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def _seed_full_stock(session) -> None:
    session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
    session.add(
        PriceDaily(
            symbol="2330",
            trade_date=date(2026, 4, 14),
            open=600.0,
            high=610.0,
            low=595.0,
            close=605.0,
            volume=12345,
        )
    )
    session.add(
        RevenueMonthly(
            symbol="2330", year=2026, month=3, revenue=250_000_000_000,
            yoy_growth=0.15, mom_growth=0.05,
        )
    )
    session.add(
        FinancialStatement(
            symbol="2330", period="2026Q1", statement_type="income",
            revenue=700_000_000_000, gross_profit=400_000_000_000,
            operating_income=350_000_000_000, net_income=280_000_000_000,
            eps=10.8,
        )
    )
    session.add(
        FinancialStatement(
            symbol="2330", period="2026Q1", statement_type="balance",
            total_assets=5_000_000_000_000,
            total_liabilities=1_500_000_000_000,
            total_equity=3_500_000_000_000,
        )
    )
    session.add(
        InstitutionalTrade(
            symbol="2330", trade_date=date(2026, 4, 14),
            foreign_net=1000, trust_net=500, dealer_net=-200, total_net=1300,
        )
    )
    session.add(
        MarginTrade(
            symbol="2330", trade_date=date(2026, 4, 14),
            margin_balance=10000, margin_buy=100, margin_sell=50,
            short_balance=2000, short_sell=20, short_cover=10,
        )
    )
    session.add(
        Event(
            symbol="2330",
            event_datetime=datetime(2026, 4, 10, 15, 30, tzinfo=UTC),
            event_type="財報",
            title="公布 Q1 財報",
            content="營收創新高",
        )
    )


def test_overview_returns_all_sections() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_full_stock(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["symbol"] == "2330"
    assert body["meta"]["industry"] == "半導體"
    assert len(body["prices"]) == 1
    assert len(body["revenues"]) == 1
    assert len(body["financials"]) == 1
    fin = body["financials"][0]
    assert fin["period"] == "2026Q1"
    assert fin["revenue"] == 700_000_000_000
    assert fin["total_equity"] == 3_500_000_000_000
    assert len(body["institutional"]) == 1
    assert len(body["margin"]) == 1
    assert len(body["events"]) == 1


def test_overview_returns_404_for_unknown_symbol() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    with TestClient(app) as client:
        resp = client.get("/api/stocks/9999/overview")

    assert resp.status_code == 404


def test_overview_merges_income_and_balance_financials() -> None:
    """同一 period 的 income + balance 要合併成單一 FinancialPoint。"""
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_full_stock(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/overview")

    fins = resp.json()["financials"]
    assert len(fins) == 1
    assert fins[0]["revenue"] is not None
    assert fins[0]["total_assets"] is not None
