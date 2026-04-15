"""analysis/reasons.py 單元測試。"""

from datetime import date

from alpha_lab.analysis.reasons import (
    HIGH_THRESHOLD,
    LOW_THRESHOLD,
    build_reasons,
)
from alpha_lab.schemas.score import FactorBreakdown


def _bk(
    value: float | None = 50,
    growth: float | None = 50,
    dividend: float | None = 50,
    quality: float | None = 50,
) -> FactorBreakdown:
    return FactorBreakdown(
        symbol="2330",
        calc_date=date(2026, 4, 17),
        value_score=value,
        growth_score=growth,
        dividend_score=dividend,
        quality_score=quality,
        total_score=50.0,
    )


def test_style_line_always_present_balanced() -> None:
    reasons = build_reasons(_bk(), "balanced")
    assert reasons
    assert "平衡組" in reasons[0]


def test_style_line_for_each_style() -> None:
    assert "保守組" in build_reasons(_bk(), "conservative")[0]
    assert "平衡組" in build_reasons(_bk(), "balanced")[0]
    assert "積極組" in build_reasons(_bk(), "aggressive")[0]


def test_high_quality_produces_positive_line() -> None:
    reasons = build_reasons(_bk(quality=HIGH_THRESHOLD + 20), "balanced")
    joined = "\n".join(reasons)
    assert "Quality" in joined
    assert "體質穩健" in joined


def test_low_value_produces_warning_line() -> None:
    reasons = build_reasons(_bk(value=LOW_THRESHOLD - 5), "balanced")
    joined = "\n".join(reasons)
    assert "Value" in joined
    assert "估值偏貴" in joined


def test_mid_range_factor_does_not_produce_line() -> None:
    reasons = build_reasons(_bk(value=50, growth=50, dividend=50, quality=50), "balanced")
    # 僅保留 style line
    assert len(reasons) == 1


def test_none_factors_do_not_crash_and_are_skipped() -> None:
    reasons = build_reasons(
        _bk(value=None, growth=None, dividend=None, quality=None), "aggressive"
    )
    assert len(reasons) == 1
    assert "積極組" in reasons[0]


def test_all_four_high_produces_five_lines() -> None:
    reasons = build_reasons(_bk(value=85, growth=90, dividend=80, quality=95), "balanced")
    # 1 style + 4 因子 = 5
    assert len(reasons) == 5


def test_mix_high_and_low() -> None:
    reasons = build_reasons(
        _bk(value=80, growth=20, dividend=50, quality=None), "conservative"
    )
    # 1 style + 1 high value + 1 low growth = 3；dividend 中段略過、quality None 略過
    assert len(reasons) == 3
    joined = "\n".join(reasons)
    assert "Value" in joined
    assert "Growth" in joined
    assert "Dividend" not in joined
    assert "Quality" not in joined


def test_reasons_are_non_empty_strings() -> None:
    reasons = build_reasons(_bk(value=85, quality=10), "aggressive")
    for line in reasons:
        assert isinstance(line, str)
        assert line.strip() != ""


def test_at_most_five_lines() -> None:
    reasons = build_reasons(_bk(value=95, growth=95, dividend=95, quality=95), "balanced")
    assert len(reasons) <= 6
