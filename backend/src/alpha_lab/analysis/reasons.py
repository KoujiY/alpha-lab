"""推薦理由靜態模板生成器（Phase 4）。

依因子分數與 style，組出 2-6 條中文短句描述「為什麼這檔入選這組」。
不呼叫外部 API；Phase 7 才會考慮接 Claude API 產生動態理由。

規則：
- 高分（≥ HIGH_THRESHOLD）→ 出現一句正向描述
- 低分（≤ LOW_THRESHOLD）→ 出現一句風險提示
- 中段（>LOW、<HIGH）→ 不生句
- style 特性句固定掛一條（每個 style 一句）
- None 的因子略過、不 crash
"""

from __future__ import annotations

from alpha_lab.analysis.weights import Style
from alpha_lab.schemas.score import FactorBreakdown

HIGH_THRESHOLD = 70.0
LOW_THRESHOLD = 30.0

_STYLE_LINES: dict[Style, str] = {
    "conservative": "保守組配置偏好：以殖利率與體質品質為主軸，波動較低。",
    "balanced": "平衡組配置偏好：Value / Growth / Dividend / Quality 四面並重。",
    "aggressive": "積極組配置偏好：優先追求營收與獲利成長動能。",
}

_FACTOR_HIGH_TEMPLATES: dict[str, str] = {
    "value": "Value {score:.0f} 分：估值相對便宜，具安全邊際。",
    "growth": "Growth {score:.0f} 分：營收或獲利成長動能強。",
    "dividend": "Dividend {score:.0f} 分：殖利率優於市場，現金回饋佳。",
    "quality": "Quality {score:.0f} 分：ROE、毛利率、負債結構等體質穩健。",
}

_FACTOR_LOW_TEMPLATES: dict[str, str] = {
    "value": "Value {score:.0f} 分：估值偏貴，留意本益比是否合理。",
    "growth": "Growth {score:.0f} 分：成長動能不足，留意基本面轉折。",
    "dividend": "Dividend {score:.0f} 分：殖利率偏低，配息支撐有限。",
    "quality": "Quality {score:.0f} 分：體質指標偏弱，留意獲利品質與負債。",
}


def _factor_line(name: str, score: float | None) -> str | None:
    if score is None:
        return None
    if score >= HIGH_THRESHOLD:
        return _FACTOR_HIGH_TEMPLATES[name].format(score=score)
    if score <= LOW_THRESHOLD:
        return _FACTOR_LOW_TEMPLATES[name].format(score=score)
    return None


def build_reasons(breakdown: FactorBreakdown, style: Style) -> list[str]:
    """回傳 1-5 條中文短句，用於 Holding.reasons。

    固定第一條為 style 特性句；後續依四因子高/低分各補一句（中段不生）。
    """

    lines: list[str] = [_STYLE_LINES[style]]
    for name, value in (
        ("value", breakdown.value_score),
        ("growth", breakdown.growth_score),
        ("dividend", breakdown.dividend_score),
        ("quality", breakdown.quality_score),
    ):
        line = _factor_line(name, value)
        if line is not None:
            lines.append(line)
    return lines
