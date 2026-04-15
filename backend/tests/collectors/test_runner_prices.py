"""日股價 upsert 測試（含 fresh-symbol 回歸測試）。"""

from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_daily_prices
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.storage.models import Base, PriceDaily, Stock


def test_upsert_daily_prices_with_fresh_symbol_no_integrity_error() -> None:
    """回歸：symbol 不在 stocks 時，多筆 rows 不得觸發 UNIQUE 衝突。

    Bug 原因：原實作在每一筆 row 的迴圈裡呼叫 `_ensure_stock`，
    當同一 symbol 出現在多筆 rows 且該 symbol 尚未 flush 到 DB，
    第二次 `session.get` 未必能看到 pending placeholder，結果
    重複 `session.add(Stock(...))`，commit/flush 時就撞到
    `UNIQUE constraint failed: stocks.symbol`。
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        # 刻意不預先 seed stocks 表
        base = date(2025, 4, 1)
        rows = [
            DailyPrice(
                symbol="0050",
                trade_date=base + timedelta(days=i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1_000_000 + i,
            )
            for i in range(20)
        ]
        n = upsert_daily_prices(session, rows)
        session.commit()

        assert n == 20
        assert session.query(PriceDaily).count() == 20
        stock = session.get(Stock, "0050")
        assert stock is not None
        assert stock.symbol == "0050"


def test_upsert_daily_prices_multiple_symbols_fresh() -> None:
    """多個 fresh symbols 混雜也不應出錯。"""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        rows = [
            DailyPrice(
                symbol=sym,
                trade_date=date(2025, 4, 1),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1_000_000,
            )
            for sym in ["0050", "2330", "0050", "2317", "2330"]
        ]
        n = upsert_daily_prices(session, rows)
        session.commit()
        assert n == 5
        assert session.query(Stock).count() == 3
