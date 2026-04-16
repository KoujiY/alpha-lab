"""Reports storage / service 單元測試。"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from alpha_lab.reports.service import (
    build_portfolio_report_markdown,
    create_portfolio_report,
    create_report,
    get_report,
    list_reports,
)
from alpha_lab.reports.storage import (
    append_summary,
    load_index,
    read_report_markdown,
    upsert_in_index,
    write_report_markdown,
)
from alpha_lab.schemas.portfolio import Holding, Portfolio, RecommendResponse
from alpha_lab.schemas.report import ReportCreate, ReportMeta
from alpha_lab.schemas.score import FactorBreakdown


def _make_recommend_resp() -> RecommendResponse:
    breakdown = FactorBreakdown(
        symbol="2330",
        calc_date=date(2026, 4, 15),
        value_score=80,
        growth_score=70,
        dividend_score=20,
        quality_score=75,
        total_score=62.5,
    )
    return RecommendResponse(
        generated_at=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
        calc_date="2026-04-15",
        portfolios=[
            Portfolio(
                style="balanced",
                label="平衡型",
                is_top_pick=True,
                holdings=[
                    Holding(
                        symbol="2330",
                        name="台積電",
                        weight=1.0,
                        score_breakdown=breakdown,
                        reasons=["價值面亮眼", "股息面偏弱"],
                    )
                ],
            )
        ],
    )


@pytest.fixture(autouse=True)
def _reports_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))
    return tmp_path


def test_write_and_read_markdown_roundtrip(_reports_root: Path) -> None:
    fm = {
        "id": "stock-2330-2026-04-14",
        "type": "stock",
        "title": "台積電深度分析",
        "symbols": ["2330"],
        "tags": ["半導體"],
        "date": "2026-04-14",
        "summary_line": "Q1 亮眼",
    }
    body = "## 執行摘要\n看好。"
    path = write_report_markdown("stock-2330-2026-04-14", body, fm)
    assert path.exists()

    fm_read, body_read = read_report_markdown("stock-2330-2026-04-14")  # type: ignore[misc]
    assert fm_read["id"] == fm["id"]
    assert fm_read["title"] == fm["title"]
    assert fm_read["symbols"] == ["2330"]
    assert body_read == body.strip()


def test_read_missing_report_returns_none(_reports_root: Path) -> None:
    assert read_report_markdown("does-not-exist") is None


def test_upsert_in_index_dedupe_and_sort(_reports_root: Path) -> None:
    m1 = ReportMeta(
        id="stock-2330-2026-04-10",
        type="stock",
        title="t1",
        symbols=["2330"],
        tags=[],
        date=date(2026, 4, 10),
        path="analysis/stock-2330-2026-04-10.md",
    )
    m2 = ReportMeta(
        id="stock-2330-2026-04-14",
        type="stock",
        title="t2",
        symbols=["2330"],
        tags=[],
        date=date(2026, 4, 14),
        path="analysis/stock-2330-2026-04-14.md",
    )
    upsert_in_index(m1)
    upsert_in_index(m2)

    # 覆寫同 id
    m2_updated = m2.model_copy(update={"title": "updated"})
    upsert_in_index(m2_updated)

    items = load_index()
    assert len(items) == 2
    # 新 → 舊
    assert items[0].id == "stock-2330-2026-04-14"
    assert items[0].title == "updated"
    assert items[1].id == "stock-2330-2026-04-10"


def test_append_summary_creates_and_appends(_reports_root: Path) -> None:
    append_summary("2026-04-14", "第一筆")
    append_summary("2026-04-14", "第二筆")
    path = _reports_root / "summaries" / "2026-04-14.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == [{"summary": "第一筆"}, {"summary": "第二筆"}]


def test_create_report_stock_requires_subject(_reports_root: Path) -> None:
    with pytest.raises(ValueError, match="stock report requires subject"):
        create_report(
            ReportCreate(
                type="stock",
                title="x",
                body_markdown="body",
                date=date(2026, 4, 14),
            )
        )


def test_create_report_research_requires_subject(_reports_root: Path) -> None:
    with pytest.raises(ValueError, match="research report requires subject"):
        create_report(
            ReportCreate(
                type="research",
                title="x",
                body_markdown="body",
                date=date(2026, 4, 14),
            )
        )


def test_create_report_portfolio_ok(_reports_root: Path) -> None:
    meta = create_report(
        ReportCreate(
            type="portfolio",
            title="本週推薦",
            body_markdown="## 推薦\n2330",
            summary_line="3 檔推薦",
            tags=["weekly"],
            date=date(2026, 4, 14),
        )
    )
    assert meta.id == "portfolio-2026-04-14"
    assert meta.path == "analysis/portfolio-2026-04-14.md"
    assert meta.date == date(2026, 4, 14)

    # index 有寫入
    items = list_reports()
    assert any(m.id == "portfolio-2026-04-14" for m in items)

    # summary 寫入
    summaries = json.loads(
        (_reports_root / "summaries" / "2026-04-14.json").read_text(encoding="utf-8")
    )
    assert summaries == [{"summary": "3 檔推薦"}]


def test_create_report_stock_writes_markdown_and_index(_reports_root: Path) -> None:
    meta = create_report(
        ReportCreate(
            type="stock",
            title="台積電深度分析",
            body_markdown="## 執行摘要\n看好",
            subject="2330",
            symbols=["2330"],
            tags=["半導體"],
            date=date(2026, 4, 14),
        )
    )
    assert meta.id == "stock-2330-2026-04-14"

    detail = get_report("stock-2330-2026-04-14")
    assert detail is not None
    assert detail.title == "台積電深度分析"
    assert "執行摘要" in detail.body_markdown


def test_list_reports_filters_by_type_and_tag(_reports_root: Path) -> None:
    create_report(
        ReportCreate(
            type="stock",
            title="a",
            body_markdown="a",
            subject="2330",
            tags=["buy"],
            date=date(2026, 4, 14),
        )
    )
    create_report(
        ReportCreate(
            type="portfolio",
            title="b",
            body_markdown="b",
            tags=["weekly"],
            date=date(2026, 4, 14),
        )
    )

    only_stock = list_reports(type_filter="stock")
    assert len(only_stock) == 1 and only_stock[0].type == "stock"

    with_buy = list_reports(tag_filter="buy")
    assert len(with_buy) == 1 and with_buy[0].id.startswith("stock-")


def test_get_report_missing_returns_none(_reports_root: Path) -> None:
    assert get_report("nope") is None


def test_build_portfolio_report_markdown_has_sections(_reports_root: Path) -> None:
    resp = _make_recommend_resp()
    summary, body = build_portfolio_report_markdown(resp)
    assert "2026-04-15" in summary
    assert "calc_date" not in summary
    assert "Top Pick: 平衡型" in summary
    assert "# 本次推薦組合" in body
    assert "## 平衡型" in body
    assert "| 2330 |" in body
    assert "- 價值面亮眼" in body


def test_create_portfolio_report_writes_files(_reports_root: Path) -> None:
    resp = _make_recommend_resp()
    meta = create_portfolio_report(resp)
    assert meta.id == "portfolio-2026-04-15"
    assert "portfolio" in meta.tags and "recommend" in meta.tags
    assert meta.symbols == ["2330"]

    detail = get_report("portfolio-2026-04-15")
    assert detail is not None
    assert "平衡型" in detail.body_markdown


def test_research_subject_slug(_reports_root: Path) -> None:
    meta = create_report(
        ReportCreate(
            type="research",
            title="AI 題材研究",
            body_markdown="body",
            subject="AI 題材 / 伺服器",
            date=date(2026, 4, 14),
        )
    )
    assert meta.id == "research-AI-題材---伺服器-2026-04-14"
