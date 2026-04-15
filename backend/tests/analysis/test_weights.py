from alpha_lab.analysis.weights import STYLE_WEIGHTS, weighted_total


def test_style_weights_sum_to_one() -> None:
    for _, w in STYLE_WEIGHTS.items():
        assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weighted_total_all_equal() -> None:
    out = weighted_total(80, 80, 80, 80, STYLE_WEIGHTS["balanced"])
    assert out == 80.0


def test_weighted_total_none_skipped() -> None:
    out = weighted_total(100, None, None, None, STYLE_WEIGHTS["balanced"])
    assert out == 100.0


def test_weighted_total_all_none() -> None:
    out = weighted_total(None, None, None, None, STYLE_WEIGHTS["balanced"])
    assert out is None
