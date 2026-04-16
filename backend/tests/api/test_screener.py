"""Screener API 整合測試。"""

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


def _seed_three_stocks(test_engine: Engine) -> None:
    _override_engine(test_engine)
    from alpha_lab.storage.engine import session_scope

    with session_scope() as session:
        stocks = [
            Stock(symbol="2330", name="台積電", industry="半導體"),
            Stock(symbol="2454", name="聯發科", industry="半導體"),
            Stock(symbol="2317", name="鴻海", industry="電子零組件"),
        ]
        session.add_all(stocks)
        session.flush()

        calc = date(2026, 4, 17)
        scores = [
            Score(
                symbol="2330",
                calc_date=calc,
                value_score=60,
                growth_score=80,
                dividend_score=50,
                quality_score=90,
                total_score=70,
            ),
            Score(
                symbol="2454",
                calc_date=calc,
                value_score=40,
                growth_score=95,
                dividend_score=30,
                quality_score=70,
                total_score=58.75,
            ),
            Score(
                symbol="2317",
                calc_date=calc,
                value_score=75,
                growth_score=50,
                dividend_score=70,
                quality_score=60,
                total_score=63.75,
            ),
        ]
        session.add_all(scores)


class TestGetFactors:
    def test_returns_five_factors(self) -> None:
        resp = TestClient(app).get("/api/screener/factors")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["factors"]) == 5
        keys = [f["key"] for f in data["factors"]]
        assert "value_score" in keys
        assert "total_score" in keys

    def test_factor_has_label_and_range(self) -> None:
        resp = TestClient(app).get("/api/screener/factors")
        factor = resp.json()["factors"][0]
        assert "label" in factor
        assert factor["min_value"] == 0.0
        assert factor["max_value"] == 100.0


class TestPostFilter:
    def test_no_filters_returns_all(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post("/api/screener/filter", json={"filters": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 3
        assert len(data["stocks"]) == 3

    def test_filter_by_growth_min_70(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post(
                "/api/screener/filter",
                json={"filters": [{"key": "growth_score", "min_value": 70}]},
            )
        data = resp.json()
        symbols = [s["symbol"] for s in data["stocks"]]
        assert "2330" in symbols  # growth=80
        assert "2454" in symbols  # growth=95
        assert "2317" not in symbols  # growth=50

    def test_filter_multiple_factors(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post(
                "/api/screener/filter",
                json={
                    "filters": [
                        {"key": "value_score", "min_value": 50},
                        {"key": "quality_score", "min_value": 80},
                    ]
                },
            )
        data = resp.json()
        symbols = [s["symbol"] for s in data["stocks"]]
        assert symbols == ["2330"]

    def test_sort_by_growth_asc(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post(
                "/api/screener/filter",
                json={
                    "filters": [],
                    "sort_by": "growth_score",
                    "sort_desc": False,
                },
            )
        symbols = [s["symbol"] for s in resp.json()["stocks"]]
        assert symbols == ["2317", "2330", "2454"]

    def test_limit(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post(
                "/api/screener/filter",
                json={"filters": [], "limit": 2},
            )
        assert len(resp.json()["stocks"]) == 2

    def test_no_scores_returns_409(self) -> None:
        eng = _make_test_engine()
        _override_engine(eng)
        with TestClient(app) as client:
            resp = client.post("/api/screener/filter", json={"filters": []})
        assert resp.status_code == 409

    def test_result_includes_stock_info(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post("/api/screener/filter", json={"filters": []})
        stock = resp.json()["stocks"][0]
        assert "name" in stock
        assert "industry" in stock
        assert "value_score" in stock

    def test_default_sort_by_total_desc(self) -> None:
        eng = _make_test_engine()
        _seed_three_stocks(eng)
        with TestClient(app) as client:
            resp = client.post("/api/screener/filter", json={"filters": []})
        stocks = resp.json()["stocks"]
        totals = [s["total_score"] for s in stocks]
        assert totals == sorted(totals, reverse=True)
