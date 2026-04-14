"""Collector 執行層：把 Pydantic 輸出 upsert 到 DB。

Stock 主資料採「若不存在就建立 placeholder」策略（name 用 symbol）；
正式的公司基本資料同步未在 Phase 1 範圍內。
"""

from sqlalchemy.orm import Session

from alpha_lab.schemas.price import DailyPrice
from alpha_lab.schemas.revenue import MonthlyRevenue
from alpha_lab.storage.models import PriceDaily, RevenueMonthly, Stock


def _ensure_stock(session: Session, symbol: str) -> None:
    existing = session.get(Stock, symbol)
    if existing is None:
        session.add(Stock(symbol=symbol, name=symbol))


def upsert_daily_prices(session: Session, rows: list[DailyPrice]) -> int:
    """upsert 日股價。回傳寫入筆數（新增 + 更新）。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        existing = session.get(
            PriceDaily, {"symbol": row.symbol, "trade_date": row.trade_date}
        )
        if existing is None:
            session.add(
                PriceDaily(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                )
            )
        else:
            existing.open = row.open
            existing.high = row.high
            existing.low = row.low
            existing.close = row.close
            existing.volume = row.volume
        count += 1
    return count


def upsert_monthly_revenues(session: Session, rows: list[MonthlyRevenue]) -> int:
    """upsert 月營收。回傳寫入筆數。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        existing = session.get(
            RevenueMonthly,
            {"symbol": row.symbol, "year": row.year, "month": row.month},
        )
        if existing is None:
            session.add(
                RevenueMonthly(
                    symbol=row.symbol,
                    year=row.year,
                    month=row.month,
                    revenue=row.revenue,
                    yoy_growth=row.yoy_growth,
                    mom_growth=row.mom_growth,
                )
            )
        else:
            existing.revenue = row.revenue
            existing.yoy_growth = row.yoy_growth
            existing.mom_growth = row.mom_growth
        count += 1
    return count
