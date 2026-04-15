"""MOPS 重大訊息 collector。

API：https://openapi.twse.com.tw/v1/opendata/t187ap04_L（上市即時重大訊息彙總）

若 TWSE OpenAPI 欄位有差異，此實作以 key 名稱逐個取值，缺欄位時以 empty string fallback。
"""

import ssl
from datetime import datetime

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.event import Event

OPENAPI_BASE = "https://openapi.twse.com.tw"
EVENTS_PATH = "/v1/opendata/t187ap04_L"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_event_date(raw: str) -> tuple[int, int, int]:
    """TWSE OpenAPI 日期欄位可能為 ROC 7 碼（1150410）或西元 8 碼（20260410）。

    以長度判斷：8 碼視為西元、7 碼視為 ROC。
    """
    s = raw.strip()
    if len(s) == 8 and s.isdigit():
        return int(s[:4]), int(s[4:6]), int(s[6:8])
    if len(s) >= 5:
        roc_year = int(s[:-4])
        month = int(s[-4:-2])
        day = int(s[-2:])
        return roc_year + 1911, month, day
    raise ValueError(f"bad event date: {raw!r}")


def _roc_date_to_iso(roc: str) -> tuple[int, int, int]:
    """'1150410' → (2026, 4, 10)。保留舊 API 以利相容。"""
    return _parse_event_date(roc)


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
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(EVENTS_PATH)
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, list):
        raise ValueError(f"unexpected events payload type: {type(payload)}")

    symbol_filter = set(symbols) if symbols else None
    results: list[Event] = []
    for item in payload:
        # TWSE OpenAPI 偶有 key 帶前後空白（如 "主旨 "），先做一次 key strip 正規化
        norm = {str(k).strip(): v for k, v in item.items()}

        symbol = str(norm.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue

        raw_date = str(
            norm.get("發言日期")
            or norm.get("發言日")
            or norm.get("資料日期")
            or ""
        )
        hms = str(
            norm.get("發言時間")
            or norm.get("時間")
            or "000000"
        )
        if not raw_date:
            continue
        year, month, day = _parse_event_date(raw_date)
        hh, mm, ss = _hhmmss_to_tuple(hms)

        title = str(norm.get("主旨", "")).strip()
        clause = str(norm.get("符合條款", "")).strip()
        results.append(
            Event(
                symbol=symbol,
                event_datetime=datetime(year, month, day, hh, mm, ss),
                event_type=clause or title or "其他",
                title=title or "(無主旨)",
                content=str(norm.get("說明", "")).strip(),
            )
        )
    return results
