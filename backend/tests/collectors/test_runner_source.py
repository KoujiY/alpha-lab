"""upsert_daily_prices 對 source 欄位的行為。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.collectors.runner import upsert_daily_prices
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.storage.models import Base, PriceDaily


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)()


def test_upsert_writes_source(session: Session) -> None:
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                open=700.0,
                high=705.0,
                low=698.0,
                close=702.0,
                volume=1_000_000,
                source="twse",
            )
        ],
    )
    session.commit()
    row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
    assert row is not None
    assert row.source == "twse"


def test_upsert_yahoo_source(session: Session) -> None:
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 2),
                open=700.0,
                high=705.0,
                low=698.0,
                close=702.0,
                volume=1_000_000,
                source="yahoo",
            )
        ],
    )
    session.commit()
    row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 2)})
    assert row is not None
    assert row.source == "yahoo"


def test_upsert_none_source_does_not_overwrite_existing(session: Session) -> None:
    """既有 row 已有 source，新 row source=None 時不可覆寫為 null。"""
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 3),
                open=700.0, high=705.0, low=698.0, close=702.0,
                volume=1_000_000, source="twse",
            )
        ],
    )
    session.commit()
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 3),
                open=701.0, high=706.0, low=699.0, close=703.0,
                volume=1_100_000, source=None,
            )
        ],
    )
    session.commit()
    row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 3)})
    assert row is not None
    assert row.close == 703.0  # OHLCV 有被更新
    assert row.source == "twse"  # source 未被 overwrite 為 null
