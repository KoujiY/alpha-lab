"""Saved portfolio service（Phase 6）。"""

from __future__ import annotations

import json
import logging
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
    SymbolPriceStatus,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import PortfolioSnapshot, PriceDaily, SavedPortfolio

logger = logging.getLogger(__name__)


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
        parent_id=row.parent_id,
        parent_nav_at_fork=row.parent_nav_at_fork,
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
        parent_id=row.parent_id,
        parent_nav_at_fork=row.parent_nav_at_fork,
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


STALE_THRESHOLD_DAYS = 7


def probe_base_date(
    symbols: list[str], target_date: date_type
) -> tuple[date_type | None, list[str], dict[str, SymbolPriceStatus]]:
    """檢查 target_date 當日哪些 symbols 缺報價，回傳分類狀態。

    回傳 (resolved_date, missing_today_symbols, symbol_statuses)：
    - resolved_date：所有 symbols 都有報價、且 <= target_date 的最大交易日
    - missing_today_symbols：在 target_date 當日缺報價的 symbol 清單
    - symbol_statuses：每個缺報價 symbol 的原因分類
      - "no_data"：該 symbol 在 DB 完全無報價紀錄
      - "stale"：有報價但最新報價距 target_date > 7 天
      - "today_missing"：有近期報價但今日無
    """

    with session_scope() as session:
        resolved = _resolve_common_base_date(session, symbols, target_date)
        missing_today: list[str] = []
        statuses: dict[str, SymbolPriceStatus] = {}
        for sym in symbols:
            has_today = session.scalar(
                select(PriceDaily.trade_date)
                .where(PriceDaily.symbol == sym)
                .where(PriceDaily.trade_date == target_date)
            )
            if has_today is not None:
                continue
            missing_today.append(sym)
            latest = session.scalar(
                select(PriceDaily.trade_date)
                .where(PriceDaily.symbol == sym)
                .where(PriceDaily.trade_date <= target_date)
                .order_by(PriceDaily.trade_date.desc())
                .limit(1)
            )
            if latest is None:
                statuses[sym] = "no_data"
            elif (target_date - latest).days > STALE_THRESHOLD_DAYS:
                statuses[sym] = "stale"
            else:
                statuses[sym] = "today_missing"
        return resolved, missing_today, statuses


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

    Phase 7：若 `payload.parent_id` 非 None，自動查 parent latest_nav 存為
    `parent_nav_at_fork`（讓績效頁能接續畫連續曲線）。parent 不存在則拋 ValueError。
    注意：parent 若尚未有任何報價（全新組合同日 fork），`latest_nav` 預設 1.0，
    `parent_nav_at_fork` 會被記成 1.0；這是刻意行為（NAV 尚未偏離起點）。
    compute_performance 會先寫一筆 parent 的 `portfolio_snapshots`，之後才展開
    child 的 session；這兩步並非單一 transaction，但 snapshots 屬快取，重試 save
    會蓋回。
    """

    parent_nav: float | None = None
    if payload.parent_id is not None:
        parent_perf = compute_performance(payload.parent_id)
        if parent_perf is None:
            raise ValueError(f"parent portfolio {payload.parent_id} not found")
        parent_nav = parent_perf.latest_nav

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
            parent_id=payload.parent_id,
            parent_nav_at_fork=parent_nav,
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


def compute_performance(
    portfolio_id: int, _visited: set[int] | None = None
) -> PerformanceResponse | None:
    """從 base_date 起每日 NAV：sum(weight_i * price_i(t) / base_price_i)。

    只取所有持股都有報價的日期；缺價日直接跳過。
    會同步 upsert 最新一筆到 `portfolio_snapshots`（供之後擴充排程用）。

    Phase 7：若此組合有 parent_id，額外把父組合 `< base_date` 的 NAV points
    附在 `parent_points`；前端可用 `parent_nav_at_fork` 把 self 段縮放後接續繪圖。
    `_visited` 防止 parent 鏈上不該出現的 cycle 導致無窮遞迴（內部用，不公開）。
    """

    visited = set(_visited) if _visited else set()
    if portfolio_id in visited:
        raise ValueError(
            f"parent cycle detected involving portfolio {portfolio_id}"
        )
    visited.add(portfolio_id)

    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return None
        holdings = _holdings_from_json(row.holdings_json)
        symbols = [h.symbol for h in holdings]
        price_map = _load_price_map(session, symbols, row.base_date)

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
        parent_id = row.parent_id
        parent_nav_at_fork = row.parent_nav_at_fork
        child_base_date = row.base_date

    parent_points: list[PerformancePoint] | None = None
    if parent_id is not None:
        parent_resp = compute_performance(parent_id, _visited=visited)
        if parent_resp is None:
            logger.warning(
                "parent portfolio %d missing for child %d; "
                "parent_nav_at_fork remains but parent_points will be None",
                parent_id,
                portfolio_id,
            )
        else:
            parent_points = [
                p for p in parent_resp.points if p.date < child_base_date
            ]

    return PerformanceResponse(
        portfolio=detail,
        points=points,
        latest_nav=latest_nav,
        total_return=total_return,
        parent_points=parent_points,
        parent_nav_at_fork=parent_nav_at_fork,
    )
