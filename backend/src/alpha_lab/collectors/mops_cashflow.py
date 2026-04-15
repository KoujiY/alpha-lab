"""MOPS 現金流量表 collector（公開資訊觀測站 t164sb05）。

來源：`https://mops.twse.com.tw/mops/web/ajax_t164sb05`（POST、form-urlencoded）。
回應為 HTML，表格列以「營業活動之淨現金流入（流出）」等會計項目字串為鍵。

本 collector 只回傳 Phase 3 Quality 因子需要的三項（OCF / ICF / FCF_proxy）。
完整項目保留原始 HTML 供呼叫端決定是否另存。

金額處理：
- 千元為 TWSE 慣例，parser 不做單位換算（呼叫端自行處理）
- 負數支援括號與負號兩種表達：`(1,234)` 與 `-1,234` 皆視為 -1234
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup, Tag

from alpha_lab.collectors._twse_common import TWSERateLimitError

logger = logging.getLogger(__name__)

MOPS_URL = "https://mops.twse.com.tw/mops/web/ajax_t164sb05"

_LABELS: dict[str, str] = {
    "operating_cf": "營業活動之淨現金流入",
    "investing_cf": "投資活動之淨現金流入",
    "financing_cf": "籌資活動之淨現金流入",
}

# MOPS WAF 阻擋頁面訊號
_WAF_SIGNATURES = (
    "THE PAGE CANNOT BE ACCESSED",
    "FOR SECURITY REASONS",
    "頁面無法執行",
    "基於安全考量",
    "因為安全性考量",
)


class Cashflow(TypedDict):
    operating_cf: int | None
    investing_cf: int | None
    financing_cf: int | None


def _empty() -> Cashflow:
    return {"operating_cf": None, "investing_cf": None, "financing_cf": None}


def _parse_amount(cell_text: str) -> int | None:
    """解析 `1,234`、`(1,234)`、`-1,234` 形式的金額，失敗回 None。"""
    s = cell_text.replace(",", "").strip()
    if not s or s == "-":
        return None
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return None


def _find_row(soup: BeautifulSoup, label_prefix: str) -> Tag | None:
    """找第一個 text 以 label 起始的 <tr>。"""
    for tr in soup.find_all("tr"):
        if not isinstance(tr, Tag):
            continue
        first_cell = tr.find(["td", "th"])
        if not isinstance(first_cell, Tag):
            continue
        text = first_cell.get_text(strip=True)
        if text.startswith(label_prefix):
            return tr
    return None


def _first_number_from_cells(row: Tag) -> int | None:
    """抓 row 內第一個成功 parse 的數字 cell（跳過 header）。"""
    cells = row.find_all("td")
    for c in cells:
        if not isinstance(c, Tag):
            continue
        val = _parse_amount(c.get_text(strip=True))
        if val is not None:
            return val
    return None


def parse_cashflow_html(html: str) -> Cashflow:
    """從 MOPS t164sb05 HTML 抽出三大現金流科目（本期金額）。

    若 HTML 為 WAF 擋頁或結構不符，對應鍵回 None。
    """
    if any(sig in html for sig in _WAF_SIGNATURES):
        logger.warning("MOPS t164sb05 response looks like WAF block; returning empty")
        return _empty()

    soup = BeautifulSoup(html, "html.parser")
    result = _empty()
    for key, label in _LABELS.items():
        row = _find_row(soup, label)
        if row is None:
            continue
        result[key] = _first_number_from_cells(row)  # type: ignore[literal-required]
    return result


def _browser_headers() -> dict[str, str]:
    """MOPS WAF 對 UA 敏感；使用瀏覽器級 headers 提高成功率。"""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://mops.twse.com.tw/mops/web/t164sb05",
        "Origin": "https://mops.twse.com.tw",
        "Accept": "*/*",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }


async def fetch_cashflow(
    symbol: str,
    roc_year: int,
    season: int,
    client: httpx.AsyncClient | None = None,
) -> Cashflow:
    """抓取單檔單季現金流。`roc_year` 是民國年（2026 → 115）。

    Raises:
        TWSERateLimitError: MOPS WAF 擋下請求時。
    """
    owns_client = client is None
    c = client or httpx.AsyncClient(timeout=30.0)
    try:
        resp = await c.post(
            MOPS_URL,
            data={
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "1",
                "TYPEK": "sii",
                "co_id": symbol,
                "year": str(roc_year),
                "season": str(season),
            },
            headers=_browser_headers(),
        )
        resp.raise_for_status()
        html = resp.text
    finally:
        if owns_client:
            await c.aclose()

    if any(sig in html for sig in _WAF_SIGNATURES):
        raise TWSERateLimitError(
            f"MOPS WAF blocked t164sb05 for {symbol} {roc_year}Q{season}"
        )
    return parse_cashflow_html(html)


def fetch_cashflow_sync(symbol: str, roc_year: int, season: int) -> Cashflow:
    return asyncio.run(fetch_cashflow(symbol, roc_year, season))
