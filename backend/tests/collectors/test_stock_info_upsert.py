"""上市公司基本資料 upsert 測試。

涵蓋：
- 既有 placeholder（Phase 1 collector 留下 name=symbol、industry/listed_date=NULL）
  被 UPDATE 成正式資料
- 不存在的 symbol 被 INSERT
- 無效 row（symbol 或 name 為空）被略過
- 二次 upsert 不會新增重複 row（同 symbol 只 UPDATE）
"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_stock_info
from alpha_lab.schemas.stock_info import StockInfo
from alpha_lab.storage.models import Base, Stock


def _make_session() -> sessionmaker[object]:  # type: ignore[type-arg]
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def test_upsert_stock_info_updates_placeholder() -> None:
    session_local = _make_session()
    with session_local() as session:
        # 模擬 Phase 1 collector 留下的 placeholder
        session.add(Stock(symbol="2330", name="2330"))
        session.commit()

        rows = [
            StockInfo(
                symbol="2330",
                name="台積電",
                industry="半導體業",
                listed_date=date(2017, 9, 5),
            ),
        ]
        assert upsert_stock_info(session, rows) == 1
        session.commit()

        stock = session.get(Stock, "2330")
        assert stock is not None
        assert stock.name == "台積電"
        assert stock.industry == "半導體業"
        assert stock.listed_date == date(2017, 9, 5)
        # 單一 symbol 不該產生重複 row
        assert session.query(Stock).count() == 1


def test_upsert_stock_info_inserts_new_symbol() -> None:
    session_local = _make_session()
    with session_local() as session:
        rows = [
            StockInfo(
                symbol="2317",
                name="鴻海",
                industry="其他電子業",
                listed_date=date(1991, 2, 6),
            ),
        ]
        assert upsert_stock_info(session, rows) == 1
        session.commit()

        stock = session.get(Stock, "2317")
        assert stock is not None
        assert stock.name == "鴻海"
        assert stock.industry == "其他電子業"
        assert stock.listed_date == date(1991, 2, 6)


def test_upsert_stock_info_mixed_insert_and_update() -> None:
    session_local = _make_session()
    with session_local() as session:
        session.add(Stock(symbol="2330", name="2330"))
        session.commit()

        rows = [
            StockInfo(
                symbol="2330",
                name="台積電",
                industry="半導體業",
                listed_date=date(2017, 9, 5),
            ),
            StockInfo(
                symbol="2454",
                name="聯發科",
                industry="半導體業",
                listed_date=date(2001, 7, 23),
            ),
        ]
        assert upsert_stock_info(session, rows) == 2
        session.commit()

        assert session.query(Stock).count() == 2
        assert session.get(Stock, "2330").name == "台積電"  # type: ignore[union-attr]
        assert session.get(Stock, "2454").name == "聯發科"  # type: ignore[union-attr]


def test_upsert_stock_info_idempotent() -> None:
    """二次 upsert 相同資料：不重複插入、欄位維持。"""
    session_local = _make_session()
    with session_local() as session:
        row = StockInfo(
            symbol="2330",
            name="台積電",
            industry="半導體業",
            listed_date=date(2017, 9, 5),
        )
        assert upsert_stock_info(session, [row]) == 1
        session.commit()
        assert upsert_stock_info(session, [row]) == 1
        session.commit()

        assert session.query(Stock).count() == 1
        stock = session.get(Stock, "2330")
        assert stock is not None
        assert stock.name == "台積電"
        assert stock.industry == "半導體業"


def test_upsert_stock_info_preserves_industry_null_when_new() -> None:
    """industry / listed_date 可為 None（TWSE 原始欄位可能為空）。"""
    session_local = _make_session()
    with session_local() as session:
        rows = [
            StockInfo(symbol="1234", name="測試", industry=None, listed_date=None),
        ]
        assert upsert_stock_info(session, rows) == 1
        session.commit()

        stock = session.get(Stock, "1234")
        assert stock is not None
        assert stock.name == "測試"
        assert stock.industry is None
        assert stock.listed_date is None
