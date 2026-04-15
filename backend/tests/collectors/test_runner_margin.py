"""融資融券 upsert 測試。"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_margin_trades
from alpha_lab.schemas.margin import MarginTrade
from alpha_lab.storage.models import Base, Stock
from alpha_lab.storage.models import MarginTrade as MTRow


def test_upsert_margin_trades_inserts_and_updates() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            MarginTrade(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                margin_buy=500,
                margin_sell=400,
                margin_balance=10200,
                short_sell=50,
                short_cover=30,
                short_balance=200,
            ),
        ]
        assert upsert_margin_trades(session, rows) == 1
        session.commit()
        assert session.query(MTRow).count() == 1

        rows2 = [
            MarginTrade(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                margin_buy=600,
                margin_sell=450,
                margin_balance=10350,
                short_sell=60,
                short_cover=40,
                short_balance=220,
            ),
        ]
        assert upsert_margin_trades(session, rows2) == 1
        session.commit()
        r = session.get(
            MTRow, {"symbol": "2330", "trade_date": date(2026, 4, 1)}
        )
        assert r is not None
        assert r.margin_balance == 10350
