"""Job API 整合測試。"""

import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import Base


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def test_post_collect_returns_job_id_and_status_pending() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    twse_payload = {
        "stat": "OK",
        "fields": [
            "日期", "成交股數", "成交金額", "開盤價", "最高價",
            "最低價", "收盤價", "漲跌價差", "成交筆數",
        ],
        "data": [
            ["115/04/01", "1000", "0", "100", "110", "99", "105", "+5", "1"],
        ],
    }

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=twse_payload)
        with TestClient(app) as client:
            resp = client.post(
                "/api/jobs/collect",
                json={
                    "type": "twse_prices",
                    "params": {"symbol": "2330", "year_month": "2026-04"},
                },
            )
            assert resp.status_code == 202
            body = resp.json()
            assert "id" in body
            assert body["status"] in ("pending", "running", "completed")

            status_resp = client.get(f"/api/jobs/status/{body['id']}")
            assert status_resp.status_code == 200
            data = status_resp.json()
            assert data["id"] == body["id"]
            assert data["status"] in ("pending", "running", "completed")


def test_get_status_404_for_missing_job() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with TestClient(app) as client:
        resp = client.get("/api/jobs/status/99999")
        assert resp.status_code == 404


def test_post_collect_rejects_unknown_type() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with TestClient(app) as client:
        resp = client.post(
            "/api/jobs/collect",
            json={"type": "unknown_type", "params": {}},
        )
        assert resp.status_code == 422
