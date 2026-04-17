"""PROCESSED_INDICATORS / PROCESSED_RATIOS job 測試。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Base, FinancialStatement, Job, PriceDaily, Stock


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)


@pytest.mark.asyncio
async def test_processed_indicators_writes_json(session_factory, tmp_path: Path, monkeypatch):
    with session_factory() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        # 30 天 close 資料就夠 ma5 / ma20（跨 1~2 月避免日期重複）
        for i in range(30):
            d = date(2026, 1, 1 + i) if i < 28 else date(2026, 2, i - 27)
            s.add(PriceDaily(
                symbol="2330",
                trade_date=d,
                open=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.0 + i, volume=1000,
            ))
        s.commit()

    monkeypatch.setattr("alpha_lab.jobs.service.get_settings_for_processed", lambda: type("X", (), {"processed_dir": tmp_path}))
    with session_factory() as s:
        job = create_job(s, job_type=JobType.PROCESSED_INDICATORS, params={"symbols": ["2330"]})
        s.commit()
        job_id = job.id

    await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "completed"

    out = tmp_path / "indicators" / "2330.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["symbol"] == "2330"
    assert payload["latest"]["ma5"] is not None


@pytest.mark.asyncio
async def test_processed_ratios_writes_json(session_factory, tmp_path: Path, monkeypatch):
    with session_factory() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        for q in ["2026Q1", "2025Q4", "2025Q3", "2025Q2"]:
            s.add(FinancialStatement(
                symbol="2330", period=q, statement_type="income",
                revenue=1_000, gross_profit=300, operating_income=200,
                net_income=150, eps=5.0,
            ))
        s.add(FinancialStatement(
            symbol="2330", period="2026Q1", statement_type="balance",
            total_assets=10_000, total_liabilities=4_000, total_equity=6_000,
        ))
        s.add(PriceDaily(symbol="2330", trade_date=date(2026, 4, 1),
                        open=100.0, high=105.0, low=98.0, close=100.0, volume=1000))
        s.commit()

    monkeypatch.setattr("alpha_lab.jobs.service.get_settings_for_processed", lambda: type("X", (), {"processed_dir": tmp_path}))
    with session_factory() as s:
        job = create_job(s, job_type=JobType.PROCESSED_RATIOS, params={"symbols": ["2330"], "as_of": "2026-04-01"})
        s.commit()
        job_id = job.id

    await run_job_sync(job_id=job_id, session_factory=session_factory)

    out = tmp_path / "ratios" / "2330.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["pe"] == pytest.approx(5.0)  # close/(eps*4) = 100/20
