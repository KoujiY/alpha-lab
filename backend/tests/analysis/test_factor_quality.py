"""Quality 因子：ROE + 毛利率（高者佳）+ 負債比（低者佳）。"""

from alpha_lab.analysis.factor_quality import compute_quality_scores


def test_quality_higher_roe_better() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "A": {"roe": 0.25, "gross_margin": 0.5, "debt_ratio": 0.3},
        "B": {"roe": 0.10, "gross_margin": 0.3, "debt_ratio": 0.6},
    }
    out = compute_quality_scores(snapshot)
    assert out["A"] == 100.0
    assert out["B"] == 0.0


def test_quality_none_ignored() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "A": {"roe": 0.25, "gross_margin": None, "debt_ratio": None},
        "B": {"roe": 0.10, "gross_margin": None, "debt_ratio": None},
    }
    out = compute_quality_scores(snapshot)
    assert out["A"] == 100.0
    assert out["B"] == 0.0


def test_quality_with_fcf() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "A": {
            "roe": 0.25,
            "gross_margin": 0.5,
            "debt_ratio": 0.3,
            "fcf": 1000.0,
        },
        "B": {
            "roe": 0.10,
            "gross_margin": 0.3,
            "debt_ratio": 0.6,
            "fcf": 100.0,
        },
    }
    out = compute_quality_scores(snapshot)
    assert out["A"] == 100.0
    assert out["B"] == 0.0


def test_quality_fcf_missing_uses_other_factors() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "A": {"roe": 0.25, "gross_margin": 0.5, "debt_ratio": 0.3, "fcf": None},
        "B": {"roe": 0.10, "gross_margin": 0.3, "debt_ratio": 0.6, "fcf": None},
    }
    out = compute_quality_scores(snapshot)
    assert out["A"] == 100.0
    assert out["B"] == 0.0
