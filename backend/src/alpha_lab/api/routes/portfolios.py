"""/api/portfolios 路由。"""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_type

from fastapi import APIRouter, HTTPException, Query

from alpha_lab.analysis.portfolio import generate_portfolio, latest_calc_date
from alpha_lab.analysis.weights import STYLE_WEIGHTS, Style
from alpha_lab.portfolios.service import (
    compute_performance,
    delete_saved,
    get_saved,
    list_saved,
    save_portfolio,
)
from alpha_lab.reports.service import create_portfolio_report
from alpha_lab.schemas.portfolio import Portfolio, RecommendResponse
from alpha_lab.schemas.saved_portfolio import (
    PerformanceResponse,
    SavedPortfolioCreate,
    SavedPortfolioDetail,
    SavedPortfolioMeta,
)
from alpha_lab.storage.engine import session_scope

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    style: Style | None = Query(None),  # noqa: B008
    save_report: bool = Query(
        False,
        description="同時把本次推薦寫成 portfolio 類型報告（data/reports/analysis/portfolio-<date>.md）",
    ),
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
        resp = RecommendResponse(
            generated_at=datetime.now(UTC),
            calc_date=calc_date.isoformat(),
            portfolios=portfolios,
        )

    if save_report:
        create_portfolio_report(resp)

    return resp


@router.get("/saved", response_model=list[SavedPortfolioMeta])
async def list_saved_portfolios_endpoint() -> list[SavedPortfolioMeta]:
    return list_saved()


@router.post("/saved", response_model=SavedPortfolioMeta, status_code=201)
async def save_portfolio_endpoint(
    payload: SavedPortfolioCreate,
) -> SavedPortfolioMeta:
    return save_portfolio(payload, base_date=date_type.today())


@router.get("/saved/{portfolio_id}", response_model=SavedPortfolioDetail)
async def get_saved_endpoint(portfolio_id: int) -> SavedPortfolioDetail:
    detail = get_saved(portfolio_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="saved portfolio not found")
    return detail


@router.delete("/saved/{portfolio_id}", status_code=204)
async def delete_saved_endpoint(portfolio_id: int) -> None:
    if not delete_saved(portfolio_id):
        raise HTTPException(status_code=404, detail="saved portfolio not found")


@router.get("/saved/{portfolio_id}/performance", response_model=PerformanceResponse)
async def performance_endpoint(portfolio_id: int) -> PerformanceResponse:
    resp = compute_performance(portfolio_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="saved portfolio not found")
    return resp
