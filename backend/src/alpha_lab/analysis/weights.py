"""四因子風格權重。總和為 1。

權重設計（初版）：
- conservative：Dividend + Quality 重
- balanced：四因子均衡
- aggressive：Growth 重
"""

from __future__ import annotations

from typing import Literal, TypedDict

Style = Literal["conservative", "balanced", "aggressive"]


class FactorWeights(TypedDict):
    value: float
    growth: float
    dividend: float
    quality: float


STYLE_WEIGHTS: dict[Style, FactorWeights] = {
    "conservative": {"value": 0.20, "growth": 0.10, "dividend": 0.35, "quality": 0.35},
    "balanced": {"value": 0.25, "growth": 0.25, "dividend": 0.25, "quality": 0.25},
    "aggressive": {"value": 0.15, "growth": 0.50, "dividend": 0.05, "quality": 0.30},
}


def weighted_total(
    value: float | None,
    growth: float | None,
    dividend: float | None,
    quality: float | None,
    weights: FactorWeights,
) -> float | None:
    """以指定權重計算總分；None 因子會被略過，剩餘權重再正規化。"""

    pairs = [
        (value, weights["value"]),
        (growth, weights["growth"]),
        (dividend, weights["dividend"]),
        (quality, weights["quality"]),
    ]
    usable = [(s, w) for s, w in pairs if s is not None]
    if not usable:
        return None
    total_w = sum(w for _, w in usable)
    if total_w == 0:
        return None
    return sum(s * w for s, w in usable) / total_w
