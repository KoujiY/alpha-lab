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
    probe_base_date,
    save_portfolio,
)
from alpha_lab.reports.service import create_portfolio_report
from alpha_lab.schemas.portfolio import Portfolio, RecommendResponse
from alpha_lab.schemas.saved_portfolio import (
    BaseDateProbe,
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


@router.get("/saved/probe", response_model=BaseDateProbe)
async def probe_endpoint(
    symbols: str = Query(..., description="逗號分隔的 symbol 清單，例 2330,2317"),
) -> BaseDateProbe:
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        raise HTTPException(status_code=400, detail="symbols required")
    target = date_type.today()
    resolved, missing, statuses = probe_base_date(sym_list, target)
    return BaseDateProbe(
        target_date=target,
        resolved_date=resolved,
        today_available=len(missing) == 0,
        missing_today_symbols=missing,
        symbol_statuses=statuses,
    )


@router.post("/saved", response_model=SavedPortfolioMeta, status_code=201)
async def save_portfolio_endpoint(
    payload: SavedPortfolioCreate,
    allow_fallback: bool = Query(
        False,
        description="若當日缺報價，自動退到所有持股都有報價的最近交易日。"
        "前端應先呼叫 /saved/probe 確認再決定是否帶此參數。",
    ),
) -> SavedPortfolioMeta:
    try:
        return save_portfolio(
            payload, base_date=date_type.today(), allow_fallback=allow_fallback
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
