"""backfill_industry 測試。"""

from pathlib import Path

from scripts.backfill_industry import backfill, load_industry_map
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, Stock


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


def test_load_industry_map_reads_yaml() -> None:
    mapping = load_industry_map()
    assert mapping.get("2330") == "半導體"


def test_backfill_updates_existing_stocks(tmp_path: Path) -> None:
    _override_engine(_make_test_engine())

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        s.add(Stock(symbol="9999", name="測試"))

    updated = backfill()
    assert updated == 1

    with session_scope() as s:
        stock = s.get(Stock, "2330")
        assert stock is not None
        assert stock.industry == "半導體"
        stub = s.get(Stock, "9999")
        assert stub is not None
        assert stub.industry is None
