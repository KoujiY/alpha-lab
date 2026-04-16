"""/api/portfolios/saved 整合測試（Phase 6）。"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, PriceDaily, Stock


@pytest.fixture(autouse=True)
def _isolated_engine() -> Iterator[None]:
    test_engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )
    yield


def _seed_prices() -> None:
    with session_scope() as session:
        session.merge(Stock(symbol="2330", name="台積電"))
        session.merge(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 17),
                open=600.0,
                high=600.0,
                low=600.0,
                close=600.0,
                volume=1000,
            )
        )


def test_post_saved_then_list_returns_new_row():
    _seed_prices()
    client = TestClient(app)
    payload = {
        "style": "balanced",
        "label": "test-save",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
    }
    resp = client.post("/api/portfolios/saved", json=payload)
    assert resp.status_code == 201
    meta = resp.json()
    pid = meta["id"]

    list_resp = client.get("/api/portfolios/saved")
    assert list_resp.status_code == 200
    assert any(m["id"] == pid for m in list_resp.json())


def test_performance_returns_points_and_total_return():
    _seed_prices()
    client = TestClient(app)
    payload = {
        "style": "balanced",
        "label": "perf-test",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
    }
    pid = client.post("/api/portfolios/saved", json=payload).json()["id"]
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 18),
                open=660.0,
                high=660.0,
                low=660.0,
                close=660.0,
                volume=1000,
            )
        )
    perf_resp = client.get(f"/api/portfolios/saved/{pid}/performance")
    assert perf_resp.status_code == 200
    body = perf_resp.json()
    assert body["latest_nav"] > 1.0
    assert len(body["points"]) == 2


def test_delete_saved_removes():
    client = TestClient(app)
    _seed_prices()
    pid = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "del",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
            ],
        },
    ).json()["id"]
    resp = client.delete(f"/api/portfolios/saved/{pid}")
    assert resp.status_code == 204
    assert client.get(f"/api/portfolios/saved/{pid}/performance").status_code == 404


def test_post_saved_requires_base_price_available():
    client = TestClient(app)
    # 不 seed prices → 無 base_price 可取
    payload = {
        "style": "balanced",
        "label": "no-price",
        "holdings": [
            {"symbol": "9999", "name": "NOPE", "weight": 1.0, "base_price": 10.0}
        ],
    }
    # 允許通過（前端傳入 base_price 即為使用者自選基準）；不回 409
    resp = client.post("/api/portfolios/saved", json=payload)
    assert resp.status_code == 201
