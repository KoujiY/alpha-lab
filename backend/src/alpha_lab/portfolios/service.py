"""Saved portfolio service（Phase 6）。"""

from __future__ import annotations

import json
from datetime import date as date_type

from sqlalchemy import select

from alpha_lab.schemas.saved_portfolio import (
    SavedHolding,
    SavedPortfolioCreate,
    SavedPortfolioDetail,
    SavedPortfolioMeta,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import SavedPortfolio


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
