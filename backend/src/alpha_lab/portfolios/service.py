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


def _resolve_common_base_date(
    session: Session, symbols: list[str], target_date: date_type
) -> date_type | None:
    """找所有 symbols 都有報價、且 <= target_date 的最近交易日。

    若任一 symbol 在 prices_daily 完全無 <= target_date 的紀錄，回傳 None。
    用途：讓 `save_portfolio` 能在週末 / 收盤前 / 部分日期缺料時自動 fallback
    到最近一個「全部持股都報價」的交易日，而非硬要 `target_date` 當天。
    """

    common_dates: set[date_type] | None = None
    for sym in symbols:
        dates = set(
            session.scalars(
                select(PriceDaily.trade_date)
                .where(PriceDaily.symbol == sym)
                .where(PriceDaily.trade_date <= target_date)
            ).all()
        )
        if not dates:
            return None
        common_dates = dates if common_dates is None else common_dates & dates
        if not common_dates:
            return None
    return max(common_dates) if common_dates else None


def probe_base_date(
    symbols: list[str], target_date: date_type
) -> tuple[date_type | None, list[str]]:
    """檢查 target_date 當日哪些 symbols 缺報價，並回傳「全有報價的最近交易日」。

    回傳 (resolved_date, missing_today_symbols)：
    - resolved_date：所有 symbols 都有報價、且 <= target_date 的最大交易日；
      若任一 symbol 完全無 <= target_date 的紀錄，回傳 None。
    - missing_today_symbols：在 target_date 當日缺報價的 symbol 清單。

    若 missing_today_symbols == []，前端可直接 strict save；否則應跳 dialog
    讓使用者決定是先補抓資料還是同意以 resolved_date 為基準儲存。
    """

    with session_scope() as session:
        resolved = _resolve_common_base_date(session, symbols, target_date)
        missing_today: list[str] = []
        for sym in symbols:
            has_today = session.scalar(
                select(PriceDaily.trade_date)
                .where(PriceDaily.symbol == sym)
                .where(PriceDaily.trade_date == target_date)
            )
            if has_today is None:
                missing_today.append(sym)
        return resolved, missing_today


def save_portfolio(
    payload: SavedPortfolioCreate,
    *,
    base_date: date_type,
    allow_fallback: bool = False,
) -> SavedPortfolioMeta:
    """儲存組合。

    預設 strict 模式：要求所有持股在 `base_date` 當日都有 prices_daily 報價。
    若 `allow_fallback=True`（前端 dialog 已警示後使用者同意），當日缺料時自動退到
    所有持股都有報價的最近交易日（`<= base_date`）。任一模式下，若連 fallback
    也找不到（某 symbol 完全無 <= base_date 紀錄），raise ValueError。

    `base_price <= 0` 的持股會用最終決定的 base_date 從 prices_daily 補值。
    """

    with session_scope() as session:
        symbols = [h.symbol for h in payload.holdings]

        if allow_fallback:
            resolved_base_date = _resolve_common_base_date(
                session, symbols, base_date
            )
            if resolved_base_date is None:
                raise ValueError(
                    f"no common trade_date for {symbols} on or before {base_date}; "
                    "run daily_collect for missing symbols first"
                )
        else:
            resolved_base_date = base_date

        enriched_holdings: list[SavedHolding] = []
        for h in payload.holdings:
            if h.base_price <= 0:
                close = session.scalar(
                    select(PriceDaily.close)
                    .where(PriceDaily.symbol == h.symbol)
                    .where(PriceDaily.trade_date == resolved_base_date)
                )
                if close is None:
                    raise ValueError(
                        f"no price for {h.symbol} on {resolved_base_date}"
                    )
                h = SavedHolding(
                    symbol=h.symbol,
                    name=h.name,
                    weight=h.weight,
                    base_price=close,
                )
            enriched_holdings.append(h)

        row = SavedPortfolio(
            style=payload.style,
            label=payload.label,
            note=payload.note,
            holdings_json=_holdings_to_json(enriched_holdings),
            base_date=resolved_base_date,
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
