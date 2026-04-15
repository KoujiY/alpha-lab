"""Collector 執行層：把 Pydantic 輸出 upsert 到 DB。

Stock 主資料採「若不存在就建立 placeholder」策略（name 用 symbol）。
TODO: 公司基本資料同步（name / industry / listed_date）尚未實作，
見 docs/knowledge/features/* 或後續 Phase 規劃。
"""

import json
from collections.abc import Iterable

from sqlalchemy.orm import Session

from alpha_lab.schemas.event import Event as EventSchema
from alpha_lab.schemas.financial_statement import (
    FinancialStatement as FinancialStatementSchema,
)
from alpha_lab.schemas.financial_statement import StatementType
from alpha_lab.schemas.institutional import (
    InstitutionalTrade as InstitutionalTradeSchema,
)
from alpha_lab.schemas.margin import MarginTrade as MarginTradeSchema
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.schemas.revenue import MonthlyRevenue
from alpha_lab.storage.models import Event as EventRow
from alpha_lab.storage.models import (
    FinancialStatement as FinancialStatementRow,
)
from alpha_lab.storage.models import (
    InstitutionalTrade as InstitutionalTradeRow,
)
from alpha_lab.storage.models import MarginTrade as MarginTradeRow
from alpha_lab.storage.models import PriceDaily, RevenueMonthly, Stock


def _ensure_stock(session: Session, symbol: str) -> None:
    """確保單一 symbol 的 Stock placeholder 存在。

    使用 `session.merge` 而非 `add`，避免同一 session 內重複 add 造成
    `UNIQUE constraint failed: stocks.symbol`。merge 會：
    - 若 DB/identity map 已有該 PK，載入既有物件（不會新建）
    - 否則插入 placeholder（name 暫以 symbol 代替）
    """
    if session.get(Stock, symbol) is not None:
        return
    session.merge(Stock(symbol=symbol, name=symbol))


def _ensure_stocks(session: Session, symbols: Iterable[str]) -> None:
    """一次確保多個 symbols 的 Stock placeholder 存在（去重）。

    在 upsert 迴圈前先呼叫，避免對同一 symbol 的多筆 row 重複觸發
    `_ensure_stock`，進而引發 race / IntegrityError。
    """
    seen: set[str] = set()
    for symbol in symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        _ensure_stock(session, symbol)
    # flush 一次，讓後續 session.get(PriceDaily, ...) 等查詢能看到
    # placeholder，同時在真的撞到 UNIQUE 衝突時立即拋錯，而不是等到
    # commit 時才發現。
    session.flush()


def upsert_daily_prices(session: Session, rows: list[DailyPrice]) -> int:
    """upsert 日股價。回傳寫入筆數（新增 + 更新）。"""
    _ensure_stocks(session, (row.symbol for row in rows))
    count = 0
    for row in rows:
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
    _ensure_stocks(session, (row.symbol for row in rows))
    count = 0
    for row in rows:
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


def upsert_institutional_trades(
    session: Session, rows: list[InstitutionalTradeSchema]
) -> int:
    """upsert 三大法人買賣超。回傳寫入筆數。"""
    _ensure_stocks(session, (row.symbol for row in rows))
    count = 0
    for row in rows:
        existing = session.get(
            InstitutionalTradeRow,
            {"symbol": row.symbol, "trade_date": row.trade_date},
        )
        if existing is None:
            session.add(
                InstitutionalTradeRow(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    foreign_net=row.foreign_net,
                    trust_net=row.trust_net,
                    dealer_net=row.dealer_net,
                    total_net=row.total_net,
                )
            )
        else:
            existing.foreign_net = row.foreign_net
            existing.trust_net = row.trust_net
            existing.dealer_net = row.dealer_net
            existing.total_net = row.total_net
        count += 1
    return count


def upsert_margin_trades(
    session: Session, rows: list[MarginTradeSchema]
) -> int:
    """upsert 融資融券餘額。回傳寫入筆數。"""
    _ensure_stocks(session, (row.symbol for row in rows))
    count = 0
    for row in rows:
        existing = session.get(
            MarginTradeRow,
            {"symbol": row.symbol, "trade_date": row.trade_date},
        )
        if existing is None:
            session.add(
                MarginTradeRow(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    margin_buy=row.margin_buy,
                    margin_sell=row.margin_sell,
                    margin_balance=row.margin_balance,
                    short_sell=row.short_sell,
                    short_cover=row.short_cover,
                    short_balance=row.short_balance,
                )
            )
        else:
            existing.margin_buy = row.margin_buy
            existing.margin_sell = row.margin_sell
            existing.margin_balance = row.margin_balance
            existing.short_sell = row.short_sell
            existing.short_cover = row.short_cover
            existing.short_balance = row.short_balance
        count += 1
    return count


def upsert_events(session: Session, rows: list[EventSchema]) -> int:
    """upsert 重大訊息。以 (symbol, event_datetime, title) 查重。回傳新插入筆數。

    既存則 skip（重大訊息不 overwrite，避免修改歷史紀錄）。
    """
    _ensure_stocks(session, (row.symbol for row in rows))
    inserted = 0
    for row in rows:
        # datetime 需為 naive（存 SQLite DateTime）；若 caller 傳 aware 需轉
        dt = (
            row.event_datetime.replace(tzinfo=None)
            if row.event_datetime.tzinfo
            else row.event_datetime
        )
        existing = (
            session.query(EventRow)
            .filter(
                EventRow.symbol == row.symbol,
                EventRow.event_datetime == dt,
                EventRow.title == row.title,
            )
            .first()
        )
        if existing is None:
            session.add(
                EventRow(
                    symbol=row.symbol,
                    event_datetime=dt,
                    event_type=row.event_type,
                    title=row.title,
                    content=row.content,
                )
            )
            inserted += 1
    return inserted


def upsert_financial_statements(
    session: Session, rows: list[FinancialStatementSchema]
) -> int:
    """upsert 季報（三表共用 wide model）。回傳寫入筆數（新增 + 更新）。

    主鍵 `(symbol, period, statement_type)`；既存同一筆會覆寫所有欄位（含
    `raw_json_text`）。不同 `statement_type` 只會填自己那組欄位，其他欄位
    保持 None。
    """
    _ensure_stocks(session, (row.symbol for row in rows))
    count = 0
    for row in rows:
        statement_type_value = (
            row.statement_type.value
            if isinstance(row.statement_type, StatementType)
            else str(row.statement_type)
        )
        pk = {
            "symbol": row.symbol,
            "period": row.period,
            "statement_type": statement_type_value,
        }
        existing = session.get(FinancialStatementRow, pk)
        raw_text = json.dumps(row.raw_json, ensure_ascii=False)
        fields = {
            "revenue": row.revenue,
            "gross_profit": row.gross_profit,
            "operating_income": row.operating_income,
            "net_income": row.net_income,
            "eps": row.eps,
            "total_assets": row.total_assets,
            "total_liabilities": row.total_liabilities,
            "total_equity": row.total_equity,
            "operating_cf": row.operating_cf,
            "investing_cf": row.investing_cf,
            "financing_cf": row.financing_cf,
            "raw_json_text": raw_text,
        }
        if existing is None:
            session.add(
                FinancialStatementRow(
                    symbol=row.symbol,
                    period=row.period,
                    statement_type=statement_type_value,
                    **fields,
                )
            )
        else:
            for k, v in fields.items():
                setattr(existing, k, v)
        count += 1
    return count
