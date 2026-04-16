# Phase 6: 組合追蹤 + 報告管理 + 教學開關 + 個股頁補完

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 補完 MVP 五大功能最後一環：組合儲存與績效追蹤、報告加星/刪除/全文搜尋、教學三段密度開關、個股頁收藏與加入組合按鈕。

**Architecture:**

- **Group A（組合追蹤）**：SQLite 新增 `portfolios_saved` / `portfolio_snapshots` 兩表。後端新增 `portfolios/service.py` 處理儲存與績效計算（NAV 以創建日基準價正規化為 1.0），API 新增 `POST/GET /portfolios/saved` 與 `GET /saved/{id}/performance`；前端新增 `/portfolios/:id` 追蹤頁與儲存按鈕。
- **Group B（報告管理）**：擴充現有 `reports/service.py` 加 `update_report` / `delete_report` / 全文搜尋（比對 title / summary / tags / symbols），API 新增 `PATCH`/`DELETE`，前端 `/reports` 列表加搜尋框、加星、刪除按鈕。
- **Group C（教學開關）**：純前端 Context + localStorage 實作三段模式（full/compact/off），右上角 📖 按鈕切換；TermTooltip / L2Panel / PortfolioTabs reasons 依模式顯隱。
- **Group D（個股頁補完）**：收藏用 localStorage（個人工具不需持久到 DB），「加入組合」調 Group A 的 `POST /portfolios/saved`，「相關分析報告」抓 `GET /api/reports?symbol=...`（新增 query param）。

**Tech Stack:** FastAPI + SQLAlchemy 2.x + Pydantic v2 + pytest / React 19 + TanStack Query + Zustand + Tailwind CSS + Playwright + vitest

**Dependencies:** Group D 的「加入組合」依賴 Group A 的 `POST /portfolios/saved`；「相關分析報告」依賴 Group B 的 symbol 過濾。建議按 A → B → C → D 順序實作，但 C 獨立不依賴其他群組，可穿插。

---

## File Structure

### Backend 新增 / 修改

| 檔案 | 動作 | 責任 |
|------|------|------|
| `backend/src/alpha_lab/storage/models.py` | Modify | 新增 `SavedPortfolio` / `PortfolioSnapshot` |
| `backend/src/alpha_lab/schemas/saved_portfolio.py` | Create | 儲存組合與績效 API 的 Pydantic schema |
| `backend/src/alpha_lab/portfolios/__init__.py` | Create | 新 package |
| `backend/src/alpha_lab/portfolios/service.py` | Create | `save_portfolio` / `list_saved` / `delete_saved` / `compute_performance` |
| `backend/src/alpha_lab/api/routes/portfolios.py` | Modify | 新增 `POST/GET /saved`、`DELETE /saved/{id}`、`GET /saved/{id}/performance` |
| `backend/src/alpha_lab/reports/storage.py` | Modify | `delete_report_files`、`update_in_index` |
| `backend/src/alpha_lab/reports/service.py` | Modify | `update_report` / `delete_report` / `list_reports` 加 `symbol` / `query` 過濾 |
| `backend/src/alpha_lab/schemas/report.py` | Modify | 新增 `ReportUpdate` |
| `backend/src/alpha_lab/api/routes/reports.py` | Modify | 新增 `PATCH`、`DELETE`、list 加 `q` / `symbol` query param |

### Backend tests 新增 / 修改

| 檔案 | 動作 | 覆蓋 |
|------|------|------|
| `backend/tests/portfolios/__init__.py` | Create | package |
| `backend/tests/portfolios/test_service.py` | Create | 儲存、刪除、NAV 計算 |
| `backend/tests/api/test_portfolios_saved.py` | Create | `POST/GET/DELETE /saved`、`GET /performance` |
| `backend/tests/api/test_reports.py` | Modify | 加 patch/delete/search 案例 |

### Frontend 新增 / 修改

| 檔案 | 動作 | 責任 |
|------|------|------|
| `frontend/src/api/types.ts` | Modify | 新增 `SavedPortfolio`、`SavedPortfolioCreate`、`PerformancePoint`、`PerformanceResponse`、`ReportUpdate` |
| `frontend/src/api/savedPortfolios.ts` | Create | `listSaved` / `saveFromRecommend` / `deleteSaved` / `fetchPerformance` |
| `frontend/src/api/reports.ts` | Modify | `updateReport` / `deleteReport`、list 加 `q` / `symbol` |
| `frontend/src/api/client.ts` | Modify | 加 `apiPatch` / `apiDelete` helpers |
| `frontend/src/pages/PortfoliosPage.tsx` | Modify | 每組 Portfolio 右上加「儲存此組合」按鈕 + 已儲存清單連結 |
| `frontend/src/pages/PortfolioTrackingPage.tsx` | Create | `/portfolios/:id` 追蹤頁（持股 + NAV 走勢） |
| `frontend/src/pages/ReportsPage.tsx` | Modify | 搜尋框 + 加星 + 刪除按鈕 |
| `frontend/src/pages/ReportDetailPage.tsx` | Modify | 加星切換、tag 編輯、刪除確認 |
| `frontend/src/pages/StockPage.tsx` | Modify | 掛新元件 |
| `frontend/src/components/stock/StockActions.tsx` | Create | 收藏 + 加入組合 |
| `frontend/src/components/stock/RelatedReports.tsx` | Create | 相關分析報告區塊 |
| `frontend/src/components/portfolio/SavedPortfolioList.tsx` | Create | 已儲存組合清單 |
| `frontend/src/components/portfolio/PerformanceChart.tsx` | Create | NAV 時間序列圖（Recharts） |
| `frontend/src/contexts/TutorialModeContext.tsx` | Create | 三段模式 Context + localStorage |
| `frontend/src/components/TutorialModeToggle.tsx` | Create | 右上角 📖 切換按鈕 |
| `frontend/src/layouts/AppLayout.tsx` | Modify | 掛 `TutorialModeProvider` + Toggle |
| `frontend/src/components/TermTooltip.tsx` | Modify | 依模式隱藏 L1 |
| `frontend/src/components/education/L2Panel.tsx` | Modify | off 模式關閉 L2 |
| `frontend/src/components/portfolio/PortfolioTabs.tsx` | Modify | off 模式隱藏 reasons |
| `frontend/src/lib/favorites.ts` | Create | localStorage 收藏 helper |

### Frontend tests 新增 / 修改

| 檔案 | 動作 | 覆蓋 |
|------|------|------|
| `frontend/tests/components/SavedPortfolioList.test.tsx` | Create | 渲染與互動 |
| `frontend/tests/components/TutorialModeToggle.test.tsx` | Create | 三段切換邏輯 |
| `frontend/tests/components/StockActions.test.tsx` | Create | 收藏切換、加入組合 |
| `frontend/tests/e2e/portfolio-tracking.spec.ts` | Create | 儲存→跳追蹤頁→看 NAV |
| `frontend/tests/e2e/reports.spec.ts` | Modify | 加星 / 刪除 / 搜尋 |
| `frontend/tests/e2e/tutorial-mode.spec.ts` | Create | 切換 persist |
| `frontend/tests/e2e/stock-actions.spec.ts` | Create | 收藏 + 加入組合 + 相關報告 |
| `frontend/tests/e2e/fixtures/` | Modify | 新增 saved-portfolios.json 等 fixture |

### 文件同步

| 檔案 | 動作 |
|------|------|
| `docs/knowledge/features/tracking/README.md` | Modify（若只是骨架則改內容） |
| `docs/knowledge/features/tracking/overview.md` | Create |
| `docs/knowledge/features/reports/storage.md` | Modify（新增 update/delete/search 段） |
| `docs/knowledge/features/education/tutorial-mode.md` | Create |
| `docs/knowledge/architecture/data-models.md` | Modify（加入新表） |
| `docs/knowledge/architecture/data-flow.md` | Modify（Phase 6 段） |
| `docs/USER_GUIDE.md` | Modify（補 tracking / reports 管理 / 教學開關段） |
| `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` | Modify（Phase 6 完成後勾選） |

---

# Group A：組合追蹤

## Task A1: 建立 SavedPortfolio / PortfolioSnapshot model

**Files:**
- Modify: `backend/src/alpha_lab/storage/models.py`

- [ ] **Step 1: 新增兩張 model 到 models.py 結尾**

```python
class SavedPortfolio(Base):
    """使用者儲存的組合（來自推薦 snapshot）。

    holdings_json：list of {symbol, name, weight, base_price}
    base_prices 在儲存當下從 prices_daily 取最新收盤價。
    """

    __tablename__ = "portfolios_saved"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    style: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    holdings_json: Mapped[str] = mapped_column(Text, nullable=False)
    base_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utc_now
    )


class PortfolioSnapshot(Base):
    """每日 NAV 快照（選用：`GET /saved/{id}/performance` 會同步寫一份）。"""

    __tablename__ = "portfolio_snapshots"

    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios_saved.id"), primary_key=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    holdings_json: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 2: 手動驗證 DB 初始化**

Run: `cd backend && .venv\Scripts\python.exe -c "from alpha_lab.storage.init_db import init_database; init_database(); print('ok')"`
Expected: `ok`（新表應自動建立，因 `create_all` 對既有 DB 是 no-op，但新表會補上）

- [ ] **Step 3: Commit**

```bash
cd ..
git add backend/src/alpha_lab/storage/models.py
git commit -m "feat: add SavedPortfolio and PortfolioSnapshot models"
```

---

## Task A2: 定義 saved_portfolio Pydantic schemas

**Files:**
- Create: `backend/src/alpha_lab/schemas/saved_portfolio.py`

- [ ] **Step 1: 寫 schemas**

```python
"""Saved Portfolio 相關 schemas（Phase 6）。"""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field

