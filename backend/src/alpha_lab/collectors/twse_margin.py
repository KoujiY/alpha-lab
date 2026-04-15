"""TWSE 融資融券（MI_MARGN）collector。

API：https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=YYYYMMDD&selectType=ALL&response=json

真實 payload 結構（2025 年版）：
- `tables[]`：信用交易彙總表通常是 tables[1]（tables[0] 為總計摘要）
- 信用表有 `title`（含 "信用交易彙總"）、`groups`（欄位群組標題，如 融資/融券）、
  `fields`（欄位名稱，融資與融券子欄位名稱相同，只能靠 groups 區分）、`data`（逐列資料）
- `groups` 項目形如 `{"span": 6, "title": "融資"}`；`start` 不一定提供，需用 span
  累加推導。實務上 groups 會包含前置股票識別群組（如 `{"title":"股票","span":2}`）
  與尾端空 title 群組，融資/融券兩群組各佔 6 欄
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

CREDIT_TITLE_KEYWORD = "信用交易彙總"
MARGIN_GROUP = "融資"
SHORT_GROUP = "融券"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_int(s: str) -> int:
    if s in ("", "-", "N/A"):
        return 0
    return int(s.replace(",", "").replace("+", ""))


def _looks_like_credit_table(t: dict[str, Any]) -> bool:
    """判斷 table 是否為個股信用交易彙總表（具備 融資/融券 兩個 groups）。"""
    groups = t.get("groups") or []
    titles = {g.get("title") for g in groups if isinstance(g, dict)}
    return MARGIN_GROUP in titles and SHORT_GROUP in titles


def _find_credit_table(payload: dict[str, Any]) -> dict[str, Any]:
    """從 TWSE MI_MARGN payload 中抽出個股融資融券彙總表。

    優先順序：
    1. tables 中 title 含「信用交易彙總」者
    2. tables 中具備 融資/融券 groups 者
    3. 退回 tables[1]（summary 通常在 [0]）
    4. legacy `creditList` 欄位
    """
    if "tables" in payload and isinstance(payload["tables"], list):
        tables: list[dict[str, Any]] = payload["tables"]
        for t in tables:
            title = t.get("title") or ""
            if CREDIT_TITLE_KEYWORD in title and _looks_like_credit_table(t):
                return t
        for t in tables:
            if _looks_like_credit_table(t):
                return t
        if len(tables) >= 2 and isinstance(tables[1], dict):
            return tables[1]
    if "creditList" in payload:
        return payload["creditList"]  # type: ignore[no-any-return]
    raise ValueError("credit table not found in TWSE MI_MARGN payload")


def _resolve_group_indices(
    groups: list[dict[str, Any]], fields: list[str], group_title: str
) -> dict[str, int]:
    """在指定 group 的 column range 內，解析 買進/賣出/今日餘額 的欄位 index。

    TWSE 的 groups 不一定帶 `start`，需按 span 累加推導。若帶了 `start` 則以它為準。
    """
    cursor = 0
    start: int | None = None
    span = 0
    for g in groups:
        if not isinstance(g, dict):
            continue
        g_span = int(g.get("span", 0))
        g_start = int(g["start"]) if "start" in g else cursor
        if g.get("title") == group_title:
            start = g_start
            span = g_span
            break
        cursor = g_start + g_span
    if start is None:
        raise ValueError(f"group not found: {group_title}")

    end = start + span
    if end > len(fields) or span <= 0:
        raise ValueError(
            f"invalid group range for {group_title}: start={start}, span={span}, "
            f"fields_len={len(fields)}"
        )

    wanted = ("買進", "賣出", "今日餘額")
    resolved: dict[str, int] = {}
    for i in range(start, end):
        name = fields[i]
        if name in wanted and name not in resolved:
            resolved[name] = i

    missing = [w for w in wanted if w not in resolved]
    if missing:
        raise ValueError(
            f"missing sub-fields {missing} in group {group_title} "
            f"(range {start}:{end}, fields={fields[start:end]})"
        )
    return resolved


def _find_symbol_idx(fields: list[str]) -> int:
    # 真實 TWSE 常用 "代號"（name 為 "名稱"）；舊版或其他 endpoint 可能用 "股票代號"/"證券代號"。
    for c in ("股票代號", "證券代號", "代號"):
        if c in fields:
            return fields.index(c)
    raise ValueError(
        f"symbol field not found (tried 股票代號/證券代號/代號), fields={fields}"
    )


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
    groups: list[dict[str, Any]] = table.get("groups") or []

    idx_symbol = _find_symbol_idx(fields)
    margin_idx = _resolve_group_indices(groups, fields, MARGIN_GROUP)
    short_idx = _resolve_group_indices(groups, fields, SHORT_GROUP)

    symbol_filter = set(symbols) if symbols else None
    results: list[MarginTrade] = []
    for row in table.get("data", []):
        symbol = row[idx_symbol].strip()
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        # 融券 group 的「買進」= 現券回補（cover）
        results.append(
            MarginTrade(
                symbol=symbol,
                trade_date=trade_date,
                margin_buy=_parse_int(row[margin_idx["買進"]]),
                margin_sell=_parse_int(row[margin_idx["賣出"]]),
                margin_balance=_parse_int(row[margin_idx["今日餘額"]]),
                short_sell=_parse_int(row[short_idx["賣出"]]),
                short_cover=_parse_int(row[short_idx["買進"]]),
                short_balance=_parse_int(row[short_idx["今日餘額"]]),
            )
        )
    return results
