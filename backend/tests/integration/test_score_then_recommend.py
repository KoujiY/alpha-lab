"""完整流程：seed → score job → recommend API。"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import (
    Base,
    FinancialStatement,
    PriceDaily,
    RevenueMonthly,
    Stock,
)


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


def _seed_universe() -> None:
    from alpha_lab.storage.engine import session_scope

    symbols = ["2330", "2454", "2603", "1301", "2882"]
    periods = [
        "2026Q1",
        "2025Q4",
        "2025Q3",
        "2025Q2",
        "2025Q1",
        "2024Q4",
        "2024Q3",
        "2024Q2",
    ]

    with session_scope() as s:
        for i, sym in enumerate(symbols):
            s.add(Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 2}"))
            s.add(
                PriceDaily(
                    symbol=sym,
                    trade_date=date(2026, 4, 15),
                    open=100,
                    high=110,
                    low=95,
                    close=100 + i,
                    volume=1000,
                )
            )
            for q in periods:
                s.add(
                    FinancialStatement(
                        symbol=sym,
                        period=q,
                        statement_type="income",
                        revenue=100 + i,
                        gross_profit=30 + i,
                        net_income=20 + i,
                        eps=1.0 + i * 0.5,
                    )
                )
            s.add(
                FinancialStatement(
                    symbol=sym,
                    period="2026Q1",
                    statement_type="balance",
                    total_assets=1000,
                    total_liabilities=400 - i * 20,
                    total_equity=600 + i * 20,
                )
            )
            for year in (2025, 2026):
                for month in range(1, 13):
                    s.add(
                        RevenueMonthly(
                            symbol=sym,
                            year=year,
                            month=month,
                            revenue=10 + month + i,
                        )
                    )


def test_score_then_recommend_flow() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)
    _seed_universe()

    with TestClient(app) as client:
        r = client.post(
            "/api/jobs/collect",
            json={"type": "score", "params": {"date": "2026-04-15"}},
        )
        assert r.status_code == 202, r.text
        job_id = r.json()["id"]

        status_resp = client.get(f"/api/jobs/status/{job_id}")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "completed", status_resp.json()

        r2 = client.post("/api/portfolios/recommend")
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert len(data["portfolios"]) == 3
        balanced = next(p for p in data["portfolios"] if p["style"] == "balanced")
        assert balanced["is_top_pick"] is True
        assert len(balanced["holdings"]) > 0