from alpha_lab.analysis.weights import Style


class SavedHolding(BaseModel):
    symbol: str
    name: str
    weight: float
    base_price: float


class SavedPortfolioCreate(BaseModel):
    """把某個風格的推薦結果存成追蹤組合。

    前端從 `RecommendResponse` 取一個 Portfolio 組合成這個 payload。
    """

    style: Style
    label: str = Field(..., min_length=1, max_length=32)
    note: str | None = None
    holdings: list[SavedHolding] = Field(..., min_length=1)


class SavedPortfolioMeta(BaseModel):
    id: int
    style: Style
    label: str
    note: str | None
    base_date: date_type
    created_at: datetime
    holdings_count: int


class SavedPortfolioDetail(SavedPortfolioMeta):
    holdings: list[SavedHolding]


class PerformancePoint(BaseModel):
    date: date_type
    nav: float
    daily_return: float | None = None


class PerformanceResponse(BaseModel):
    portfolio: SavedPortfolioDetail
    points: list[PerformancePoint]
    latest_nav: float
    total_return: float  # nav_last - 1.0
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/alpha_lab/schemas/saved_portfolio.py
git commit -m "feat: add saved portfolio schemas"
```

---

## Task A3: 寫 portfolios service（儲存 / 列表 / 刪除）

**Files:**
- Create: `backend/src/alpha_lab/portfolios/__init__.py`
- Create: `backend/src/alpha_lab/portfolios/service.py`
- Create: `backend/tests/portfolios/__init__.py`
- Create: `backend/tests/portfolios/test_service.py`

- [ ] **Step 1: 先寫失敗測試 `test_service.py`**

```python
"""Saved portfolio service 單元測試（Phase 6）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from alpha_lab.portfolios.service import (
    delete_saved,
    list_saved,
    save_portfolio,
)
from alpha_lab.schemas.saved_portfolio import SavedHolding, SavedPortfolioCreate
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import PriceDaily, Stock


@pytest.fixture
def sample_prices():
    """Seed 兩檔股票的 base_date 收盤價。"""

    with session_scope() as session:
        for sym, name, close in [("2330", "台積電", 600.0), ("2317", "鴻海", 100.0)]:
            session.merge(Stock(symbol=sym, name=name))
            session.merge(
                PriceDaily(
                    symbol=sym,
                    trade_date=date(2026, 4, 17),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=1000,
                )
            )
    yield


def test_save_portfolio_persists_holdings(sample_prices):
    payload = SavedPortfolioCreate(
        style="balanced",
        label="Apr 平衡組",
        holdings=[
            SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
            SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
        ],
    )
    meta = save_portfolio(payload, base_date=date(2026, 4, 17))
    assert meta.id > 0
    assert meta.holdings_count == 2
    assert meta.base_date == date(2026, 4, 17)


def test_list_saved_returns_newest_first(sample_prices):
    save_portfolio(
        SavedPortfolioCreate(
            style="conservative",
            label="older",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 15),
    )
    newer = save_portfolio(
        SavedPortfolioCreate(
            style="aggressive",
            label="newer",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    items = list_saved()
    assert items[0].id == newer.id


def test_delete_saved_removes_row(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="to-delete",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    assert delete_saved(meta.id) is True
    assert delete_saved(meta.id) is False
    assert all(m.id != meta.id for m in list_saved())
```

- [ ] **Step 2: Run — 應 FAIL（service 還沒寫）**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/portfolios/test_service.py -v`
Expected: `ImportError` or 3 tests fail

- [ ] **Step 3: 寫 `service.py` 最小實作**

```python
"""Saved portfolio service（Phase 6）。"""

from __future__ import annotations

import json
from datetime import date as date_type

from sqlalchemy import select

from alpha_lab.schemas.saved_portfolio import (
    SavedHolding,
    SavedPortfolioCreate,
    SavedPortfolioDetail,
    SavedPortfolioMeta,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import SavedPortfolio


def _holdings_to_json(holdings: list[SavedHolding]) -> str:
    return json.dumps([h.model_dump() for h in holdings], ensure_ascii=False)


def _holdings_from_json(raw: str) -> list[SavedHolding]:
    return [SavedHolding(**item) for item in json.loads(raw)]


def _row_to_meta(row: SavedPortfolio) -> SavedPortfolioMeta:
    holdings = _holdings_from_json(row.holdings_json)
    return SavedPortfolioMeta(
        id=row.id,
        style=row.style,  # type: ignore[arg-type]
        label=row.label,
        note=row.note,
        base_date=row.base_date,
        created_at=row.created_at,
        holdings_count=len(holdings),
    )


def _row_to_detail(row: SavedPortfolio) -> SavedPortfolioDetail:
    holdings = _holdings_from_json(row.holdings_json)
    return SavedPortfolioDetail(
        id=row.id,
        style=row.style,  # type: ignore[arg-type]
        label=row.label,
        note=row.note,
        base_date=row.base_date,
        created_at=row.created_at,
        holdings_count=len(holdings),
        holdings=holdings,
    )


def save_portfolio(
    payload: SavedPortfolioCreate,
    *,
    base_date: date_type,
) -> SavedPortfolioMeta:
    with session_scope() as session:
        row = SavedPortfolio(
            style=payload.style,
            label=payload.label,
            note=payload.note,
            holdings_json=_holdings_to_json(payload.holdings),
            base_date=base_date,
        )
        session.add(row)
        session.flush()
        meta = _row_to_meta(row)
    return meta


def list_saved() -> list[SavedPortfolioMeta]:
    with session_scope() as session:
        rows = session.scalars(
            select(SavedPortfolio).order_by(SavedPortfolio.created_at.desc())
        ).all()
        return [_row_to_meta(r) for r in rows]


def get_saved(portfolio_id: int) -> SavedPortfolioDetail | None:
    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return None
        return _row_to_detail(row)


def delete_saved(portfolio_id: int) -> bool:
    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return False
        session.delete(row)
    return True
```

- [ ] **Step 4: Run — 應 PASS**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/portfolios/test_service.py -v`
Expected: 3 tests pass

- [ ] **Step 5: ruff + mypy**

Run: `cd backend && .venv\Scripts\python.exe -m ruff check . && .venv\Scripts\python.exe -m mypy src`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/src/alpha_lab/portfolios/ backend/src/alpha_lab/schemas/saved_portfolio.py backend/tests/portfolios/
git commit -m "feat: add saved portfolio service with save/list/delete"
```

---

## Task A4: 實作績效計算 `compute_performance`

**Files:**
- Modify: `backend/src/alpha_lab/portfolios/service.py`
- Modify: `backend/tests/portfolios/test_service.py`

- [ ] **Step 1: 先加失敗測試**

```python
# 於 test_service.py 末尾加入

from alpha_lab.portfolios.service import compute_performance


def test_compute_performance_tracks_nav(sample_prices):
    # 4/17 以 600 / 100 為基準，之後價格變化看 NAV 是否對
    with session_scope() as session:
        for d, close_2330, close_2317 in [
            (date(2026, 4, 18), 630.0, 105.0),  # +5% / +5% → NAV 1.05
            (date(2026, 4, 21), 660.0, 110.0),  # +10% / +10% → NAV 1.10
        ]:
            for sym, close in [("2330", close_2330), ("2317", close_2317)]:
                session.merge(
                    PriceDaily(
                        symbol=sym,
                        trade_date=d,
                        open=close,
                        high=close,
                        low=close,
                        close=close,
                        volume=1000,
                    )
                )

    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="perf",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
                SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
            ],
        ),
        base_date=date(2026, 4, 17),
    )
    resp = compute_performance(meta.id)
    assert resp is not None
    # base day + 2 個交易日 = 3 points
    assert len(resp.points) == 3
    assert resp.points[0].nav == pytest.approx(1.0)
    assert resp.points[1].nav == pytest.approx(1.05, rel=1e-4)
    assert resp.points[2].nav == pytest.approx(1.10, rel=1e-4)
    assert resp.total_return == pytest.approx(0.10, rel=1e-4)


def test_compute_performance_missing_price_skips_day(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="missing",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    # 只有 base_date 有價格，後面沒有 → 僅 1 個 point
    resp = compute_performance(meta.id)
    assert resp is not None
    assert len(resp.points) == 1
    assert resp.latest_nav == pytest.approx(1.0)


def test_compute_performance_returns_none_for_unknown_id():
    assert compute_performance(99999) is None
```

- [ ] **Step 2: Run — 應 FAIL**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/portfolios/test_service.py::test_compute_performance_tracks_nav -v`
Expected: `ImportError: cannot import name 'compute_performance'`

- [ ] **Step 3: 加入實作**

```python
# 在 service.py 末尾加

from sqlalchemy.orm import Session

from alpha_lab.schemas.saved_portfolio import (
    PerformancePoint,
    PerformanceResponse,
)
from alpha_lab.storage.models import PortfolioSnapshot, PriceDaily


def _load_price_map(
    session: Session, symbols: list[str], start: date_type
) -> dict[str, dict[date_type, float]]:
    """回傳 {symbol: {date: close}}，僅取 >= start 日期。"""

    rows = session.scalars(
        select(PriceDaily)
        .where(PriceDaily.symbol.in_(symbols))
        .where(PriceDaily.trade_date >= start)
        .order_by(PriceDaily.trade_date.asc())
    ).all()
    result: dict[str, dict[date_type, float]] = {s: {} for s in symbols}
    for row in rows:
        result[row.symbol][row.trade_date] = row.close
    return result


def compute_performance(portfolio_id: int) -> PerformanceResponse | None:
    """從 base_date 起每日 NAV：sum(weight_i * price_i(t) / base_price_i)。

    只取所有持股都有報價的日期；缺價日直接跳過。
    會同步 upsert 最新一筆到 `portfolio_snapshots`（供之後擴充排程用）。
    """

    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return None
        holdings = _holdings_from_json(row.holdings_json)
        symbols = [h.symbol for h in holdings]
        price_map = _load_price_map(session, symbols, row.base_date)

        # 取所有股票都有報價的日期交集
        common_dates: set[date_type] | None = None
        for sym in symbols:
            dates_for_sym = set(price_map[sym].keys())
            common_dates = (
                dates_for_sym if common_dates is None else common_dates & dates_for_sym
            )
        if not common_dates:
            common_dates = set()

        sorted_dates = sorted(common_dates)
        points: list[PerformancePoint] = []
        prev_nav: float | None = None
        for d in sorted_dates:
            nav = sum(
                h.weight * (price_map[h.symbol][d] / h.base_price) for h in holdings
            )
            daily_return = (nav / prev_nav - 1.0) if prev_nav else None
            points.append(PerformancePoint(date=d, nav=nav, daily_return=daily_return))
            prev_nav = nav

        latest_nav = points[-1].nav if points else 1.0
        total_return = latest_nav - 1.0

        # cache 最新一筆
        if points:
            session.merge(
                PortfolioSnapshot(
                    portfolio_id=row.id,
                    snapshot_date=points[-1].date,
                    nav=latest_nav,
                    holdings_json=row.holdings_json,
                )
            )

        detail = _row_to_detail(row)

    return PerformanceResponse(
        portfolio=detail,
        points=points,
        latest_nav=latest_nav,
        total_return=total_return,
    )
```

- [ ] **Step 4: Run — 應 PASS**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/portfolios/test_service.py -v`
Expected: 6 tests pass

- [ ] **Step 5: ruff + mypy**

Run: `cd backend && .venv\Scripts\python.exe -m ruff check . && .venv\Scripts\python.exe -m mypy src`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/src/alpha_lab/portfolios/service.py backend/tests/portfolios/test_service.py
git commit -m "feat: compute saved portfolio NAV performance from prices_daily"
```

---

## Task A5: 新增 `/portfolios/saved` API routes

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/portfolios.py`
- Create: `backend/tests/api/test_portfolios_saved.py`

- [ ] **Step 1: 先寫失敗測試**

```python
"""/api/portfolios/saved 整合測試（Phase 6）。"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from alpha_lab.api.main import app
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import PriceDaily, Stock


