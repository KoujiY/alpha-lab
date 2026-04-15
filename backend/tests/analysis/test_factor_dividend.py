"""Dividend 因子：殖利率越高分越高。"""

from alpha_lab.analysis.factor_dividend import compute_dividend_scores


def test_higher_yield_higher_score() -> None:
    snapshot: dict[str, float | None] = {"A": 0.05, "B": 0.03, "C": 0.01}
    out = compute_dividend_scores(snapshot)
    assert out["A"] == 100.0
    assert out["C"] == 0.0


def test_none_passthrough() -> None:
    out = compute_dividend_scores({"A": None, "B": 0.03})
    assert out["A"] is None
    assert out["B"] == 50.0
