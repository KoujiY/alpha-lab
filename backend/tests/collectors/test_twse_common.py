"""_twse_common.check_twse_waf 單元測試。"""

from __future__ import annotations

import httpx
import pytest

from alpha_lab.collectors._twse_common import TWSERateLimitError, check_twse_waf


def _make_response(status_code: int, body: bytes, headers: dict[str, str]) -> httpx.Response:
    return httpx.Response(status_code=status_code, content=body, headers=headers)


def test_check_twse_waf_noop_on_200() -> None:
    resp = _make_response(200, b"ok", {})
    check_twse_waf(resp)  # 不拋


def test_check_twse_waf_noop_on_real_redirect_with_location() -> None:
    resp = _make_response(307, b"", {"location": "https://elsewhere/"})
    check_twse_waf(resp)  # 有 Location 視為正常 redirect，不拋


def test_check_twse_waf_raises_on_anti_bot_body() -> None:
    body = (
        b"<html>THE PAGE CANNOT BE ACCESSED!<br>"
        b"FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED!</html>"
    )
    resp = _make_response(307, body, {"content-type": "text/html"})
    with pytest.raises(TWSERateLimitError, match="WAF"):
        check_twse_waf(resp)


def test_check_twse_waf_raises_on_chinese_sentinel() -> None:
    body = "基於安全考量，您所執行的查詢無法呈現".encode()
    resp = _make_response(307, body, {"content-type": "text/html; charset=UTF-8"})
    with pytest.raises(TWSERateLimitError):
        check_twse_waf(resp)


def test_check_twse_waf_noop_on_307_without_signatures() -> None:
    """307 但 body 不是 anti-bot 訊號 → 不誤判（交給 raise_for_status）。"""
    resp = _make_response(307, b"<html>normal body</html>", {})
    check_twse_waf(resp)
