from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alpha_lab.analysis.pipeline import score_all
from alpha_lab.storage.models import (
    Base,
    FinancialStatement,
    PriceDaily,
    RevenueMonthly,
    Score,
    Stock,
)


def _seed(session: Session) -> None:
    for sym, name in [("2330", "台積電"), ("2454", "聯發科"), ("1301", "台塑")]:
        session.add(Stock(symbol=sym, name=name))
        session.add(
            PriceDaily(
                symbol=sym,
                trade_date=date(2026, 4, 15),
                open=100,
                high=110,
                low=95,
                close=105,
                volume=1000,
            )
        )
        for q_idx, period in enumerate(
            [
                "2026Q1",
                "2025Q4",
                "2025Q3",
                "2025Q2",
                "2025Q1",
                "2024Q4",
                "2024Q3",
                "2024Q2",
            ]
        ):
            session.add(
                FinancialStatement(
                    symbol=sym,
                    period=period,
                    statement_type="income",
                    revenue=100 + q_idx,
                    gross_profit=30,
                    net_income=20,
                    eps=2.0 if sym == "2330" else 1.0,
                )
            )
        session.add(
            FinancialStatement(
                symbol=sym,
                period="2026Q1",
                statement_type="balance",
                total_assets=1000,
                total_liabilities=400,
                total_equity=600,
            )
        )
        for year in (2025, 2026):
            for month in range(1, 13):
                session.add(
                    RevenueMonthly(
                        symbol=sym, year=year, month=month, revenue=10 + month
                    )
                )
    session.commit()


def test_score_all_writes_scores() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed(session)
        written = score_all(session, date(2026, 4, 15))
        assert written == 3

        rows = session.execute(select(Score)).scalars().all()
        assert len(rows) == 3
        row_2330 = next(r for r in rows if r.symbol == "2330")
        assert row_2330.value_score == 100.0
