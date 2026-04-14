"""TWSE 資料抓取。

Phase 1: 日股價（STOCK_DAY）
Phase 1.5 將新增：三大法人、融資融券
"""

import ssl
from datetime import date

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.price import DailyPrice

TWSE_BASE_URL = "https://www.twse.com.tw"
STOCK_DAY_PATH = "/rwd/zh/afterTrading/STOCK_DAY"


def _build_ssl_context() -> ssl.SSLContext:
    """改用系統 CA store（Windows/macOS），避免 Python 3.14 + OpenSSL 3
    對缺少 Subject Key Identifier 的憑證（例：TWSE）嚴格拒絕。
    """
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _roc_date_to_iso(roc: str) -> date:
    """民國日期字串（例：'115/04/01'）轉西元 date。"""
    parts = roc.split("/")
    if len(parts) != 3:
        raise ValueError(f"bad ROC date: {roc}")
    year = int(parts[0]) + 1911
    return date(year, int(parts[1]), int(parts[2]))


def _parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def _parse_float(s: str) -> float:
    return float(s.replace(",", ""))


async def fetch_daily_prices(symbol: str, year_month: date) -> list[DailyPrice]:
    """抓取單一股票、單一月份的每日 OHLCV。

    TWSE API 以月為單位回傳該月所有交易日。`year_month` 只會使用年月。
    """
    settings = get_settings()
    params = {
        "date": year_month.strftime("%Y%m01"),
        "stockNo": symbol,
        "response": "json",
    }
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=TWSE_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(STOCK_DAY_PATH, params=params)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("stat") != "OK":
        raise ValueError(f"TWSE returned non-OK stat: {payload.get('stat')}")

    results: list[DailyPrice] = []
    for row in payload.get("data", []):
        results.append(
            DailyPrice(
                symbol=symbol,
                trade_date=_roc_date_to_iso(row[0]),
                open=_parse_float(row[3]),
                high=_parse_float(row[4]),
                low=_parse_float(row[5]),
                close=_parse_float(row[6]),
                volume=_parse_int(row[1]),
            )
        )
    return results
