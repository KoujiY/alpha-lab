"""Section builder 單元測試。"""

from datetime import date

from alpha_lab.briefing.sections import (
    build_events_section,
    build_institutional_section,
    build_market_overview_section,
    build_portfolio_tracking_section,
)


class TestBuildMarketOverviewSection:
    def test_returns_markdown_with_header(self) -> None:
        prices = [
            {"symbol": "2330", "name": "台積電", "close": 850.0, "change": 10.0, "change_pct": 1.19, "volume": 25000},
            {"symbol": "2317", "name": "鴻海", "close": 150.0, "change": -2.0, "change_pct": -1.32, "volume": 18000},
        ]
        result = build_market_overview_section(prices, trade_date=date(2026, 4, 17))
        assert "## 市場概況" in result
        assert "2330" in result
        assert "台積電" in result
        assert "850" in result

    def test_empty_prices_shows_no_data_message(self) -> None:
        result = build_market_overview_section([], trade_date=date(2026, 4, 17))
        assert "## 市場概況" in result
        assert "無資料" in result


class TestBuildInstitutionalSection:
    def test_returns_markdown_with_net_buy_sell(self) -> None:
        inst = [
            {"symbol": "2330", "name": "台積電", "foreign_net": 5000, "trust_net": 1000, "dealer_net": -200, "total_net": 5800},
        ]
        result = build_institutional_section(inst, trade_date=date(2026, 4, 17))
        assert "## 法人動向" in result
        assert "2330" in result
        assert "5,800" in result or "5800" in result

    def test_empty_institutional_shows_no_data(self) -> None:
        result = build_institutional_section([], trade_date=date(2026, 4, 17))
        assert "## 法人動向" in result
        assert "無資料" in result


class TestBuildEventsSection:
    def test_returns_markdown_with_events(self) -> None:
        events = [
            {"symbol": "2330", "title": "董事會決議配息", "event_type": "股利", "event_datetime": "2026-04-17 14:30"},
            {"symbol": "2317", "title": "合併案公告", "event_type": "重組", "event_datetime": "2026-04-17 10:00"},
        ]
        result = build_events_section(events)
        assert "## 重大訊息" in result
        assert "2330" in result
        assert "董事會決議配息" in result

    def test_empty_events_shows_no_data(self) -> None:
        result = build_events_section([])
        assert "## 重大訊息" in result
        assert "無資料" in result


class TestBuildPortfolioTrackingSection:
    def test_returns_portfolio_summary(self) -> None:
        portfolios = [
            {"id": 1, "label": "保守組", "nav": 1.05, "return_pct": 5.0, "base_date": "2026-04-01"},
        ]
        result = build_portfolio_tracking_section(portfolios)
        assert "## 組合追蹤" in result
        assert "保守組" in result
        assert "5.0" in result or "5.00" in result

    def test_empty_portfolios_shows_no_data(self) -> None:
        result = build_portfolio_tracking_section([])
        assert "## 組合追蹤" in result
        assert "無儲存的組合" in result
