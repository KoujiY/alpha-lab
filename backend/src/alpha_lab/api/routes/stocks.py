"""Stocks API routes。

GET /api/stocks/{symbol}/overview → 個股頁首屏聚合資料
GET /api/stocks/{symbol}/prices?start=&end= → 股價細端點
GET /api/stocks/{symbol}/revenues?limit= → 月營收細端點
... (see A3)
"""

from datetime import date as _date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from alpha_lab.schemas.stock import (
    DailyPricePoint,
    EventPoint,
    FinancialPoint,
    InstitutionalPoint,
    MarginPoint,
    RevenuePoint,
    StockMeta,
    StockOverview,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import (
    Event,
    FinancialStatement,
    InstitutionalTrade,
    MarginTrade,
    PriceDaily,
    RevenueMonthly,
    Stock,
)

router = APIRouter(tags=["stocks"])

PRICES_DEFAULT_LIMIT = 60
REVENUES_DEFAULT_LIMIT = 12
FINANCIALS_DEFAULT_LIMIT = 4
INSTITUTIONAL_DEFAULT_LIMIT = 20
MARGIN_DEFAULT_LIMIT = 20
EVENTS_DEFAULT_LIMIT = 20


def _get_stock_or_404(session: Session, symbol: str) -> Stock:
    stock = session.get(Stock, symbol)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock {symbol} not found")
    return stock


def _load_prices(session: Session, symbol: str, limit: int) -> list[DailyPricePoint]:
    rows = session.execute(
        select(PriceDaily)
        .where(PriceDaily.symbol == symbol)
        .order_by(desc(PriceDaily.trade_date))
        .limit(limit)
    ).scalars().all()
    return [
        DailyPricePoint(
            trade_date=r.trade_date,
            open=r.open, high=r.high, low=r.low, close=r.close,
            volume=r.volume,
        )
        for r in reversed(rows)
    ]


def _load_revenues(session: Session, symbol: str, limit: int) -> list[RevenuePoint]:
    rows = session.execute(
        select(RevenueMonthly)
        .where(RevenueMonthly.symbol == symbol)
        .order_by(desc(RevenueMonthly.year), desc(RevenueMonthly.month))
        .limit(limit)
    ).scalars().all()
    return [
        RevenuePoint(
            year=r.year, month=r.month, revenue=r.revenue,
            yoy_growth=r.yoy_growth, mom_growth=r.mom_growth,
        )
        for r in reversed(rows)
    ]


def _load_financials(session: Session, symbol: str, limit: int) -> list[FinancialPoint]:
    """合併 income + balance 成單一 FinancialPoint（依 period 分組）。"""
    rows = session.execute(
        select(FinancialStatement)
        .where(FinancialStatement.symbol == symbol)
        .order_by(desc(FinancialStatement.period))
        .limit(limit * 2)
    ).scalars().all()

    by_period: dict[str, dict[str, object]] = {}
    for r in rows:
        acc = by_period.setdefault(r.period, {"period": r.period})
        if r.statement_type == "income":
            acc.update({
                "revenue": r.revenue,
                "gross_profit": r.gross_profit,
                "operating_income": r.operating_income,
                "net_income": r.net_income,
                "eps": r.eps,
            })
        elif r.statement_type == "balance":
            acc.update({
                "total_assets": r.total_assets,
                "total_liabilities": r.total_liabilities,
                "total_equity": r.total_equity,
            })

    sorted_periods = sorted(by_period.keys(), reverse=True)[:limit]
    return [FinancialPoint.model_validate(by_period[p]) for p in reversed(sorted_periods)]


def _load_institutional(
    session: Session, symbol: str, limit: int
) -> list[InstitutionalPoint]:
    rows = session.execute(
        select(InstitutionalTrade)
        .where(InstitutionalTrade.symbol == symbol)
        .order_by(desc(InstitutionalTrade.trade_date))
        .limit(limit)
    ).scalars().all()
    return [
        InstitutionalPoint(
            trade_date=r.trade_date,
            foreign_net=r.foreign_net, trust_net=r.trust_net,
            dealer_net=r.dealer_net, total_net=r.total_net,
        )
        for r in reversed(rows)
    ]


def _load_margin(session: Session, symbol: str, limit: int) -> list[MarginPoint]:
    rows = session.execute(
        select(MarginTrade)
        .where(MarginTrade.symbol == symbol)
        .order_by(desc(MarginTrade.trade_date))
        .limit(limit)
    ).scalars().all()
    return [
        MarginPoint(
            trade_date=r.trade_date,
            margin_balance=r.margin_balance,
            margin_buy=r.margin_buy, margin_sell=r.margin_sell,
            short_balance=r.short_balance,
            short_sell=r.short_sell, short_cover=r.short_cover,
        )
        for r in reversed(rows)
    ]


def _load_events(session: Session, symbol: str, limit: int) -> list[EventPoint]:
    """載入個股事件，回傳新到舊排序（UI 時間軸顯示最新消息在上）。"""
    rows = session.execute(
        select(Event)
        .where(Event.symbol == symbol)
        .order_by(desc(Event.event_datetime))
        .limit(limit)
    ).scalars().all()
    return [
        EventPoint(
            id=r.id, event_datetime=r.event_datetime,
            event_type=r.event_type, title=r.title, content=r.content,
        )
        for r in rows  # 事件刻意維持新到舊（UI 以時間軸顯示最新消息在上）
    ]


@router.get("/stocks", response_model=list[StockMeta])
async def list_stocks(
    q: str | None = Query(None, description="查詢代號或名稱（部分字串）"),
    limit: int = Query(50, ge=1, le=500),
) -> list[StockMeta]:
    with session_scope() as session:
        stmt = select(Stock)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Stock.symbol.like(like), Stock.name.like(like)))
        stmt = stmt.order_by(Stock.symbol).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [
            StockMeta(
                symbol=r.symbol, name=r.name,
                industry=r.industry, listed_date=r.listed_date,
            )
            for r in rows
        ]


