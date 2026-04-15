"""Glossary API 測試。"""

from fastapi.testclient import TestClient

from alpha_lab.api.main import app
from alpha_lab.glossary.loader import clear_cache


def test_get_term_returns_known_term() -> None:
    clear_cache()
    with TestClient(app) as client:
        resp = client.get("/api/glossary/PE")
    assert resp.status_code == 200
    body = resp.json()
    assert body["term"] == "本益比"
    assert "short" in body


def test_get_term_404_for_unknown() -> None:
    clear_cache()
    with TestClient(app) as client:
        resp = client.get("/api/glossary/NOT_A_TERM")
    assert resp.status_code == 404


def test_list_terms_returns_all_keys() -> None:
    clear_cache()
    with TestClient(app) as client:
        resp = client.get("/api/glossary")
    assert resp.status_code == 200
    body = resp.json()
    assert "PE" in body
