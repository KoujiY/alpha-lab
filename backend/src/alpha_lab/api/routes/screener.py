"""/api/screener 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from alpha_lab.analysis.portfolio import latest_calc_date
from alpha_lab.analysis.weights import STYLE_WEIGHTS, weighted_total
from alpha_lab.schemas.screener import (
    FactorMeta,
    FactorRange,
    FactorsResponse,
    FilterRequest,
    FilterResponse,
    ScreenerStock,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Score, Stock

router = APIRouter(prefix="/screener", tags=["screener"])

FACTOR_DEFINITIONS: list[FactorMeta] = [
    FactorMeta(
        key="value_score", label="價值 Value", description="PE、PB 等估值指標"
    ),
    FactorMeta(
        key="growth_score", label="成長 Growth", description="營收 YoY、EPS YoY"
    ),
    FactorMeta(
        key="dividend_score",
        label="股息 Dividend",
        description="殖利率、配息穩定度",
    ),
    FactorMeta(
        key="quality_score",
        label="品質 Quality",
        description="ROE、毛利率、負債比、FCF",
    ),
    FactorMeta(
        key="total_score", label="總分 Total", description="四因子加權平均"
    ),
]

VALID_SORT_KEYS = {f.key for f in FACTOR_DEFINITIONS}


@router.get("/factors", response_model=FactorsResponse)
async def get_factors() -> FactorsResponse:
    return FactorsResponse(factors=FACTOR_DEFINITIONS)


@router.post("/filter", response_model=FilterResponse)
async def filter_stocks(req: FilterRequest) -> FilterResponse:
    with session_scope() as session:
        calc_date = latest_calc_date(session)
        if calc_date is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "no scores available; run POST /api/jobs/collect "
                    "with job_type='score' first"
                ),
            )

        stmt = (
            select(Score, Stock)
            .join(Stock, Stock.symbol == Score.symbol)
            .where(Score.calc_date == calc_date)
        )
        rows = session.execute(stmt).all()

        results: list[ScreenerStock] = []
        for score, stock in rows:
            if not _passes_filters(score, req.filters):
                continue

            total = weighted_total(
                score.value_score,
                score.growth_score,
                score.dividend_score,
                score.quality_score,
                STYLE_WEIGHTS["balanced"],
            )

            results.append(
                ScreenerStock(
                    symbol=stock.symbol,
                    name=stock.name,
                    industry=stock.industry,
                    value_score=score.value_score,
                    growth_score=score.growth_score,
                    dividend_score=score.dividend_score,
                    quality_score=score.quality_score,
                    total_score=total,
                )
            )

    sort_key = req.sort_by if req.sort_by in VALID_SORT_KEYS else "total_score"
    results.sort(
        key=lambda s: getattr(s, sort_key) if getattr(s, sort_key) is not None else -1.0,
        reverse=req.sort_desc,
    )

    return FilterResponse(
        calc_date=calc_date.isoformat(),
        total_count=len(results),
        stocks=results[: req.limit],
    )


def _passes_filters(score: Score, filters: list[FactorRange]) -> bool:
    for f in filters:
        val = getattr(score, f.key, None)
        if val is None:
            return False
        if val < f.min_value or val > f.max_value:
            return False
    return True
