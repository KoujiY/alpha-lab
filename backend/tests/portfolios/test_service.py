"""Saved portfolio service 單元測試（Phase 6）。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.portfolios.service import (
    compute_performance,
    delete_saved,
    get_saved,
    list_saved,
    probe_base_date,
    save_portfolio,
)
from alpha_lab.schemas.saved_portfolio import SavedHolding, SavedPortfolioCreate
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, PriceDaily, SavedPortfolio, Stock


def _make_test_engine() -> Engine:
    return create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


@pytest.fixture(autouse=True)
def _isolated_engine():
    """每個測試都用獨立 in-memory SQLite engine，避免碰到真正的 data/alpha_lab.db。"""

    _override_engine(_make_test_engine())
    yield


@pytest.fixture
def sample_prices():
    """Seed 兩檔股票的 base_date 收盤價。"""

    with session_scope() as session:
        for sym, name, close in [("2330", "台積電", 600.0), ("2317", "鴻海", 100.0)]:
            session.merge(Stock(symbol=sym, name=name))
            session.merge(
                PriceDaily(
                    symbol=sym,
                    trade_date=date(2026, 4, 17),
                    open=close, high=close, low=close, close=close,
                    volume=1000,
                )
            )
    yield


def test_save_portfolio_persists_holdings(sample_prices):
    payload = SavedPortfolioCreate(
        style="balanced",
        label="Apr 平衡組",
        holdings=[
            SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
            SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
        ],
    )
    meta = save_portfolio(payload, base_date=date(2026, 4, 17))
    assert meta.id > 0
    assert meta.holdings_count == 2
    assert meta.base_date == date(2026, 4, 17)


def test_list_saved_returns_newest_first(sample_prices):
    save_portfolio(
        SavedPortfolioCreate(
            style="conservative", label="older",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 15),
    )
    newer = save_portfolio(
        SavedPortfolioCreate(
            style="aggressive", label="newer",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    items = list_saved()
    assert items[0].id == newer.id


def test_delete_saved_removes_row(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="to-delete",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    assert delete_saved(meta.id) is True
    assert delete_saved(meta.id) is False
    assert all(m.id != meta.id for m in list_saved())


def test_compute_performance_tracks_nav(sample_prices):
    # 4/17 以 600 / 100 為基準，之後價格變化看 NAV 是否對
    with session_scope() as session:
        for d, close_2330, close_2317 in [
            (date(2026, 4, 18), 630.0, 105.0),  # +5% / +5% → NAV 1.05
            (date(2026, 4, 21), 660.0, 110.0),  # +10% / +10% → NAV 1.10
        ]:
            for sym, close in [("2330", close_2330), ("2317", close_2317)]:
                session.merge(
                    PriceDaily(
                        symbol=sym,
                        trade_date=d,
                        open=close, high=close, low=close, close=close,
                        volume=1000,
                    )
                )

    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="perf",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
                SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
            ],
        ),
        base_date=date(2026, 4, 17),
    )
    resp = compute_performance(meta.id)
    assert resp is not None
    # base day + 2 個交易日 = 3 points
    assert len(resp.points) == 3
    assert resp.points[0].nav == pytest.approx(1.0)
    assert resp.points[1].nav == pytest.approx(1.05, rel=1e-4)
    assert resp.points[2].nav == pytest.approx(1.10, rel=1e-4)
    assert resp.total_return == pytest.approx(0.10, rel=1e-4)


def test_compute_performance_missing_price_skips_day(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="missing",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    # 只有 base_date 有價格，後面沒有 → 僅 1 個 point
    resp = compute_performance(meta.id)
    assert resp is not None
    assert len(resp.points) == 1
    assert resp.latest_nav == pytest.approx(1.0)


def test_compute_performance_returns_none_for_unknown_id():
    assert compute_performance(99999) is None


def test_save_portfolio_fills_base_price_from_prices_daily(sample_prices):
    # base_price=0 → 由 service 查 prices_daily 回填
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="auto-base-price",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=0.0),
            ],
        ),
        base_date=date(2026, 4, 17),
    )
    detail = get_saved(meta.id)
    assert detail is not None
    assert detail.holdings[0].base_price == pytest.approx(600.0)


def test_save_portfolio_raises_when_base_price_missing(sample_prices):
    # 股票在 prices_daily 中沒資料 → raise ValueError
    with pytest.raises(ValueError, match="no price"):
        save_portfolio(
            SavedPortfolioCreate(
                style="balanced",
                label="no-price",
                holdings=[
                    SavedHolding(symbol="9999", name="NOPE", weight=1.0, base_price=0.0),
                ],
            ),
            base_date=date(2026, 4, 17),
        )


def test_save_portfolio_strict_fails_when_today_missing(sample_prices):
    # sample_prices 只有 4/17；用 4/18 strict save 應該失敗
    with pytest.raises(ValueError, match="no price"):
        save_portfolio(
            SavedPortfolioCreate(
                style="balanced",
                label="strict",
                holdings=[
                    SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=0.0),
                ],
            ),
            base_date=date(2026, 4, 18),
        )


def test_save_portfolio_allow_fallback_uses_latest_common_date(sample_prices):
    # sample_prices 只有 4/17；base_date=4/20 + allow_fallback → 退到 4/17
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="fallback",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=0.0),
                SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=0.0),
            ],
        ),
        base_date=date(2026, 4, 20),
        allow_fallback=True,
    )
    assert meta.base_date == date(2026, 4, 17)
    detail = get_saved(meta.id)
    assert detail is not None
    assert detail.holdings[0].base_price == pytest.approx(600.0)
    assert detail.holdings[1].base_price == pytest.approx(100.0)


def test_save_portfolio_allow_fallback_raises_when_no_common_date(sample_prices):
    # 9999 完全無報價，allow_fallback 也救不了
    with pytest.raises(ValueError, match="no common trade_date"):
        save_portfolio(
            SavedPortfolioCreate(
                style="balanced",
                label="no-common",
                holdings=[
                    SavedHolding(symbol="9999", name="NOPE", weight=1.0, base_price=0.0),
                ],
            ),
            base_date=date(2026, 4, 17),
            allow_fallback=True,
        )


def test_probe_base_date_returns_today_when_all_present(sample_prices):
    resolved, missing = probe_base_date(["2330", "2317"], date(2026, 4, 17))
    assert resolved == date(2026, 4, 17)
    assert missing == []


def test_probe_base_date_reports_missing_today(sample_prices):
    resolved, missing = probe_base_date(["2330", "2317"], date(2026, 4, 18))
    assert resolved == date(2026, 4, 17)
    assert sorted(missing) == ["2317", "2330"]


def test_probe_base_date_returns_none_when_no_history(sample_prices):
    resolved, missing = probe_base_date(["9999"], date(2026, 4, 17))
    assert resolved is None
    assert missing == ["9999"]


def test_save_portfolio_with_parent_stores_lineage(sample_prices):
    parent = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="parent",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    # parent 當下 latest_nav（僅 base_date 一個 point）= 1.0
    child = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="child",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
                SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
            ],
            parent_id=parent.id,
        ),
        base_date=date(2026, 4, 17),
    )
    detail = get_saved(child.id)
    assert detail is not None
    assert detail.parent_id == parent.id
    assert detail.parent_nav_at_fork == pytest.approx(1.0)


def test_save_portfolio_with_nonexistent_parent_raises(sample_prices):
    with pytest.raises(ValueError, match=r"parent portfolio .* not found"):
        save_portfolio(
            SavedPortfolioCreate(
                style="balanced",
                label="orphan",
                holdings=[
                    SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)
                ],
                parent_id=99999,
            ),
            base_date=date(2026, 4, 17),
        )


def test_save_portfolio_parent_nav_snapshot_reflects_latest_prices(sample_prices):
    # 先建 parent，再給 parent 的後續交易日加價，driven parent latest_nav
    parent = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="p2",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 18),
                open=660.0, high=660.0, low=660.0, close=660.0,
                volume=1000,
            )
        )

    child = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="c2",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=660.0)],
            parent_id=parent.id,
        ),
        base_date=date(2026, 4, 18),
    )
    detail = get_saved(child.id)
    assert detail is not None
    # parent 從 600 -> 660 = 1.10
    assert detail.parent_nav_at_fork == pytest.approx(1.10, rel=1e-4)


def test_compute_performance_returns_parent_points_when_forked(sample_prices):
    # parent: 4/17 買入 2330@600，4/18 -> 660（NAV 1.10）
    # child: 4/18 fork，parent_nav_at_fork=1.10
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330", trade_date=date(2026, 4, 18),
                open=660.0, high=660.0, low=660.0, close=660.0, volume=1000,
            )
        )
    parent = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="parent",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    child = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="child",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=660.0)],
            parent_id=parent.id,
        ),
        base_date=date(2026, 4, 18),
    )
    resp = compute_performance(child.id)
    assert resp is not None
    assert resp.parent_nav_at_fork == pytest.approx(1.10, rel=1e-4)
    # parent_points 應該只含 < 4/18 的日期（即 4/17）
    assert resp.parent_points is not None
    assert len(resp.parent_points) == 1
    assert resp.parent_points[0].date == date(2026, 4, 17)
    assert resp.parent_points[0].nav == pytest.approx(1.0)


def test_compute_performance_without_parent_has_no_parent_points(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="solo",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    resp = compute_performance(meta.id)
    assert resp is not None
    assert resp.parent_points is None
    assert resp.parent_nav_at_fork is None


def test_compute_performance_raises_on_parent_cycle(sample_prices):
    # 建兩個組合，用 session 手動把 parent_id 改成互指，模擬人為錯誤寫入
    a = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="a",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    b = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="b",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
            parent_id=a.id,
        ),
        base_date=date(2026, 4, 17),
    )
    with session_scope() as session:
        row_a = session.get(SavedPortfolio, a.id)
        assert row_a is not None
        row_a.parent_id = b.id  # a -> b -> a 形成 cycle

    with pytest.raises(ValueError, match="parent cycle detected"):
        compute_performance(b.id)
