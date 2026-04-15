"""TWSE collectors 共用錯誤與偵測工具。"""

from __future__ import annotations

import httpx


class TWSERateLimitError(RuntimeError):
    """TWSE 端以 307 + anti-bot body 回應時拋出。

    出現條件（實測 2026-04-15）：
    - status code = 307 Temporary Redirect
    - 沒有 `Location` header
    - body 含 `THE PAGE CANNOT BE ACCESSED` 或
      `基於安全考量` / `FOR SECURITY REASONS`

    成因：短時間內對 TWSE 發太多請求，IP 被 WAF 暫時封鎖。
    處理建議：等封鎖解除（數分鐘到數小時），下次抓取時減少頻率或明示 `--symbols`。
    """


_WAF_BODY_SIGNATURES = (
    "THE PAGE CANNOT BE ACCESSED",
    "FOR SECURITY REASONS",
    "基於安全考量",
)


def check_twse_waf(resp: httpx.Response) -> None:
    """若 response 看起來是 TWSE WAF 封鎖，拋 `TWSERateLimitError`；否則返回。

    呼叫位置：`client.get(...)` 之後、`resp.raise_for_status()` 之前。
    """
    if resp.status_code != 307:
        return
    if resp.headers.get("location"):
        return
    body = resp.text
    if any(sig in body for sig in _WAF_BODY_SIGNATURES):
        raise TWSERateLimitError(
            "TWSE WAF blocked the request (HTTP 307, no Location, anti-bot body). "
            "Likely IP rate-limited; retry later or reduce request frequency."
        )
