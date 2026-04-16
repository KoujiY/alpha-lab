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


def test_probe_endpoint_reports_today_status():
    _seed_prices()  # 只 seed 2330 在 2026-04-17
    client = TestClient(app)
    resp = client.get("/api/portfolios/saved/probe?symbols=2330,2317")
    assert resp.status_code == 200
    body = resp.json()
    # today != 2026-04-17 → 至少一個 missing_today
    # 2317 完全沒 seed → resolved_date 為 None
    assert "today_available" in body
    assert "missing_today_symbols" in body
    assert "resolved_date" in body
    assert "target_date" in body


def test_post_saved_with_parent_creates_lineage():
    _seed_prices()
    client = TestClient(app)
    parent_payload = {
        "style": "balanced",
        "label": "parent",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
    }
    parent_id = client.post("/api/portfolios/saved", json=parent_payload).json()["id"]

    child_payload = {
        "style": "balanced",
        "label": "child",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
        "parent_id": parent_id,
    }
    resp = client.post("/api/portfolios/saved", json=child_payload)
    assert resp.status_code == 201
    meta = resp.json()
    assert meta["parent_id"] == parent_id
    assert meta["parent_nav_at_fork"] == pytest.approx(1.0)


def test_post_saved_rejects_unknown_parent_id():
    _seed_prices()
    client = TestClient(app)
    resp = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "orphan",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
            ],
            "parent_id": 999,
        },
    )
    assert resp.status_code == 400
    assert "parent portfolio" in resp.json()["detail"]


def test_post_saved_rejects_duplicate_symbol():
    _seed_prices()
    client = TestClient(app)
    resp = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "dup",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 0.5, "base_price": 600.0},
                {"symbol": "2330", "name": "台積電", "weight": 0.5, "base_price": 600.0},
            ],
        },
    )
    assert resp.status_code == 422  # Pydantic validation error


def test_post_saved_rejects_weights_not_summing_to_one():
    _seed_prices()
    client = TestClient(app)
    resp = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "bad-sum",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 0.8, "base_price": 600.0},
            ],
        },
    )
    assert resp.status_code == 422


def test_performance_returns_parent_points_when_forked():
    # 透過 HTTP 測試時 parent / child 的 base_date 都來自 `date.today()`，因此
    # 兩者相同。parent_points 實際值為空 list（非 None），但 parent_nav_at_fork
    # 會紀錄 parent latest NAV。service-level 測試負責驗證跨日期的過濾邏輯
    # （見 test_service.py::test_compute_performance_returns_parent_points_when_forked）。
    _seed_prices()
    client = TestClient(app)
    parent_id = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "parent",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
            ],
        },
    ).json()["id"]
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
    child_id = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "child",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 660.0}
            ],
            "parent_id": parent_id,
        },
    ).json()["id"]
    perf = client.get(f"/api/portfolios/saved/{child_id}/performance").json()
    # parent latest NAV 於 child 建立時為 1.10（04-18 @ 660 / 600）
    assert perf["parent_nav_at_fork"] == pytest.approx(1.10, rel=1e-4)
    # HTTP 路徑 parent/child base_date 同為 today，parent_points filter 結果為空
    assert perf["parent_points"] is not None
    assert isinstance(perf["parent_points"], list)
