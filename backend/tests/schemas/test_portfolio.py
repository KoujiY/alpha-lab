from datetime import date, datetime

from alpha_lab.schemas.portfolio import Holding, Portfolio, RecommendResponse
from alpha_lab.schemas.score import FactorBreakdown


def test_portfolio_with_holdings() -> None:
    fb = FactorBreakdown(symbol="2330", calc_date=date(2026, 4, 15), total_score=80)
    h = Holding(symbol="2330", name="台積電", weight=0.3, score_breakdown=fb)
    p = Portfolio(
        style="balanced",
        label="平衡組",
        is_top_pick=True,
        holdings=[h],
        expected_yield=4.2,
        risk_score=45.0,
    )
    assert p.is_top_pick
    assert p.holdings[0].weight == 0.3


def test_recommend_response() -> None:
    resp = RecommendResponse(
        generated_at=datetime(2026, 4, 15, 20, 0, 0),
        calc_date="2026-04-15",
        portfolios=[],
    )
    assert resp.calc_date == "2026-04-15"
