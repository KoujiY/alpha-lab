"""Daily briefing assembler 測試（用 in-memory DB）。"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.briefing.daily import build_daily_briefing
from alpha_lab.storage.models import (
    Base,
    Event,
    InstitutionalTrade,
    PriceDaily,
    Stock,
)


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        session.add(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 17),
                open=840.0,
                high=855.0,
                low=838.0,
                close=850.0,
                volume=25000,
            )
        )
        session.add(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 16),
                open=835.0,
                high=842.0,
                low=833.0,
                close=840.0,
                volume=20000,
            )
        )
        session.add(
            InstitutionalTrade(
                symbol="2330",
                trade_date=date(2026, 4, 17),
                foreign_net=5000,
                trust_net=1000,
                dealer_net=-200,
                total_net=5800,
            )
        )
        session.add(
            Event(
                symbol="2330",
                event_datetime=datetime(2026, 4, 17, 14, 30),
                event_type="股利",
                title="董事會決議配息",
                content="每股配息 3 元",
            )
        )
        session.commit()
    return factory


class TestBuildDailyBriefing:
    def test_returns_complete_markdown(self, session_factory) -> None:
        md = build_daily_briefing(session_factory, trade_date=date(2026, 4, 17))
        assert "# 每日市場簡報" in md
        assert "## 市場概況" in md
        assert "## 法人動向" in md
        assert "## 重大訊息" in md
        assert "2330" in md
        assert "台積電" in md

    def test_price_change_calculated(self, session_factory) -> None:
        md = build_daily_briefing(session_factory, trade_date=date(2026, 4, 17))
        assert "850.00" in md
        assert "+10.00" in md

    def test_no_data_date_still_produces_report(self, session_factory) -> None:
        md = build_daily_briefing(session_factory, trade_date=date(2026, 1, 1))
        assert "# 每日市場簡報" in md
        assert "無資料" in md
