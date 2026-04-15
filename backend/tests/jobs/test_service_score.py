"""job_type='score' dispatcher 測試。"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Base, Job, Stock


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


async def test_run_score_job(session_factory) -> None:
    from alpha_lab.storage.models import FinancialStatement

    with session_factory() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        # 評分只涵蓋有財報的 symbol，故需至少一筆 FinancialStatement
        session.add(
            FinancialStatement(
                symbol="2330",
                period="2026Q1",
                statement_type="income",
                revenue=100,
                gross_profit=30,
                net_income=20,
                eps=2.0,
            )
        )
        job = create_job(
            session,
            job_type=JobType.SCORE,
            params={"date": "2026-04-15"},
        )
        session.commit()
        job_id = job.id

    await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.result_summary is not None
        assert "scored" in completed.result_summary
        from alpha_lab.storage.models import Score

        rows = session.execute(select(Score)).scalars().all()
        assert len(rows) == 1
