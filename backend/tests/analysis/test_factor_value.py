"""Value 因子：PE 越低分越高，PB 同理；None 值被忽略。"""

from alpha_lab.analysis.factor_value import compute_value_scores


def test_compute_value_scores_pe_only() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "2330": {"pe": 15.0, "pb": None},
        "2454": {"pe": 20.0, "pb": None},
        "1301": {"pe": 25.0, "pb": None},
    }
    out = compute_value_scores(snapshot)
    assert out["2330"] == 100.0
    assert out["1301"] == 0.0


def test_compute_value_scores_none_passthrough() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "2330": {"pe": None, "pb": None},
        "2454": {"pe": 20.0, "pb": None},
    }
    out = compute_value_scores(snapshot)
    assert out["2330"] is None
    assert out["2454"] == 50.0


def test_compute_value_scores_pe_and_pb_averaged() -> None:
    snapshot: dict[str, dict[str, float | None]] = {
        "2330": {"pe": 15.0, "pb": 5.0},
        "2454": {"pe": 25.0, "pb": 2.0},
    }
    out = compute_value_scores(snapshot)
    assert out["2330"] == 50.0
    assert out["2454"] == 50.0
