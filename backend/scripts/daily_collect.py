"""每日例行抓取 CLI。

用法：
    python scripts/daily_collect.py                                   # 今天、三大法人/融資融券/重大訊息；prices 會被 skip
    python scripts/daily_collect.py --symbols 2330,2317 --date 2026-04-11
    python scripts/daily_collect.py --all --date 2026-04-11            # 明示意圖：對 DB watchlist 全體逐檔抓 prices

會依序跑：TWSE 上市公司基本資料 → TWSE 日成交（需 --symbols 或 --all） → 三大法人
→ 融資融券 → 重大訊息。公司基本資料擺最前面，讓後續 collector 的 `_ensure_stock`
看到 DB 時有正確的 name / industry / listed_date。

月營收、季報不列入 daily（發布頻率不同），請手動觸發對應 job。

全市場保險：`--symbols` 與 `--all` 互斥；未傳兩者之一時 prices 會被 skip，避免誤觸
TWSE 對短時間多次請求的 IP 限流（逐檔抓全 watchlist 約耗時 20-40 分鐘）。
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.engine import get_session_factory
from alpha_lab.storage.init_db import init_database
from alpha_lab.storage.models import Job, Stock


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="alpha-lab daily collect")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="trade date YYYY-MM-DD, default today",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="comma-separated symbols for TWSE prices",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="run TWSE prices against entire DB watchlist (may take 20-40 min, risk of TWSE rate limit)",
    )
    return p.parse_args(argv)


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    y, m, d = value.split("-")
    return date(int(y), int(m), int(d))


def _load_watchlist_symbols(session_factory: sessionmaker[Session]) -> list[str]:
    """讀取 stocks 表中所有 symbol，依 symbol 升冪排序回傳。"""
    with session_factory() as session:
        rows = session.execute(select(Stock.symbol).order_by(Stock.symbol)).scalars().all()
    return list(rows)


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
    all_market: bool,
    session_factory: sessionmaker[Session],
) -> list[tuple[str, str, str]]:
    """主流程。回傳 [(label, status, summary), ...]，供測試斷言。

    prices 執行條件：
    - symbols 非空 → 用傳入 symbols
    - symbols 為 None 且 all_market=True → 用 DB watchlist
    - 其餘（含未傳任何 flag、空 --symbols）→ skip prices
    """
    trade_date_str = trade_date.strftime("%Y-%m-%d")
    year_month_str = trade_date.strftime("%Y-%m")

    print(
        f"=== daily_collect trade_date={trade_date_str} "
        f"symbols={symbols or ('ALL' if all_market else 'NONE')} ==="
    )

    results: list[tuple[str, str, str]] = []

    # 公司基本資料放最前面：後續 collector 若遇到新 symbol，placeholder 會被填充
    # 為正式 name / industry / listed_date；若失敗（例如 TWSE WAF 擋）不影響其他 job。
    stock_info_status, stock_info_summary = await _run_one(
        "TWSE stock info",
        JobType.TWSE_STOCK_INFO,
        {"symbols": symbols},
        session_factory,
    )
    results.append(("TWSE stock info", stock_info_status, stock_info_summary))

    price_symbols: list[str] = []
    if symbols:
        price_symbols = symbols
    elif all_market:
        price_symbols = _load_watchlist_symbols(session_factory)

    if not price_symbols:
        if symbols is not None:
            print("\n[TWSE prices] skipped (empty --symbols)")
        elif all_market:
            print("\n[TWSE prices] skipped (stocks table is empty)")
        else:
            print(
                "\n[TWSE prices] skipped (pass --symbols a,b,c or --all to enable; "
                "--all iterates full DB watchlist which may trigger TWSE rate limit)"
            )
    else:
        if not symbols:
            print(f"\n[TWSE prices] using DB watchlist ({len(price_symbols)} symbols)")
        for sym in price_symbols:
            label = f"TWSE prices {sym}"
            status, summary = await _run_one(
                label,
                JobType.TWSE_PRICES,
                {"symbol": sym, "year_month": year_month_str},
                session_factory,
            )
            results.append((label, status, summary))

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

    # Phase 7B.1：若有明確 symbols，跑一次 processed 指標落檔（--all 不自動跑，避免 60 分鐘）
    if price_symbols:
        _label = "processed indicators"
        status, summary = await _run_one(
            _label,
            JobType.PROCESSED_INDICATORS,
            {"symbols": price_symbols},
            session_factory,
        )
        results.append((_label, status, summary))

        _label = "processed ratios"
        status, summary = await _run_one(
            _label,
            JobType.PROCESSED_RATIOS,
            {"symbols": price_symbols, "as_of": trade_date_str},
            session_factory,
        )
        results.append((_label, status, summary))

    # Phase 7B.2：每日簡報
    briefing_label = "daily briefing"
    status, summary = await _run_one(
        briefing_label,
        JobType.DAILY_BRIEFING,
        {"trade_date": trade_date_str},
        session_factory,
    )
    results.append((briefing_label, status, summary))

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

    results = await run_daily_collect(trade_date, symbols, args.all, session_factory)
    any_failed = any(status != "completed" for _, status, _ in results)
    return 1 if any_failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
