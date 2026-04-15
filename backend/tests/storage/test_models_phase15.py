"""Phase 1.5 新 models 結構測試。"""

import json
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage.models import (
    Base,
    Event,
    FinancialStatement,
    InstitutionalTrade,
    MarginTrade,
    Stock,
)


def test_new_tables_registered() -> None:
    expected = {
        "institutional_trades",
        "margin_trades",
        "events",
        "financial_statements",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_insert_institutional_trade() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            InstitutionalTrade(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                foreign_net=1000000,
                trust_net=-500000,
                dealer_net=100000,
                total_net=600000,
            )
        )
        session.commit()
        assert session.query(InstitutionalTrade).count() == 1


def test_insert_margin_trade() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            MarginTrade(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                margin_balance=10000,
                margin_buy=500,
                margin_sell=400,
                short_balance=200,
                short_sell=50,
                short_cover=30,
            )
        )
        session.commit()
        assert session.query(MarginTrade).count() == 1


def test_insert_event_autoincrement_id() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        ev = Event(
            symbol="2330",
            event_datetime=datetime(2026, 4, 1, 14, 30, tzinfo=UTC),
            event_type="董事會決議",
            title="通過配息案",
            content="...",
        )
        session.add(ev)
        session.commit()
        assert ev.id is not None


def test_insert_financial_statement_with_raw_json() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            FinancialStatement(
                symbol="2330",
                period="2026Q1",
                statement_type="income",
                revenue=300000000,
                net_income=100000000,
                eps=10.5,
                raw_json_text=json.dumps({"custom_field": 1}),
            )
        )
        session.commit()
        assert session.query(FinancialStatement).count() == 1
