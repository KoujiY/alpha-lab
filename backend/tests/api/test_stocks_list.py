"""Stocks list 端點整合測試。"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import Base, Stock


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


def _seed_two_stocks(session: Session) -> None:
    session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
    session.add(Stock(symbol="2317", name="鴻海", industry="電子代工"))


def test_list_returns_all_stocks() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_two_stocks(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    symbols = {item["symbol"] for item in body}
    assert symbols == {"2330", "2317"}


def test_list_filters_by_query() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_two_stocks(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks?q=2330")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "2330"


def test_list_matches_by_name_substring() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_two_stocks(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks?q=台積")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "2330"


def test_list_accepts_limit_3000() -> None:
    """Phase 8：/stocks 列表頁需要一次載入全市場（~2000 檔），上限提升到 3000。"""
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_two_stocks(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks?limit=3000")

    assert resp.status_code == 200
    assert len(resp.json()) == 2
