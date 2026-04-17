# Phase 7B.2「內容自動化」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 alpha-lab 每日自動產出市場簡報（daily briefing），並能彙整重大訊息與新聞成週報，存至 `data/reports/daily/` 與 `data/reports/analysis/`。

**Architecture:** 新增兩個後端模組——`briefing` 產出每日簡報、`news` 彙整新聞。兩者都走現有 Job 系統（`JobType` + `run_job_sync`），由 `daily_collect.py` 尾端自動觸發 daily briefing。新聞彙整暫不引入外部爬蟲，以「彙整 DB 已有的 events + scores 資料」為主，未來 Phase 再接外部新聞源。Daily briefing 寫入 `data/reports/daily/{date}.md` 並同步更新 `index.json`。

**Tech Stack:** Python 3.11+、FastAPI、SQLAlchemy 2.x、Pydantic v2、pytest

---

## File Structure

```
backend/src/alpha_lab/
├── briefing/                       # 新建：每日簡報產出
│   ├── __init__.py
│   ├── daily.py                    # build_daily_briefing() 核心邏輯
│   └── sections.py                 # 各 section builder（市場概況、法人動向、事件摘要、組合追蹤）
├── jobs/
│   └── types.py                    # 新增 DAILY_BRIEFING JobType
├── reports/
│   ├── service.py                  # 新增 create_daily_report() 寫入 daily/ 子目錄
│   └── storage.py                  # 新增 write_daily_markdown() 寫入 daily/<date>.md
└── scripts/
    └── daily_collect.py            # 尾端串接 DAILY_BRIEFING job

backend/tests/
├── briefing/
│   ├── test_daily.py
│   └── test_sections.py
└── reports/
    └── test_daily_report.py

docs/knowledge/
├── architecture/
│   └── daily-briefing.md           # 新建知識庫條目
└── collectors/
    └── README.md                   # 更新規劃中表格
```

---

## Group A：Daily Briefing 核心邏輯（Tasks 1-4）

### Task 1: Section Builders — 市場概況 & 法人動向

**Files:**
- Create: `backend/src/alpha_lab/briefing/__init__.py`
- Create: `backend/src/alpha_lab/briefing/sections.py`
- Test: `backend/tests/briefing/test_sections.py`

- [ ] **Step 1: Write the failing tests for `build_market_overview_section`**

```python
# backend/tests/briefing/test_sections.py
"""Section builder 單元測試。"""

from datetime import date

import pytest

from alpha_lab.briefing.sections import (
    build_market_overview_section,
    build_institutional_section,
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/briefing/test_sections.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Create `__init__.py` and implement section builders**

```python
# backend/src/alpha_lab/briefing/__init__.py
```

```python
# backend/src/alpha_lab/briefing/sections.py
"""Daily briefing section builders。

每個 builder 接收結構化資料（dict list），回傳 Markdown 字串。
不直接操作 DB——由上層 daily.py 查詢後傳入。
"""

from __future__ import annotations

from datetime import date


