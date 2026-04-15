"""TWSE 上市公司基本資料 collector。

資料源：TWSE OpenAPI `v1/opendata/t187ap03_L`（上市公司基本資料彙總）。
用途：補 `stocks` 表的 `name` / `industry` / `listed_date`（Phase 1 collector 只建
placeholder，name 與 symbol 同值、industry/listed_date 皆 None）。

欄位名查找採「多候選」策略，與 `mops_financials` 一致：TWSE OpenAPI 欄位命名偶有
微調（全形括號、簡稱/名稱擇一、產業別命名差異），容忍多個別名。
"""

import logging
import ssl
from datetime import date
from typing import Any

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.stock_info import StockInfo

logger = logging.getLogger(__name__)

OPENAPI_BASE = "https://openapi.twse.com.tw"
STOCK_INFO_PATH = "/v1/opendata/t187ap03_L"

# 欄位名候選：對不同版本 / 端點變體的 OpenAPI 命名容忍
_SYMBOL_KEYS: tuple[str, ...] = ("公司代號", "證券代號")
_NAME_KEYS: tuple[str, ...] = ("公司簡稱", "公司名稱", "證券名稱")
_INDUSTRY_KEYS: tuple[str, ...] = ("產業別", "產業類別", "產業")
_LISTED_DATE_KEYS: tuple[str, ...] = ("上市日期", "上市日", "公司上市日期")


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _lookup(item: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for key in candidates:
        if key in item:
            return item[key]
    return None


def _parse_roc_date(s: Any) -> date | None:
    """解析 TWSE 民國日期。支援 7 碼（YYYMMDD，前導 0）、6 碼（YYMMDD，< 民國 100）
    以及 `YYY/MM/DD` 格式。無法解析回 None。
    """
    if s is None:
        return None
    raw = str(s).strip()
    if not raw or raw == "-":
        return None
    # 分隔符變體：YYY/MM/DD or YYY-MM-DD
    if "/" in raw or "-" in raw:
        parts = raw.replace("-", "/").split("/")
        if len(parts) != 3:
            return None
        try:
            roc_year, month, day = (int(p) for p in parts)
        except ValueError:
            return None
    else:
        digits = raw
        if not digits.isdigit():
            return None
        if len(digits) == 7:
            roc_year = int(digits[:3])
            month = int(digits[3:5])
            day = int(digits[5:7])
        elif len(digits) == 6:
            roc_year = int(digits[:2])
            month = int(digits[2:4])
            day = int(digits[4:6])
        else:
            return None
    if roc_year <= 0:
        return None
    try:
        return date(roc_year + 1911, month, day)
    except ValueError:
        return None


def _clean_str(s: Any) -> str | None:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


async def _fetch_payload(path: str) -> list[dict[str, Any]]:
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}
    async with httpx.AsyncClient(
        base_url=OPENAPI_BASE,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(path)
        if resp.status_code in (301, 302, 307, 308):
            logger.warning(
                "TWSE OpenAPI path %s redirected (%s) -> likely unavailable, "
                "returning empty payload",
                path,
                resp.status_code,
            )
            return []
        if resp.status_code == 404:
            logger.warning(
                "TWSE OpenAPI path %s returned 404, returning empty payload", path
            )
            return []
        resp.raise_for_status()
        payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError(f"unexpected stock_info payload: {type(payload)}")
    return payload


async def fetch_stock_info(
    symbols: list[str] | None = None,
) -> list[StockInfo]:
    """抓取上市公司基本資料。

    Args:
        symbols: 若提供，僅回傳清單內代號；None 代表全部上市公司。

    欄位缺失（symbol 或 name 任一）的 row 會被略過並記 debug log，不拋例外。
    """
    payload = await _fetch_payload(STOCK_INFO_PATH)
    symbol_filter = set(symbols) if symbols else None

    results: list[StockInfo] = []
    for item in payload:
        symbol = _clean_str(_lookup(item, _SYMBOL_KEYS))
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        name = _clean_str(_lookup(item, _NAME_KEYS))
        if not name:
            logger.debug("stock_info row skipped: missing name for %s", symbol)
            continue
        industry = _clean_str(_lookup(item, _INDUSTRY_KEYS))
        listed_date = _parse_roc_date(_lookup(item, _LISTED_DATE_KEYS))
        results.append(
            StockInfo(
                symbol=symbol,
                name=name,
                industry=industry,
                listed_date=listed_date,
            )
        )
    return results
