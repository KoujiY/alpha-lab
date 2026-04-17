"""probe_base_date symbol_statuses 分類測試。"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.portfolios.service import probe_base_date
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import Base, PriceDaily, Stock


def _make_test_engine():
    return create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(autouse=True)
def _isolated_engine():
    eng = _make_test_engine()
    Base.metadata.create_all(eng)
    engine_module._engine = eng
    engine_module._SessionLocal = sessionmaker(
        bind=eng, autoflush=False, autocommit=False, future=True
    )
    yield


@pytest.fixture()
def _seed_stocks():
    """建立測試用 Stock + PriceDaily。"""
    from alpha_lab.storage.engine import session_scope

    today = date.today()
    yesterday = today - timedelta(days=1)
    old_date = today - timedelta(days=30)

    with session_scope() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            PriceDaily(
                symbol="2330",
                trade_date=today,
                open=100,
                high=105,
                low=99,
                close=103,
                volume=50000,
            )
        )

        session.add(Stock(symbol="2317", name="鴻海"))
        session.add(
            PriceDaily(
                symbol="2317",
                trade_date=yesterday,
                open=90,
                high=92,
                low=89,
                close=91,
                volume=30000,
            )
        )

        session.add(Stock(symbol="3008", name="大立光"))
        session.add(
            PriceDaily(
                symbol="3008",
                trade_date=old_date,
                open=2000,
                high=2050,
                low=1980,
                close=2010,
                volume=500,
            )
        )

        session.add(Stock(symbol="6666", name="虛擬股"))


@pytest.mark.usefixtures("_seed_stocks")
class TestProbeSymbolStatuses:
    def test_today_missing(self) -> None:
        _, missing, statuses = probe_base_date(["2317"], date.today())
        assert "2317" in missing
        assert statuses["2317"] == "today_missing"

    def test_stale(self) -> None:
        _, missing, statuses = probe_base_date(["3008"], date.today())
        assert "3008" in missing
        assert statuses["3008"] == "stale"

    def test_no_data(self) -> None:
        _, missing, statuses = probe_base_date(["6666"], date.today())
        assert "6666" in missing
        assert statuses["6666"] == "no_data"

    def test_available_not_in_statuses(self) -> None:
        _, missing, statuses = probe_base_date(["2330"], date.today())
        assert "2330" not in missing
        assert "2330" not in statuses

    def test_mixed(self) -> None:
        _, missing, statuses = probe_base_date(
            ["2330", "2317", "3008", "6666"], date.today()
        )
        assert "2330" not in missing
        assert statuses.get("2317") == "today_missing"
        assert statuses.get("3008") == "stale"
        assert statuses.get("6666") == "no_data"
