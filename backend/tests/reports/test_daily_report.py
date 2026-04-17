"""Daily report 寫入 / 讀取測試。"""

from datetime import date

import pytest

from alpha_lab.reports.service import create_daily_report
from alpha_lab.reports.storage import (
    load_index,
    read_daily_markdown,
    write_daily_markdown,
)


@pytest.fixture(autouse=True)
def _tmp_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))


class TestWriteDailyMarkdown:
    def test_writes_to_daily_subdir(self) -> None:
        body = "# Test\n\nHello"
        path = write_daily_markdown(date(2026, 4, 17), body)
        assert path.name == "2026-04-17.md"
        assert "daily" in str(path)
        assert path.read_text(encoding="utf-8").strip() == body.strip()

    def test_overwrites_existing(self) -> None:
        write_daily_markdown(date(2026, 4, 17), "old content")
        write_daily_markdown(date(2026, 4, 17), "new content")
        content = read_daily_markdown(date(2026, 4, 17))
        assert content is not None
        assert "new content" in content


class TestCreateDailyReport:
    def test_creates_report_and_updates_index(self) -> None:
        body = "# 每日市場簡報（2026-04-17）\n\n## 市場概況\n..."
        meta = create_daily_report(
            trade_date=date(2026, 4, 17),
            body_markdown=body,
            summary_line="2026-04-17 市場簡報",
        )
        assert meta.id == "daily-2026-04-17"
        assert meta.type == "daily"
        assert meta.path == "daily/2026-04-17.md"

        items = load_index()
        assert any(m.id == "daily-2026-04-17" for m in items)

    def test_overwrites_same_date(self) -> None:
        create_daily_report(
            trade_date=date(2026, 4, 17),
            body_markdown="# First",
            summary_line="first",
        )
        create_daily_report(
            trade_date=date(2026, 4, 17),
            body_markdown="# Second",
            summary_line="second",
        )
        items = load_index()
        daily_items = [m for m in items if m.id == "daily-2026-04-17"]
        assert len(daily_items) == 1
        content = read_daily_markdown(date(2026, 4, 17))
        assert content is not None
        assert "Second" in content
