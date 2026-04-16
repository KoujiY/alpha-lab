"""Reports service：update / delete / search 測試（Phase 6）。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from alpha_lab.reports.service import (
    create_report,
    delete_report,
    list_reports,
    update_report,
)
from alpha_lab.schemas.report import ReportCreate, ReportUpdate


@pytest.fixture(autouse=True)
def _reports_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))
    return tmp_path


def _make_stock_report(date_: date, title: str, symbols: list[str]) -> str:
    meta = create_report(
        ReportCreate(
            type="stock",
            title=title,
            body_markdown="## body\n",
            summary_line=f"summary-{title}",
            symbols=symbols,
            tags=["tag-a"],
            subject=symbols[0],
            date=date_,
        )
    )
    return meta.id


def test_update_report_toggles_starred(_reports_root: Path) -> None:
    rid = _make_stock_report(date(2026, 4, 17), "T", ["2330"])
    updated = update_report(rid, ReportUpdate(starred=True))
    assert updated is not None
    assert updated.starred is True


def test_update_report_returns_none_for_unknown(_reports_root: Path) -> None:
    assert update_report("nope", ReportUpdate(starred=True)) is None


def test_delete_report_removes_file_and_index(_reports_root: Path) -> None:
    rid = _make_stock_report(date(2026, 4, 17), "T", ["2330"])
    assert delete_report(rid) is True
    assert all(m.id != rid for m in list_reports())
    assert delete_report(rid) is False


def test_list_reports_query_matches_title_summary_symbols_tags(
    _reports_root: Path,
) -> None:
    _make_stock_report(date(2026, 4, 17), "TSMC 分析", ["2330"])
    _make_stock_report(date(2026, 4, 17), "鴻海深度", ["2317"])
    hits = list_reports(query="TSMC")
    assert len(hits) == 1
    assert hits[0].title == "TSMC 分析"
    hits2 = list_reports(query="2317")
    assert len(hits2) == 1


def test_list_reports_symbol_filter(_reports_root: Path) -> None:
    _make_stock_report(date(2026, 4, 17), "TSMC", ["2330"])
    _make_stock_report(date(2026, 4, 17), "HHP", ["2317"])
    hits = list_reports(symbol="2330")
    assert len(hits) == 1
