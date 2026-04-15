"""驗證百分位歸一化：最小→0、最大→100、線性內插。"""

from alpha_lab.analysis.normalize import percentile_rank, percentile_rank_inverted


def test_percentile_rank_extremes() -> None:
    values: dict[str, float | None] = {"A": 10.0, "B": 20.0, "C": 30.0}
    out = percentile_rank(values)
    assert out["A"] == 0.0
    assert out["C"] == 100.0
    assert out["B"] is not None and 0 < out["B"] < 100


def test_percentile_rank_handles_ties() -> None:
    values: dict[str, float | None] = {"A": 10.0, "B": 10.0, "C": 30.0}
    out = percentile_rank(values)
    assert out["A"] == out["B"]
    assert out["C"] == 100.0


def test_percentile_rank_skips_none() -> None:
    values: dict[str, float | None] = {"A": 10.0, "B": None, "C": 30.0}
    out = percentile_rank(values)
    assert out["B"] is None
    assert out["A"] == 0.0
    assert out["C"] == 100.0


def test_percentile_rank_inverted_lower_is_better() -> None:
    values: dict[str, float | None] = {"A": 10.0, "B": 20.0, "C": 30.0}
    out = percentile_rank_inverted(values)
    assert out["A"] == 100.0
    assert out["C"] == 0.0


def test_percentile_rank_single_value() -> None:
    out = percentile_rank({"A": 10.0})
    assert out["A"] == 50.0
