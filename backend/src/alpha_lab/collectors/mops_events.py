"""MOPS 重大訊息 collector。

API：https://openapi.twse.com.tw/v1/opendata/t187ap04_L（上市即時重大訊息彙總）

若 TWSE OpenAPI 欄位有差異，此實作以 key 名稱逐個取值，缺欄位時以 empty string fallback。
"""

from datetime import datetime

import httpx

from alpha_lab.config import get_settings
from alpha_lab.schemas.event import Event

OPENAPI_BASE = "https://openapi.twse.com.tw"
EVENTS_PATH = "/v1/opendata/t187ap04_L"


def _roc_date_to_iso(roc: str) -> tuple[int, int, int]:
    """'1150410' → (2026, 4, 10)。"""
    if len(roc) < 5:
        raise ValueError(f"bad ROC date: {roc}")
    roc_year = int(roc[:-4])
    month = int(roc[-4:-2])
    day = int(roc[-2:])
    return roc_year + 1911, month, day


def _hhmmss_to_tuple(s: str) -> tuple[int, int, int]:
    """'143020' → (14, 30, 20)；不足 6 碼左補 0。"""
    s = s.zfill(6)
    return int(s[:2]), int(s[2:4]), int(s[4:6])


async def fetch_latest_events(
    symbols: list[str] | None = None,
) -> list[Event]:
    """抓取最新一批上市重大訊息。

    Args:
        symbols: 若提供，僅回傳清單內代號。
    """
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=OPENAPI_BASE,
        timeout=settings.http_timeout_seconds,
        headers=headers,
    ) as client:
        resp = await client.get(EVENTS_PATH)
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, list):
        raise ValueError(f"unexpected events payload type: {type(payload)}")

    symbol_filter = set(symbols) if symbols else None
    results: list[Event] = []
    for item in payload:
        symbol = str(item.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue

        roc_d = str(item.get("發言日期", ""))
        hms = str(item.get("發言時間", "000000"))
        if not roc_d:
            continue
        year, month, day = _roc_date_to_iso(roc_d)
        hh, mm, ss = _hhmmss_to_tuple(hms)

        results.append(
            Event(
                symbol=symbol,
                event_datetime=datetime(year, month, day, hh, mm, ss),
                event_type=str(item.get("符合條款") or item.get("主旨") or "其他"),
                title=str(item.get("主旨", "")).strip() or "(無主旨)",
                content=str(item.get("說明", "")).strip(),
            )
        )
    return results