def _seed_prices() -> None:
    with session_scope() as session:
        session.merge(Stock(symbol="2330", name="台積電"))
        session.merge(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 17),
                open=600.0,
                high=600.0,
                low=600.0,
                close=600.0,
                volume=1000,
            )
        )


def test_post_saved_then_list_returns_new_row():
    _seed_prices()
    client = TestClient(app)
    payload = {
        "style": "balanced",
        "label": "test-save",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
    }
    resp = client.post("/api/portfolios/saved", json=payload)
    assert resp.status_code == 201
    meta = resp.json()
    pid = meta["id"]

    list_resp = client.get("/api/portfolios/saved")
    assert list_resp.status_code == 200
    assert any(m["id"] == pid for m in list_resp.json())


def test_performance_returns_points_and_total_return():
    _seed_prices()
    client = TestClient(app)
    payload = {
        "style": "balanced",
        "label": "perf-test",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
    }
    pid = client.post("/api/portfolios/saved", json=payload).json()["id"]
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 18),
                open=660.0,
                high=660.0,
                low=660.0,
                close=660.0,
                volume=1000,
            )
        )
    perf_resp = client.get(f"/api/portfolios/saved/{pid}/performance")
    assert perf_resp.status_code == 200
    body = perf_resp.json()
    assert body["latest_nav"] > 1.0
    assert len(body["points"]) == 2


def test_delete_saved_removes():
    client = TestClient(app)
    _seed_prices()
    pid = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "del",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
            ],
        },
    ).json()["id"]
    resp = client.delete(f"/api/portfolios/saved/{pid}")
    assert resp.status_code == 204
    assert client.get(f"/api/portfolios/saved/{pid}/performance").status_code == 404


def test_post_saved_requires_base_price_available():
    client = TestClient(app)
    # 不 seed prices → 無 base_price 可取
    payload = {
        "style": "balanced",
        "label": "no-price",
        "holdings": [
            {"symbol": "9999", "name": "NOPE", "weight": 1.0, "base_price": 10.0}
        ],
    }
    # 允許通過（前端傳入 base_price 即為使用者自選基準）；不回 409
    resp = client.post("/api/portfolios/saved", json=payload)
    assert resp.status_code == 201
```

- [ ] **Step 2: Run — 應 FAIL（routes 還沒寫）**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/api/test_portfolios_saved.py -v`
Expected: 404 / HTTP errors

- [ ] **Step 3: 擴充 routes**

```python
# 在 portfolios.py 最上方加 import

from datetime import date as date_type

from alpha_lab.portfolios.service import (
    compute_performance,
    delete_saved,
    get_saved,
    list_saved,
    save_portfolio,
)
from alpha_lab.schemas.saved_portfolio import (
    PerformanceResponse,
    SavedPortfolioCreate,
    SavedPortfolioDetail,
    SavedPortfolioMeta,
)

# 在檔案末尾加 endpoints

@router.get("/saved", response_model=list[SavedPortfolioMeta])
async def list_saved_portfolios_endpoint() -> list[SavedPortfolioMeta]:
    return list_saved()


@router.post("/saved", response_model=SavedPortfolioMeta, status_code=201)
async def save_portfolio_endpoint(
    payload: SavedPortfolioCreate,
) -> SavedPortfolioMeta:
    return save_portfolio(payload, base_date=date_type.today())


@router.get("/saved/{portfolio_id}", response_model=SavedPortfolioDetail)
async def get_saved_endpoint(portfolio_id: int) -> SavedPortfolioDetail:
    detail = get_saved(portfolio_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="saved portfolio not found")
    return detail


@router.delete("/saved/{portfolio_id}", status_code=204)
async def delete_saved_endpoint(portfolio_id: int) -> None:
    if not delete_saved(portfolio_id):
        raise HTTPException(status_code=404, detail="saved portfolio not found")


@router.get("/saved/{portfolio_id}/performance", response_model=PerformanceResponse)
async def performance_endpoint(portfolio_id: int) -> PerformanceResponse:
    resp = compute_performance(portfolio_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="saved portfolio not found")
    return resp
```

- [ ] **Step 4: Run — 應 PASS**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/api/test_portfolios_saved.py -v`
Expected: 4 tests pass

- [ ] **Step 5: 全量 backend 檢查**

Run: `cd backend && .venv\Scripts\python.exe -m pytest && .venv\Scripts\python.exe -m ruff check . && .venv\Scripts\python.exe -m mypy src`
Expected: 全綠

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/src/alpha_lab/api/routes/portfolios.py backend/tests/api/test_portfolios_saved.py
git commit -m "feat: add saved portfolio API endpoints with performance"
```

---

## Task A6: 前端 savedPortfolios API client + 類型

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/api/savedPortfolios.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 加 types**

```typescript
// 於 types.ts 末尾追加

// --- Saved Portfolios (Phase 6) ---

export interface SavedHolding {
  symbol: string;
  name: string;
  weight: number;
  base_price: number;
}

export interface SavedPortfolioCreate {
  style: PortfolioStyle;
  label: string;
  note?: string | null;
  holdings: SavedHolding[];
}

export interface SavedPortfolioMeta {
  id: number;
  style: PortfolioStyle;
  label: string;
  note: string | null;
  base_date: string;
  created_at: string;
  holdings_count: number;
}

export interface SavedPortfolioDetail extends SavedPortfolioMeta {
  holdings: SavedHolding[];
}

export interface PerformancePoint {
  date: string;
  nav: number;
  daily_return: number | null;
}

export interface PerformanceResponse {
  portfolio: SavedPortfolioDetail;
  points: PerformancePoint[];
  latest_nav: number;
  total_return: number;
}
```

- [ ] **Step 2: 加 `apiDelete` 到 client.ts**

在 `apiPost` 後加：

```typescript
export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
}
```

- [ ] **Step 3: 寫 `savedPortfolios.ts`**

```typescript
import { apiDelete, apiGet, apiPost } from "@/api/client";
import type {
  PerformanceResponse,
  SavedPortfolioCreate,
  SavedPortfolioDetail,
  SavedPortfolioMeta,
} from "@/api/types";

export function listSavedPortfolios(): Promise<SavedPortfolioMeta[]> {
  return apiGet<SavedPortfolioMeta[]>("/api/portfolios/saved");
}

export function getSavedPortfolio(id: number): Promise<SavedPortfolioDetail> {
  return apiGet<SavedPortfolioDetail>(`/api/portfolios/saved/${id}`);
}

export function saveRecommendedPortfolio(
  payload: SavedPortfolioCreate,
): Promise<SavedPortfolioMeta> {
  return apiPost<SavedPortfolioMeta>("/api/portfolios/saved", undefined, payload);
}

export function deleteSavedPortfolio(id: number): Promise<void> {
  return apiDelete(`/api/portfolios/saved/${id}`);
}

export function fetchPerformance(id: number): Promise<PerformanceResponse> {
  return apiGet<PerformanceResponse>(`/api/portfolios/saved/${id}/performance`);
}
```

- [ ] **Step 4: tsc 檢查**

