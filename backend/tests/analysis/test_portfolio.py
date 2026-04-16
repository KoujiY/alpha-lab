from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alpha_lab.analysis.portfolio import generate_portfolio, latest_calc_date
from alpha_lab.storage.models import Base, Score, Stock


def _seed_scores(session: Session, n: int) -> None:
    for i in range(n):
        sym = f"A{i:03d}"
        session.add(Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 3}"))
        session.add(
            Score(
                symbol=sym,
                calc_date=date(2026, 4, 15),
                value_score=50 + i,
                growth_score=50 + i,
                dividend_score=50 + i,
                quality_score=50 + i,
                total_score=50 + i,
            )
        )
    session.commit()


def test_latest_calc_date() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        _seed_scores(s, 3)
        assert latest_calc_date(s) == date(2026, 4, 15)


def test_generate_portfolio_balanced_is_top_pick() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        _seed_scores(s, 12)
        p = generate_portfolio(s, "balanced", date(2026, 4, 15))
        assert p.is_top_pick is True
        assert p.style == "balanced"
        assert len(p.holdings) <= 10
        assert abs(sum(h.weight for h in p.holdings) - 1.0) < 1e-3
        assert all(h.weight <= 0.30 + 1e-6 for h in p.holdings)
        # Phase 4: 每檔 holding 至少有 style 特性句
        assert all(len(h.reasons) >= 1 for h in p.holdings)
        assert all(
            "平衡組" in h.reasons[0] for h in p.holdings
        ), "balanced 組的第一條理由應含「平衡組」字樣"


def test_generate_portfolio_reasons_reflect_style() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        _seed_scores(s, 12)
        conservative = generate_portfolio(s, "conservative", date(2026, 4, 15))
        aggressive = generate_portfolio(s, "aggressive", date(2026, 4, 15))
        assert "保守組" in conservative.holdings[0].reasons[0]
        assert "積極組" in aggressive.holdings[0].reasons[0]


def test_industry_diversification() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for i in range(30):
            sym = f"B{i:03d}"
            s.add(Stock(symbol=sym, name=f"同業{i}", industry="半導體"))
            s.add(
                Score(
                    symbol=sym,
                    calc_date=date(2026, 4, 15),
                    value_score=50 + i,
                    growth_score=50 + i,
                    dividend_score=50 + i,
                    quality_score=50 + i,
                    total_score=50 + i,
                )
            )
        s.commit()
        p = generate_portfolio(s, "balanced", date(2026, 4, 15))
        assert len(p.holdings) == 5
