"""Saved portfolio service 單元測試（Phase 6）。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.portfolios.service import (
    compute_performance,
    delete_saved,
    list_saved,
    save_portfolio,
)
from alpha_lab.schemas.saved_portfolio import SavedHolding, SavedPortfolioCreate
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, PriceDaily, Stock


def _make_test_engine() -> Engine:
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


@pytest.fixture(autouse=True)
def _isolated_engine():
    """每個測試都用獨立 in-memory SQLite engine，避免碰到真正的 data/alpha_lab.db。"""

    _override_engine(_make_test_engine())
    yield


@pytest.fixture
def sample_prices():
    """Seed 兩檔股票的 base_date 收盤價。"""

    with session_scope() as session:
        for sym, name, close in [("2330", "台積電", 600.0), ("2317", "鴻海", 100.0)]:
            session.merge(Stock(symbol=sym, name=name))
            session.merge(
                PriceDaily(
                    symbol=sym,
                    trade_date=date(2026, 4, 17),
                    open=close, high=close, low=close, close=close,
                    volume=1000,
                )
            )
    yield


def test_save_portfolio_persists_holdings(sample_prices):
    payload = SavedPortfolioCreate(
        style="balanced",
        label="Apr 平衡組",
        holdings=[
            SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
            SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
        ],
    )
    meta = save_portfolio(payload, base_date=date(2026, 4, 17))
    assert meta.id > 0
    assert meta.holdings_count == 2
    assert meta.base_date == date(2026, 4, 17)


def test_list_saved_returns_newest_first(sample_prices):
    save_portfolio(
        SavedPortfolioCreate(
            style="conservative", label="older",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 15),
    )
    newer = save_portfolio(
        SavedPortfolioCreate(
            style="aggressive", label="newer",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    items = list_saved()
    assert items[0].id == newer.id


def test_delete_saved_removes_row(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="to-delete",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    assert delete_saved(meta.id) is True
    assert delete_saved(meta.id) is False
    assert all(m.id != meta.id for m in list_saved())


def test_compute_performance_tracks_nav(sample_prices):
    # 4/17 以 600 / 100 為基準，之後價格變化看 NAV 是否對
    with session_scope() as session:
        for d, close_2330, close_2317 in [
            (date(2026, 4, 18), 630.0, 105.0),  # +5% / +5% → NAV 1.05
            (date(2026, 4, 21), 660.0, 110.0),  # +10% / +10% → NAV 1.10
        ]:
            for sym, close in [("2330", close_2330), ("2317", close_2317)]:
                session.merge(
                    PriceDaily(
                        symbol=sym,
                        trade_date=d,
                        open=close, high=close, low=close, close=close,
                        volume=1000,
                    )
                )

    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="perf",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
                SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
            ],
        ),
        base_date=date(2026, 4, 17),
    )
    resp = compute_performance(meta.id)
    assert resp is not None
    # base day + 2 個交易日 = 3 points
    assert len(resp.points) == 3
    assert resp.points[0].nav == pytest.approx(1.0)
    assert resp.points[1].nav == pytest.approx(1.05, rel=1e-4)
    assert resp.points[2].nav == pytest.approx(1.10, rel=1e-4)
    assert resp.total_return == pytest.approx(0.10, rel=1e-4)


def test_compute_performance_missing_price_skips_day(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="missing",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    # 只有 base_date 有價格，後面沒有 → 僅 1 個 point
    resp = compute_performance(meta.id)
    assert resp is not None
    assert len(resp.points) == 1
    assert resp.latest_nav == pytest.approx(1.0)


def test_compute_performance_returns_none_for_unknown_id():
    assert compute_performance(99999) is None