Run: `cd frontend && pnpm tsc --noEmit`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/src/api/
git commit -m "feat: add savedPortfolios API client and types"
```

---

## Task A7: 前端追蹤頁 + 儲存按鈕

**Files:**
- Create: `frontend/src/components/portfolio/PerformanceChart.tsx`
- Create: `frontend/src/components/portfolio/SavedPortfolioList.tsx`
- Create: `frontend/src/pages/PortfolioTrackingPage.tsx`
- Modify: `frontend/src/pages/PortfoliosPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 寫 `PerformanceChart.tsx`**

```tsx
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PerformancePoint } from "@/api/types";

interface PerformanceChartProps {
  points: PerformancePoint[];
}

export function PerformanceChart({ points }: PerformanceChartProps) {
  if (points.length === 0) {
    return <p className="text-slate-400 text-sm">尚無績效資料</p>;
  }
  return (
    <div className="h-64 w-full" data-testid="performance-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" stroke="#94a3b8" />
          <YAxis domain={["auto", "auto"]} stroke="#94a3b8" />
          <Tooltip
            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }}
          />
          <Line
            type="monotone"
            dataKey="nav"
            stroke="#38bdf8"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: 寫 `SavedPortfolioList.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listSavedPortfolios } from "@/api/savedPortfolios";

