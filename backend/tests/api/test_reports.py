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


def _seed_stock(client: TestClient, symbol: str, title: str) -> str:
    r = client.post(
        "/api/reports",
        json={
            "type": "stock",
            "title": title,
            "body_markdown": "## body",
            "summary_line": f"summary-{symbol}",
            "subject": symbol,
            "symbols": [symbol],
            "tags": ["tag-a"],
            "date": "2026-04-17",
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def test_patch_report_toggles_starred(client: TestClient) -> None:
    rid = _seed_stock(client, "2330", "TSMC")
    resp = client.patch(f"/api/reports/{rid}", json={"starred": True})
    assert resp.status_code == 200
    assert resp.json()["starred"] is True


def test_patch_report_unknown_returns_404(client: TestClient) -> None:
    resp = client.patch("/api/reports/nope", json={"starred": True})
    assert resp.status_code == 404


def test_delete_report_returns_204(client: TestClient) -> None:
    rid = _seed_stock(client, "2330", "TSMC")
    resp = client.delete(f"/api/reports/{rid}")
    assert resp.status_code == 204
    assert client.get(f"/api/reports/{rid}").status_code == 404


def test_delete_report_unknown_returns_404(client: TestClient) -> None:
    resp = client.delete("/api/reports/nope")
    assert resp.status_code == 404


def test_list_reports_search_query(client: TestClient) -> None:
    _seed_stock(client, "2330", "TSMC 分析")
    _seed_stock(client, "2317", "鴻海深度")
    resp = client.get("/api/reports", params={"q": "2330"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["symbols"] == ["2330"]


def test_list_reports_symbol_filter(client: TestClient) -> None:
    _seed_stock(client, "2330", "TSMC")
    _seed_stock(client, "2317", "HHP")
    resp = client.get("/api/reports", params={"symbol": "2330"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
