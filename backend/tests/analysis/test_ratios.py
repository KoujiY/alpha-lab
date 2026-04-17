"""基本面比率模組測試。`compute_ratios` 從 DB session 拉資料算。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.analysis.ratios import compute_ratios
from alpha_lab.storage.models import Base, FinancialStatement, PriceDaily, Stock


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)()


def _seed_financials(s: Session, symbol: str):
    s.add(Stock(symbol=symbol, name=symbol))
    # 兩年 income：近四季 + 前四季
    quarters = ["2026Q1", "2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2"]
    for q in quarters:
        s.add(FinancialStatement(
            symbol=symbol, period=q, statement_type="income",
            revenue=1_000_000, gross_profit=300_000, operating_income=200_000,
            net_income=150_000, eps=5.0,
        ))
    s.add(FinancialStatement(
        symbol=symbol, period="2026Q1", statement_type="balance",
        total_assets=10_000_000, total_liabilities=4_000_000, total_equity=6_000_000,
    ))
    s.add(PriceDaily(
        symbol=symbol, trade_date=date(2026, 4, 1),
        open=100.0, high=105.0, low=98.0, close=100.0, volume=1_000_000,
    ))
    s.commit()


def test_compute_ratios_pe_roe(session: Session):
    _seed_financials(session, "2330")
    r = compute_ratios(session, "2330", as_of=date(2026, 4, 1))
    # EPS TTM = 5 * 4 = 20；close=100 → PE=5
    assert r.pe == pytest.approx(5.0)
    # ROE = net_income TTM (150k*4=600k) / equity (6M) ≈ 0.1
    assert r.roe == pytest.approx(0.1)
    # gross margin TTM = 300k*4 / 1M*4 = 0.3
    assert r.gross_margin == pytest.approx(0.3)
    # debt_ratio = 4M / 10M = 0.4
    assert r.debt_ratio == pytest.approx(0.4)


def test_compute_ratios_no_financials_returns_nones(session: Session):
    session.add(Stock(symbol="XXXX", name="XXXX"))
    session.commit()
    r = compute_ratios(session, "XXXX", as_of=date(2026, 4, 1))
    assert r.pe is None
    assert r.roe is None
