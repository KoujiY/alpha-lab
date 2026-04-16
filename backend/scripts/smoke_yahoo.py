"""真打一次 Yahoo Chart API，確認真實端點仍可用。"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from alpha_lab.collectors.yahoo import fetch_yahoo_daily_prices


async def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="2330")
    p.add_argument("--days", type=int, default=5)
    args = p.parse_args(argv)

    end = date.today()
    start = end - timedelta(days=args.days)
    rows = await fetch_yahoo_daily_prices(args.symbol, start=start, end=end)
    for r in rows:
        print(f"{r.trade_date} O={r.open} H={r.high} L={r.low} C={r.close} V={r.volume} src={r.source}")
    print(f"[total {len(rows)} rows]")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