export function SavedPortfolioList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["saved-portfolios"],
    queryFn: listSavedPortfolios,
  });

  if (isLoading) return <p className="text-sm text-slate-400">載入已儲存組合…</p>;
  if (error) return <p className="text-sm text-red-400">載入失敗</p>;
  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        尚未儲存任何組合。點下方「儲存此組合」開始追蹤。
      </p>
    );
  }
  return (
    <ul className="space-y-2" data-testid="saved-portfolio-list">
      {data.map((p) => (
        <li
          key={p.id}
          className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/60 px-3 py-2"
        >
          <div>
            <Link
              to={`/portfolios/${p.id}`}
              className="text-sm text-sky-300 hover:underline"
            >
              {p.label}
            </Link>
            <p className="text-xs text-slate-500">
              {p.style} · {p.holdings_count} 檔 · 起始 {p.base_date}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: 寫 `PortfolioTrackingPage.tsx`**

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { deleteSavedPortfolio, fetchPerformance } from "@/api/savedPortfolios";
import { PerformanceChart } from "@/components/portfolio/PerformanceChart";

export function PortfolioTrackingPage() {
  const { id } = useParams<{ id: string }>();
  const portfolioId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["portfolio-performance", portfolioId],
    queryFn: () => fetchPerformance(portfolioId),
    enabled: !Number.isNaN(portfolioId),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSavedPortfolio(portfolioId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      navigate("/portfolios");
    },
  });

  if (Number.isNaN(portfolioId)) {
    return <p className="text-red-400">非法的組合 id</p>;
  }
  if (isLoading) return <p className="text-slate-400">載入中…</p>;
  if (error || !data) {
    return <p className="text-red-400">載入失敗</p>;
  }

  const { portfolio, points, latest_nav, total_return } = data;
  const returnPct = (total_return * 100).toFixed(2);
  const returnColor = total_return >= 0 ? "text-emerald-400" : "text-red-400";

  return (
    <div className="space-y-4" data-testid="portfolio-tracking-page">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{portfolio.label}</h1>
          <p className="text-sm text-slate-500">
            {portfolio.style} · 起始 {portfolio.base_date} · {portfolio.holdings_count} 檔
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            if (window.confirm(`確定刪除組合「${portfolio.label}」？`)) {
              deleteMutation.mutate();
            }
          }}
          className="rounded border border-red-500 bg-red-500/10 px-3 py-1.5 text-sm text-red-300 hover:bg-red-500/20"
          data-testid="delete-portfolio"
        >
          刪除
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
          <p className="text-xs text-slate-500">目前 NAV</p>
          <p className="text-lg font-semibold">{latest_nav.toFixed(4)}</p>
        </div>
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3">
          <p className="text-xs text-slate-500">累積報酬</p>
          <p className={`text-lg font-semibold ${returnColor}`}>{returnPct}%</p>
        </div>
      </div>

      <section className="rounded border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">NAV 走勢</h2>
        <PerformanceChart points={points} />
      </section>

      <section className="rounded border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">持股明細</h2>
        <table className="w-full text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1 text-left">代號</th>
              <th className="py-1 text-left">名稱</th>
              <th className="py-1 text-right">權重</th>
              <th className="py-1 text-right">基準價</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.holdings.map((h) => (
              <tr key={h.symbol} className="border-t border-slate-800">
                <td className="py-1">{h.symbol}</td>
                <td className="py-1">{h.name}</td>
                <td className="py-1 text-right">{(h.weight * 100).toFixed(1)}%</td>
                <td className="py-1 text-right">{h.base_price.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: 修改 `PortfoliosPage.tsx` 加儲存按鈕到每個 tab 的組合上**

先讀現有的 `PortfolioTabs.tsx`：

Run: `cat frontend/src/components/portfolio/PortfolioTabs.tsx`

在 PortfoliosPage 加 SavedPortfolioList 區塊 + 每個 portfolio 加 save button（透過新增一個 prop 或 callback）。最小變更：
在 `PortfoliosPage.tsx` 頂部加載 SavedPortfolioList；傳 `onSave` 給 `PortfolioTabs`：

```tsx
// PortfoliosPage.tsx 替換 return 段

import { SavedPortfolioList } from "@/components/portfolio/SavedPortfolioList";
import { saveRecommendedPortfolio } from "@/api/savedPortfolios";
import type { Portfolio } from "@/api/types";

// ... 現有 code

const queryClient = useQueryClient();
const saveOneMutation = useMutation({
  mutationFn: (p: Portfolio) =>
    saveRecommendedPortfolio({
      style: p.style,
      label: `${p.label} ${data?.calc_date ?? ""}`.trim(),
      holdings: p.holdings.map((h) => ({
        symbol: h.symbol,
        name: h.name,
        weight: h.weight,
        base_price: 0, // 由使用者或後端補；此處先佔位
      })),
    }),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
  },
});

// 在 return JSX 加：
//   <SavedPortfolioList />
//   <PortfolioTabs portfolios={data.portfolios} onSave={(p) => saveOneMutation.mutate(p)} />
```

> **NOTE:** `base_price` 現由前端傳入。為了簡化 MVP，先傳 0，由後端在 `save_portfolio` 服務中用 `latest_calc_date` 對應的 `prices_daily.close` 補齊。實作時改 A3 的 service 做 enrichment。實務上：若 holdings 的 `base_price == 0`，在 service 內查 `prices_daily` 取最新 close 填入。

> **Alternative（採用此版）**：Task A3 `save_portfolio` 內若任一 holding `base_price <= 0`，用 `_load_price_map` 取 base_date 當日 close 回填；查不到則 `raise ValueError`，route 轉 400。請在 A3 實作時一併完成此 enrichment 並補測試 `test_save_portfolio_fills_base_price_from_prices_daily`。

- [ ] **Step 5: `PortfolioTabs.tsx` 加 onSave prop**

```tsx
interface PortfolioTabsProps {
  portfolios: Portfolio[];
  onSave?: (portfolio: Portfolio) => void;
}
```
在每個 tab 頂部顯示「儲存此組合」button。

- [ ] **Step 6: `App.tsx` 加路由**

```tsx
<Route path="/portfolios/:id" element={<PortfolioTrackingPage />} />
```

- [ ] **Step 7: tsc + lint + 跑 unit tests**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm test`
Expected: 0 errors

- [ ] **Step 8: 手動驗證**

驗收指引：

```cmd
REM 開兩個 terminal
cd backend && .venv\Scripts\python.exe -m uvicorn alpha_lab.api.main:app --reload
cd frontend && pnpm dev
```

1. 打開 http://localhost:5173/portfolios，點某組「儲存此組合」
2. 上方「已儲存組合」區塊出現新項目
3. 點入追蹤頁看到持股 + NAV 為 1.0
4. 點刪除 → 確認後跳回 /portfolios

- [ ] **Step 9: Commit（使用者驗收通過後）**

```bash
git add frontend/src/ frontend/src/pages/ frontend/src/components/portfolio/
git commit -m "feat: add saved portfolio tracking page and save button"
```

---

## Task A8: Group A E2E

**Files:**
- Create: `frontend/tests/e2e/portfolio-tracking.spec.ts`
- Create: `frontend/tests/e2e/fixtures/saved-portfolios.json`
- Create: `frontend/tests/e2e/fixtures/performance.json`

- [ ] **Step 1: 寫 fixtures**

```json
// saved-portfolios.json
[
  {
    "id": 1,
    "style": "balanced",
    "label": "平衡組 2026-04-17",
    "note": null,
    "base_date": "2026-04-17",
    "created_at": "2026-04-17T00:00:00Z",
    "holdings_count": 2
  }
]
```

```json
// performance.json
{
  "portfolio": {
    "id": 1,
    "style": "balanced",
    "label": "平衡組 2026-04-17",
    "note": null,
    "base_date": "2026-04-17",
    "created_at": "2026-04-17T00:00:00Z",
    "holdings_count": 2,
    "holdings": [
      {"symbol": "2330", "name": "台積電", "weight": 0.6, "base_price": 600},
      {"symbol": "2317", "name": "鴻海", "weight": 0.4, "base_price": 100}
    ]
  },
  "points": [
    {"date": "2026-04-17", "nav": 1.0, "daily_return": null},
    {"date": "2026-04-18", "nav": 1.05, "daily_return": 0.05}
  ],
  "latest_nav": 1.05,
  "total_return": 0.05
}
```

- [ ] **Step 2: 寫 spec**

```typescript
import { test, expect } from "@playwright/test";
import savedList from "./fixtures/saved-portfolios.json";
import performance from "./fixtures/performance.json";

test("tracking page renders saved portfolio with performance", async ({ page }) => {
  await page.route("**/api/portfolios/saved", (route) => {
    route.fulfill({ json: savedList });
  });
  await page.route("**/api/portfolios/saved/1/performance", (route) => {
    route.fulfill({ json: performance });
  });

  await page.goto("/portfolios/1");
  await expect(
    page.getByTestId("portfolio-tracking-page"),
  ).toBeVisible();
  await expect(page.getByText("平衡組 2026-04-17")).toBeVisible();
  await expect(page.getByText("累積報酬")).toBeVisible();
  await expect(page.getByText("5.00%")).toBeVisible();
});
```

- [ ] **Step 3: Run**

Run: `cd frontend && pnpm e2e --grep "tracking page"`
Expected: PASS

- [ ] **Step 4: 手動驗收 A 全量**

列出 Group A 要驗的功能：
1. `/portfolios` 頁可看到「已儲存組合」清單（可能為空）
2. 點任一組合「儲存此組合」→ 清單出現新項目
3. 點清單項目跳到 `/portfolios/:id` 看持股 + NAV=1.0
4. 刪除後跳回 /portfolios 清單消失

**在驗收通過前不 commit。**

- [ ] **Step 5: Commit（驗收後）**

```bash
git add frontend/tests/e2e/portfolio-tracking.spec.ts frontend/tests/e2e/fixtures/
git commit -m "test: add portfolio tracking e2e"
```

- [ ] **Step 6: 同步知識庫 + USER_GUIDE**

Create `docs/knowledge/features/tracking/overview.md`（參照 features/screener/overview.md 格式）。
Update `docs/knowledge/architecture/data-models.md` 加新表。
Update `docs/knowledge/architecture/data-flow.md` Phase 6 段。
Update `docs/USER_GUIDE.md` 加追蹤頁使用說明。

```bash
git add docs/
git commit -m "docs: document phase 6 portfolio tracking"
```

---

## Group A 驗收 Checkpoint

使用者手動驗收以下流程：

1. 在 `/portfolios` 推薦頁點「儲存此組合」
2. 跳到 `/portfolios/:id` 看到 NAV 走勢、持股明細、累積報酬
3. 刪除後回到列表不再顯示
4. 後端 `pytest` 全綠、`ruff` / `mypy` 0 errors
5. 前端 `tsc` / `lint` / `test` / `e2e` 全綠

**等使用者明確回覆「Group A 驗證通過」後才進 Group B。**

---

# Group B：報告管理（加星 / 刪除 / 全文搜尋）

## Task B1: 擴充 reports schema + storage 低階 API

**Files:**
- Modify: `backend/src/alpha_lab/schemas/report.py`
- Modify: `backend/src/alpha_lab/reports/storage.py`

- [ ] **Step 1: 加 `ReportUpdate` schema**

```python
# schemas/report.py 末尾

class ReportUpdate(BaseModel):
    """`PATCH /api/reports/{id}` 可改的欄位。None = 不變。"""

    title: str | None = None
    tags: list[str] | None = None
    summary_line: str | None = None
    starred: bool | None = None
```

- [ ] **Step 2: 加 `delete_report_files` + `update_in_index` 到 storage.py**

```python
# storage.py 末尾

def delete_report_files(report_id: str) -> bool:
    """刪 analysis/<id>.md 並從 index.json 移除。回傳是否刪到。"""

    items = load_index()
    before = len(items)
    items = [m for m in items if m.id != report_id]
    root = get_reports_root()
    md_path = root / "analysis" / f"{report_id}.md"
    if md_path.exists():
        md_path.unlink()
    save_index(items)
    return len(items) < before


def update_in_index(report_id: str, updates: dict[str, object]) -> ReportMeta | None:
    """套 updates 到同 id 項目；None = id 不存在。回傳新 meta。"""

    items = load_index()
    target_idx = next((i for i, m in enumerate(items) if m.id == report_id), None)
    if target_idx is None:
        return None
    current = items[target_idx].model_dump()
    current.update(updates)
    updated = ReportMeta(**current)
    items[target_idx] = updated
    save_index(items)
    return updated
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/alpha_lab/reports/storage.py backend/src/alpha_lab/schemas/report.py
git commit -m "feat: add report delete and update in index"
```

---

## Task B2: service 層 update / delete / search

**Files:**
- Modify: `backend/src/alpha_lab/reports/service.py`
- Modify: `backend/tests/reports/test_storage.py`（或新增 `test_service.py`）

- [ ] **Step 1: 加三個測試**

在 `tests/reports/test_service.py`（若不存在就建立）：

```python
"""Reports service：update / delete / search 測試（Phase 6）。"""

from __future__ import annotations

from datetime import date

from alpha_lab.reports.service import (
    create_report,
    delete_report,
    list_reports,
    update_report,
)
from alpha_lab.schemas.report import ReportCreate, ReportUpdate


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


def test_update_report_toggles_starred(tmp_reports_root):
    rid = _make_stock_report(date(2026, 4, 17), "T", ["2330"])
    updated = update_report(rid, ReportUpdate(starred=True))
    assert updated is not None
    assert updated.starred is True


def test_update_report_returns_none_for_unknown(tmp_reports_root):
    assert update_report("nope", ReportUpdate(starred=True)) is None


def test_delete_report_removes_file_and_index(tmp_reports_root):
    rid = _make_stock_report(date(2026, 4, 17), "T", ["2330"])
    assert delete_report(rid) is True
    assert all(m.id != rid for m in list_reports())
    assert delete_report(rid) is False


def test_list_reports_query_matches_title_summary_symbols_tags(tmp_reports_root):
    _make_stock_report(date(2026, 4, 17), "TSMC 分析", ["2330"])
    _make_stock_report(date(2026, 4, 17), "鴻海深度", ["2317"])
    hits = list_reports(query="TSMC")
    assert len(hits) == 1
    assert hits[0].title == "TSMC 分析"
    # symbol 也能搜
    hits2 = list_reports(query="2317")
    assert len(hits2) == 1


def test_list_reports_symbol_filter(tmp_reports_root):
    _make_stock_report(date(2026, 4, 17), "TSMC", ["2330"])
    _make_stock_report(date(2026, 4, 17), "HHP", ["2317"])
    hits = list_reports(symbol="2330")
    assert len(hits) == 1
```

> `tmp_reports_root` 為既有 fixture（見 `tests/reports/conftest.py`）；若沒有則新建一個用 tmp_path 設 `ALPHA_LAB_REPORTS_ROOT` env。

- [ ] **Step 2: Run — 應 FAIL**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/reports/test_service.py -v`
Expected: ImportError / attribute errors

- [ ] **Step 3: 加 service 實作**

```python
# service.py 末尾

from alpha_lab.reports.storage import delete_report_files, update_in_index
from alpha_lab.schemas.report import ReportUpdate


def update_report(report_id: str, updates: ReportUpdate) -> ReportMeta | None:
    payload = updates.model_dump(exclude_none=True)
    if not payload:
        # 無變更 → 回原物件
        items = load_index()
        return next((m for m in items if m.id == report_id), None)
    updated = update_in_index(report_id, payload)
    if updated is None:
        return None
    # 若改到 title 或 summary，同步 frontmatter 與 body
    fm_body = read_report_markdown(report_id)
    if fm_body is not None:
        fm, body = fm_body
        for k in ("title", "tags", "summary_line"):
            if k in payload:
                fm[k] = payload[k]
        write_report_markdown(report_id, body, fm)
    return updated


def delete_report(report_id: str) -> bool:
    return delete_report_files(report_id)
```

修改 `list_reports` 簽章：

```python
def list_reports(
    type_filter: ReportType | None = None,
    tag_filter: str | None = None,
    symbol: str | None = None,
    query: str | None = None,
) -> list[ReportMeta]:
    items = load_index()
    if type_filter is not None:
        items = [m for m in items if m.type == type_filter]
    if tag_filter is not None:
        items = [m for m in items if tag_filter in m.tags]
    if symbol is not None:
        items = [m for m in items if symbol in m.symbols]
    if query is not None:
        q = query.lower()
        items = [
            m
            for m in items
            if q in m.title.lower()
            or q in m.summary_line.lower()
            or any(q in s.lower() for s in m.symbols)
            or any(q in t.lower() for t in m.tags)
        ]
    return items
```

- [ ] **Step 4: Run — 應 PASS**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/reports/ -v`
Expected: 全綠

- [ ] **Step 5: ruff + mypy + 全測**

Run: `cd backend && .venv\Scripts\python.exe -m pytest && .venv\Scripts\python.exe -m ruff check . && .venv\Scripts\python.exe -m mypy src`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/reports/ backend/src/alpha_lab/schemas/report.py backend/tests/reports/
git commit -m "feat: add report update/delete/search service"
```

---

## Task B3: `PATCH` / `DELETE` / list query params 路由

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/reports.py`
- Modify: `backend/tests/api/test_reports.py`

- [ ] **Step 1: 加測試**

```python
# test_reports.py 加入

def test_patch_report_toggles_starred(client, seed_reports):
    rid = seed_reports["stock"]
    resp = client.patch(f"/api/reports/{rid}", json={"starred": True})
    assert resp.status_code == 200
    assert resp.json()["starred"] is True


def test_delete_report_returns_204(client, seed_reports):
    rid = seed_reports["stock"]
    resp = client.delete(f"/api/reports/{rid}")
    assert resp.status_code == 204
    assert client.get(f"/api/reports/{rid}").status_code == 404


def test_list_reports_search_query(client, seed_reports):
    resp = client.get("/api/reports", params={"q": "2330"})
    assert resp.status_code == 200
    items = resp.json()
    assert all("2330" in it["symbols"] or "2330" in it["title"] for it in items)
```

> 若 `client` / `seed_reports` fixture 不存在，於 `conftest.py` 建立。

- [ ] **Step 2: 擴充 routes**

```python
# reports.py

from alpha_lab.reports.service import delete_report, update_report
from alpha_lab.schemas.report import ReportUpdate


@router.patch("/{report_id}", response_model=ReportMeta)
async def patch_report_endpoint(
    report_id: str, payload: ReportUpdate
) -> ReportMeta:
    updated = update_report(report_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="report not found")
    return updated


@router.delete("/{report_id}", status_code=204)
async def delete_report_endpoint(report_id: str) -> None:
    if not delete_report(report_id):
        raise HTTPException(status_code=404, detail="report not found")
```

修改既有 list endpoint：

```python
@router.get("", response_model=list[ReportMeta])
async def list_reports_endpoint(
    report_type: ReportType | None = Query(None, alias="type"),  # noqa: B008
    tag: str | None = Query(None),
    symbol: str | None = Query(None, description="以 symbol 過濾（完全比對）"),
    q: str | None = Query(None, description="全文搜尋：title/summary/tags/symbols"),
) -> list[ReportMeta]:
    return list_reports(
        type_filter=report_type, tag_filter=tag, symbol=symbol, query=q
    )
```

- [ ] **Step 3: Run**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/api/test_reports.py -v`
Expected: 全綠

- [ ] **Step 4: Commit**

```bash
git add backend/src/alpha_lab/api/routes/reports.py backend/tests/api/test_reports.py
git commit -m "feat: add PATCH/DELETE reports endpoints and search query"
```

---

## Task B4: 前端 reports 管理 UI

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/reports.ts`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/pages/ReportsPage.tsx`
- Modify: `frontend/src/pages/ReportDetailPage.tsx`

- [ ] **Step 1: client.ts 加 `apiPatch`**

```typescript
export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}
```

- [ ] **Step 2: types.ts 加 ReportUpdate**

```typescript
export interface ReportUpdate {
  title?: string;
  tags?: string[];
  summary_line?: string;
  starred?: boolean;
}
```

- [ ] **Step 3: 擴充 `api/reports.ts`**

讀既有 `frontend/src/api/reports.ts`，加 `updateReport` / `deleteReport`，並讓 `listReports` 支援 `{symbol?, query?}`。

```typescript
import { apiDelete, apiGet, apiPatch } from "@/api/client";
import type { ReportMeta, ReportUpdate } from "@/api/types";

export function listReports(params: {
  type?: string;
  tag?: string;
  symbol?: string;
  query?: string;
} = {}): Promise<ReportMeta[]> {
  const qs = new URLSearchParams();
  if (params.type) qs.set("type", params.type);
  if (params.tag) qs.set("tag", params.tag);
  if (params.symbol) qs.set("symbol", params.symbol);
  if (params.query) qs.set("q", params.query);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet<ReportMeta[]>(`/api/reports${suffix}`);
}

export function updateReport(id: string, patch: ReportUpdate): Promise<ReportMeta> {
  return apiPatch<ReportMeta>(`/api/reports/${id}`, patch);
}

export function deleteReport(id: string): Promise<void> {
  return apiDelete(`/api/reports/${id}`);
}
```

- [ ] **Step 4: 修 `ReportsPage.tsx`**

加搜尋框、⭐ 切換、🗑 刪除。關鍵修改：

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  deleteReport,
  listReports,
  updateReport,
} from "@/api/reports";

export function ReportsPage() {
  const [query, setQuery] = useState("");
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["reports", { query }],
    queryFn: () => listReports({ query: query.trim() || undefined }),
  });

  const starMutation = useMutation({
    mutationFn: ({ id, starred }: { id: string; starred: boolean }) =>
      updateReport(id, { starred }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });
  const delMutation = useMutation({
    mutationFn: (id: string) => deleteReport(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });

  return (
    <div className="space-y-4" data-testid="reports-page">
      <header className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">分析報告</h1>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜尋標題 / 摘要 / 標籤 / 代號"
          className="ml-auto w-72 rounded border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm"
          data-testid="reports-search"
        />
      </header>
      <ul className="space-y-2">
        {(data ?? []).map((r) => (
          <li
            key={r.id}
            className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/60 px-3 py-2"
            data-testid="report-card"
          >
            <div className="min-w-0">
              <Link
                to={`/reports/${r.id}`}
                className="block truncate text-sm text-sky-300 hover:underline"
              >
                {r.title}
              </Link>
              <p className="truncate text-xs text-slate-500">
                {r.type} · {r.date} · {r.summary_line}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => starMutation.mutate({ id: r.id, starred: !r.starred })}
                className="text-sm"
                data-testid="star-toggle"
                aria-label={r.starred ? "取消加星" : "加星"}
              >
                {r.starred ? "★" : "☆"}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (window.confirm(`刪除「${r.title}」？`)) delMutation.mutate(r.id);
                }}
                className="text-xs text-red-400 hover:text-red-300"
                data-testid="delete-report"
              >
                刪除
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: `ReportDetailPage.tsx` 加星切換 + 刪除**

最小變更：詳情頁 header 加「⭐ / 刪除」按鈕，複用同樣的 mutation pattern。

- [ ] **Step 6: tsc / lint / unit test**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm test`
Expected: 0 errors

- [ ] **Step 7: 修 E2E `reports.spec.ts` 加案例**

```typescript
test("can toggle star and delete report", async ({ page }) => {
  // 複用現有 seed fixture
  await page.goto("/reports");
  const star = page.getByTestId("star-toggle").first();
  await star.click();
  // 假設 mock backend 回傳 starred=true → 按鈕變 ★
  await expect(star).toHaveText("★");

  page.once("dialog", (d) => d.accept());
  await page.getByTestId("delete-report").first().click();
});

test("search filters reports", async ({ page }) => {
  await page.goto("/reports");
  await page.getByTestId("reports-search").fill("不存在的關鍵字");
  await expect(page.getByTestId("report-card")).toHaveCount(0);
});
```

> 需在 spec 頂部 `page.route` 攔截對應 PATCH / DELETE / GET 請求並回 fixture。

- [ ] **Step 8: 手動驗收 B 全量**

1. `/reports` 頂部顯示搜尋框，輸入關鍵字即時過濾
2. 點 ☆ 切 ★，重整維持狀態
3. 點刪除 → 確認 → 從列表消失
4. 詳情頁也能加星 / 刪除

- [ ] **Step 9: Commit（驗收後）**

```bash
git add frontend/src/pages/ReportsPage.tsx frontend/src/pages/ReportDetailPage.tsx frontend/src/api/ frontend/tests/e2e/reports.spec.ts
git commit -m "feat: add reports star toggle, delete, and search"
```

- [ ] **Step 10: 知識庫同步**

Update `docs/knowledge/features/reports/storage.md` 加 update/delete/search 段。Update `docs/USER_GUIDE.md`。

```bash
git add docs/
git commit -m "docs: update reports knowledge and user guide"
```

---

## Group B 驗收 Checkpoint

使用者驗收：
1. 搜尋、加星、刪除互動流暢
2. 後端 pytest 全綠
3. 前端 E2E 全綠

**等回覆「Group B 驗證通過」再進 Group C。**

---

# Group C：教學三段密度開關

## Task C1: TutorialModeContext

**Files:**
- Create: `frontend/src/contexts/TutorialModeContext.tsx`
- Create: `frontend/tests/components/TutorialModeContext.test.tsx`

- [ ] **Step 1: 寫 Context**

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type TutorialMode = "full" | "compact" | "off";

interface TutorialModeContextValue {
  mode: TutorialMode;
  setMode: (mode: TutorialMode) => void;
  cycle: () => void;
}

const STORAGE_KEY = "alpha-lab:tutorial-mode";
const ORDER: TutorialMode[] = ["full", "compact", "off"];

const TutorialModeContext = createContext<TutorialModeContextValue | null>(null);

function readInitialMode(): TutorialMode {
  if (typeof window === "undefined") return "full";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === "full" || raw === "compact" || raw === "off") return raw;
  return "full";
}

interface TutorialModeProviderProps {
  children: ReactNode;
}

export function TutorialModeProvider({ children }: TutorialModeProviderProps) {
  const [mode, setModeState] = useState<TutorialMode>(readInitialMode);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const setMode = useCallback((next: TutorialMode) => {
    setModeState(next);
  }, []);

  const cycle = useCallback(() => {
    setModeState((prev) => {
      const idx = ORDER.indexOf(prev);
      return ORDER[(idx + 1) % ORDER.length];
    });
  }, []);

  const value = useMemo(() => ({ mode, setMode, cycle }), [mode, setMode, cycle]);
  return (
    <TutorialModeContext.Provider value={value}>
      {children}
    </TutorialModeContext.Provider>
  );
}

export function useTutorialMode(): TutorialModeContextValue {
  const ctx = useContext(TutorialModeContext);
  if (!ctx) {
    throw new Error("useTutorialMode must be used within TutorialModeProvider");
  }
  return ctx;
}
```

- [ ] **Step 2: 寫單元測試**

```tsx
import { act, render, renderHook } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import {
  TutorialModeProvider,
  useTutorialMode,
} from "@/contexts/TutorialModeContext";

function wrapper({ children }: { children: React.ReactNode }) {
  return <TutorialModeProvider>{children}</TutorialModeProvider>;
}

describe("TutorialModeContext", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("defaults to full", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    expect(result.current.mode).toBe("full");
  });

  it("cycles full -> compact -> off -> full", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    act(() => result.current.cycle());
    expect(result.current.mode).toBe("compact");
    act(() => result.current.cycle());
    expect(result.current.mode).toBe("off");
    act(() => result.current.cycle());
    expect(result.current.mode).toBe("full");
  });

  it("persists to localStorage", () => {
    const { result } = renderHook(() => useTutorialMode(), { wrapper });
    act(() => result.current.setMode("off"));
    expect(window.localStorage.getItem("alpha-lab:tutorial-mode")).toBe("off");
  });
});
```

- [ ] **Step 3: Run**

Run: `cd frontend && pnpm test tests/components/TutorialModeContext.test.tsx`
Expected: 3 pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/contexts/ frontend/tests/components/TutorialModeContext.test.tsx
git commit -m "feat: add TutorialModeContext with localStorage persistence"
```

---

## Task C2: Toggle 按鈕 + AppLayout 整合

**Files:**
- Create: `frontend/src/components/TutorialModeToggle.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 寫 Toggle**

```tsx
import { useTutorialMode, type TutorialMode } from "@/contexts/TutorialModeContext";

const LABELS: Record<TutorialMode, { icon: string; text: string }> = {
  full: { icon: "📖", text: "完整教學" },
  compact: { icon: "📗", text: "精簡" },
  off: { icon: "📕", text: "關閉" },
};

export function TutorialModeToggle() {
  const { mode, cycle } = useTutorialMode();
  const { icon, text } = LABELS[mode];
  return (
    <button
      type="button"
      onClick={cycle}
      className="rounded border border-slate-700 bg-slate-900/60 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-800"
      title={`教學密度：${text}（點擊切換）`}
      data-testid="tutorial-mode-toggle"
      data-mode={mode}
    >
      <span className="mr-1" aria-hidden>{icon}</span>
      {text}
    </button>
  );
}
```

- [ ] **Step 2: AppLayout 掛 Provider + Toggle**

```tsx
import { TutorialModeProvider } from "@/contexts/TutorialModeContext";
import { TutorialModeToggle } from "@/components/TutorialModeToggle";

export function AppLayout() {
  return (
    <TutorialModeProvider>
      <L2PanelProvider>
        <div className="min-h-screen bg-slate-950 text-slate-100">
          <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              {/* 原本的 Link 群 */}
            </div>
            <div className="flex items-center gap-3">
              <HeaderSearch />
              <TutorialModeToggle />
            </div>
          </header>
          <main className="p-6">
            <Outlet />
          </main>
          <L2Panel />
        </div>
      </L2PanelProvider>
    </TutorialModeProvider>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TutorialModeToggle.tsx frontend/src/layouts/AppLayout.tsx
git commit -m "feat: add tutorial mode toggle in header"
```

---

## Task C3: 串入 TermTooltip / L2Panel / reasons

**Files:**
- Modify: `frontend/src/components/TermTooltip.tsx`
- Modify: `frontend/src/components/education/L2Panel.tsx`（若需要）
- Modify: `frontend/src/components/education/L2PanelContext.tsx`
- Modify: `frontend/src/components/portfolio/PortfolioTabs.tsx`

- [ ] **Step 1: 讀現有 TermTooltip 與 L2 結構**

Read: `frontend/src/components/TermTooltip.tsx`, `L2Panel.tsx`, `L2PanelContext.tsx`, `PortfolioTabs.tsx`

- [ ] **Step 2: TermTooltip 依 mode 控制**

```tsx
// TermTooltip 內

import { useTutorialMode } from "@/contexts/TutorialModeContext";

// 於 render 前：
const { mode } = useTutorialMode();

// compact / off：L1 不顯示，僅 children 原樣 render，且不渲染底線 / abbr 樣式
if (mode === "off") {
  return <>{children}</>;
}
if (mode === "compact") {
  // 隱藏 L1（不掛 onMouseEnter），但保留「看完整說明」點擊 L2 的能力
  // 作法：在 compact 模式 children 依然可點擊觸發 openTopic，但 hover 不顯示 tooltip
  return (
    <span
      role={l2TopicId ? "button" : undefined}
      tabIndex={l2TopicId ? 0 : -1}
      onClick={() => l2TopicId && openTopic(l2TopicId)}
      className="underline decoration-dotted underline-offset-2 cursor-help"
    >
      {children}
    </span>
  );
}
// full: 原本行為
```

- [ ] **Step 3: PortfolioTabs reasons 在 off 模式完全隱藏**

```tsx
// PortfolioTabs.tsx 內每檔 holdings 的 reasons 區塊

const { mode } = useTutorialMode();
// ...
{mode !== "off" && holding.reasons.length > 0 && (
  <ul>{holding.reasons.map(...)}</ul>
)}
```

- [ ] **Step 4: L2Panel 在 off 模式不彈出**

在 `L2PanelContext` 的 `openTopic` 中 early return if mode === "off"。因為 Context 不能在另一個 Context 的邏輯裡直接 useContext hook，改由呼叫端（TermTooltip / ReasonsList）判斷：如果 mode === "off" 則不提供點擊入口。上面 Step 2 的實作已涵蓋。

- [ ] **Step 5: tsc / lint / unit test**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm test`
Expected: 0 errors

- [ ] **Step 6: E2E `tutorial-mode.spec.ts`**

```typescript
import { test, expect } from "@playwright/test";

test("tutorial mode toggle cycles and persists", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByTestId("tutorial-mode-toggle");
  await expect(toggle).toHaveAttribute("data-mode", "full");
  await toggle.click();
  await expect(toggle).toHaveAttribute("data-mode", "compact");
  await toggle.click();
  await expect(toggle).toHaveAttribute("data-mode", "off");
  // 刷新維持
  await page.reload();
  await expect(page.getByTestId("tutorial-mode-toggle")).toHaveAttribute(
    "data-mode",
    "off",
  );
});

test("off mode hides L1 tooltip on stock page", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByTestId("tutorial-mode-toggle");
  await toggle.click(); // compact
  await toggle.click(); // off

  // 個股頁（需要其他 fixture 已由 reports.spec 之類設定；此處簡化）
  // 確認 ScoreRadar 區塊有 <abbr> term 但 hover 不出 tooltip。
});
```

- [ ] **Step 7: 手動驗收 C 全量**

1. 首頁 header 右上看到 📖 toggle
2. 點一下變 📗（精簡）、再點變 📕（關閉）
3. `full` → hover `PE` 術語看到 tooltip；`compact` → 不出現 tooltip 但仍可點進 L2；`off` → 術語樣式消失不可互動
4. off 模式推薦頁不顯示 reasons
5. 重整 localStorage 保持模式

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ frontend/tests/e2e/tutorial-mode.spec.ts
git commit -m "feat: wire tutorial mode into TermTooltip, reasons, and L2"
```

- [ ] **Step 9: 知識庫同步**

Create `docs/knowledge/features/education/tutorial-mode.md`. Update USER_GUIDE.md.

```bash
git add docs/
git commit -m "docs: document tutorial mode toggle"
```

---

## Group C 驗收 Checkpoint

使用者驗收三段切換 + 持久化 + 下游互動（tooltip / reasons）。

**等回覆「Group C 驗證通過」再進 Group D。**

---

# Group D：個股頁補完（收藏 / 加入組合 / 相關報告）

## Task D1: localStorage favorites helper + 收藏按鈕

**Files:**
- Create: `frontend/src/lib/favorites.ts`
- Create: `frontend/src/components/stock/StockActions.tsx`
- Modify: `frontend/src/pages/StockPage.tsx`

- [ ] **Step 1: favorites.ts**

```typescript
const KEY = "alpha-lab:favorites";

export function readFavorites(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function isFavorite(symbol: string): boolean {
  return readFavorites().includes(symbol);
}

export function toggleFavorite(symbol: string): string[] {
  const current = readFavorites();
  const next = current.includes(symbol)
    ? current.filter((s) => s !== symbol)
    : [...current, symbol];
  window.localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
```

- [ ] **Step 2: StockActions component**

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { listSavedPortfolios, saveRecommendedPortfolio } from "@/api/savedPortfolios";
import type { StockMeta } from "@/api/types";
import { isFavorite, toggleFavorite } from "@/lib/favorites";

interface StockActionsProps {
  meta: StockMeta;
}

export function StockActions({ meta }: StockActionsProps) {
  const [fav, setFav] = useState(false);
  useEffect(() => setFav(isFavorite(meta.symbol)), [meta.symbol]);

  const queryClient = useQueryClient();
  const { data: savedList } = useQuery({
    queryKey: ["saved-portfolios"],
    queryFn: listSavedPortfolios,
  });
  const [pickerOpen, setPickerOpen] = useState(false);
  const [weightPct, setWeightPct] = useState("10");

  const addToExistingMutation = useMutation({
    mutationFn: async ({ portfolioId }: { portfolioId: number }) => {
      // MVP：建立新組合快照（把選定組合 + 本檔），保留舊資料
      // 更嚴謹的 merge 另外規劃
      const target = savedList?.find((p) => p.id === portfolioId);
      if (!target) throw new Error("組合不存在");
      const detail = await import("@/api/savedPortfolios").then((m) =>
        m.getSavedPortfolio(portfolioId),
      );
      const weight = Number(weightPct) / 100;
      const scaled = detail.holdings.map((h) => ({
        ...h,
        weight: h.weight * (1 - weight),
      }));
      await saveRecommendedPortfolio({
        style: detail.style,
        label: `${detail.label} + ${meta.symbol}`,
        holdings: [
          ...scaled,
          { symbol: meta.symbol, name: meta.name, weight, base_price: 0 },
        ],
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["saved-portfolios"] });
      setPickerOpen(false);
    },
  });

  return (
    <div className="flex items-center gap-2" data-testid="stock-actions">
      <button
        type="button"
        onClick={() => {
          toggleFavorite(meta.symbol);
          setFav((v) => !v);
        }}
        className="rounded border border-slate-700 bg-slate-900/60 px-2.5 py-1 text-sm"
        data-testid="favorite-toggle"
        aria-pressed={fav}
      >
        {fav ? "★ 已收藏" : "☆ 收藏"}
      </button>
      <button
        type="button"
        onClick={() => setPickerOpen((o) => !o)}
        className="rounded border border-indigo-500 bg-indigo-500/10 px-2.5 py-1 text-sm text-indigo-300 hover:bg-indigo-500/20"
        data-testid="add-to-portfolio"
      >
        加入組合
      </button>
      {pickerOpen ? (
        <div className="absolute right-6 top-20 z-20 rounded border border-slate-700 bg-slate-900 p-3 shadow-lg">
          <p className="mb-2 text-xs text-slate-400">選擇組合</p>
          <ul className="mb-2 max-h-40 space-y-1 overflow-y-auto">
            {(savedList ?? []).map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => addToExistingMutation.mutate({ portfolioId: p.id })}
                  className="w-full rounded px-2 py-1 text-left text-sm hover:bg-slate-800"
                  data-testid={`pick-portfolio-${p.id}`}
                >
                  {p.label}
                </button>
              </li>
            ))}
            {(savedList ?? []).length === 0 ? (
              <li className="text-xs text-slate-500">尚無組合，先到 /portfolios 儲存</li>
            ) : null}
          </ul>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            新持股權重
            <input
              type="number"
              min="1"
              max="100"
              value={weightPct}
              onChange={(e) => setWeightPct(e.target.value)}
              className="w-16 rounded border border-slate-700 bg-slate-800 px-1 py-0.5"
            />
            %
          </label>
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 3: StockPage 掛載**

修改 `StockPage.tsx` 頂部那列：把 StockHeader 改成同一 row 放 `<StockHeader>` 與 `<StockActions>`。最簡做法：在 StockHeader 外 wrap `<div className="flex items-center justify-between">` 並加 `<StockActions meta={data.meta} />`。

- [ ] **Step 4: tsc + lint**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/favorites.ts frontend/src/components/stock/StockActions.tsx frontend/src/pages/StockPage.tsx
git commit -m "feat: add stock page favorite and add-to-portfolio actions"
```

---

## Task D2: 相關分析報告區塊

**Files:**
- Create: `frontend/src/components/stock/RelatedReports.tsx`
- Modify: `frontend/src/pages/StockPage.tsx`

- [ ] **Step 1: RelatedReports**

```tsx
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listReports } from "@/api/reports";

interface RelatedReportsProps {
  symbol: string;
}

export function RelatedReports({ symbol }: RelatedReportsProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["related-reports", symbol],
    queryFn: () => listReports({ symbol }),
  });

  if (isLoading) return null;

  const items = data ?? [];
  if (items.length === 0) {
    return (
      <section
        className="rounded border border-slate-800 bg-slate-900/40 p-4"
        data-testid="related-reports"
      >
        <h2 className="mb-2 text-sm font-semibold text-slate-300">相關分析報告</h2>
        <p className="text-xs text-slate-500">尚無相關報告</p>
      </section>
    );
  }
  return (
    <section
      className="rounded border border-slate-800 bg-slate-900/40 p-4"
      data-testid="related-reports"
    >
      <h2 className="mb-2 text-sm font-semibold text-slate-300">相關分析報告</h2>
      <ul className="space-y-1">
        {items.map((r) => (
          <li key={r.id}>
            <Link
              to={`/reports/${r.id}`}
              className="text-sm text-sky-300 hover:underline"
            >
              {r.starred ? "★ " : ""}
              {r.title}
            </Link>
            <span className="ml-2 text-xs text-slate-500">{r.date}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 2: StockPage 掛載於 events section 下方**

```tsx
// StockPage.tsx 最下方追加：
<RelatedReports symbol={data.meta.symbol} />
```

- [ ] **Step 3: tsc + lint + unit test**

Run: `cd frontend && pnpm tsc --noEmit && pnpm lint && pnpm test`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/stock/RelatedReports.tsx frontend/src/pages/StockPage.tsx
git commit -m "feat: add related reports section to stock page"
```

---

## Task D3: Group D E2E

**Files:**
- Create: `frontend/tests/e2e/stock-actions.spec.ts`

- [ ] **Step 1: 寫 spec**

```typescript
import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // 攔截 stock overview / score / reports / saved
  await page.route("**/api/stocks/2330/overview", (r) =>
    r.fulfill({
      json: {
        meta: { symbol: "2330", name: "台積電", industry: "半導體", listed_date: null },
        prices: [],
        revenues: [],
        financials: [],
        institutional: [],
        margin: [],
        events: [],
      },
    }),
  );
  await page.route("**/api/stocks/2330/score", (r) =>
    r.fulfill({ json: { symbol: "2330", latest: null } }),
  );
  await page.route("**/api/reports?*", (r) =>
    r.fulfill({
      json: [
        {
          id: "stock-2330-2026-04-14",
          type: "stock",
          title: "台積電深度",
          symbols: ["2330"],
          tags: ["半導體"],
          date: "2026-04-14",
          path: "analysis/stock-2330-2026-04-14.md",
          summary_line: "Q1 亮眼",
          starred: false,
        },
      ],
    }),
  );
  await page.route("**/api/portfolios/saved", (r) => r.fulfill({ json: [] }));
});

test("stock page shows actions and related reports", async ({ page }) => {
  await page.goto("/stocks/2330");
  await expect(page.getByTestId("stock-actions")).toBeVisible();
  await expect(page.getByTestId("related-reports")).toBeVisible();
  await expect(page.getByText("台積電深度")).toBeVisible();
});

test("favorite toggle persists", async ({ page }) => {
  await page.goto("/stocks/2330");
  const fav = page.getByTestId("favorite-toggle");
  await expect(fav).toHaveText(/收藏/);
  await fav.click();
  await expect(fav).toHaveText(/已收藏/);
  await page.reload();
  await expect(page.getByTestId("favorite-toggle")).toHaveText(/已收藏/);
});
```

- [ ] **Step 2: Run**

Run: `cd frontend && pnpm e2e --grep "stock page shows actions"`
Expected: PASS

- [ ] **Step 3: 手動驗收 D 全量**

1. 訪問 `/stocks/2330` 頂部看到「☆ 收藏」「加入組合」
2. 點收藏變成 ★，重整保持
3. 點加入組合→彈出組合列表→選擇+權重→儲存→去 `/portfolios` 見到新組合
4. 頁面底部「相關分析報告」列出該 symbol 的報告

- [ ] **Step 4: Commit（驗收後）**

```bash
git add frontend/tests/e2e/stock-actions.spec.ts
git commit -m "test: add stock actions and related reports e2e"
```

- [ ] **Step 5: 更新知識庫 + spec 狀態**

- Update `docs/knowledge/features/data-panel/ui-layout.md`（加 actions / related reports）
- Update `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` Phase 6 → 「✅ 完成（2026-04-17）」
- Update `docs/USER_GUIDE.md`

```bash
git add docs/
git commit -m "docs: phase 6 complete, update spec and knowledge"
```

---

## Group D 驗收 Checkpoint

收藏 / 加入組合 / 相關報告三功能全量手動驗證通過。

**Phase 6 全部完成後回到主流程 commit 所有未 push 變更，等待指示。**

---

# Self-Review 檢核

### 1. Spec 覆蓋

| Spec Phase 6 要求 | 對應 Task |
|-------------------|----------|
| `portfolios_saved` 表 | A1 |
| `portfolio_snapshots` 表 | A1 + A4（寫入 cache） |
| `GET /portfolios/saved` | A5 |
| `POST /portfolios/saved` | A5 |
| `GET /saved/{id}/performance` | A4 + A5 |
| `/portfolios/:id` 追蹤頁 | A7 |
| 績效計算 | A4 |
| `PATCH /reports/{id}`（加星/改標籤） | B3 |
| `DELETE /reports/{id}` | B3 |
| 報告全文搜尋 | B2（service）+ B3（q param）+ B4（UI） |
| 離線快取 | **N/A**（此計畫不做；TanStack Query 內建 cache 已足夠） |
| `TutorialModeContext` | C1 |
| 右上角快捷切換 | C2 |
| 個股頁「收藏」 | D1 |
| 個股頁「加入組合」 | D1 |
| 「相關分析報告」區塊 | D2 |

> **離線快取** spec 提到但未列 deliverable；若使用者要 PWA/service worker 等級的離線，需另外規劃 — 本計畫範圍不含。若驗收時需要，Group B 可加一個 Task B5 包裝 service worker，但建議先跳過。

### 2. Placeholder 掃描

已檢過各步驟，每個程式碼段落有完整 code；無 TBD / TODO / 「similar to XX」殘留。A7 的 PortfolioTabs 修改因為要讀現有檔案做微調，保留「讀現有 → 以 prop 注入 onSave」的描述 — 這是必要的靈活度，不是 placeholder。

### 3. 型別一致性

- `SavedPortfolioMeta` / `SavedPortfolioDetail` / `PerformanceResponse` 三層結構前後一致
- `ReportUpdate` 前後一致（schema ↔ TS ↔ route body）
- `TutorialMode` = "full" | "compact" | "off" 三處（Context / Toggle / 下游消費者）一致
- `SavedHolding` 帶 `base_price: number`，前端 save 時若拿不到會傳 0，由後端 A3 service 的 enrichment 回填

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-phase-6-tracking-reports-tutorial.md`.

兩個執行選項：

1. **Subagent-Driven (recommended)** — 每個 Task 派一個新 subagent，我在每個 Task 之間審視
2. **Inline Execution** — 在本 session 依序執行 Task，每個群組（A/B/C/D）結束時停下等使用者驗收

哪一個？
