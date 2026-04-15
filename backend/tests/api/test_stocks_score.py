"""GET /api/stocks/{symbol}/score 整合測試。"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import Base, Score, Stock


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


def test_get_stock_score_latest() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        s.add(
            Score(
                symbol="2330",
                calc_date=date(2026, 4, 15),
                value_score=70,
                growth_score=80,
                dividend_score=50,
                quality_score=90,
                total_score=72.5,
            )
        )

    with TestClient(app) as client:
        r = client.get("/api/stocks/2330/score")

    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "2330"
    assert body["latest"]["total_score"] == 72.5
    assert body["latest"]["value_score"] == 70


def test_get_stock_score_none_if_absent() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        s.add(Stock(symbol="9999", name="無評分"))

    with TestClient(app) as client:
        r = client.get("/api/stocks/9999/score")

    assert r.status_code == 200
    assert r.json()["latest"] is None
