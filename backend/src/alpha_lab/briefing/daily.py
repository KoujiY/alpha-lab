"""Daily briefing assembler：從 DB 查詢 → 組合成完整 Markdown。"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.briefing.sections import (
    build_events_section,
    build_institutional_section,
    build_market_overview_section,
    build_portfolio_tracking_section,
)
from alpha_lab.storage.models import (
    Event,
    InstitutionalTrade,
    PriceDaily,
    SavedPortfolio,
    Stock,
)


def _query_prices_with_change(
    session: Session, trade_date: date
) -> list[dict[str, Any]]:
    prev_date_sub = (
        select(func.max(PriceDaily.trade_date))
        .where(PriceDaily.trade_date < trade_date)
        .correlate(None)
        .scalar_subquery()
    )

    rows = session.execute(
        select(
            PriceDaily.symbol,
            Stock.name,
            PriceDaily.close,
            PriceDaily.volume,
        )
        .join(Stock, PriceDaily.symbol == Stock.symbol)
        .where(PriceDaily.trade_date == trade_date)
        .order_by(PriceDaily.volume.desc())
    ).all()

    prev_map: dict[str, float] = {}
    prev_rows = session.execute(
        select(PriceDaily.symbol, PriceDaily.close).where(
            PriceDaily.trade_date == prev_date_sub
        )
    ).all()
    for sym, close in prev_rows:
        prev_map[sym] = float(close)

    result = []
    for sym, name, close, volume in rows:
        close_f = float(close)
        prev_close = prev_map.get(sym)
        change = close_f - prev_close if prev_close else 0.0
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        result.append(
            {
                "symbol": sym,
                "name": name,
                "close": close_f,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
            }
        )
    return result


def _query_institutional(session: Session, trade_date: date) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            InstitutionalTrade.symbol,
            Stock.name,
            InstitutionalTrade.foreign_net,
            InstitutionalTrade.trust_net,
            InstitutionalTrade.dealer_net,
            InstitutionalTrade.total_net,
        )
        .join(Stock, InstitutionalTrade.symbol == Stock.symbol)
        .where(InstitutionalTrade.trade_date == trade_date)
        .order_by(func.abs(InstitutionalTrade.total_net).desc())
    ).all()
    return [
        {
            "symbol": sym,
            "name": name,
            "foreign_net": foreign,
            "trust_net": trust,
            "dealer_net": dealer,
            "total_net": total,
        }
        for sym, name, foreign, trust, dealer, total in rows
    ]


def _query_events(session: Session, trade_date: date) -> list[dict[str, Any]]:
    end_dt = trade_date + timedelta(days=1)
    rows = (
        session.execute(
            select(Event)
            .where(Event.event_datetime >= trade_date)
            .where(Event.event_datetime < end_dt)
            .order_by(Event.event_datetime.desc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "symbol": r.symbol,
            "title": r.title,
            "event_type": r.event_type,
            "event_datetime": r.event_datetime.strftime("%Y-%m-%d %H:%M"),
        }
        for r in rows
    ]


def _query_saved_portfolios(session: Session) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            select(SavedPortfolio).order_by(SavedPortfolio.created_at.desc())
        )
        .scalars()
        .all()
    )
    result = []
    for p in rows:
        json.loads(p.holdings_json) if p.holdings_json else []
        result.append(
            {
                "id": p.id,
                "label": p.label,
                "nav": 1.0,
                "return_pct": 0.0,
                "base_date": p.base_date.isoformat() if p.base_date else "",
            }
        )
    return result


def build_daily_briefing(
    session_factory: sessionmaker[Session],
    trade_date: date,
) -> str:
    with session_factory() as session:
        prices = _query_prices_with_change(session, trade_date)
        inst = _query_institutional(session, trade_date)
        events = _query_events(session, trade_date)
        portfolios = _query_saved_portfolios(session)

    parts = [
        f"# 每日市場簡報（{trade_date.isoformat()}）\n",
        build_market_overview_section(prices, trade_date),
        build_institutional_section(inst, trade_date),
        build_events_section(events),
    ]
    if portfolios:
        parts.append(build_portfolio_tracking_section(portfolios))

    return "\n".join(parts)
