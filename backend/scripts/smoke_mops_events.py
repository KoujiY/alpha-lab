"""MOPS 重大訊息 collector 煙霧測試。

預設過濾 2330/2317/2454；若當期無資料則額外列印前 10 筆（不過濾）
以確認 API 串接真的有資料。
"""

import asyncio

from alpha_lab.collectors.mops_events import fetch_latest_events


async def main() -> None:
    targets = ["2330", "2317", "2454"]
    events = await fetch_latest_events(symbols=targets)
    print(f"Fetched {len(events)} events for {targets}")
    for e in events[:10]:
        print(
            f"  {e.event_datetime:%Y-%m-%d %H:%M} [{e.symbol}] "
            f"{e.event_type}: {e.title[:40]}"
        )

    if not events:
        print("\n(目標代號當期無重訊，改抓全市場前 10 筆以確認 API 串接成功)")
        all_events = await fetch_latest_events()
        print(f"All-market events: {len(all_events)}")
        for e in all_events[:10]:
            print(
                f"  {e.event_datetime:%Y-%m-%d %H:%M} [{e.symbol}] "
                f"{e.event_type}: {e.title[:40]}"
            )


if __name__ == "__main__":
    asyncio.run(main())
