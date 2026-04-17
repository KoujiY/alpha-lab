"""基本面比率計算：PE / ROE / gross margin / debt ratio / FCF TTM 等。

與 `analysis/pipeline.build_snapshot` 邏輯相近，但只算單一 symbol，回傳扁平
`RatioSnapshot`，供 `processed_store` 寫入 JSON。兩邊可在 Phase 8 統一抽出
`fundamentals.py`；此處先獨立避免大改 pipeline。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from alpha_lab.storage.models import FinancialStatement, PriceDaily


@dataclass
class RatioSnapshot:
    as_of: date
    symbol: str
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_ratio: float | None = None
    fcf_ttm: int | None = None


def _sum_n(vals: list[float | int | None]) -> float | None:
    filtered = [v for v in vals if v is not None]
    if len(filtered) < len(vals) or not filtered:
        return None
    return float(sum(filtered))


def compute_ratios(session: Session, symbol: str, as_of: date) -> RatioSnapshot:
    snap = RatioSnapshot(as_of=as_of, symbol=symbol)

    price_row = session.execute(
        select(PriceDaily.close)
        .where(PriceDaily.symbol == symbol, PriceDaily.trade_date <= as_of)
        .order_by(PriceDaily.trade_date.desc())
        .limit(1)
    ).first()
    close = float(price_row[0]) if price_row else None

    income_rows = (
        session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == symbol,
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
            FinancialStatement.symbol == symbol,
            FinancialStatement.statement_type == "balance",
        )
        .order_by(FinancialStatement.period.desc())
        .limit(1)
    ).scalar_one_or_none()

    cashflow_rows = (
        session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == symbol,
                FinancialStatement.statement_type == "cashflow",
            )
            .order_by(FinancialStatement.period.desc())
            .limit(4)
        )
        .scalars()
        .all()
    )

    eps_ttm = _sum_n([r.eps for r in income_rows[:4]])
    rev_ttm = _sum_n([r.revenue for r in income_rows[:4]])
    gross_ttm = _sum_n([r.gross_profit for r in income_rows[:4]])
    ni_ttm = _sum_n([r.net_income for r in income_rows[:4]])

    if close and eps_ttm and eps_ttm > 0:
        snap.pe = close / eps_ttm

    if (
        ni_ttm is not None
        and balance_row is not None
        and balance_row.total_equity
    ):
        snap.roe = ni_ttm / balance_row.total_equity

    if gross_ttm is not None and rev_ttm:
        snap.gross_margin = gross_ttm / rev_ttm

    if (
        balance_row is not None
        and balance_row.total_liabilities is not None
        and balance_row.total_assets
    ):
        snap.debt_ratio = balance_row.total_liabilities / balance_row.total_assets

    if len(cashflow_rows) == 4 and all(
        r.operating_cf is not None for r in cashflow_rows
    ):
        snap.fcf_ttm = int(
            sum(r.operating_cf for r in cashflow_rows if r.operating_cf is not None)
        )

    return snap
