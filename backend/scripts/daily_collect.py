"""每日例行抓取 CLI。

用法：
    python scripts/daily_collect.py                                   # 今天、全體上市（prices 會被跳過）
    python scripts/daily_collect.py --date 2026-04-11
    python scripts/daily_collect.py --symbols 2330,2317 --date 2026-04-11

會依序跑：TWSE 日成交（需 --symbols） → 三大法人 → 融資融券 → 重大訊息。
月營收、季報不列入 daily（發布頻率不同），請手動觸發對應 job。
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.engine import get_session_factory
from alpha_lab.storage.init_db import init_database
from alpha_lab.storage.models import Job


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="alpha-lab daily collect")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="trade date YYYY-MM-DD, default today",
    )
    p.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="comma-separated symbols, default ALL",
    )
    return p.parse_args(argv)


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    y, m, d = value.split("-")
    return date(int(y), int(m), int(d))


async def _run_one(
    label: str,
    job_type: JobType,
    params: dict[str, Any],
    session_factory: sessionmaker[Session],
) -> tuple[str, str]:
    """執行單個 job，回傳 (status, summary)。失敗不 re-raise（交由 run_job_sync 記錄）。"""
    with session_factory() as session:
        job = create_job(session, job_type=job_type, params=params)
        session.commit()
        job_id = job.id

    print(f"\n[{label}] job_id={job_id} params={params}")
    started = datetime.now()
    await run_job_sync(job_id=job_id, session_factory=session_factory)
    elapsed = (datetime.now() - started).total_seconds()

    with session_factory() as session:
        done = session.get(Job, job_id)
        assert done is not None
        status = done.status
        summary = done.result_summary or done.error_message or ""
    print(f"  -> {status} ({elapsed:.1f}s) {summary}")
    return status, summary


async def run_daily_collect(
    trade_date: date,
    symbols: list[str] | None,
    session_factory: sessionmaker[Session],
) -> list[tuple[str, str, str]]:
    """主流程。回傳 [(label, status, summary), ...]，供測試斷言。"""
    trade_date_str = trade_date.strftime("%Y-%m-%d")
    year_month_str = trade_date.strftime("%Y-%m")

    print(
        f"=== daily_collect trade_date={trade_date_str} "
        f"symbols={symbols or 'ALL'} ==="
    )

    results: list[tuple[str, str, str]] = []

    # TWSE_PRICES 每次抓一檔、一個月；無 --symbols 則跳過（collector 不支援 ALL）
    if symbols:
        for sym in symbols:
            label = f"TWSE prices {sym}"
            status, summary = await _run_one(
                label,
                JobType.TWSE_PRICES,
                {"symbol": sym, "year_month": year_month_str},
                session_factory,
            )
            results.append((label, status, summary))
    else:
        print("\n[TWSE prices] skipped (no --symbols given)")

    daily_jobs: list[tuple[str, JobType, dict[str, Any]]] = [
        (
            "TWSE institutional",
            JobType.TWSE_INSTITUTIONAL,
            {"trade_date": trade_date_str, "symbols": symbols},
        ),
        (
            "TWSE margin",
            JobType.TWSE_MARGIN,
            {"trade_date": trade_date_str, "symbols": symbols},
        ),
        (
            "MOPS events",
            JobType.MOPS_EVENTS,
            {"symbols": symbols},
        ),
    ]
    for label, job_type, params in daily_jobs:
        status, summary = await _run_one(label, job_type, params, session_factory)
        results.append((label, status, summary))

    print("\n=== summary ===")
    for label, status, summary in results:
        print(f"  [{label}] {status}: {summary}")

    return results


async def _async_main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    init_database()
    session_factory = get_session_factory()

    trade_date = _parse_date(args.date)
    symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else None
    )

    results = await run_daily_collect(trade_date, symbols, session_factory)
    any_failed = any(status != "completed" for _, status, _ in results)
    return 1 if any_failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
