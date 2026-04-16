"""Saved portfolio service 單元測試（Phase 6）。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.portfolios.service import (
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


@pytest.fixture
def sample_prices():
    """Seed 兩檔股票的 base_date 收盤價（使用 in-memory SQLite 隔離）。"""

    _override_engine(_make_test_engine())

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
