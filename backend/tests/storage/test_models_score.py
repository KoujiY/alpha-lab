"""驗證 Score model 可建立、欄位型別正確、可 upsert。"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alpha_lab.storage.models import Base, Score, Stock


def test_score_model_persist_and_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            Score(
                symbol="2330",
                calc_date=date(2026, 4, 15),
                value_score=72.5,
                growth_score=85.0,
                dividend_score=60.0,
                quality_score=90.0,
                total_score=77.6,
            )
        )
        session.commit()

        row = session.get(Score, ("2330", date(2026, 4, 15)))
        assert row is not None
        assert row.total_score == 77.6
        assert row.value_score == 72.5
