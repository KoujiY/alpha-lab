"""MOPS 資料抓取。

Phase 1: 月營收（openapi.twse.com.tw 的 t187ap05_L，最新一期全上市公司）
Phase 1.5 將新增：季報、重大訊息
"""

import ssl

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.revenue import MonthlyRevenue

MOPS_OPENAPI_BASE = "https://openapi.twse.com.tw"
MONTHLY_REVENUE_PATH = "/v1/opendata/t187ap05_L"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_year_month(roc_ym: str) -> tuple[int, int]:
    """'11503' → (2026, 3)。"""
    if len(roc_ym) < 4:
        raise ValueError(f"bad ROC year-month: {roc_ym}")
    roc_year = int(roc_ym[:-2])
    month = int(roc_ym[-2:])
    return roc_year + 1911, month


def _parse_optional_float(s: str) -> float | None:
    if s in ("", "-", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


async def fetch_latest_monthly_revenues(
    symbols: list[str] | None = None,
) -> list[MonthlyRevenue]:
    """抓取最新一期全上市公司月營收。

    Args:
        symbols: 若提供，僅回傳清單內代號；None 代表全部。
    """
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=MOPS_OPENAPI_BASE,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(MONTHLY_REVENUE_PATH)
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, list):
        raise ValueError(f"unexpected MOPS payload type: {type(payload)}")

    symbol_filter = set(symbols) if symbols else None
    results: list[MonthlyRevenue] = []
    for item in payload:
        symbol = item.get("公司代號", "")
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        year, month = _parse_year_month(item["資料年月"])
        results.append(
            MonthlyRevenue(
                symbol=symbol,
                year=year,
                month=month,
                revenue=int(item["營業收入-當月營收"]),
                yoy_growth=_parse_optional_float(
                    item.get("營業收入-去年同月增減(%)", "")
                ),
                mom_growth=_parse_optional_float(
                    item.get("營業收入-上月比較增減(%)", "")
                ),
            )
        )
    return results
