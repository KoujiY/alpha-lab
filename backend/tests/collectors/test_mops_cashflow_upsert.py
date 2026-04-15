"""upsert_cashflow 單元測試：寫入 / 覆寫既有 cashflow 列。"""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alpha_lab.collectors.mops_cashflow import Cashflow, upsert_cashflow
from alpha_lab.storage.models import Base, FinancialStatement, Stock


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_upsert_cashflow_inserts_row() -> None:
    session = _make_session()
    session.add(Stock(symbol="2330", name="台積電"))
    session.commit()

    cf: Cashflow = {
        "operating_cf": 1000,
        "investing_cf": -500,
        "financing_cf": -200,
    }
    n = upsert_cashflow(session, "2330", "2026Q1", cf)
    session.commit()

    assert n == 1
    row = session.execute(
        select(FinancialStatement).where(
            FinancialStatement.symbol == "2330",
            FinancialStatement.period == "2026Q1",
            FinancialStatement.statement_type == "cashflow",
        )
    ).scalar_one()
    assert row.operating_cf == 1000
    assert row.investing_cf == -500
    assert row.financing_cf == -200


def test_upsert_cashflow_overwrites_existing() -> None:
    session = _make_session()
    session.add(Stock(symbol="2330", name="台積電"))
    session.commit()

    upsert_cashflow(
        session,
        "2330",
        "2026Q1",
        {"operating_cf": 100, "investing_cf": -50, "financing_cf": -20},
    )
    session.commit()
    upsert_cashflow(
        session,
        "2330",
        "2026Q1",
        {"operating_cf": 999, "investing_cf": -111, "financing_cf": -55},
    )
    session.commit()

    rows = session.execute(
        select(FinancialStatement).where(
            FinancialStatement.symbol == "2330",
            FinancialStatement.period == "2026Q1",
            FinancialStatement.statement_type == "cashflow",
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].operating_cf == 999


def test_upsert_cashflow_creates_stock_placeholder() -> None:
    """無預先 Stock 應自動建 placeholder。"""
    session = _make_session()
    upsert_cashflow(
        session,
        "9999",
        "2026Q1",
        {"operating_cf": 1, "investing_cf": 2, "financing_cf": 3},
    )
    session.commit()

    stock = session.get(Stock, "9999")
    assert stock is not None
