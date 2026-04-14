"""TWSE collector 真實網路煙霧測試。

用法：
    python scripts/smoke_twse.py

會實際打 TWSE API 抓 2330 本月資料並印出前 3 筆。
若 TWSE 改 API 規格，此腳本可快速 reproduce。
"""

import asyncio
from datetime import date

from alpha_lab.collectors.twse import fetch_daily_prices


async def main() -> None:
    today = date.today()
    rows = await fetch_daily_prices(symbol="2330", year_month=today)
    print(f"Fetched {len(rows)} rows for 2330 in {today:%Y-%m}")
    for row in rows[:3]:
        print(
            f"  {row.trade_date} O={row.open} H={row.high} "
            f"L={row.low} C={row.close} V={row.volume}"
        )


if __name__ == "__main__":
    asyncio.run(main())
