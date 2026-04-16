"""TWSE → Yahoo fallback 決策。

設計原則：
- **WAF 錯誤不 fallback**：IP 被封，Yahoo 也治標不治本，該讓使用者等封鎖解除
- **「沒有符合條件」不 fallback**：那是假日/盤中，Yahoo 查也是空
- 其他 ValueError（TWSE 明確回錯誤 stat）、HTTP 4xx/5xx、timeout → fallback
- 未知例外 → 保守不 fallback，讓 caller decide
"""

from __future__ import annotations

import httpx

from alpha_lab.collectors._twse_common import TWSERateLimitError

_NO_DATA_MARKERS = ("沒有符合條件",)


def should_fallback_to_yahoo(exc: BaseException) -> bool:
    """判斷該例外類型是否該觸發 Yahoo fallback。"""
    if isinstance(exc, TWSERateLimitError):
        return False
    if isinstance(exc, ValueError):
        msg = str(exc)
        if any(m in msg for m in _NO_DATA_MARKERS):
            return False
        return True
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError)):
        return True
    return False
