"""MOPS collector 真實網路煙霧測試。

抓取最新一期全上市公司月營收，印出前幾筆確認連線與解析正常。
"""

import asyncio

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues


async def main() -> None:
    rows = await fetch_latest_monthly_revenues(symbols=["2330", "2317", "2454"])
    print(f"Fetched {len(rows)} rows")
    for row in rows:
        print(
            f"  {row.symbol} {row.year}-{row.month:02d} "
            f"revenue={row.revenue} yoy={row.yoy_growth} mom={row.mom_growth}"
        )


if __name__ == "__main__":
    asyncio.run(main())
