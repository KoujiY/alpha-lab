"""TWSE 三大法人 collector 真實網路煙霧測試。

用法：python scripts/smoke_twse_institutional.py [YYYY-MM-DD]
若省略日期則用今天（可能尚未收盤，會無資料）。
"""

import asyncio
import sys
from datetime import date

from alpha_lab.collectors.twse_institutional import fetch_institutional_trades


async def main() -> None:
    if len(sys.argv) >= 2:
        y, m, d = sys.argv[1].split("-")
        trade_date = date(int(y), int(m), int(d))
    else:
        trade_date = date.today()

    rows = await fetch_institutional_trades(
        trade_date=trade_date, symbols=["2330", "2317", "0050"]
    )
    print(f"Fetched {len(rows)} rows for {trade_date}")
    for r in rows:
        print(
            f"  {r.symbol} foreign={r.foreign_net:>12,} "
            f"trust={r.trust_net:>10,} dealer={r.dealer_net:>10,} "
            f"total={r.total_net:>12,}"
        )


if __name__ == "__main__":
    asyncio.run(main())
