"""季報三表 upsert 測試。"""

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_financial_statements
from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType
from alpha_lab.storage.models import Base, Stock
from alpha_lab.storage.models import FinancialStatement as FSRow


def test_upsert_financial_statements_inserts_three_types() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            FinancialStatement(
                symbol="2330",
                period="2026Q1",
                statement_type=StatementType.INCOME,
                revenue=300_000_000,
                net_income=100_000_000,
                eps=10.5,
                raw_json={"a": 1},
            ),
            FinancialStatement(
                symbol="2330",
                period="2026Q1",
                statement_type=StatementType.BALANCE,
                total_assets=5_000_000_000,
                total_liabilities=1_500_000_000,
                total_equity=3_500_000_000,
                raw_json={"b": 2},
            ),
            FinancialStatement(
                symbol="2330",
                period="2026Q1",
                statement_type=StatementType.CASHFLOW,
                operating_cf=150_000_000,
                investing_cf=-80_000_000,
                financing_cf=-40_000_000,
                raw_json={"c": 3},
            ),
        ]
        assert upsert_financial_statements(session, rows) == 3
        session.commit()
        assert session.query(FSRow).count() == 3

        income_row = session.get(
            FSRow,
            {"symbol": "2330", "period": "2026Q1", "statement_type": "income"},
        )
        assert income_row is not None
        assert json.loads(income_row.raw_json_text) == {"a": 1}


def test_upsert_financial_statements_updates_existing() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, future=True)

    with session_local() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        assert (
            upsert_financial_statements(
                session,
                [
                    FinancialStatement(
                        symbol="2330",
                        period="2026Q1",
                        statement_type=StatementType.INCOME,
                        revenue=100,
                        raw_json={"v": 1},
                    ),
                ],
            )
            == 1
        )
        session.commit()

        assert (
            upsert_financial_statements(
                session,
                [
                    FinancialStatement(
                        symbol="2330",
                        period="2026Q1",
                        statement_type=StatementType.INCOME,
                        revenue=200,
                        raw_json={"v": 2},
                    ),
                ],
            )
            == 1
        )
        session.commit()

        row = session.get(
            FSRow,
            {"symbol": "2330", "period": "2026Q1", "statement_type": "income"},
        )
        assert row is not None
        assert row.revenue == 200
        assert json.loads(row.raw_json_text) == {"v": 2}
