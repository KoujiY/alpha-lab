"""Job service 單元測試。"""

import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Base, Job, PriceDaily


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def test_create_job_returns_pending(session_factory) -> None:
    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        assert job.id is not None
        assert job.status == "pending"
        assert job.job_type == "twse_prices"


async def test_run_job_sync_twse_prices_happy_path(session_factory) -> None:
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

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=twse_payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.finished_at is not None
        assert session.query(PriceDaily).count() == 1


async def test_run_job_sync_marks_failed_on_error(session_factory) -> None:
    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(500)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        failed = session.get(Job, job_id)
        assert failed is not None
        assert failed.status == "failed"
        assert failed.error_message is not None
