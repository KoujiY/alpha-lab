"""Job service：建立 job、執行 job、更新狀態。

執行模型：
- run_job_sync 是 async 函式，在 FastAPI BackgroundTasks 中排程（單程序單執行緒）
- 適合本地個人工具；未來若要併發可改 Celery / RQ
"""

import json
import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.runner import upsert_daily_prices, upsert_monthly_revenues
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Job

logger = logging.getLogger(__name__)


def create_job(
    session: Session, *, job_type: JobType, params: dict[str, Any]
) -> Job:
    """建立 pending 狀態的 job。呼叫端負責 commit。"""
    job = Job(
        job_type=job_type.value,
        params_json=json.dumps(params, ensure_ascii=False),
        status="pending",
    )
    session.add(job)
    session.flush()
    return job


async def run_job_sync(
    *, job_id: int, session_factory: sessionmaker[Session]
) -> None:
    """執行 job。失敗會把狀態寫回 DB 但不 re-raise（背景任務不應中斷 app）。"""
    with session_factory() as session:
        job = session.get(Job, job_id)
        if job is None:
            logger.error("job %s not found", job_id)
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        session.commit()
        params = json.loads(job.params_json)
        job_type = JobType(job.job_type)

    try:
        summary = await _dispatch(job_type, params, session_factory)
        with session_factory() as session:
            completed = session.get(Job, job_id)
            assert completed is not None
            completed.status = "completed"
            completed.result_summary = summary
            completed.finished_at = datetime.now(UTC)
            session.commit()
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        with session_factory() as session:
            failed = session.get(Job, job_id)
            assert failed is not None
            failed.status = "failed"
            failed.error_message = f"{type(exc).__name__}: {exc}"
            failed.finished_at = datetime.now(UTC)
            session.commit()


async def _dispatch(
    job_type: JobType,
    params: dict[str, Any],
    session_factory: sessionmaker[Session],
) -> str:
    if job_type is JobType.TWSE_PRICES:
        symbol = params["symbol"]
        year_month_str = params["year_month"]
        year, month = year_month_str.split("-")
        price_rows = await fetch_daily_prices(
            symbol=symbol, year_month=date(int(year), int(month), 1)
        )
        with session_factory() as session:
            n = upsert_daily_prices(session, price_rows)
            session.commit()
        return f"upserted {n} price rows for {symbol} {year_month_str}"

    if job_type is JobType.MOPS_REVENUE:
        symbols = params.get("symbols")
        revenue_rows = await fetch_latest_monthly_revenues(symbols=symbols)
        with session_factory() as session:
            n = upsert_monthly_revenues(session, revenue_rows)
            session.commit()
        return f"upserted {n} revenue rows"

    raise ValueError(f"unknown job type: {job_type}")
