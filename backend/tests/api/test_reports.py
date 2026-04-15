"""/api/reports 路由整合測試。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from alpha_lab.api.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))
    with TestClient(app) as c:
        yield c


def test_post_list_get_roundtrip(client: TestClient) -> None:
    payload = {
        "type": "stock",
        "title": "台積電",
        "body_markdown": "## 執行摘要\n看好",
        "summary_line": "Q1 亮眼",
        "subject": "2330",
        "symbols": ["2330"],
        "tags": ["半導體", "buy"],
        "date": "2026-04-14",
    }
    r = client.post("/api/reports", json=payload)
    assert r.status_code == 201, r.text
    meta = r.json()
    assert meta["id"] == "stock-2330-2026-04-14"

    r_list = client.get("/api/reports")
    assert r_list.status_code == 200
    items = r_list.json()
    assert any(m["id"] == "stock-2330-2026-04-14" for m in items)

    r_detail = client.get(f"/api/reports/{meta['id']}")
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert detail["title"] == "台積電"
    assert "執行摘要" in detail["body_markdown"]


def test_list_filters(client: TestClient) -> None:
    client.post(
        "/api/reports",
        json={
            "type": "stock",
            "title": "a",
            "body_markdown": "a",
            "subject": "2330",
            "tags": ["buy"],
            "date": "2026-04-14",
        },
    )
    client.post(
        "/api/reports",
        json={
            "type": "portfolio",
            "title": "b",
            "body_markdown": "b",
            "tags": ["weekly"],
            "date": "2026-04-14",
        },
    )

    r = client.get("/api/reports", params={"type": "stock"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1 and items[0]["type"] == "stock"

    r = client.get("/api/reports", params={"tag": "weekly"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1 and items[0]["type"] == "portfolio"


def test_get_missing_returns_404(client: TestClient) -> None:
    r = client.get("/api/reports/nope")
    assert r.status_code == 404


def test_post_stock_missing_subject_returns_400(client: TestClient) -> None:
    r = client.post(
        "/api/reports",
        json={
            "type": "stock",
            "title": "x",
            "body_markdown": "x",
            "date": "2026-04-14",
        },
    )
    assert r.status_code == 400
    assert "subject" in r.json()["detail"]
