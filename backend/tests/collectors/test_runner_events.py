"""重大訊息 upsert 測試。"""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_events
from alpha_lab.schemas.event import Event
from alpha_lab.storage.models import Base, Stock
from alpha_lab.storage.models import Event as EventRow


def test_upsert_events_inserts_new_and_skips_duplicate() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        events = [
            Event(
                symbol="2330",
                event_datetime=datetime(2026, 4, 10, 14, 30, 20),
                event_type="第五款",
                title="配息案",
                content="每股 11 元",
            ),
        ]
        assert upsert_events(session, events) == 1
        session.commit()
        assert session.query(EventRow).count() == 1

        # 再次 upsert 同一則 → 不新增
        assert upsert_events(session, events) == 0
        session.commit()
        assert session.query(EventRow).count() == 1


def test_upsert_events_different_datetime_creates_new_row() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        events = [
            Event(
                symbol="2330",
                event_datetime=datetime(2026, 4, 10, 14, 30, 20),
                event_type="第五款",
                title="A",
                content="",
            ),
            Event(
                symbol="2330",
                event_datetime=datetime(2026, 4, 11, 9, 0, 0),
                event_type="第五款",
                title="A",
                content="",
            ),
        ]
        assert upsert_events(session, events) == 2
        session.commit()
        assert session.query(EventRow).count() == 2
