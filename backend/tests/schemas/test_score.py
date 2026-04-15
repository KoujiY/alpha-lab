from datetime import date

from alpha_lab.schemas.score import FactorBreakdown, ScoreResponse


def test_factor_breakdown_optional_fields() -> None:
    fb = FactorBreakdown(symbol="2330", calc_date=date(2026, 4, 15))
    assert fb.total_score is None


def test_score_response_with_latest() -> None:
    resp = ScoreResponse(
        symbol="2330",
        latest=FactorBreakdown(
            symbol="2330",
            calc_date=date(2026, 4, 15),
            value_score=70,
            total_score=70,
        ),
    )
    assert resp.latest is not None
    assert resp.latest.value_score == 70
