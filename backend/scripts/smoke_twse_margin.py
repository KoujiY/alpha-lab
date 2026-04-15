"""TWSE 融資融券 collector 煙霧測試。

用法：python scripts/smoke_twse_margin.py [YYYY-MM-DD]
"""

import asyncio
import sys
from datetime import date

from alpha_lab.collectors.twse_margin import fetch_margin_trades


async def main() -> None:
    if len(sys.argv) >= 2:
        y, m, d = sys.argv[1].split("-")
        trade_date = date(int(y), int(m), int(d))
    else:
        trade_date = date.today()

    rows = await fetch_margin_trades(
        trade_date=trade_date, symbols=["2330", "2317", "2454"]
    )
    print(f"Fetched {len(rows)} rows for {trade_date}")
    for r in rows:
        print(
            f"  {r.symbol} 融資餘={r.margin_balance:>8,} "
            f"(買{r.margin_buy:>6,}/賣{r.margin_sell:>6,}) "
            f"融券餘={r.short_balance:>6,} "
            f"(賣{r.short_sell:>5,}/回{r.short_cover:>5,})"
        )


if __name__ == "__main__":
    asyncio.run(main())
