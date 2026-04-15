"""/api/portfolios 路由。"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from alpha_lab.analysis.portfolio import generate_portfolio, latest_calc_date
from alpha_lab.analysis.weights import STYLE_WEIGHTS, Style
from alpha_lab.schemas.portfolio import Portfolio, RecommendResponse
from alpha_lab.storage.engine import session_scope

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    style: Style | None = Query(None),  # noqa: B008
) -> RecommendResponse:
    with session_scope() as session:
        calc_date = latest_calc_date(session)
        if calc_date is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "no scores available; run POST /api/jobs/collect with "
                    "job_type='score' first"
                ),
            )

        styles: list[Style] = (
            list(STYLE_WEIGHTS.keys()) if style is None else [style]
        )

        portfolios: list[Portfolio] = [
            generate_portfolio(session, s, calc_date) for s in styles
        ]
        return RecommendResponse(
            generated_at=datetime.now(UTC),
            calc_date=calc_date.isoformat(),
            portfolios=portfolios,
        )
