"""Scoring pipeline：從 DB 拉快照、算四因子 + balanced 總分、upsert `scores` 表。

Balanced total 儲存進 `scores.total_score`；其他風格在 recommend 時
runtime 以 `weighted_total` 重新算（避免三倍儲存）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from alpha_lab.analysis.factor_dividend import compute_dividend_scores
from alpha_lab.analysis.factor_growth import compute_growth_scores
from alpha_lab.analysis.factor_quality import compute_quality_scores
from alpha_lab.analysis.factor_value import compute_value_scores
from alpha_lab.analysis.weights import STYLE_WEIGHTS, weighted_total
from alpha_lab.storage.models import (
    FinancialStatement,
    PriceDaily,
    RevenueMonthly,
    Score,
    Stock,
)


@dataclass
class Snapshot:
    """單一 calc_date 的快照，供四因子使用。"""

    value: dict[str, dict[str, float | None]]
    growth: dict[str, dict[str, float | None]]
    dividend: dict[str, float | None]
    quality: dict[str, dict[str, float | None]]


def build_snapshot(session: Session, calc_date: date) -> Snapshot:
    """從 DB 組合當日快照。

    - PE = close / eps_ttm（近四季 EPS 加總）
    - PB 目前 None（缺 shares_outstanding，Phase 4+ 補）
    - revenue_yoy：近 12 月營收 vs 前 12 月
    - eps_yoy：近四季 EPS 總和 vs 前四季
    - dividend_yield：目前 None（資料來源待 Phase 4/5 補）
    - ROE = net_income_ttm / total_equity
    - gross_margin = gross_profit_ttm / revenue_ttm
    - debt_ratio = total_liabilities / total_assets
    """

    symbols = [row[0] for row in session.execute(select(Stock.symbol)).all()]
    value: dict[str, dict[str, float | None]] = {}
    growth: dict[str, dict[str, float | None]] = {}
    dividend: dict[str, float | None] = {}
    quality: dict[str, dict[str, float | None]] = {}

    for sym in symbols:
        price_row = session.execute(
            select(PriceDaily.close)
            .where(PriceDaily.symbol == sym, PriceDaily.trade_date <= calc_date)
            .order_by(PriceDaily.trade_date.desc())
            .limit(1)
        ).first()
        close = float(price_row[0]) if price_row else None

        income_rows = (
            session.execute(
                select(FinancialStatement)
                .where(
                    FinancialStatement.symbol == sym,
                    FinancialStatement.statement_type == "income",
                )
                .order_by(FinancialStatement.period.desc())
                .limit(8)
            )
            .scalars()
            .all()
        )

        balance_row = session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == sym,
                FinancialStatement.statement_type == "balance",
            )
            .order_by(FinancialStatement.period.desc())
            .limit(1)
        ).scalar_one_or_none()

        eps_ttm = _sum_n([r.eps for r in income_rows[:4]])
        prev_eps_ttm = _sum_n([r.eps for r in income_rows[4:8]])
        rev_ttm = _sum_n([r.revenue for r in income_rows[:4]])
        gross_ttm = _sum_n([r.gross_profit for r in income_rows[:4]])
        ni_ttm = _sum_n([r.net_income for r in income_rows[:4]])

        pe = (close / eps_ttm) if close and eps_ttm and eps_ttm > 0 else None

        eps_yoy: float | None = None
        if eps_ttm is not None and prev_eps_ttm is not None and prev_eps_ttm != 0:
            eps_yoy = (eps_ttm - prev_eps_ttm) / abs(prev_eps_ttm)

        rev_12m = _sum_revenue_12m(session, sym, offset=0)
        rev_prev = _sum_revenue_12m(session, sym, offset=12)
        revenue_yoy: float | None = None
        if rev_12m is not None and rev_prev is not None and rev_prev != 0:
            revenue_yoy = (rev_12m - rev_prev) / rev_prev

        roe = (
            ni_ttm / balance_row.total_equity
            if ni_ttm is not None
            and balance_row is not None
            and balance_row.total_equity
            else None
        )
        gross_margin = (
            gross_ttm / rev_ttm if gross_ttm is not None and rev_ttm else None
        )
        debt_ratio = (
            balance_row.total_liabilities / balance_row.total_assets
            if balance_row is not None
            and balance_row.total_liabilities is not None
            and balance_row.total_assets
            else None
        )

        value[sym] = {"pe": pe, "pb": None}
        growth[sym] = {"revenue_yoy": revenue_yoy, "eps_yoy": eps_yoy}
        dividend[sym] = None
        quality[sym] = {
            "roe": roe,
            "gross_margin": gross_margin,
            "debt_ratio": debt_ratio,
        }

    return Snapshot(value=value, growth=growth, dividend=dividend, quality=quality)


def _sum_n(items: list[float | int | None]) -> float | None:
    vals = [x for x in items if x is not None]
    if len(vals) < len(items) or not vals:
        return None
    return float(sum(vals))


def _sum_revenue_12m(session: Session, symbol: str, offset: int) -> float | None:
    rows = session.execute(
        select(RevenueMonthly.revenue)
        .where(RevenueMonthly.symbol == symbol)
        .order_by(RevenueMonthly.year.desc(), RevenueMonthly.month.desc())
        .offset(offset)
        .limit(12)
    ).all()
    if len(rows) < 12:
        return None
    return float(sum(r[0] for r in rows))


def score_all(session: Session, calc_date: date) -> int:
    """算分並 upsert 到 scores 表。回傳寫入筆數。"""

    snap = build_snapshot(session, calc_date)
    value_scores = compute_value_scores(snap.value)
    growth_scores = compute_growth_scores(snap.growth)
    dividend_scores = compute_dividend_scores(snap.dividend)
    quality_scores = compute_quality_scores(snap.quality)

    rows: list[dict[str, object]] = []
    for sym in snap.value:
        total = weighted_total(
            value_scores[sym],
            growth_scores[sym],
            dividend_scores[sym],
            quality_scores[sym],
            STYLE_WEIGHTS["balanced"],
        )
        rows.append(
            {
                "symbol": sym,
                "calc_date": calc_date,
                "value_score": value_scores[sym],
                "growth_score": growth_scores[sym],
                "dividend_score": dividend_scores[sym],
                "quality_score": quality_scores[sym],
                "total_score": total,
            }
        )

    if not rows:
        return 0

    stmt = sqlite_insert(Score).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "calc_date"],
        set_={
            "value_score": stmt.excluded.value_score,
            "growth_score": stmt.excluded.growth_score,
            "dividend_score": stmt.excluded.dividend_score,
            "quality_score": stmt.excluded.quality_score,
            "total_score": stmt.excluded.total_score,
        },
    )
    session.execute(stmt)
    session.commit()
    return len(rows)
