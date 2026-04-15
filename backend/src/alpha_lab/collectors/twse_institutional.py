"""TWSE 三大法人買賣超（T86）collector。

API：https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json
"""

import ssl
from datetime import date

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.institutional import InstitutionalTrade

TWSE_BASE_URL = "https://www.twse.com.tw"
T86_PATH = "/rwd/zh/fund/T86"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_int(s: object) -> int:
    """去千分位後轉 int；空字串或 '-' 視為 0。

    TWSE 有時會直接以 int/float 回傳數字欄位，需一併處理。
    """
    if isinstance(s, (int, float)):
        return int(s)
    if s in ("", "-", "N/A", None):
        return 0
    return int(str(s).replace(",", "").replace("+", ""))


def _find_field_index(fields: list[str], *candidates: str) -> int:
    """回傳第一個完全相符的欄位 index；找不到則拋例外。"""
    for c in candidates:
        if c in fields:
            return fields.index(c)
    raise ValueError(f"required field not found in {fields}: tried {candidates}")


async def fetch_institutional_trades(
    trade_date: date, symbols: list[str] | None = None
) -> list[InstitutionalTrade]:
    """抓取某交易日所有標的的三大法人買賣超。

    Args:
        trade_date: 交易日
        symbols: 若提供，僅回傳清單內代號；None 代表全部。
    """
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
        resp = await client.get(T86_PATH, params=params)
        resp.raise_for_status()
        payload = resp.json()

    stat = payload.get("stat", "")
    if stat != "OK":
        if "沒有符合條件" in stat:
            print(f"[twse_institutional] no data for {trade_date} (stat={stat})")
            return []
        raise ValueError(f"TWSE T86 returned non-OK stat: {stat}")

    fields: list[str] = payload["fields"]
    idx_symbol = _find_field_index(fields, "證券代號")
    idx_foreign_main = _find_field_index(
        fields, "外陸資買賣超股數(不含外資自營商)", "外資買賣超股數"
    )
    # 「外資自營商買賣超股數」於 2018 年後獨立欄位；舊報表可能無
    idx_foreign_dealer: int | None
    try:
        idx_foreign_dealer = _find_field_index(fields, "外資自營商買賣超股數")
    except ValueError:
        idx_foreign_dealer = None
    idx_trust = _find_field_index(fields, "投信買賣超股數")
    idx_dealer_total = _find_field_index(fields, "自營商買賣超股數")
    idx_total = _find_field_index(fields, "三大法人買賣超股數")

    symbol_filter = set(symbols) if symbols else None
    required_indices = [
        idx_symbol,
        idx_foreign_main,
        idx_foreign_dealer,
        idx_trust,
        idx_dealer_total,
        idx_total,
    ]
    max_idx = max(i for i in required_indices if i is not None)
    results: list[InstitutionalTrade] = []
    for row in payload.get("data", []):
        if len(row) <= max_idx:
            print(
                f"[twse_institutional] skip malformed row "
                f"(len={len(row)}, need>{max_idx}): {row[:4]}..."
            )
            continue
        symbol = row[idx_symbol].strip()
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        foreign_main = _parse_int(row[idx_foreign_main])
        foreign_dealer = (
            _parse_int(row[idx_foreign_dealer]) if idx_foreign_dealer is not None else 0
        )
        results.append(
            InstitutionalTrade(
                symbol=symbol,
                trade_date=trade_date,
                foreign_net=foreign_main + foreign_dealer,
                trust_net=_parse_int(row[idx_trust]),
                dealer_net=_parse_int(row[idx_dealer_total]),
                total_net=_parse_int(row[idx_total]),
            )
        )
    return results
