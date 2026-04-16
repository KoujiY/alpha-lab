"""Yahoo Finance Chart API collector（台股備援）。

用途：TWSE 失敗或查無資料時退而求其次的價格來源。
端點：GET https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.TW
      ?period1={epoch}&period2={epoch}&interval=1d

注意：
- 台股 symbol 需附 `.TW` 後綴（上市）；上櫃 `.TWO`（Phase 8 再處理）
- 回傳 timestamps 為 UTC epoch；收盤日期取當地（台北 UTC+8）日期
- indicators.quote[0] 內任一欄位為 None 表示該日沒收盤（盤中/假日），整列捨棄
- 這是 **非官方 API**，隨時可能被拿掉；失敗時上拋 YahooFetchError
"""

from __future__ import annotations

import ssl
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.price import DailyPrice

YAHOO_BASE_URL = "https://query1.finance.yahoo.com"
CHART_PATH_TEMPLATE = "/v8/finance/chart/{symbol}.TW"

# Yahoo 回傳是 UTC；台北 = UTC+8
TAIPEI_TZ = timezone(timedelta(hours=8))


class YahooFetchError(RuntimeError):
    """Yahoo Chart API 明確失敗（error envelope 或 HTTP 非 2xx）。"""


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _epoch_from_taipei_date(d: date, end_of_day: bool = False) -> int:
    t = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    dt = datetime.combine(d, t, tzinfo=TAIPEI_TZ)
    return int(dt.timestamp())


async def fetch_yahoo_daily_prices(
    symbol: str, start: date, end: date
) -> list[DailyPrice]:
    """抓取 [start, end] 區間的每日 OHLCV。

    Raises:
        YahooFetchError: Yahoo 回錯誤 envelope 或 HTTP 5xx/4xx
    """
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}
    params: dict[str, str | int] = {
        "period1": _epoch_from_taipei_date(start),
        "period2": _epoch_from_taipei_date(end, end_of_day=True),
        "interval": "1d",
    }
    path = CHART_PATH_TEMPLATE.format(symbol=symbol)

    async with httpx.AsyncClient(
        base_url=YAHOO_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(path, params=params)
        if resp.status_code >= 400:
            raise YahooFetchError(
                f"Yahoo chart HTTP {resp.status_code} for {symbol}: {resp.text[:200]}"
            )
        payload = resp.json()

    chart = payload.get("chart") or {}
    err = chart.get("error")
    if err:
        code = err.get("code") or "Unknown"
        desc = err.get("description") or ""
        raise YahooFetchError(f"Yahoo chart error for {symbol}: {code} {desc}")

    result_list = chart.get("result") or []
    if not result_list:
        return []
    result = result_list[0]

    timestamps: list[int] = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    rows: list[DailyPrice] = []
    for i, ts in enumerate(timestamps):
        o = _get(opens, i)
        h = _get(highs, i)
        lo = _get(lows, i)
        c = _get(closes, i)
        v = _get(volumes, i)
        if any(x is None for x in (o, h, lo, c, v)):
            continue
        trade_date = datetime.fromtimestamp(ts, tz=TAIPEI_TZ).date()
        rows.append(
            DailyPrice(
                symbol=symbol,
                trade_date=trade_date,
                open=float(o),
                high=float(h),
                low=float(lo),
                close=float(c),
                volume=int(v),
                source="yahoo",
            )
        )
    return rows


def _get(arr: list[Any], i: int) -> Any:
    return arr[i] if i < len(arr) else None
