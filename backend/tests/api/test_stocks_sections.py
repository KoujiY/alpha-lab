"""Stocks section detail endpoints 整合測試。"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import (
    Base,
    PriceDaily,
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


def _seed_stock_only(session: Session, symbol: str = "2330") -> None:
    session.add(Stock(symbol=symbol, name="台積電", industry="半導體"))


def test_prices_endpoint_filters_by_date_range() -> None:
    """日期範圍過濾：只回傳 start <= trade_date <= end 的資料。"""
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        _seed_stock_only(s)
        for d in [date(2026, 4, 10), date(2026, 4, 12), date(2026, 4, 14)]:
            s.add(
                PriceDaily(
                    symbol="2330",
                    trade_date=d,
                    open=600.0,
                    high=610.0,
                    low=595.0,
                    close=605.0,
                    volume=10000,
                )
            )

    with TestClient(app) as client:
        resp = client.get(
            "/api/stocks/2330/prices",
            params={"start": "2026-04-11", "end": "2026-04-13"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["trade_date"] == "2026-04-12"


def test_prices_endpoint_defaults_return_recent_60() -> None:
    """無 query 參數時預設最多回傳 60 筆（由新到舊取 60，回傳時由舊到新）。"""
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        _seed_stock_only(s)
        # 植入 5 筆資料，確認回傳筆數 <= 60
        for i in range(5):
            s.add(
                PriceDaily(
                    symbol="2330",
                    trade_date=date(2026, 1, i + 1),
                    open=600.0,
                    high=610.0,
                    low=595.0,
                    close=605.0,
                    volume=10000,
                )
            )

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/prices")

    assert resp.status_code == 200
    assert len(resp.json()) <= 60


def test_revenues_endpoint_returns_list() -> None:
    """無月營收資料時回傳空陣列（200 OK）。"""
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        _seed_stock_only(s)
        # 不植入任何 RevenueMonthly

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/revenues")

    assert resp.status_code == 200
    assert resp.json() == []


def test_section_endpoints_return_404_for_unknown_symbol() -> None:
    """所有細端點對未知 symbol 回傳 404。"""
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    sections = [
        "/api/stocks/9999/prices",
        "/api/stocks/9999/revenues",
        "/api/stocks/9999/financials",
        "/api/stocks/9999/institutional",
        "/api/stocks/9999/margin",
        "/api/stocks/9999/events",
    ]

    with TestClient(app) as client:
        for url in sections:
            resp = client.get(url)
            assert resp.status_code == 404, f"Expected 404 for {url}, got {resp.status_code}"
