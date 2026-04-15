"""Growth 因子：YoY 越高分越高。"""

from alpha_lab.analysis.factor_growth import compute_growth_scores


def test_higher_yoy_higher_score() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "A": {"revenue_yoy": 0.30, "eps_yoy": 0.50},
        "B": {"revenue_yoy": 0.10, "eps_yoy": 0.10},
        "C": {"revenue_yoy": -0.10, "eps_yoy": -0.20},
    }
    out = compute_growth_scores(snapshot)
    assert out["A"] == 100.0
    assert out["C"] == 0.0


def test_none_ignored() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "A": {"revenue_yoy": 0.3, "eps_yoy": None},
        "B": {"revenue_yoy": 0.1, "eps_yoy": 0.1},
    }
    out = compute_growth_scores(snapshot)
    assert out["A"] is not None
    assert out["B"] is not None