@router.get("/stocks/{symbol}/overview", response_model=StockOverview)
async def get_stock_overview(symbol: str) -> StockOverview:
    with session_scope() as session:
        stock = _get_stock_or_404(session, symbol)
        meta = StockMeta(
            symbol=stock.symbol, name=stock.name,
            industry=stock.industry, listed_date=stock.listed_date,
        )
        return StockOverview(
            meta=meta,
            prices=_load_prices(session, symbol, PRICES_DEFAULT_LIMIT),
            revenues=_load_revenues(session, symbol, REVENUES_DEFAULT_LIMIT),
            financials=_load_financials(session, symbol, FINANCIALS_DEFAULT_LIMIT),
            institutional=_load_institutional(
                session, symbol, INSTITUTIONAL_DEFAULT_LIMIT
            ),
            margin=_load_margin(session, symbol, MARGIN_DEFAULT_LIMIT),
            events=_load_events(session, symbol, EVENTS_DEFAULT_LIMIT),
        )


@router.get("/stocks/{symbol}/prices", response_model=list[DailyPricePoint])
async def get_stock_prices(
    symbol: str,
    start: _date | None = Query(None),  # noqa: B008
    end: _date | None = Query(None),  # noqa: B008
    limit: int = Query(PRICES_DEFAULT_LIMIT, ge=1, le=500),
) -> list[DailyPricePoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        stmt = select(PriceDaily).where(PriceDaily.symbol == symbol)
        if start is not None:
            stmt = stmt.where(PriceDaily.trade_date >= start)
        if end is not None:
            stmt = stmt.where(PriceDaily.trade_date <= end)
        stmt = stmt.order_by(desc(PriceDaily.trade_date)).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [
            DailyPricePoint(
                trade_date=r.trade_date,
                open=r.open, high=r.high, low=r.low, close=r.close,
                volume=r.volume,
            )
            for r in reversed(rows)
        ]


@router.get("/stocks/{symbol}/revenues", response_model=list[RevenuePoint])
async def get_stock_revenues(
    symbol: str,
    limit: int = Query(REVENUES_DEFAULT_LIMIT, ge=1, le=120),
) -> list[RevenuePoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_revenues(session, symbol, limit)


@router.get("/stocks/{symbol}/financials", response_model=list[FinancialPoint])
async def get_stock_financials(
    symbol: str,
    limit: int = Query(FINANCIALS_DEFAULT_LIMIT, ge=1, le=40),
) -> list[FinancialPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_financials(session, symbol, limit)


@router.get("/stocks/{symbol}/institutional", response_model=list[InstitutionalPoint])
async def get_stock_institutional(
    symbol: str,
    limit: int = Query(INSTITUTIONAL_DEFAULT_LIMIT, ge=1, le=500),
) -> list[InstitutionalPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_institutional(session, symbol, limit)


@router.get("/stocks/{symbol}/margin", response_model=list[MarginPoint])
async def get_stock_margin(
    symbol: str,
    limit: int = Query(MARGIN_DEFAULT_LIMIT, ge=1, le=500),
) -> list[MarginPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_margin(session, symbol, limit)


@router.get("/stocks/{symbol}/events", response_model=list[EventPoint])
async def get_stock_events(
    symbol: str,
    limit: int = Query(EVENTS_DEFAULT_LIMIT, ge=1, le=200),
) -> list[EventPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_events(session, symbol, limit)
