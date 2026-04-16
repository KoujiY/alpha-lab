"""/api/education 路由整合測試。"""

import pytest
from fastapi.testclient import TestClient

from alpha_lab.api.main import app
from alpha_lab.education.loader import clear_cache


@pytest.fixture(autouse=True)
def _clear_l2_cache() -> None:
    clear_cache()


def test_list_l2_topics_returns_core_set() -> None:
    with TestClient(app) as client:
        r = client.get("/api/education/l2")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert {"PE", "ROE", "dividend-yield", "monthly-revenue", "multi-factor-scoring"} <= ids


def test_get_l2_topic_ok() -> None:
    with TestClient(app) as client:
        r = client.get("/api/education/l2/PE")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "PE"
    assert "本益比" in body["title"]
    assert body["body_markdown"].startswith("# 本益比是什麼")


def test_get_l2_topic_404() -> None:
    with TestClient(app) as client:
        r = client.get("/api/education/l2/no-such-topic")
    assert r.status_code == 404
