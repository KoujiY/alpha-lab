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

from alpha_lab.analysis.pipeline import score_all
from alpha_lab.collectors._twse_common import TWSERateLimitError
from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.mops_cashflow import fetch_cashflow, upsert_cashflow
from alpha_lab.collectors.mops_events import fetch_latest_events
from alpha_lab.collectors.mops_financials import (
    fetch_balance_sheet,
    fetch_cashflow_statement,
    fetch_income_statement,
)
from alpha_lab.collectors.runner import (
    upsert_daily_prices,
    upsert_events,
    upsert_financial_statements,
    upsert_institutional_trades,
    upsert_margin_trades,
    upsert_monthly_revenues,
    upsert_stock_info,
)
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
from alpha_lab.collectors.twse_margin import fetch_margin_trades
from alpha_lab.collectors.twse_stock_info import fetch_stock_info
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
    except TWSERateLimitError as exc:
        logger.warning("job %s blocked by TWSE WAF: %s", job_id, exc)
        with session_factory() as session:
            failed = session.get(Job, job_id)
            assert failed is not None
            failed.status = "failed"
            failed.error_message = f"{type(exc).__name__}: {exc}"
            failed.finished_at = datetime.now(UTC)
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

    if job_type is JobType.TWSE_PRICES_BATCH:
        batch_symbols: list[str] = [str(s) for s in params["symbols"]]
        year_month_str = str(
            params.get("year_month")
            or datetime.now(UTC).date().strftime("%Y-%m")
        )
        year, month = year_month_str.split("-")
        ym_date = date(int(year), int(month), 1)
        total = 0
        failed_symbols: list[str] = []
        for sym in batch_symbols:
            try:
                price_rows = await fetch_daily_prices(
                    symbol=sym, year_month=ym_date
                )
                with session_factory() as session:
                    n = upsert_daily_prices(session, price_rows)
                    session.commit()
                total += n
            except Exception as exc:
                logger.warning("batch prices: %s failed: %s", sym, exc)
                failed_symbols.append(sym)
        suffix = (
            f"; failed: {','.join(failed_symbols)}" if failed_symbols else ""
        )
        return (
            f"batch upserted {total} price rows for {len(batch_symbols)} symbols "
            f"{year_month_str}{suffix}"
        )

    if job_type is JobType.TWSE_STOCK_INFO:
        symbols = params.get("symbols")
        info_rows = await fetch_stock_info(symbols=symbols)
        with session_factory() as session:
            n = upsert_stock_info(session, info_rows)
            session.commit()
        return f"upserted {n} stock info rows"

    if job_type is JobType.MOPS_REVENUE:
        symbols = params.get("symbols")
        revenue_rows = await fetch_latest_monthly_revenues(symbols=symbols)
        with session_factory() as session:
            n = upsert_monthly_revenues(session, revenue_rows)
            session.commit()
        return f"upserted {n} revenue rows"

    if job_type is JobType.TWSE_INSTITUTIONAL:
        trade_date_str = params["trade_date"]  # "YYYY-MM-DD"
        year, month, day = trade_date_str.split("-")
        symbols = params.get("symbols")
        inst_rows = await fetch_institutional_trades(
            trade_date=date(int(year), int(month), int(day)),
            symbols=symbols,
        )
        with session_factory() as session:
            n = upsert_institutional_trades(session, inst_rows)
            session.commit()
        return f"upserted {n} institutional rows for {trade_date_str}"

    if job_type is JobType.TWSE_MARGIN:
        trade_date_str = params["trade_date"]
        year, month, day = trade_date_str.split("-")
        symbols = params.get("symbols")
        margin_rows = await fetch_margin_trades(
            trade_date=date(int(year), int(month), int(day)),
            symbols=symbols,
        )
        with session_factory() as session:
            n = upsert_margin_trades(session, margin_rows)
            session.commit()
        return f"upserted {n} margin rows for {trade_date_str}"

    if job_type is JobType.MOPS_EVENTS:
        symbols = params.get("symbols")
        event_rows = await fetch_latest_events(symbols=symbols)
        with session_factory() as session:
            n = upsert_events(session, event_rows)
            session.commit()
        return f"inserted {n} new events"

    if job_type is JobType.MOPS_FINANCIALS:
        symbols = params.get("symbols")
        types = set(params.get("types") or ["income", "balance", "cashflow"])

        total_rows: list[Any] = []
        if "income" in types:
            total_rows += await fetch_income_statement(symbols=symbols)
        if "balance" in types:
            total_rows += await fetch_balance_sheet(symbols=symbols)
        if "cashflow" in types:
            total_rows += await fetch_cashflow_statement(symbols=symbols)

        with session_factory() as session:
            n = upsert_financial_statements(session, total_rows)
            session.commit()
        return f"upserted {n} financial statement rows ({sorted(types)})"

    if job_type is JobType.MOPS_CASHFLOW:
        symbol = str(params["symbol"])
        period = str(params["period"])  # "2026Q1"
        year_int, quarter = int(period[:4]), int(period[-1])
        roc_year = year_int - 1911
        cf = await fetch_cashflow(symbol, roc_year, quarter)
        with session_factory() as session:
            n = upsert_cashflow(session, symbol, period, cf)
            session.commit()
        return f"upserted {n} cashflow row for {symbol} {period}"

    if job_type is JobType.SCORE:
        date_str = params.get("date")
        calc_date = (
            date.fromisoformat(str(date_str))
            if isinstance(date_str, str)
            else datetime.now(UTC).date()
        )
        with session_factory() as session:
            n = score_all(session, calc_date)
        return f"scored {n} symbols for {calc_date.isoformat()}"

    raise ValueError(f"unknown job type: {job_type}")
