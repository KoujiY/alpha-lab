"""TWSE 融資融券（MI_MARGN）collector。

API：https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=YYYYMMDD&selectType=ALL&response=json
"""

import ssl
from datetime import date
from typing import Any

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.margin import MarginTrade

TWSE_BASE_URL = "https://www.twse.com.tw"
MI_MARGN_PATH = "/rwd/zh/marginTrading/MI_MARGN"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_int(s: str) -> int:
    if s in ("", "-", "N/A"):
        return 0
    return int(s.replace(",", "").replace("+", ""))


def _find_credit_table(payload: dict[str, Any]) -> dict[str, Any]:
    """從不同 TWSE 版本的 payload 中抽出個股融資融券表。"""
    if "tables" in payload and isinstance(payload["tables"], list):
        for t in payload["tables"]:
            fields = t.get("fields") or []
            if any("融資" in f for f in fields) and any("融券" in f for f in fields):
                return t  # type: ignore[no-any-return]
    if "creditList" in payload:
        return payload["creditList"]  # type: ignore[no-any-return]
    raise ValueError("credit table not found in TWSE MI_MARGN payload")


def _find_idx(fields: list[str], *candidates: str) -> int:
    for c in candidates:
        if c in fields:
            return fields.index(c)
    raise ValueError(f"field not found: tried {candidates}")


async def fetch_margin_trades(
    trade_date: date, symbols: list[str] | None = None
) -> list[MarginTrade]:
    """抓取某交易日所有標的的融資融券餘額。"""
    settings = get_settings()
    params = {
        "date": trade_date.strftime("%Y%m%d"),
        "selectType": "ALL",
        "response": "json",
    }
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=TWSE_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(MI_MARGN_PATH, params=params)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("stat") != "OK":
        raise ValueError(f"TWSE MI_MARGN returned non-OK stat: {payload.get('stat')}")

    table = _find_credit_table(payload)
    fields: list[str] = table["fields"]

    idx_symbol = _find_idx(fields, "股票代號", "證券代號")
    idx_margin_buy = _find_idx(fields, "融資買進")
    idx_margin_sell = _find_idx(fields, "融資賣出")
    idx_margin_balance = _find_idx(fields, "融資今日餘額", "今日餘額")
    idx_short_buy = _find_idx(fields, "融券買進")
    idx_short_sell = _find_idx(fields, "融券賣出")
    idx_short_balance = _find_idx(fields, "融券今日餘額")

    # 融券買進 = 現券回補 / 融券買回 — 本專案視為 cover
    symbol_filter = set(symbols) if symbols else None
    results: list[MarginTrade] = []
    for row in table.get("data", []):
        symbol = row[idx_symbol].strip()
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        results.append(
            MarginTrade(
                symbol=symbol,
                trade_date=trade_date,
                margin_buy=_parse_int(row[idx_margin_buy]),
                margin_sell=_parse_int(row[idx_margin_sell]),
                margin_balance=_parse_int(row[idx_margin_balance]),
                short_sell=_parse_int(row[idx_short_sell]),
                short_cover=_parse_int(row[idx_short_buy]),
                short_balance=_parse_int(row[idx_short_balance]),
            )
        )
    return results
