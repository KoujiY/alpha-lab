"""fallback 決策：什麼例外該 fallback 到 Yahoo。"""

from __future__ import annotations

import httpx

from alpha_lab.collectors._fallback import should_fallback_to_yahoo
from alpha_lab.collectors._twse_common import TWSERateLimitError


def test_waf_error_does_not_fallback():
    assert should_fallback_to_yahoo(TWSERateLimitError("waf")) is False


def test_no_data_holiday_does_not_fallback():
    assert should_fallback_to_yahoo(ValueError("TWSE returned non-OK stat: 很抱歉，沒有符合條件的資料")) is False


def test_other_value_error_falls_back():
    assert should_fallback_to_yahoo(ValueError("TWSE returned non-OK stat: 系統忙線中")) is True


def test_http_error_falls_back():
    resp = httpx.Response(503, request=httpx.Request("GET", "https://x"))
    assert should_fallback_to_yahoo(httpx.HTTPStatusError("5xx", request=resp.request, response=resp)) is True


def test_timeout_falls_back():
    assert should_fallback_to_yahoo(httpx.TimeoutException("timeout")) is True


def test_unknown_exception_does_not_fallback():
    """未知例外保守處理：不 fallback，直接上拋。"""
    assert should_fallback_to_yahoo(RuntimeError("something else")) is False
