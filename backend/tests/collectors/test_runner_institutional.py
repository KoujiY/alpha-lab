"""三大法人 upsert 測試。"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_institutional_trades
from alpha_lab.schemas.institutional import InstitutionalTrade
from alpha_lab.storage.models import Base, Stock
from alpha_lab.storage.models import InstitutionalTrade as ITRow


def test_upsert_institutional_trades_inserts_and_updates() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            InstitutionalTrade(
                symbol="2330", trade_date=date(2026, 4, 1),
                foreign_net=1000, trust_net=-500, dealer_net=100, total_net=600,
            ),
        ]
        n = upsert_institutional_trades(session, rows)
        session.commit()
        assert n == 1
        assert session.query(ITRow).count() == 1

        # 同 symbol + date → update
        rows2 = [
            InstitutionalTrade(
                symbol="2330", trade_date=date(2026, 4, 1),
                foreign_net=2000, trust_net=-1000, dealer_net=200, total_net=1200,
            ),
        ]
        n2 = upsert_institutional_trades(session, rows2)
        session.commit()
        assert n2 == 1
        assert session.query(ITRow).count() == 1
        row = session.get(ITRow, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
        assert row is not None
        assert row.foreign_net == 2000
