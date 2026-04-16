"""Saved portfolio service（Phase 6）。"""

from __future__ import annotations

import json
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.orm import Session

from alpha_lab.schemas.saved_portfolio import (
    PerformancePoint,
    PerformanceResponse,
    SavedHolding,
    SavedPortfolioCreate,
    SavedPortfolioDetail,
    SavedPortfolioMeta,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import PortfolioSnapshot, PriceDaily, SavedPortfolio


def _holdings_to_json(holdings: list[SavedHolding]) -> str:
    return json.dumps([h.model_dump() for h in holdings], ensure_ascii=False)


def _holdings_from_json(raw: str) -> list[SavedHolding]:
    return [SavedHolding(**item) for item in json.loads(raw)]


def _row_to_meta(row: SavedPortfolio) -> SavedPortfolioMeta:
    holdings = _holdings_from_json(row.holdings_json)
    return SavedPortfolioMeta(
        id=row.id,
        style=row.style,  # type: ignore[arg-type]
        label=row.label,
        note=row.note,
        base_date=row.base_date,
        created_at=row.created_at,
        holdings_count=len(holdings),
    )


def _row_to_detail(row: SavedPortfolio) -> SavedPortfolioDetail:
    holdings = _holdings_from_json(row.holdings_json)
    return SavedPortfolioDetail(
        id=row.id,
        style=row.style,  # type: ignore[arg-type]
        label=row.label,
        note=row.note,
        base_date=row.base_date,
        created_at=row.created_at,
        holdings_count=len(holdings),
        holdings=holdings,
    )


def save_portfolio(
    payload: SavedPortfolioCreate,
    *,
    base_date: date_type,
) -> SavedPortfolioMeta:
    with session_scope() as session:
        row = SavedPortfolio(
            style=payload.style,
            label=payload.label,
            note=payload.note,
            holdings_json=_holdings_to_json(payload.holdings),
            base_date=base_date,
        )
        session.add(row)
        session.flush()
        meta = _row_to_meta(row)
    return meta


def list_saved() -> list[SavedPortfolioMeta]:
    with session_scope() as session:
        rows = session.scalars(
            select(SavedPortfolio).order_by(SavedPortfolio.created_at.desc())
        ).all()
        return [_row_to_meta(r) for r in rows]


def get_saved(portfolio_id: int) -> SavedPortfolioDetail | None:
    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return None
        return _row_to_detail(row)


def delete_saved(portfolio_id: int) -> bool:
    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return False
        session.delete(row)
    return True


def _load_price_map(
    session: Session, symbols: list[str], start: date_type
) -> dict[str, dict[date_type, float]]:
    """回傳 {symbol: {date: close}}，僅取 >= start 日期。"""

    rows = session.scalars(
        select(PriceDaily)
        .where(PriceDaily.symbol.in_(symbols))
        .where(PriceDaily.trade_date >= start)
        .order_by(PriceDaily.trade_date.asc())
    ).all()
    result: dict[str, dict[date_type, float]] = {s: {} for s in symbols}
    for row in rows:
        result[row.symbol][row.trade_date] = row.close
    return result


def compute_performance(portfolio_id: int) -> PerformanceResponse | None:
    """從 base_date 起每日 NAV：sum(weight_i * price_i(t) / base_price_i)。

    只取所有持股都有報價的日期；缺價日直接跳過。
    會同步 upsert 最新一筆到 `portfolio_snapshots`（供之後擴充排程用）。
    """

    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return None
        holdings = _holdings_from_json(row.holdings_json)
        symbols = [h.symbol for h in holdings]
        price_map = _load_price_map(session, symbols, row.base_date)

        # 取所有股票都有報價的日期交集
        common_dates: set[date_type] | None = None
        for sym in symbols:
            dates_for_sym = set(price_map[sym].keys())
            common_dates = (
                dates_for_sym if common_dates is None else common_dates & dates_for_sym
            )
        if not common_dates:
            common_dates = set()

        sorted_dates = sorted(common_dates)
        points: list[PerformancePoint] = []
        prev_nav: float | None = None
        for d in sorted_dates:
            nav = sum(
                h.weight * (price_map[h.symbol][d] / h.base_price) for h in holdings
            )
            daily_return = (nav / prev_nav - 1.0) if prev_nav else None
            points.append(PerformancePoint(date=d, nav=nav, daily_return=daily_return))
            prev_nav = nav

        latest_nav = points[-1].nav if points else 1.0
        total_return = latest_nav - 1.0

        # cache 最新一筆
        if points:
            session.merge(
                PortfolioSnapshot(
                    portfolio_id=row.id,
                    snapshot_date=points[-1].date,
                    nav=latest_nav,
                    holdings_json=row.holdings_json,
                )
            )

        detail = _row_to_detail(row)

    return PerformanceResponse(
        portfolio=detail,
        points=points,
        latest_nav=latest_nav,
        total_return=total_return,
    )