def build_market_overview_section(
    prices: list[dict],
    trade_date: date,
) -> str:
    lines = [f"## 市場概況（{trade_date.isoformat()}）", ""]
    if not prices:
        lines.append("_無資料_")
        return "\n".join(lines) + "\n"

    lines.append("| 代號 | 名稱 | 收盤 | 漲跌 | 漲跌% | 成交量 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for p in prices:
        change = p.get("change", 0)
        sign = "+" if change > 0 else ""
        pct = p.get("change_pct", 0)
        pct_sign = "+" if pct > 0 else ""
        lines.append(
            f"| {p['symbol']} | {p['name']} "
            f"| {p['close']:.2f} "
            f"| {sign}{change:.2f} "
            f"| {pct_sign}{pct:.2f}% "
            f"| {p['volume']:,} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_institutional_section(
    inst: list[dict],
    trade_date: date,
) -> str:
    lines = [f"## 法人動向（{trade_date.isoformat()}）", ""]
    if not inst:
        lines.append("_無資料_")
        return "\n".join(lines) + "\n"

    lines.append("| 代號 | 名稱 | 外資 | 投信 | 自營商 | 合計 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for row in inst:
        lines.append(
            f"| {row['symbol']} | {row['name']} "
            f"| {row['foreign_net']:,} "
            f"| {row['trust_net']:,} "
            f"| {row['dealer_net']:,} "
            f"| {row['total_net']:,} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/briefing/test_sections.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/alpha_lab/briefing/__init__.py backend/src/alpha_lab/briefing/sections.py backend/tests/briefing/test_sections.py
git commit -m "feat: add market overview and institutional section builders for daily briefing"
```

---

### Task 2: Section Builders — 事件摘要 & 組合追蹤

**Files:**
- Modify: `backend/src/alpha_lab/briefing/sections.py`
- Test: `backend/tests/briefing/test_sections.py`（追加）

- [ ] **Step 1: Write failing tests for `build_events_section` and `build_portfolio_tracking_section`**

```python
# 追加到 backend/tests/briefing/test_sections.py

from alpha_lab.briefing.sections import (
    build_events_section,
    build_portfolio_tracking_section,
)


class TestBuildEventsSection:
    def test_returns_markdown_with_events(self) -> None:
        events = [
            {"symbol": "2330", "title": "董事會決議配息", "event_type": "股利", "event_datetime": "2026-04-17 14:30:00"},
            {"symbol": "2317", "title": "合併案公告", "event_type": "重組", "event_datetime": "2026-04-17 10:00:00"},
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/briefing/test_sections.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement `build_events_section` and `build_portfolio_tracking_section`**

```python
# 追加到 backend/src/alpha_lab/briefing/sections.py

def build_events_section(events: list[dict]) -> str:
    lines = ["## 重大訊息", ""]
    if not events:
        lines.append("_無資料_")
        return "\n".join(lines) + "\n"

    for ev in events:
        lines.append(f"- **{ev['symbol']}** {ev['title']}（{ev['event_type']}，{ev['event_datetime']}）")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_portfolio_tracking_section(portfolios: list[dict]) -> str:
    lines = ["## 組合追蹤", ""]
    if not portfolios:
        lines.append("_無儲存的組合_")
        return "\n".join(lines) + "\n"

    lines.append("| # | 名稱 | NAV | 報酬% | 基準日 |")
    lines.append("| ---: | --- | ---: | ---: | --- |")
    for p in portfolios:
        lines.append(
            f"| {p['id']} | {p['label']} "
            f"| {p['nav']:.4f} "
            f"| {p['return_pct']:+.2f}% "
            f"| {p['base_date']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/briefing/test_sections.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/alpha_lab/briefing/sections.py backend/tests/briefing/test_sections.py
git commit -m "feat: add events and portfolio tracking section builders"
```

---

### Task 3: Daily Briefing Assembler — `build_daily_briefing()`

**Files:**
- Create: `backend/src/alpha_lab/briefing/daily.py`
- Test: `backend/tests/briefing/test_daily.py`

這個模組負責從 DB 查詢資料、呼叫 section builders、組合成完整 Markdown。

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/briefing/test_daily.py
"""Daily briefing assembler 測試（用 in-memory DB）。"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.briefing.daily import build_daily_briefing
from alpha_lab.storage.models import (
    Base,
    Event,
    PriceDaily,
    Stock,
    InstitutionalTrade,
    SavedPortfolio,
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
                symbol="2330", trade_date=date(2026, 4, 17),
                open=840.0, high=855.0, low=838.0, close=850.0,
                volume=25000,
            )
        )
        session.add(
            PriceDaily(
                symbol="2330", trade_date=date(2026, 4, 16),
                open=835.0, high=842.0, low=833.0, close=840.0,
                volume=20000,
            )
        )
        session.add(
            InstitutionalTrade(
                symbol="2330", trade_date=date(2026, 4, 17),
                foreign_net=5000, trust_net=1000, dealer_net=-200, total_net=5800,
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

    def test_no_data_date_still_produces_report(self, session_factory) -> None:
        md = build_daily_briefing(session_factory, trade_date=date(2026, 1, 1))
        assert "# 每日市場簡報" in md
        assert "無資料" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/briefing/test_daily.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement `build_daily_briefing()`**

```python
# backend/src/alpha_lab/briefing/daily.py
"""Daily briefing assembler：從 DB 查詢 → 組合成完整 Markdown。"""

from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.briefing.sections import (
    build_events_section,
    build_institutional_section,
    build_market_overview_section,
    build_portfolio_tracking_section,
)
from alpha_lab.storage.models import (
    Event,
    InstitutionalTrade,
    PriceDaily,
    SavedPortfolio,
    Stock,
)


def _query_prices_with_change(
    session: Session, trade_date: date
) -> list[dict]:
    prev_date_sub = (
        select(func.max(PriceDaily.trade_date))
        .where(PriceDaily.trade_date < trade_date)
        .correlate(None)
        .scalar_subquery()
    )

    rows = session.execute(
        select(
            PriceDaily.symbol,
            Stock.name,
            PriceDaily.close,
            PriceDaily.volume,
        )
        .join(Stock, PriceDaily.symbol == Stock.symbol)
        .where(PriceDaily.trade_date == trade_date)
        .order_by(PriceDaily.volume.desc())
    ).all()

    prev_map: dict[str, float] = {}
    prev_rows = session.execute(
        select(PriceDaily.symbol, PriceDaily.close)
        .where(PriceDaily.trade_date == prev_date_sub)
    ).all()
    for sym, close in prev_rows:
        prev_map[sym] = float(close)

    result = []
    for sym, name, close, volume in rows:
        close_f = float(close)
        prev_close = prev_map.get(sym)
        change = close_f - prev_close if prev_close else 0.0
        change_pct = (change / prev_close * 100) if prev_close else 0.0
        result.append({
            "symbol": sym,
            "name": name,
            "close": close_f,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
        })
    return result


def _query_institutional(session: Session, trade_date: date) -> list[dict]:
    rows = session.execute(
        select(
            InstitutionalTrade.symbol,
            Stock.name,
            InstitutionalTrade.foreign_net,
            InstitutionalTrade.trust_net,
            InstitutionalTrade.dealer_net,
            InstitutionalTrade.total_net,
        )
        .join(Stock, InstitutionalTrade.symbol == Stock.symbol)
        .where(InstitutionalTrade.trade_date == trade_date)
        .order_by(func.abs(InstitutionalTrade.total_net).desc())
    ).all()
    return [
        {
            "symbol": sym,
            "name": name,
            "foreign_net": foreign,
            "trust_net": trust,
            "dealer_net": dealer,
            "total_net": total,
        }
        for sym, name, foreign, trust, dealer, total in rows
    ]


def _query_events(session: Session, trade_date: date) -> list[dict]:
    start = trade_date
    end_dt = trade_date + timedelta(days=1)
    rows = session.execute(
        select(Event)
        .where(Event.event_datetime >= start)
        .where(Event.event_datetime < end_dt)
        .order_by(Event.event_datetime.desc())
    ).scalars().all()
    return [
        {
            "symbol": r.symbol,
            "title": r.title,
            "event_type": r.event_type,
            "event_datetime": r.event_datetime.strftime("%Y-%m-%d %H:%M"),
        }
        for r in rows
    ]


def _query_saved_portfolios(session: Session) -> list[dict]:
    rows = session.execute(
        select(SavedPortfolio).order_by(SavedPortfolio.created_at.desc())
    ).scalars().all()
    result = []
    for p in rows:
        holdings = json.loads(p.holdings_json) if p.holdings_json else []
        result.append({
            "id": p.id,
            "label": p.label,
            "nav": 1.0,
            "return_pct": 0.0,
            "base_date": p.base_date.isoformat() if p.base_date else "",
        })
    return result


def build_daily_briefing(
    session_factory: sessionmaker[Session],
    trade_date: date,
) -> str:
    with session_factory() as session:
        prices = _query_prices_with_change(session, trade_date)
        inst = _query_institutional(session, trade_date)
        events = _query_events(session, trade_date)
        portfolios = _query_saved_portfolios(session)

    parts = [
        f"# 每日市場簡報（{trade_date.isoformat()}）\n",
        build_market_overview_section(prices, trade_date),
        build_institutional_section(inst, trade_date),
        build_events_section(events),
    ]
    if portfolios:
        parts.append(build_portfolio_tracking_section(portfolios))

    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/briefing/test_daily.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/alpha_lab/briefing/daily.py backend/tests/briefing/test_daily.py
git commit -m "feat: add daily briefing assembler with DB queries"
```

---

### Task 4: Daily Report Storage — 寫入 `data/reports/daily/`

**Files:**
- Modify: `backend/src/alpha_lab/reports/storage.py`（新增 `write_daily_markdown`、`read_daily_markdown`）
- Modify: `backend/src/alpha_lab/reports/service.py`（新增 `create_daily_report`）
- Modify: `backend/src/alpha_lab/schemas/report.py`（`ReportType` 加入 `"daily"`）
- Test: `backend/tests/reports/test_daily_report.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/reports/test_daily_report.py
"""Daily report 寫入 / 讀取測試。"""

import json
from datetime import date
from pathlib import Path

import pytest

from alpha_lab.reports.service import create_daily_report
from alpha_lab.reports.storage import (
    get_reports_root,
    load_index,
    read_daily_markdown,
    write_daily_markdown,
)


@pytest.fixture(autouse=True)
def _tmp_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))


class TestWriteDailyMarkdown:
    def test_writes_to_daily_subdir(self, tmp_path) -> None:
        body = "# Test\n\nHello"
        path = write_daily_markdown(date(2026, 4, 17), body)
        assert path.name == "2026-04-17.md"
        assert "daily" in str(path)
        assert path.read_text(encoding="utf-8").strip() == body.strip()

    def test_overwrites_existing(self, tmp_path) -> None:
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/reports/test_daily_report.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Extend `ReportType` to include `"daily"`**

```python
# backend/src/alpha_lab/schemas/report.py — 修改 ReportType
ReportType = Literal["stock", "portfolio", "events", "research", "daily"]
```

- [ ] **Step 4: Add `write_daily_markdown` and `read_daily_markdown` to storage**

```python
# 追加到 backend/src/alpha_lab/reports/storage.py

def write_daily_markdown(report_date: date, body: str) -> Path:
    """寫入 daily/<YYYY-MM-DD>.md。覆寫同日既有檔案。"""
    root = get_reports_root()
    daily_dir = root / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{report_date.isoformat()}.md"
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return path


def read_daily_markdown(report_date: date) -> str | None:
    """讀取 daily/<YYYY-MM-DD>.md 內容，不存在回傳 None。"""
    root = get_reports_root()
    path = root / "daily" / f"{report_date.isoformat()}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
```

需在頂部加入 `from datetime import date as date_type`（若尚未 import）。注意 storage.py 已有 `from pathlib import Path`。

- [ ] **Step 5: Add `create_daily_report` to service**

```python
# 追加到 backend/src/alpha_lab/reports/service.py

from alpha_lab.reports.storage import write_daily_markdown

def create_daily_report(
    trade_date: date_type,
    body_markdown: str,
    summary_line: str = "",
) -> ReportMeta:
    """寫入 daily/<date>.md 並更新 index.json。"""
    report_id = f"daily-{trade_date.isoformat()}"
    write_daily_markdown(trade_date, body_markdown)

    meta = ReportMeta(
        id=report_id,
        type="daily",
        title=f"每日市場簡報 {trade_date.isoformat()}",
        symbols=[],
        tags=["daily", "briefing"],
        date=trade_date,
        path=f"daily/{trade_date.isoformat()}.md",
        summary_line=summary_line,
        starred=False,
    )
    upsert_in_index(meta)

    if summary_line:
        append_summary(trade_date.isoformat(), summary_line)

    return meta
```

也需更新 `_build_report_id` 加入 `"daily"` 分支（雖然 `create_daily_report` 不走該函式，但保持一致性）：

```python
# 在 _build_report_id 裡加入
if report_type == "daily":
    return f"daily-{d}"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/reports/test_daily_report.py -v`
Expected: PASS

- [ ] **Step 7: Run ruff + mypy**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 errors

- [ ] **Step 8: Commit**

```bash
git add backend/src/alpha_lab/schemas/report.py backend/src/alpha_lab/reports/storage.py backend/src/alpha_lab/reports/service.py backend/tests/reports/test_daily_report.py
git commit -m "feat: add daily report type with write/read to data/reports/daily/"
```

---

## Group B：Job 串接 & CLI 整合（Tasks 5-6）

### Task 5: DAILY_BRIEFING JobType & Dispatch

**Files:**
- Modify: `backend/src/alpha_lab/jobs/types.py`（新增 `DAILY_BRIEFING`）
- Modify: `backend/src/alpha_lab/jobs/service.py`（新增 dispatch 分支）

- [ ] **Step 1: Add `DAILY_BRIEFING` to JobType**

```python
# backend/src/alpha_lab/jobs/types.py — 追加
DAILY_BRIEFING = "daily_briefing"
```

- [ ] **Step 2: Add dispatch branch in `_dispatch`**

```python
# 追加到 backend/src/alpha_lab/jobs/service.py 的 _dispatch 函式，在最後的 raise ValueError 之前

if job_type is JobType.DAILY_BRIEFING:
    trade_date_str = params.get("trade_date")
    trade_date = (
        date.fromisoformat(str(trade_date_str))
        if trade_date_str
        else datetime.now(UTC).date()
    )
    from alpha_lab.briefing.daily import build_daily_briefing
    from alpha_lab.reports.service import create_daily_report

    body = build_daily_briefing(session_factory, trade_date)
    lines = body.split("\n")
    first_content_line = next(
        (l for l in lines if l.strip() and not l.startswith("#")),
        "每日簡報已產出",
    )
    summary = f"{trade_date.isoformat()} 每日簡報"
    create_daily_report(
        trade_date=trade_date,
        body_markdown=body,
        summary_line=summary,
    )
    return f"daily briefing for {trade_date.isoformat()} written"
```

- [ ] **Step 3: Run existing test suite to verify no regression**

Run: `cd backend && python -m pytest tests/ -v --timeout=30`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/src/alpha_lab/jobs/types.py backend/src/alpha_lab/jobs/service.py
git commit -m "feat: add DAILY_BRIEFING job type with dispatch"
```

---

### Task 6: 串接 `daily_collect.py`

**Files:**
- Modify: `backend/scripts/daily_collect.py`

在 `run_daily_collect` 函式的最尾端（在 processed 之後、summary 列印之前），加入 daily briefing job。

- [ ] **Step 1: Add daily briefing to `daily_collect.py`**

在 `run_daily_collect` 函式中，於 `print("\n=== summary ===")` 之前插入：

```python
    # Phase 7B.2：每日簡報
    briefing_label = "daily briefing"
    status, summary = await _run_one(
        briefing_label,
        JobType.DAILY_BRIEFING,
        {"trade_date": trade_date_str},
        session_factory,
    )
    results.append((briefing_label, status, summary))
```

- [ ] **Step 2: Run daily_collect with `--help` to verify import**

Run: `cd backend && python scripts/daily_collect.py --help`
Expected: help output without import errors

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/daily_collect.py
git commit -m "feat: hook daily briefing into daily_collect pipeline"
```

---

## Group C：知識庫 & 文件同步（Tasks 7-8）

### Task 7: 知識庫條目 — `daily-briefing.md`

**Files:**
- Create: `docs/knowledge/architecture/daily-briefing.md`
- Modify: `docs/knowledge/collectors/README.md`

- [ ] **Step 1: Create `daily-briefing.md`**

```markdown
---
domain: architecture/daily-briefing
updated: 2026-04-18
related: [processed-store.md, ../collectors/README.md]
---

# 每日市場簡報（Daily Briefing）

## 目的

每天收盤後自動產出一份 Markdown 簡報，涵蓋：市場概況、法人動向、重大訊息、組合追蹤。存至 `data/reports/daily/{date}.md`，同步更新 `data/reports/index.json`。

## 現行實作

- `briefing/sections.py`：四個 section builder（純函式，接收 dict list）
- `briefing/daily.py`：assembler，從 DB 查詢資料並組合各 section
- `reports/service.py` → `create_daily_report()`：寫檔 + 更新 index
- `reports/storage.py` → `write_daily_markdown()`：寫入 `daily/` 子目錄
- `JobType.DAILY_BRIEFING`：透過 job 系統觸發
- `daily_collect.py`：pipeline 尾端自動跑

## 關鍵檔案

- [backend/src/alpha_lab/briefing/daily.py](../../../backend/src/alpha_lab/briefing/daily.py)
- [backend/src/alpha_lab/briefing/sections.py](../../../backend/src/alpha_lab/briefing/sections.py)
- [backend/src/alpha_lab/reports/service.py](../../../backend/src/alpha_lab/reports/service.py)
- [backend/src/alpha_lab/reports/storage.py](../../../backend/src/alpha_lab/reports/storage.py)

## 修改時注意事項

- 新增 section：在 `sections.py` 加 builder，在 `daily.py` 的 `build_daily_briefing` 串入
- section builder 不可直接存取 DB（職責分離）；DB 查詢統一在 `daily.py`
- Daily 報告不寫 frontmatter（與 analysis/ 下的報告不同）——純 Markdown body
- `ReportType` 已擴充為 `"daily"`，前端 list reports 時需注意新類型
```

- [ ] **Step 2: Update `docs/knowledge/collectors/README.md`**

在「規劃中」表格中移除 `news.md` 的暫緩標記，改為「Phase 7B.2+ 新聞彙整（目前以 DB events 為主）」。

- [ ] **Step 3: Commit**

```bash
git add docs/knowledge/architecture/daily-briefing.md docs/knowledge/collectors/README.md
git commit -m "docs: add daily-briefing knowledge base entry and update collectors README"
```

---

### Task 8: 設計 spec & USER_GUIDE 同步更新

**Files:**
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（Phase 7B.2 狀態更新）
- Modify: `docs/USER_GUIDE.md`（新增 daily briefing 使用說明）

- [ ] **Step 1: Update design spec Phase table**

把 Phase 7B.2 的狀態從「未開始」改為「✅ 完成（2026-04-18）」，補上交付物描述：

```
| 7B.2 | ✅ 完成（2026-04-18） | 內容自動化 | Daily Briefing（market overview / institutional / events / portfolio tracking 四段式 Markdown）、`DAILY_BRIEFING` JobType、`daily_collect.py` 尾端自動觸發、`data/reports/daily/` 儲存 + index 同步；新聞彙整暫以 DB events 彙整為主，外部新聞源留待後續 |
```

- [ ] **Step 2: Add daily briefing section to USER_GUIDE.md**

新增「每日市場簡報」段落，說明：
- 自動產出時機（daily_collect 尾端）
- 檔案位置（`data/reports/daily/YYYY-MM-DD.md`）
- 手動觸發方式

使用者驗收指引格式（CMD）：
```cmd
REM 手動觸發 daily briefing
cd backend
.venv\Scripts\python.exe -c "from alpha_lab.jobs.service import create_job, run_job_sync; from alpha_lab.jobs.types import JobType; from alpha_lab.storage.engine import get_session_factory; from alpha_lab.storage.init_db import init_database; import asyncio; init_database(); sf=get_session_factory(); session=sf(); job=create_job(session, job_type=JobType.DAILY_BRIEFING, params={'trade_date':'2026-04-17'}); session.commit(); asyncio.run(run_job_sync(job_id=job.id, session_factory=sf))"

REM 確認產出
dir ..\data\reports\daily\
type ..\data\reports\daily\2026-04-17.md
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-14-alpha-lab-design.md docs/USER_GUIDE.md
git commit -m "docs: sync design spec and user guide for Phase 7B.2"
```

---

## 使用者驗收指引（Group A-C 完成後）

以下為 Windows CMD 格式：

```cmd
REM 1. 跑靜態檢查
cd backend
ruff check . && mypy src

REM 2. 跑所有測試
python -m pytest tests/ -v

REM 3. 手動觸發 daily briefing（需要先有 DB 資料）
.venv\Scripts\python.exe scripts\daily_collect.py --symbols 2330 --date 2026-04-17

REM 4. 確認 daily briefing 產出
type ..\data\reports\daily\2026-04-17.md

REM 5. 確認 index.json 有 daily 類型條目
type ..\data\reports\index.json | findstr "daily"
```

驗證重點：
- `data/reports/daily/2026-04-17.md` 存在且包含四段（市場概況、法人動向、重大訊息、組合追蹤）
- `data/reports/index.json` 有 `"daily-2026-04-17"` 條目
- 靜態檢查 0 error
- 測試全綠

---

## 設計決策備註

1. **不引入外部新聞爬蟲**：Phase 7B.2 暫以 DB 既有 `events` 表為新聞/訊息來源。理由：免費新聞 API 不穩定、版權問題；重大訊息已覆蓋最關鍵資訊。外部新聞源列為後續可擴充項目。

2. **Daily 報告不寫 YAML frontmatter**：`daily/<date>.md` 是純 Markdown（與 `analysis/*.md` 帶 frontmatter 不同）。理由：daily 報告結構固定、由程式產出，frontmatter 資訊已在 `index.json` 中。

3. **排程機制選擇**：本 Phase 不引入 APScheduler 或系統 cron。理由：alpha-lab 是個人工具，`daily_collect.py` 已能手動或由外部排程（Windows Task Scheduler）觸發。若未來需要排程，可在 Phase 7B.3 或更後面加入。

4. **組合追蹤 section 的 NAV 計算**：目前組合追蹤 section 只顯示基本資訊（不即時算 NAV），因為即時 NAV 需要當日收盤價已入庫。briefing 在 daily_collect 尾端跑，此時價格已入庫，但首版先以靜態展示為主，後續可強化。
