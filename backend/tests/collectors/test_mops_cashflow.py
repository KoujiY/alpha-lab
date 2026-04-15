"""MOPS t164sb05 cashflow parser 測試。"""

from pathlib import Path

from alpha_lab.collectors.mops_cashflow import parse_cashflow_html


def _fixture_html() -> str:
    return (
        Path(__file__).parent.parent
        / "fixtures"
        / "mops_t164sb05_2330_2026Q1.html"
    ).read_text(encoding="utf-8")


def test_parse_cashflow_all_three_keys_present() -> None:
    result = parse_cashflow_html(_fixture_html())
    assert set(result.keys()) == {"operating_cf", "investing_cf", "financing_cf"}


def test_parse_cashflow_values() -> None:
    result = parse_cashflow_html(_fixture_html())
    assert result["operating_cf"] == 612_345_678
    assert result["investing_cf"] == -234_567_890
    assert result["financing_cf"] == -180_000_000


def test_parse_cashflow_waf_blocked_returns_none() -> None:
    html = (
        "<html><body>THE PAGE CANNOT BE ACCESSED! 頁面無法執行</body></html>"
    )
    result = parse_cashflow_html(html)
    assert result == {
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
    }


def test_parse_cashflow_empty_html() -> None:
    result = parse_cashflow_html("<html><body></body></html>")
    assert result == {
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
    }
