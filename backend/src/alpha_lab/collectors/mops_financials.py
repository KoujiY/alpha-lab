"""MOPS 季報三表 collector。

資料源：TWSE OpenAPI 彙總端點（v1/opendata/t187ap06/07/10_L_ci）
回傳：list[FinancialStatement]（以 statement_type 區分三表）

Phase 1.5 Task E1：僅實作 income（合併綜合損益表）。
balance / cashflow 留待 E2、E3。

注意：TWSE OpenAPI 端點名稱與欄位名偶有調整。本模組在欄位名查找上採「多候選」容忍策略，
若 smoke 測試仍對不上實際 payload，請用 curl 確認後更新欄位候選清單與 sample，
並同步更新知識庫 `docs/knowledge/collectors/mops.md`。
"""

import json
import ssl
from typing import Any

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType

OPENAPI_BASE = "https://openapi.twse.com.tw"
INCOME_PATH = "/v1/opendata/t187ap06_L_ci"
BALANCE_PATH = "/v1/opendata/t187ap07_L_ci"
CASHFLOW_PATH = "/v1/opendata/t187ap10_L_ci"

# 欄位名候選：對不同版本的 OpenAPI 命名容忍
_INCOME_FIELDS: dict[str, tuple[str, ...]] = {
    "revenue": ("營業收入", "營業收入合計"),
    "gross_profit": ("營業毛利(毛損)", "營業毛利（毛損）", "營業毛利"),
    "operating_income": ("營業利益(損失)", "營業利益（損失）", "營業利益"),
    "net_income": (
        "本期淨利(淨損)",
        "本期淨利（淨損）",
        "本期綜合損益總額",
        "本期淨利",
    ),
    "eps": ("基本每股盈餘(元)", "基本每股盈餘（元）", "基本每股盈餘"),
}


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _lookup(item: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for key in candidates:
        if key in item:
            return item[key]
    return None


def _parse_int_or_none(s: Any) -> int | None:
    if s is None or s == "" or s == "-":
        return None
    try:
        return int(float(str(s).replace(",", "")))
    except ValueError:
        return None


def _parse_float_or_none(s: Any) -> float | None:
    if s is None or s == "" or s == "-":
        return None
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def _build_period(roc_year: str, quarter: str) -> str:
    """'115', '1' → '2026Q1'。"""
    return f"{int(roc_year) + 1911}Q{int(quarter)}"


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
        resp.raise_for_status()
        payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError(f"unexpected financial payload: {type(payload)}")
    return payload


def _filter(symbols: list[str] | None) -> set[str] | None:
    return set(symbols) if symbols else None


async def fetch_income_statement(
    symbols: list[str] | None = None,
) -> list[FinancialStatement]:
    """抓取最新一期全上市公司合併綜合損益表。

    Args:
        symbols: 若提供，僅回傳清單內代號；None 代表全部。
    """
    payload = await _fetch_payload(INCOME_PATH)
    symbol_filter = _filter(symbols)

    results: list[FinancialStatement] = []
    for item in payload:
        symbol = str(item.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        roc_year = str(item.get("年度", "")).strip()
        quarter = str(item.get("季別", "")).strip()
        if not roc_year or not quarter:
            continue
        period = _build_period(roc_year, quarter)
        results.append(
            FinancialStatement(
                symbol=symbol,
                period=period,
                statement_type=StatementType.INCOME,
                revenue=_parse_int_or_none(
                    _lookup(item, _INCOME_FIELDS["revenue"])
                ),
                gross_profit=_parse_int_or_none(
                    _lookup(item, _INCOME_FIELDS["gross_profit"])
                ),
                operating_income=_parse_int_or_none(
                    _lookup(item, _INCOME_FIELDS["operating_income"])
                ),
                net_income=_parse_int_or_none(
                    _lookup(item, _INCOME_FIELDS["net_income"])
                ),
                eps=_parse_float_or_none(_lookup(item, _INCOME_FIELDS["eps"])),
                total_assets=None,
                total_liabilities=None,
                total_equity=None,
                operating_cf=None,
                investing_cf=None,
                financing_cf=None,
                raw_json=item,
            )
        )
    return results


def serialize_raw(fs: FinancialStatement) -> str:
    """把 raw_json（dict）序列化，供 runner 寫入 DB。"""
    return json.dumps(fs.raw_json, ensure_ascii=False)
