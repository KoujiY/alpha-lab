"""Job service：建立 job、執行 job、更新狀態。

執行模型：
- run_job_sync 是 async 函式，在 FastAPI BackgroundTasks 中排程（單程序單執行緒）
- 適合本地個人工具；未來若要併發可改 Celery / RQ
"""

import asyncio
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.analysis.indicators import compute_indicators
from alpha_lab.analysis.pipeline import score_all
from alpha_lab.analysis.ratios import compute_ratios
from alpha_lab.collectors._fallback import should_fallback_to_yahoo
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
from alpha_lab.collectors.yahoo import YahooFetchError, fetch_yahoo_daily_prices
from alpha_lab.config import get_settings
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Job, PriceDaily
from alpha_lab.storage.processed_store import write_indicators_json, write_ratios_json

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
        ym_date = date(int(year), int(month), 1)
        fallback_used = False
        try:
            price_rows = await fetch_daily_prices(symbol=symbol, year_month=ym_date)
        except Exception as exc:
            if not should_fallback_to_yahoo(exc):
                raise
            logger.info(
                "twse_prices %s %s → yahoo fallback triggered by %s",
                symbol, year_month_str, type(exc).__name__,
            )
            last_day = _last_day_of_month(ym_date)
            try:
                price_rows = await fetch_yahoo_daily_prices(
                    symbol=symbol, start=ym_date, end=last_day
                )
            except YahooFetchError as y_exc:
                raise RuntimeError(
                    f"both TWSE and Yahoo failed for {symbol} {year_month_str}: "
                    f"twse={type(exc).__name__}:{exc}; yahoo={y_exc}"
                ) from y_exc
            fallback_used = True
        with session_factory() as session:
            n = upsert_daily_prices(session, price_rows)
            session.commit()
        src = "yahoo" if fallback_used else "twse"
        return f"upserted {n} price rows for {symbol} {year_month_str} (source={src})"

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
        # 為什麼 throttle + retry：TWSE 對短時間連打有 WAF。batch 一次跑 20+ 檔
        # 很容易撞到偶發失敗，實測會回「非 OK stat」（非標準 307）導致個檔
        # 被誤判為永久失敗。加 0.3s 間隔降低觸發率，加一次 1s 退避重試吃掉偶發。
        # TWSERateLimitError（明確 WAF 封鎖）不重試，直接上拋讓整個 job 失敗。
        for i, sym in enumerate(batch_symbols):
            if i > 0:
                await asyncio.sleep(0.3)
            try:
                price_rows = await fetch_daily_prices(
                    symbol=sym, year_month=ym_date
                )
            except TWSERateLimitError:
                raise
            except ValueError as exc:
                if "沒有符合條件" in str(exc):
                    logger.info("batch prices: %s no data, skip", sym)
                    continue
                logger.info("batch prices: %s transient stat, retry once: %s", sym, exc)
                await asyncio.sleep(1.0)
                try:
                    price_rows = await fetch_daily_prices(
                        symbol=sym, year_month=ym_date
                    )
                except Exception as retry_exc:
                    if not should_fallback_to_yahoo(retry_exc):
                        logger.warning("batch prices: %s failed after retry: %s", sym, retry_exc)
                        failed_symbols.append(sym)
                        continue
                    try:
                        last_day = _last_day_of_month(ym_date)
                        price_rows = await fetch_yahoo_daily_prices(symbol=sym, start=ym_date, end=last_day)
                        logger.info("batch prices: %s fallback to yahoo ok", sym)
                    except YahooFetchError as y_exc:
                        logger.warning("batch prices: %s fallback yahoo failed: %s", sym, y_exc)
                        failed_symbols.append(sym)
                        continue
            except httpx.HTTPError as exc:
                try:
                    last_day = _last_day_of_month(ym_date)
                    price_rows = await fetch_yahoo_daily_prices(symbol=sym, start=ym_date, end=last_day)
                    logger.info("batch prices: %s http err → yahoo fallback: %s", sym, exc)
                except YahooFetchError as y_exc:
                    logger.warning("batch prices: %s both failed: twse=%s yahoo=%s", sym, exc, y_exc)
                    failed_symbols.append(sym)
                    continue
            with session_factory() as session:
                n = upsert_daily_prices(session, price_rows)
                session.commit()
            total += n
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

    if job_type is JobType.YAHOO_PRICES:
        symbol = str(params["symbol"])
        start = date.fromisoformat(str(params["start"]))
        end = date.fromisoformat(str(params["end"]))
        price_rows = await fetch_yahoo_daily_prices(symbol=symbol, start=start, end=end)
        with session_factory() as session:
            n = upsert_daily_prices(session, price_rows)
            session.commit()
        return f"upserted {n} price rows from yahoo for {symbol} {start}~{end}"

    if job_type is JobType.PROCESSED_INDICATORS:
        symbols = params.get("symbols") or []
        settings = get_settings_for_processed()
        processed_dir = Path(settings.processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)
        total = 0
        with session_factory() as session:
            for sym in symbols:
                rows = session.execute(
                    select(
                        PriceDaily.trade_date, PriceDaily.close,
                        PriceDaily.high, PriceDaily.low,
                    )
                    .where(PriceDaily.symbol == sym)
                    .order_by(PriceDaily.trade_date.asc())
                ).all()
                series = compute_indicators(
                    [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in rows],
                )
                if series.as_of is None:
                    continue
                write_indicators_json(
                    base_dir=processed_dir, symbol=sym, series=series,
                )
                total += 1
        return f"wrote {total} indicators json files"

    if job_type is JobType.PROCESSED_RATIOS:
        symbols = params.get("symbols") or []
        as_of_str = params.get("as_of")
        as_of = (
            date.fromisoformat(str(as_of_str))
            if as_of_str
            else datetime.now(UTC).date()
        )
        settings = get_settings_for_processed()
        processed_dir = Path(settings.processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)
        total = 0
        with session_factory() as session:
            for sym in symbols:
                snap = compute_ratios(session, sym, as_of)
                write_ratios_json(base_dir=processed_dir, snap=snap)
                total += 1
        return f"wrote {total} ratios json files for {as_of}"

    if job_type is JobType.DAILY_BRIEFING:
        trade_date_str = params.get("trade_date")
        td = (
            date.fromisoformat(str(trade_date_str))
            if trade_date_str
            else datetime.now(UTC).date()
        )
        from alpha_lab.briefing.daily import build_daily_briefing
        from alpha_lab.reports.service import create_daily_report

        body = build_daily_briefing(session_factory, td)
        summary = f"{td.isoformat()} 每日簡報"
        create_daily_report(
            trade_date=td,
            body_markdown=body,
            summary_line=summary,
        )
        return f"daily briefing for {td.isoformat()} written"

    raise ValueError(f"unknown job type: {job_type}")


def get_settings_for_processed() -> Any:
    """獨立取出供測試 monkeypatch（直接 patch get_settings 會影響其他模組）。"""
    return get_settings()


def _last_day_of_month(ym_date: date) -> date:
    """回傳該月最後一天。"""
    if ym_date.month == 12:
        return date(ym_date.year, 12, 31)
    next_month = date(ym_date.year, ym_date.month + 1, 1)
    return next_month - timedelta(days=1)
