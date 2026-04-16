# Phase 7：組合追蹤強化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「加入組合」建立的新組合跟母組合串成連續 NAV 曲線，並在 schema 層為 holdings 加上 symbol 唯一性與權重總和容忍度檢查。

**Architecture:**
- 後端：`portfolios_saved` 新增 `parent_id` + `parent_nav_at_fork` 兩欄（SQLite ALTER 手動 migration）。`save_portfolio` 在收到 `parent_id` 時呼叫 `compute_performance(parent_id).latest_nav` 自動算出 `parent_nav_at_fork`。`compute_performance` 若 row 有 parent，順手抓父組合到 fork date 為止的 NAV points 一起回傳（`parent_points`），self 段 NAV 語意不變。
- 前端：`StockActions`「加入組合」時帶 `parent_id`；`PortfolioTrackingPage` / `PerformanceChart` 拿到 `parent_points` 後把 self 段 NAV 乘以 `parent_nav_at_fork` 做視覺接續。原 `total_return`（自 self base_date 起）繼續顯示；有 parent 時額外顯示「自母組合起累積報酬」。
- Schema：`SavedPortfolioCreate` 新增 `model_validator` 檢查 symbol 唯一、`abs(sum(weights) - 1.0) < 1e-6`。

**Tech Stack:** FastAPI + SQLAlchemy 2.x（SQLite）、Pydantic v2、React 19 + TanStack Query + Recharts、vitest、Playwright。

---

## File Structure

### 新增
- `backend/src/alpha_lab/storage/migrations.py` — 極簡 idempotent 欄位新增工具（`add_column_if_missing`）
- `backend/tests/storage/test_migrations.py` — migration helper 單元測試

### 修改
後端：
- `backend/src/alpha_lab/storage/models.py` — `SavedPortfolio` 新增 `parent_id` / `parent_nav_at_fork` 欄位
- `backend/src/alpha_lab/storage/init_db.py` — `create_all` 之後呼叫 migration helper 補欄位
- `backend/src/alpha_lab/schemas/saved_portfolio.py` — `SavedPortfolioCreate` 加 `model_validator`、`parent_id` 欄位；`SavedPortfolioMeta` / `Detail` 加 `parent_id` / `parent_nav_at_fork`；`PerformanceResponse` 加 `parent_points` / `parent_nav_at_fork`
- `backend/src/alpha_lab/portfolios/service.py` — `save_portfolio` 支援 `parent_id`、`compute_performance` 填入 `parent_points`
- `backend/src/alpha_lab/api/routes/portfolios.py` — `POST /saved` 吃 payload 內 `parent_id`（非 query）
- `backend/tests/portfolios/test_service.py`、`backend/tests/api/test_portfolios_saved.py` — 加血緣與 schema 驗證測試

前端：
- `frontend/src/api/types.ts` — 補齊 `parent_id` / `parent_nav_at_fork` / `parent_points` 欄位
- `frontend/src/api/savedPortfolios.ts` — `saveRecommendedPortfolio` 支援 `parent_id`
- `frontend/src/components/stock/StockActions.tsx` — `persistMerged` 傳入 `parent_id`
- `frontend/src/components/portfolio/PerformanceChart.tsx` — 收到 `parent_points` 時做連續曲線
- `frontend/src/pages/PortfolioTrackingPage.tsx` — 顯示血緣區塊、額外顯示「自母組合起報酬」
- `frontend/tests/components/PerformanceChart.test.tsx` —（新增）連續曲線計算單元測試
- `frontend/tests/e2e/stock-actions.spec.ts` — 加血緣 assertion
- `frontend/tests/e2e/portfolio-tracking.spec.ts` — 加連續曲線 assertion

文件：
- `docs/knowledge/features/tracking/overview.md` — 更新血緣語意
- `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` — Phase 7 status 與子計畫拆分註記
- `docs/USER_GUIDE.md` — 追蹤頁新增血緣顯示說明

---

## Task 1：migration helper

**Files:**
- Create: `backend/src/alpha_lab/storage/migrations.py`
- Create: `backend/tests/storage/test_migrations.py`
- Create: `backend/tests/storage/__init__.py`（若不存在）

- [ ] **Step 1：先看 tests 目錄是否已有 storage 子資料夾**

Run: `ls backend/tests/storage 2>/dev/null || echo "missing"`
若輸出 `missing` 則下一步需要建立 `__init__.py`（空檔）。

- [ ] **Step 2：寫 failing 測試**

建立 `backend/tests/storage/test_migrations.py`：

```python
"""storage.migrations helper 單元測試。"""

from __future__ import annotations

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect
from sqlalchemy.pool import StaticPool

from alpha_lab.storage.migrations import add_column_if_missing


def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_add_column_if_missing_adds_new_column():
    engine = _make_engine()
    meta = MetaData()
    Table("foo", meta, Column("id", Integer, primary_key=True))
    meta.create_all(engine)

    add_column_if_missing(engine, "foo", "note", "TEXT")

    cols = {c["name"] for c in inspect(engine).get_columns("foo")}
    assert "note" in cols


def test_add_column_if_missing_skips_when_present():
    engine = _make_engine()
    meta = MetaData()
    Table(
        "foo",
        meta,
        Column("id", Integer, primary_key=True),
        Column("note", String),
    )
    meta.create_all(engine)

    # 呼叫兩次不會炸
    add_column_if_missing(engine, "foo", "note", "TEXT")
    add_column_if_missing(engine, "foo", "note", "TEXT")

    cols = {c["name"] for c in inspect(engine).get_columns("foo")}
    assert "note" in cols


def test_add_column_if_missing_table_not_exist_raises():
    engine = _make_engine()
    import pytest

    with pytest.raises(ValueError, match="table 'foo' not found"):
        add_column_if_missing(engine, "foo", "note", "TEXT")
```

- [ ] **Step 3：執行測試確認 RED**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/storage/test_migrations.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'alpha_lab.storage.migrations'`

- [ ] **Step 4：實作 migrations.py**

建立 `backend/src/alpha_lab/storage/migrations.py`：

```python
"""極簡 idempotent schema migration helper。

SQLite 新增欄位一律走 ALTER TABLE ADD COLUMN；只在欄位不存在時執行。
遇到欄位型別不相容不做任何轉換——這套只負責補欄位，不處理型別遷移。
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def add_column_if_missing(
    engine: Engine, table: str, column: str, column_type_sql: str
) -> bool:
    """若 `table.column` 不存在則 ALTER TABLE 新增。回傳是否實際新增。

    `column_type_sql`：原始 SQL 型別字串（例如 "INTEGER", "FLOAT", "TEXT"）。
    """

    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        raise ValueError(f"table '{table}' not found")
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return False
    with engine.begin() as conn:
        conn.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type_sql}")
        )
    return True
```

- [ ] **Step 5：再跑測試確認 GREEN**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/storage/test_migrations.py -v`
Expected: 3 passed

- [ ] **Step 6：ruff / mypy 靜態檢查**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check src tests && .venv/Scripts/python.exe -m mypy src`
Expected: 0 error

- [ ] **Step 7：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add backend/src/alpha_lab/storage/migrations.py backend/tests/storage/ && rtk git commit -m "feat: add idempotent column-add migration helper"
```

---

## Task 2：SavedPortfolio 新增血緣欄位 + 啟用 migration

**Files:**
- Modify: `backend/src/alpha_lab/storage/models.py`（`SavedPortfolio`）
- Modify: `backend/src/alpha_lab/storage/init_db.py`

- [ ] **Step 1：修改 models.py**

把 `SavedPortfolio` class 內容替換為：

```python
class SavedPortfolio(Base):
    """使用者儲存的組合（來自推薦 snapshot 或由其他組合 fork 而來）。

    holdings_json：list of {symbol, name, weight, base_price}
    parent_id / parent_nav_at_fork：若此組合由另一組合「加入個股」建立，記錄血緣。
    parent_nav_at_fork 存 fork 當下父組合的 latest_nav，讓績效頁能把父段與 self 段
    NAV 接成連續曲線顯示。
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
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("portfolios_saved.id"), nullable=True
    )
    parent_nav_at_fork: Mapped[float | None] = mapped_column(Float, nullable=True)
```

- [ ] **Step 2：修改 init_db.py**

替換 `init_database` 為：

```python
"""Phase 1 採用 SQLAlchemy create_all 自動建表；Phase 7 起補上欄位 migration。"""

from pathlib import Path

from alpha_lab.storage.engine import get_engine
from alpha_lab.storage.migrations import add_column_if_missing
from alpha_lab.storage.models import Base


def init_database() -> None:
    """建立所有表（若已存在則跳過）並補上新增欄位。"""
    engine = get_engine()
    url = str(engine.url)
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:"):
        db_path = Path(url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(engine)

    # Phase 7 portfolios_saved 血緣欄位
    add_column_if_missing(engine, "portfolios_saved", "parent_id", "INTEGER")
    add_column_if_missing(
        engine, "portfolios_saved", "parent_nav_at_fork", "FLOAT"
    )
```

- [ ] **Step 3：寫一個 end-to-end migration 測試**

新增 `backend/tests/storage/test_init_db_migration.py`：

```python
"""驗證 init_database() 在既存舊 schema DB 上能補欄位。"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.init_db import init_database


def test_init_database_adds_parent_columns_to_existing_old_schema():
    test_engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 模擬舊版 schema：手動建表但不含 parent_id / parent_nav_at_fork
    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE portfolios_saved (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    style VARCHAR(16) NOT NULL,
                    label VARCHAR(32) NOT NULL,
                    note TEXT,
                    holdings_json TEXT NOT NULL,
                    base_date DATE NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
    engine_module._engine = test_engine
    engine_module._SessionLocal = None

    init_database()

    cols = {c["name"] for c in inspect(test_engine).get_columns("portfolios_saved")}
    assert "parent_id" in cols
    assert "parent_nav_at_fork" in cols
```

- [ ] **Step 4：跑新測試確認 GREEN**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/storage/test_init_db_migration.py -v`
Expected: PASS

- [ ] **Step 5：跑完整 test suite 確認不壞既有**

Run: `cd backend && .venv/Scripts/python.exe -m pytest`
Expected: 全 pass（既有 `test_portfolios_saved.py` / `test_service.py` 雖未動到新欄位，但 `create_all` 會產生新欄位 nullable，不破壞）。

- [ ] **Step 6：ruff / mypy**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check src tests && .venv/Scripts/python.exe -m mypy src`
Expected: 0 error

- [ ] **Step 7：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add backend/src/alpha_lab/storage/models.py backend/src/alpha_lab/storage/init_db.py backend/tests/storage/test_init_db_migration.py && rtk git commit -m "feat: add parent_id and parent_nav_at_fork to portfolios_saved"
```

---

## Task 3：SavedPortfolioCreate schema 驗證（唯一性 + 權重總和）

**Files:**
- Modify: `backend/src/alpha_lab/schemas/saved_portfolio.py`
- Create: `backend/tests/schemas/test_saved_portfolio.py`
- Create: `backend/tests/schemas/__init__.py`（若不存在）

- [ ] **Step 1：確認 tests/schemas 目錄存在**

Run: `ls backend/tests/schemas 2>/dev/null || echo "missing"`
若 missing，後面 Step 2 同時建 `__init__.py`。

- [ ] **Step 2：寫 failing 測試**

建 `backend/tests/schemas/test_saved_portfolio.py`：

```python
"""SavedPortfolioCreate schema 驗證測試（Phase 7）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from alpha_lab.schemas.saved_portfolio import SavedHolding, SavedPortfolioCreate


def _holding(symbol: str, weight: float) -> SavedHolding:
    return SavedHolding(symbol=symbol, name=symbol, weight=weight, base_price=100.0)


def test_create_accepts_valid_weights_summing_to_one():
    payload = SavedPortfolioCreate(
        style="balanced",
        label="ok",
        holdings=[_holding("2330", 0.6), _holding("2317", 0.4)],
    )
    assert sum(h.weight for h in payload.holdings) == pytest.approx(1.0)


def test_create_accepts_float_drift_within_1e6():
    # 典型 buildMergedHoldings 產生的浮點漂移
    payload = SavedPortfolioCreate(
        style="balanced",
        label="drift",
        holdings=[
            _holding("2330", 0.54),
            _holding("2317", 0.36),
            _holding("9999", 0.10000000001),  # 漂移在 1e-6 以內
        ],
    )
    assert len(payload.holdings) == 3


def test_create_rejects_weights_not_summing_to_one():
    with pytest.raises(ValidationError, match="weights must sum to 1.0"):
        SavedPortfolioCreate(
            style="balanced",
            label="bad-sum",
            holdings=[_holding("2330", 0.6), _holding("2317", 0.3)],
        )


def test_create_rejects_duplicate_symbols():
    with pytest.raises(ValidationError, match="duplicate symbol"):
        SavedPortfolioCreate(
            style="balanced",
            label="dup",
            holdings=[_holding("2330", 0.5), _holding("2330", 0.5)],
        )


def test_create_accepts_parent_id_optional():
    payload = SavedPortfolioCreate(
        style="balanced",
        label="fork",
        holdings=[_holding("2330", 1.0)],
        parent_id=7,
    )
    assert payload.parent_id == 7


def test_create_defaults_parent_id_none():
    payload = SavedPortfolioCreate(
        style="balanced",
        label="solo",
        holdings=[_holding("2330", 1.0)],
    )
    assert payload.parent_id is None
```

- [ ] **Step 3：跑 RED**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/schemas/test_saved_portfolio.py -v`
Expected: FAIL（缺 `parent_id` 欄位、缺 validator）

- [ ] **Step 4：修改 schemas/saved_portfolio.py**

整份檔案替換為：

```python
"""Saved Portfolio 相關 schemas（Phase 6 + Phase 7 血緣）。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from alpha_lab.analysis.weights import Style

WEIGHT_SUM_TOLERANCE = 1e-6


class SavedHolding(BaseModel):
    symbol: str
    name: str
    weight: float
    base_price: float


class SavedPortfolioCreate(BaseModel):
    """把某個風格的推薦結果存成追蹤組合。

    `parent_id`：若此組合由另一個已儲存組合「加入個股」而來，帶上母組合 id；
    後端會自動查 parent latest_nav 並填 `parent_nav_at_fork`。
    """

    style: Style
    label: str = Field(..., min_length=1, max_length=32)
    note: str | None = None
    holdings: list[SavedHolding] = Field(..., min_length=1)
    parent_id: int | None = None

    @model_validator(mode="after")
    def _validate_holdings(self) -> "SavedPortfolioCreate":
        symbols = [h.symbol for h in self.holdings]
        if len(symbols) != len(set(symbols)):
            seen: set[str] = set()
            dup: list[str] = []
            for s in symbols:
                if s in seen:
                    dup.append(s)
                seen.add(s)
            raise ValueError(f"duplicate symbol in holdings: {dup}")
        total = sum(h.weight for h in self.holdings)
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"weights must sum to 1.0 (got {total:.8f}, "
                f"tolerance {WEIGHT_SUM_TOLERANCE})"
            )
        return self


class SavedPortfolioMeta(BaseModel):
    id: int
    style: Style
    label: str
    note: str | None
    base_date: date_type
    created_at: datetime
    holdings_count: int
    parent_id: int | None = None
    parent_nav_at_fork: float | None = None


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
    total_return: float  # self 段：nav_last - 1.0
    parent_points: list[PerformancePoint] | None = None
    parent_nav_at_fork: float | None = None


class BaseDateProbe(BaseModel):
    """`GET /api/portfolios/saved/probe` 回傳。"""

    target_date: date_type
    resolved_date: date_type | None
    today_available: bool
    missing_today_symbols: list[str]
```

- [ ] **Step 5：跑 schema 測試 GREEN**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/schemas/test_saved_portfolio.py -v`
Expected: 6 passed

- [ ] **Step 6：跑完整後端 test 確認不壞既有**

Run: `cd backend && .venv/Scripts/python.exe -m pytest`
Expected: 全 pass（既有 test 的 holdings sum 本來就是 1.0，不受影響）

- [ ] **Step 7：ruff / mypy**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check src tests && .venv/Scripts/python.exe -m mypy src`
Expected: 0 error

- [ ] **Step 8：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add backend/src/alpha_lab/schemas/saved_portfolio.py backend/tests/schemas/ && rtk git commit -m "feat: validate holdings uniqueness and weight sum in SavedPortfolioCreate"
```

---

## Task 4：save_portfolio service 支援 parent_id

**Files:**
- Modify: `backend/src/alpha_lab/portfolios/service.py`
- Modify: `backend/tests/portfolios/test_service.py`

- [ ] **Step 1：先寫 failing 測試（append 到 test_service.py）**

在 `backend/tests/portfolios/test_service.py` 檔尾追加：

```python
def test_save_portfolio_with_parent_stores_lineage(sample_prices):
    parent = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="parent",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    # parent 當下 latest_nav（僅 base_date 一個 point）= 1.0
    child = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="child",
            holdings=[
                SavedHolding(symbol="2330", name="台積電", weight=0.6, base_price=600.0),
                SavedHolding(symbol="2317", name="鴻海", weight=0.4, base_price=100.0),
            ],
            parent_id=parent.id,
        ),
        base_date=date(2026, 4, 17),
    )
    detail = get_saved(child.id)
    assert detail is not None
    assert detail.parent_id == parent.id
    assert detail.parent_nav_at_fork == pytest.approx(1.0)


def test_save_portfolio_with_nonexistent_parent_raises(sample_prices):
    with pytest.raises(ValueError, match="parent portfolio .* not found"):
        save_portfolio(
            SavedPortfolioCreate(
                style="balanced",
                label="orphan",
                holdings=[
                    SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)
                ],
                parent_id=99999,
            ),
            base_date=date(2026, 4, 17),
        )


def test_save_portfolio_parent_nav_snapshot_reflects_latest_prices(sample_prices):
    # 先建 parent，再給 parent 的後續交易日加價，driven parent latest_nav
    parent = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="p2",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330",
                trade_date=date(2026, 4, 18),
                open=660.0, high=660.0, low=660.0, close=660.0,
                volume=1000,
            )
        )

    child = save_portfolio(
        SavedPortfolioCreate(
            style="balanced",
            label="c2",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=660.0)],
            parent_id=parent.id,
        ),
        base_date=date(2026, 4, 18),
    )
    detail = get_saved(child.id)
    assert detail is not None
    # parent 從 600 -> 660 = 1.10
    assert detail.parent_nav_at_fork == pytest.approx(1.10, rel=1e-4)
```

- [ ] **Step 2：跑 RED**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/portfolios/test_service.py -v -k "parent"`
Expected: 3 tests FAIL

- [ ] **Step 3：修改 service.py**

找到 `save_portfolio` 函式簽名（約 line 113），整個函式替換為：

```python
def save_portfolio(
    payload: SavedPortfolioCreate,
    *,
    base_date: date_type,
    allow_fallback: bool = False,
) -> SavedPortfolioMeta:
    """儲存組合。

    預設 strict 模式：要求所有持股在 `base_date` 當日都有 prices_daily 報價。
    若 `allow_fallback=True`（前端 dialog 已警示後使用者同意），當日缺料時自動退到
    所有持股都有報價的最近交易日（`<= base_date`）。任一模式下，若連 fallback
    也找不到（某 symbol 完全無 <= base_date 紀錄），raise ValueError。

    `base_price <= 0` 的持股會用最終決定的 base_date 從 prices_daily 補值。

    Phase 7：若 `payload.parent_id` 非 None，自動查 parent latest_nav 存為
    `parent_nav_at_fork`（讓績效頁能接續畫連續曲線）。parent 不存在則拋 ValueError。
    """

    parent_nav: float | None = None
    if payload.parent_id is not None:
        parent_perf = compute_performance(payload.parent_id)
        if parent_perf is None:
            raise ValueError(f"parent portfolio {payload.parent_id} not found")
        parent_nav = parent_perf.latest_nav

    with session_scope() as session:
        symbols = [h.symbol for h in payload.holdings]

        if allow_fallback:
            resolved_base_date = _resolve_common_base_date(
                session, symbols, base_date
            )
            if resolved_base_date is None:
                raise ValueError(
                    f"no common trade_date for {symbols} on or before {base_date}; "
                    "run daily_collect for missing symbols first"
                )
        else:
            resolved_base_date = base_date

        enriched_holdings: list[SavedHolding] = []
        for h in payload.holdings:
            if h.base_price <= 0:
                close = session.scalar(
                    select(PriceDaily.close)
                    .where(PriceDaily.symbol == h.symbol)
                    .where(PriceDaily.trade_date == resolved_base_date)
                )
                if close is None:
                    raise ValueError(
                        f"no price for {h.symbol} on {resolved_base_date}"
                    )
                h = SavedHolding(
                    symbol=h.symbol,
                    name=h.name,
                    weight=h.weight,
                    base_price=close,
                )
            enriched_holdings.append(h)

        row = SavedPortfolio(
            style=payload.style,
            label=payload.label,
            note=payload.note,
            holdings_json=_holdings_to_json(enriched_holdings),
            base_date=resolved_base_date,
            parent_id=payload.parent_id,
            parent_nav_at_fork=parent_nav,
        )
        session.add(row)
        session.flush()
        meta = _row_to_meta(row)
    return meta
```

在同檔內，找 `_row_to_meta` 與 `_row_to_detail`，整段替換為：

```python
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
        parent_id=row.parent_id,
        parent_nav_at_fork=row.parent_nav_at_fork,
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
        parent_id=row.parent_id,
        parent_nav_at_fork=row.parent_nav_at_fork,
        holdings=holdings,
    )
```

- [ ] **Step 4：跑 service 測試 GREEN**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/portfolios/test_service.py -v`
Expected: 全 pass（含 3 個新測試）

- [ ] **Step 5：ruff / mypy**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check src tests && .venv/Scripts/python.exe -m mypy src`
Expected: 0 error

- [ ] **Step 6：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add backend/src/alpha_lab/portfolios/service.py backend/tests/portfolios/test_service.py && rtk git commit -m "feat: record parent lineage when saving a forked portfolio"
```

---

## Task 5：compute_performance 回傳 parent_points

**Files:**
- Modify: `backend/src/alpha_lab/portfolios/service.py`（`compute_performance`）
- Modify: `backend/tests/portfolios/test_service.py`

設計：若 `row.parent_id is not None`，遞迴呼叫 `compute_performance(parent_id)`，只取 `points` 中 `date < row.base_date` 的部分當作 `parent_points`（fork 當天不重複）。`parent_nav_at_fork` 直接讀 row。

- [ ] **Step 1：append 測試**

在 `backend/tests/portfolios/test_service.py` 檔尾追加：

```python
def test_compute_performance_returns_parent_points_when_forked(sample_prices):
    # parent: 4/17 買入 2330@600，4/18 -> 660（NAV 1.10）
    # child: 4/18 fork，parent_nav_at_fork=1.10
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330", trade_date=date(2026, 4, 18),
                open=660.0, high=660.0, low=660.0, close=660.0, volume=1000,
            )
        )
    parent = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="parent",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    child = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="child",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=660.0)],
            parent_id=parent.id,
        ),
        base_date=date(2026, 4, 18),
    )
    resp = compute_performance(child.id)
    assert resp is not None
    assert resp.parent_nav_at_fork == pytest.approx(1.10, rel=1e-4)
    # parent_points 應該只含 < 4/18 的日期（即 4/17）
    assert resp.parent_points is not None
    assert len(resp.parent_points) == 1
    assert resp.parent_points[0].date == date(2026, 4, 17)
    assert resp.parent_points[0].nav == pytest.approx(1.0)


def test_compute_performance_without_parent_has_no_parent_points(sample_prices):
    meta = save_portfolio(
        SavedPortfolioCreate(
            style="balanced", label="solo",
            holdings=[SavedHolding(symbol="2330", name="台積電", weight=1.0, base_price=600.0)],
        ),
        base_date=date(2026, 4, 17),
    )
    resp = compute_performance(meta.id)
    assert resp is not None
    assert resp.parent_points is None
    assert resp.parent_nav_at_fork is None
```

- [ ] **Step 2：跑 RED**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/portfolios/test_service.py -v -k "parent_points or without_parent"`
Expected: 2 FAIL（欄位尚未被 compute_performance 填入）

- [ ] **Step 3：修改 compute_performance**

找到 `compute_performance` 函式（檔尾），整個函式替換為：

```python
def compute_performance(portfolio_id: int) -> PerformanceResponse | None:
    """從 base_date 起每日 NAV：sum(weight_i * price_i(t) / base_price_i)。

    只取所有持股都有報價的日期；缺價日直接跳過。
    會同步 upsert 最新一筆到 `portfolio_snapshots`（供之後擴充排程用）。

    Phase 7：若此組合有 parent_id，額外把父組合 `< base_date` 的 NAV points
    附在 `parent_points`；前端可用 `parent_nav_at_fork` 把 self 段縮放後接續繪圖。
    """

    with session_scope() as session:
        row = session.get(SavedPortfolio, portfolio_id)
        if row is None:
            return None
        holdings = _holdings_from_json(row.holdings_json)
        symbols = [h.symbol for h in holdings]
        price_map = _load_price_map(session, symbols, row.base_date)

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
        parent_id = row.parent_id
        parent_nav_at_fork = row.parent_nav_at_fork
        child_base_date = row.base_date

    parent_points: list[PerformancePoint] | None = None
    if parent_id is not None:
        parent_resp = compute_performance(parent_id)
        if parent_resp is not None:
            parent_points = [
                p for p in parent_resp.points if p.date < child_base_date
            ]

    return PerformanceResponse(
        portfolio=detail,
        points=points,
        latest_nav=latest_nav,
        total_return=total_return,
        parent_points=parent_points,
        parent_nav_at_fork=parent_nav_at_fork,
    )
```

- [ ] **Step 4：跑全 backend test**

Run: `cd backend && .venv/Scripts/python.exe -m pytest`
Expected: 全 pass

- [ ] **Step 5：ruff / mypy**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check src tests && .venv/Scripts/python.exe -m mypy src`
Expected: 0 error

- [ ] **Step 6：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add backend/src/alpha_lab/portfolios/service.py backend/tests/portfolios/test_service.py && rtk git commit -m "feat: include parent performance points when portfolio has lineage"
```

---

## Task 6：API route 與整合測試

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/portfolios.py`
- Modify: `backend/tests/api/test_portfolios_saved.py`

註：路由簽名不用改——`SavedPortfolioCreate` 已經有 `parent_id` 欄位，FastAPI 會自動吃到 body。但我們要確認實際 HTTP 路徑能動，並擋住 parent 不存在的 400。

- [ ] **Step 1：append 整合測試**

在 `backend/tests/api/test_portfolios_saved.py` 檔尾追加：

```python
def test_post_saved_with_parent_creates_lineage():
    _seed_prices()
    client = TestClient(app)
    parent_payload = {
        "style": "balanced",
        "label": "parent",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
    }
    parent_id = client.post("/api/portfolios/saved", json=parent_payload).json()["id"]

    child_payload = {
        "style": "balanced",
        "label": "child",
        "holdings": [
            {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
        ],
        "parent_id": parent_id,
    }
    resp = client.post("/api/portfolios/saved", json=child_payload)
    assert resp.status_code == 201
    meta = resp.json()
    assert meta["parent_id"] == parent_id
    assert meta["parent_nav_at_fork"] == pytest.approx(1.0)


def test_post_saved_rejects_unknown_parent_id():
    _seed_prices()
    client = TestClient(app)
    resp = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "orphan",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
            ],
            "parent_id": 999,
        },
    )
    assert resp.status_code == 400
    assert "parent portfolio" in resp.json()["detail"]


def test_post_saved_rejects_duplicate_symbol():
    _seed_prices()
    client = TestClient(app)
    resp = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "dup",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 0.5, "base_price": 600.0},
                {"symbol": "2330", "name": "台積電", "weight": 0.5, "base_price": 600.0},
            ],
        },
    )
    assert resp.status_code == 422  # Pydantic validation error


def test_post_saved_rejects_weights_not_summing_to_one():
    _seed_prices()
    client = TestClient(app)
    resp = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "bad-sum",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 0.8, "base_price": 600.0},
            ],
        },
    )
    assert resp.status_code == 422


def test_performance_returns_parent_points_when_forked():
    _seed_prices()
    client = TestClient(app)
    parent_id = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "parent",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 600.0}
            ],
        },
    ).json()["id"]
    with session_scope() as session:
        session.merge(
            PriceDaily(
                symbol="2330", trade_date=date(2026, 4, 18),
                open=660.0, high=660.0, low=660.0, close=660.0, volume=1000,
            )
        )
    child_id = client.post(
        "/api/portfolios/saved",
        json={
            "style": "balanced",
            "label": "child",
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight": 1.0, "base_price": 660.0}
            ],
            "parent_id": parent_id,
        },
    ).json()["id"]
    perf = client.get(f"/api/portfolios/saved/{child_id}/performance").json()
    assert perf["parent_nav_at_fork"] == pytest.approx(1.10, rel=1e-4)
    assert perf["parent_points"] is not None
    assert len(perf["parent_points"]) == 1
```

於檔案開頭 import 補上（若尚未）：

```python
import pytest
```

- [ ] **Step 2：跑 RED → 新測試應該 FAIL（parent 400 那題會看到 400 還是拿到 201 要檢查）**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/api/test_portfolios_saved.py -v`
Expected: 新加的 parent_nav_at_fork 測試可能因 route 500 而失敗（`compute_performance` 在 route 中 catch 不到 ValueError）——轉 Step 3 修 route。

- [ ] **Step 3：修 route**

在 `backend/src/alpha_lab/api/routes/portfolios.py` 找到 `save_portfolio_endpoint`，確認 `except ValueError as e → 400`。原本已有，不用改。但 `compute_performance` 的 ValueError 需要被 catch。檢查 `save_portfolio` 現在會 call `compute_performance(parent_id)`，若 parent 不存在拋 ValueError — 在同一個 try/except 裡已經被 catch 到，OK。

不動 route code，直接跑：

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/api/test_portfolios_saved.py -v`
Expected: 全 pass

- [ ] **Step 4：若 test fail 再看實際錯誤訊息修正測試或 service**

若 `test_post_saved_with_parent_creates_lineage` 的 `parent_nav_at_fork == 1.0` 失敗，回頭檢查 `_seed_prices()` 只 seed 一天，parent latest_nav 應為 1.0，預期正確。

- [ ] **Step 5：ruff / mypy**

Run: `cd backend && .venv/Scripts/python.exe -m ruff check src tests && .venv/Scripts/python.exe -m mypy src`
Expected: 0 error

- [ ] **Step 6：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add backend/tests/api/test_portfolios_saved.py && rtk git commit -m "test: cover parent lineage and schema validation at API layer"
```

---

## Task 7：Frontend types + API client

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/savedPortfolios.ts`

- [ ] **Step 1：更新 types.ts**

找到 `SavedPortfolioCreate` / `SavedPortfolioMeta` / `PerformanceResponse` 三個 interface，分別替換為：

```typescript
export interface SavedPortfolioCreate {
  style: PortfolioStyle;
  label: string;
  note?: string | null;
  holdings: SavedHolding[];
  parent_id?: number | null;
}

export interface SavedPortfolioMeta {
  id: number;
  style: PortfolioStyle;
  label: string;
  note: string | null;
  base_date: string;
  created_at: string;
  holdings_count: number;
  parent_id: number | null;
  parent_nav_at_fork: number | null;
}

export interface SavedPortfolioDetail extends SavedPortfolioMeta {
  holdings: SavedHolding[];
}

export interface PerformanceResponse {
  portfolio: SavedPortfolioDetail;
  points: PerformancePoint[];
  latest_nav: number;
  total_return: number;
  parent_points: PerformancePoint[] | null;
  parent_nav_at_fork: number | null;
}
```

（`PerformancePoint`、`BaseDateProbe`、`SavedHolding` 不變。）

- [ ] **Step 2：更新 savedPortfolios.ts**

替換 `saveRecommendedPortfolio` 為：

```typescript
export function saveRecommendedPortfolio(
  payload: SavedPortfolioCreate,
  options?: { allowFallback?: boolean },
): Promise<SavedPortfolioMeta> {
  const params = options?.allowFallback ? { allow_fallback: "true" } : undefined;
  return apiPost<SavedPortfolioMeta>("/api/portfolios/saved", params, payload);
}
```

（簽名不用改，但 `payload` type 現在帶 `parent_id?: number | null`，呼叫端自動支援。）

- [ ] **Step 3：tsc 檢查**

Run: `cd frontend && pnpm type-check`
Expected: 0 error

- [ ] **Step 4：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add frontend/src/api/types.ts frontend/src/api/savedPortfolios.ts && rtk git commit -m "feat: extend saved portfolio types with parent lineage"
```

---

## Task 8：StockActions 傳入 parent_id

**Files:**
- Modify: `frontend/src/components/stock/StockActions.tsx`

- [ ] **Step 1：修改 persistMerged**

在 `frontend/src/components/stock/StockActions.tsx` 找到 `persistMerged` 函式（約 line 53），整個替換為：

```typescript
  async function persistMerged(
    detail: SavedPortfolioDetail,
    allowFallback: boolean,
  ): Promise<void> {
    const delta = Number(weightPct) / 100;
    const merged = buildMergedHoldings({
      existing: detail.holdings,
      symbol: meta.symbol,
      name: meta.name,
      delta,
    });
    await saveRecommendedPortfolio(
      {
        style: detail.style,
        label: `${detail.label} + ${meta.symbol}`,
        holdings: merged,
        parent_id: detail.id,
      },
      { allowFallback },
    );
  }
```

- [ ] **Step 2：tsc**

Run: `cd frontend && pnpm type-check`
Expected: 0 error

- [ ] **Step 3：既有元件測試**

Run: `cd frontend && pnpm test --run`
Expected: 全 pass（現有 test 沒 assert `parent_id`，會通過）

- [ ] **Step 4：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add frontend/src/components/stock/StockActions.tsx && rtk git commit -m "feat: tag forked portfolio with parent id on add-to-portfolio"
```

---

## Task 9：PerformanceChart 連續曲線邏輯

**Files:**
- Modify: `frontend/src/components/portfolio/PerformanceChart.tsx`
- Create: `frontend/tests/components/PerformanceChart.test.tsx`

設計：
- 輸入多兩個 optional prop：`parentPoints?: PerformancePoint[] | null`、`parentNavAtFork?: number | null`
- 若兩者都有值，計算連續序列：
  - `parent_series = parentPoints.map(p => ({date: p.date, nav: p.nav, series: "parent"}))`
  - `self_series = points.map(p => ({date: p.date, nav: p.nav * parentNavAtFork, series: "self"}))`
  - 畫兩條 Line（不同顏色），但把 parent 段虛線、self 段實線
- 若無 parent，維持原單 Line 行為

- [ ] **Step 1：寫 failing 測試**

建 `frontend/tests/components/PerformanceChart.test.tsx`：

```typescript
import { describe, expect, it } from "vitest";

import { buildChartSeries } from "@/components/portfolio/PerformanceChart";

describe("buildChartSeries", () => {
  it("returns self-only series when parent info absent", () => {
    const result = buildChartSeries({
      points: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
        { date: "2026-04-18", nav: 1.05, daily_return: 0.05 },
      ],
      parentPoints: null,
      parentNavAtFork: null,
    });
    expect(result.forkDate).toBeNull();
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: null, self: 1.0 },
      { date: "2026-04-18", parent: null, self: 1.05 },
    ]);
  });

  it("scales self nav by parent_nav_at_fork and prepends parent points", () => {
    const result = buildChartSeries({
      points: [
        { date: "2026-04-18", nav: 1.0, daily_return: null },
        { date: "2026-04-21", nav: 1.08, daily_return: 0.08 },
      ],
      parentPoints: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
      ],
      parentNavAtFork: 1.1,
    });
    expect(result.forkDate).toBe("2026-04-18");
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: 1.0, self: null },
      // fork 日：parent 段最後 + self 段起點，兩條連起來
      { date: "2026-04-18", parent: 1.1, self: 1.1 },
      { date: "2026-04-21", parent: null, self: 1.1 * 1.08 },
    ]);
  });

  it("handles empty self points by returning only parent series", () => {
    const result = buildChartSeries({
      points: [],
      parentPoints: [
        { date: "2026-04-17", nav: 1.0, daily_return: null },
      ],
      parentNavAtFork: 1.1,
    });
    expect(result.forkDate).toBeNull();
    expect(result.rows).toEqual([
      { date: "2026-04-17", parent: 1.0, self: null },
    ]);
  });
});
```

- [ ] **Step 2：跑 RED**

Run: `cd frontend && pnpm test --run tests/components/PerformanceChart.test.tsx`
Expected: FAIL（`buildChartSeries` 未 export）

- [ ] **Step 3：修改 PerformanceChart.tsx**

整份檔案替換為：

```typescript
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PerformancePoint } from "@/api/types";

interface PerformanceChartProps {
  points: PerformancePoint[];
  parentPoints?: PerformancePoint[] | null;
  parentNavAtFork?: number | null;
}

interface ChartRow {
  date: string;
  parent: number | null;
  self: number | null;
}

interface BuildArgs {
  points: PerformancePoint[];
  parentPoints: PerformancePoint[] | null | undefined;
  parentNavAtFork: number | null | undefined;
}

interface BuildResult {
  rows: ChartRow[];
  forkDate: string | null;
}

export function buildChartSeries(args: BuildArgs): BuildResult {
  const { points, parentPoints, parentNavAtFork } = args;
  const hasParent =
    parentPoints != null &&
    parentPoints.length > 0 &&
    parentNavAtFork != null &&
    Number.isFinite(parentNavAtFork);
  const scale = hasParent ? (parentNavAtFork as number) : 1;

  const rows: ChartRow[] = [];
  if (hasParent) {
    for (const p of parentPoints as PerformancePoint[]) {
      rows.push({ date: p.date, parent: p.nav, self: null });
    }
  }

  if (points.length === 0) {
    return { rows, forkDate: null };
  }

  const forkDate = hasParent ? points[0].date : null;
  for (let i = 0; i < points.length; i += 1) {
    const p = points[i];
    const selfNav = p.nav * scale;
    if (i === 0 && hasParent) {
      // 接續點：parent 最後 + self 起點都畫，讓兩條線在 fork date 交會
      rows.push({ date: p.date, parent: scale, self: selfNav });
    } else {
      rows.push({ date: p.date, parent: null, self: selfNav });
    }
  }
  return { rows, forkDate };
}

export function PerformanceChart({
  points,
  parentPoints = null,
  parentNavAtFork = null,
}: PerformanceChartProps) {
  if (points.length === 0 && (!parentPoints || parentPoints.length === 0)) {
    return <p className="text-slate-400 text-sm">尚無績效資料</p>;
  }
  const { rows, forkDate } = buildChartSeries({
    points,
    parentPoints,
    parentNavAtFork,
  });
  return (
    <div className="h-64 w-full" data-testid="performance-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" stroke="#94a3b8" />
          <YAxis domain={["auto", "auto"]} stroke="#94a3b8" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0f172a",
              border: "1px solid #334155",
            }}
          />
          {forkDate ? (
            <ReferenceLine
              x={forkDate}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: "fork", fill: "#f59e0b", position: "top" }}
            />
          ) : null}
          {parentPoints && parentPoints.length > 0 ? (
            <Line
              type="monotone"
              dataKey="parent"
              stroke="#94a3b8"
              strokeDasharray="4 4"
              dot={false}
              strokeWidth={2}
              connectNulls={false}
              name="parent"
            />
          ) : null}
          <Line
            type="monotone"
            dataKey="self"
            stroke="#38bdf8"
            dot={false}
            strokeWidth={2}
            connectNulls={false}
            name="self"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 4：跑 GREEN**

Run: `cd frontend && pnpm test --run tests/components/PerformanceChart.test.tsx`
Expected: 3 passed

- [ ] **Step 5：lint + tsc**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 error

- [ ] **Step 6：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add frontend/src/components/portfolio/PerformanceChart.tsx frontend/tests/components/PerformanceChart.test.tsx && rtk git commit -m "feat: render continuous NAV curve across parent and self segments"
```

---

## Task 10：PortfolioTrackingPage 血緣顯示

**Files:**
- Modify: `frontend/src/pages/PortfolioTrackingPage.tsx`

顯示規則：
- 標題下方小字：若 `parent_id !== null`，加一行「由 組合 #{parent_id} 分裂 · fork NAV {parent_nav_at_fork.toFixed(4)}」，`#{parent_id}` 為 `<Link to="/portfolios/{parent_id}">`。
- 報酬卡片：若有 parent，新增一張「自母組合起累積報酬」= `(parent_nav_at_fork * latest_nav - 1) * 100%`
- `PerformanceChart` 傳入 `parent_points` + `parent_nav_at_fork`

- [ ] **Step 1：替換 PortfolioTrackingPage.tsx 整份檔案**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

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

  const { portfolio, points, latest_nav, total_return, parent_points, parent_nav_at_fork } = data;
  const returnPct = (total_return * 100).toFixed(2);
  const returnColor = total_return >= 0 ? "text-emerald-400" : "text-red-400";

  const hasLineage =
    portfolio.parent_id != null && portfolio.parent_nav_at_fork != null;
  const continuousReturn = hasLineage
    ? (portfolio.parent_nav_at_fork as number) * latest_nav - 1.0
    : null;
  const continuousPct =
    continuousReturn != null ? (continuousReturn * 100).toFixed(2) : null;
  const continuousColor =
    continuousReturn != null && continuousReturn >= 0
      ? "text-emerald-400"
      : "text-red-400";

  return (
    <div className="space-y-4" data-testid="portfolio-tracking-page">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{portfolio.label}</h1>
          <p className="text-sm text-slate-500">
            {portfolio.style} · 起始 {portfolio.base_date} ·{" "}
            {portfolio.holdings_count} 檔
          </p>
          {hasLineage ? (
            <p
              className="mt-1 text-xs text-amber-300"
              data-testid="lineage-info"
            >
              由{" "}
              <Link
                to={`/portfolios/${portfolio.parent_id}`}
                className="underline hover:text-amber-200"
                data-testid="lineage-parent-link"
              >
                組合 #{portfolio.parent_id}
              </Link>{" "}
              分裂 · fork NAV {portfolio.parent_nav_at_fork?.toFixed(4)}
            </p>
          ) : null}
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
        {continuousPct != null ? (
          <div
            className="rounded border border-amber-700 bg-amber-900/20 p-3"
            data-testid="continuous-return-card"
          >
            <p className="text-xs text-amber-300">自母組合起報酬</p>
            <p className={`text-lg font-semibold ${continuousColor}`}>
              {continuousPct}%
            </p>
          </div>
        ) : null}
      </div>

      <section className="rounded border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">NAV 走勢</h2>
        <PerformanceChart
          points={points}
          parentPoints={parent_points}
          parentNavAtFork={parent_nav_at_fork}
        />
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
                <td className="py-1 text-right">
                  {(h.weight * 100).toFixed(1)}%
                </td>
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

- [ ] **Step 2：tsc + lint**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 error

- [ ] **Step 3：跑既有前端單元測試**

Run: `cd frontend && pnpm test --run`
Expected: 全 pass

- [ ] **Step 4：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add frontend/src/pages/PortfolioTrackingPage.tsx && rtk git commit -m "feat: show lineage info and continuous return on tracking page"
```

---

## Task 11：E2E 更新

**Files:**
- Modify: `frontend/tests/e2e/stock-actions.spec.ts`
- Modify: `frontend/tests/e2e/portfolio-tracking.spec.ts`

- [ ] **Step 1：先讀兩個 e2e 檔，找到適合加 assertion 的點**

Run: `cat frontend/tests/e2e/stock-actions.spec.ts frontend/tests/e2e/portfolio-tracking.spec.ts | head -400`
記下每個 spec 的 test 命名風格與 fixture 準備方式。

- [ ] **Step 2：在 stock-actions.spec.ts 加一個「加入組合後新組合帶血緣」的測試**

在 stock-actions.spec.ts 檔尾追加（若現有 test 有 fixture、複製其模式）：

```typescript
test("加入組合後新組合會帶 parent_id 血緣", async ({ page, request }) => {
  // 前置：建一個 parent 組合（直接打 API，繞過 UI）
  const parent = await request.post("/api/portfolios/saved", {
    data: {
      style: "balanced",
      label: "e2e-parent",
      holdings: [
        { symbol: "2330", name: "台積電", weight: 1.0, base_price: 600.0 },
      ],
    },
  });
  expect(parent.ok()).toBeTruthy();
  const parentJson = await parent.json();

  await page.goto("/stocks/2317");
  await page.getByTestId("add-to-portfolio").click();
  await page.getByTestId(`pick-portfolio-${parentJson.id}`).click();

  // 等 saved-portfolios list invalidate 後，新組合會出現在列表
  await expect
    .poll(async () => {
      const list = await request.get("/api/portfolios/saved");
      const items = await list.json();
      return items.find(
        (i: { parent_id: number | null; label: string }) =>
          i.label.startsWith("e2e-parent +") && i.parent_id === parentJson.id,
      );
    })
    .toBeTruthy();
});
```

注意：此 test 需要 `2317` 與 `2330` 在 `prices_daily` 今日有報價才不會撞 probe dialog。若 E2E 環境沒 seed，先修 fixture 或改 test 順序點 `save-confirm-proceed` 走 fallback 路徑。

- [ ] **Step 3：在 portfolio-tracking.spec.ts 加「血緣頁面顯示」測試**

檔尾追加：

```typescript
test("forked 組合追蹤頁顯示血緣資訊", async ({ page, request }) => {
  const parent = await request.post("/api/portfolios/saved", {
    data: {
      style: "balanced",
      label: "e2e-lineage-parent",
      holdings: [
        { symbol: "2330", name: "台積電", weight: 1.0, base_price: 600.0 },
      ],
    },
  });
  const parentJson = await parent.json();

  const child = await request.post("/api/portfolios/saved", {
    data: {
      style: "balanced",
      label: "e2e-lineage-child",
      holdings: [
        { symbol: "2330", name: "台積電", weight: 1.0, base_price: 600.0 },
      ],
      parent_id: parentJson.id,
    },
  });
  const childJson = await child.json();

  await page.goto(`/portfolios/${childJson.id}`);
  await expect(page.getByTestId("lineage-info")).toBeVisible();
  await expect(page.getByTestId("lineage-parent-link")).toHaveAttribute(
    "href",
    `/portfolios/${parentJson.id}`,
  );
  await expect(page.getByTestId("continuous-return-card")).toBeVisible();
});
```

- [ ] **Step 4：跑 E2E**

Run: `cd frontend && pnpm e2e --reporter=list`
Expected: 全 pass

（如果新 test fail，看 trace 確認是 seed 問題還是實作問題。若是 seed 缺 `2330`/`2317` 收盤價，跟使用者確認是否在 E2E 環境跑 `rtk git status`，或把 seed 加到 e2e.globalSetup）

- [ ] **Step 5：commit**

```bash
cd g:/codingdata/alpha-lab && rtk git add frontend/tests/e2e/ && rtk git commit -m "test: cover portfolio lineage flow in e2e"
```

---

## Task 12：文件同步

**Files:**
- Modify: `docs/knowledge/features/tracking/overview.md`
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（Phase 7 狀態註記）
- Modify: `docs/USER_GUIDE.md`

- [ ] **Step 1：更新 `docs/knowledge/features/tracking/overview.md`**

在 `updated:` 欄位改為 `2026-04-16`（或執行日期）。在「現行實作（Phase 6）」區塊標題下追加：

````markdown
### Phase 7 追加：血緣欄位與連續 NAV

**資料表新增欄位：**

- `portfolios_saved.parent_id`：指向母組合（`portfolios_saved.id`，nullable）
- `portfolios_saved.parent_nav_at_fork`：fork 當下母組合的 `latest_nav`（nullable）

**`save_portfolio` 流程新增：**

- 若 `payload.parent_id` 非 None，先呼叫 `compute_performance(parent_id)` 取 `latest_nav`，存為 `parent_nav_at_fork`；parent 不存在 → `ValueError` → 400。

**`compute_performance` 回傳新增：**

- `parent_points`：若 row 有 `parent_id`，遞迴取 parent 的 `points` 中 `date < child.base_date` 的部分。
- `parent_nav_at_fork`：直接讀 row 欄位。

**SavedPortfolioCreate schema 驗證（Pydantic model_validator）：**

- `holdings` 內 `symbol` 不得重複 → `ValidationError` → 422
- `abs(sum(weights) - 1.0) > 1e-6` → `ValidationError` → 422（`buildMergedHoldings` 產生的浮點漂移落在容忍內）

**前端連續曲線：**

- `PerformanceChart` 新增 `parentPoints` / `parentNavAtFork` props；拿到時把 self 段 NAV `× parentNavAtFork` 勾連 parent 段末端成為連續曲線，並在 fork date 畫垂直 `ReferenceLine`。
- `PortfolioTrackingPage` 顯示「由 組合 #X 分裂」區塊（連結回父組合）與「自母組合起報酬」卡片。
````

並在「關鍵檔案」清單追加：

```
- [backend/src/alpha_lab/storage/migrations.py](../../../../backend/src/alpha_lab/storage/migrations.py)
- [frontend/tests/components/PerformanceChart.test.tsx](../../../../frontend/tests/components/PerformanceChart.test.tsx)
```

「修改時注意事項」區塊追加：

```
- **Phase 7 血緣欄位為 nullable**：既有儲存組合的 `parent_id` / `parent_nav_at_fork` 皆為 NULL，所有前端 UI 必須把「沒 parent」當正常狀態顯示。
- **fork 不會 rebuild 父組合歷史**：`parent_points` 是在 `compute_performance(child)` 時臨時遞迴出來的，parent 本身資料改動會即時反映；若 parent 被刪除，child `parent_points` 將變 `None`（ORM FK 不 cascade，row 仍可 resolve parent 不到就略過）。要動刪除語意時同步決定要不要 cascade / 阻擋。
```

- [ ] **Step 2：更新 spec Phase 表**

在 `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` 找到 Phase 7 那行（約 471），修改為：

```markdown
| 7A | ✅ 完成（2026-04-16） | 組合追蹤強化 | `portfolios_saved.parent_id` + `parent_nav_at_fork` 血緣欄位；`SavedPortfolioCreate` model_validator（symbol 唯一 / `\|sum(weights)-1\| < 1e-6`）；`/performance` 回傳 `parent_points`；追蹤頁連續 NAV 曲線 + 「自母組合起報酬」卡片；idempotent schema migration helper |
| 7B | 未開始 | 數據源與自動化 | Yahoo Finance 備援數據源、新聞彙整（每週掃描）、每日自動簡報（`data/reports/daily/`）、`data/processed/` 計算後指標、報告離線快取 |
```

（驗收日期請在實作完成後用使用者確認日期；本步驟由執行者填入。）

- [ ] **Step 3：更新 USER_GUIDE.md**

搜尋「追蹤」或「組合追蹤」章節，追加一段：

```markdown
### 組合血緣（Phase 7A）

當你在個股頁點「加入組合」建立的新組合，會自動記錄來自哪個母組合。進到新組合的追蹤頁時：

- 標題下方會顯示「由 組合 #X 分裂」連結，可一鍵回到母組合
- 報酬卡片會多一張「自母組合起報酬」，呈現從母組合 base_date 起算的連續報酬
- NAV 走勢圖會把母組合的歷史走勢（灰色虛線）接在新組合之前，fork 當日畫一條橘色虛線標示切換點
```

- [ ] **Step 4：中文亂碼掃描**

Run: `cd g:/codingdata/alpha-lab && rtk grep "��" docs/ backend/src/ frontend/src/ 2>/dev/null | head -20`
Expected: 無輸出

- [ ] **Step 5：commit 文件**

```bash
cd g:/codingdata/alpha-lab && rtk git add docs/ && rtk git commit -m "docs: document portfolio lineage and Phase 7A status"
```

---

## Task 13：手動驗收指引（交給使用者跑）

- [ ] **Step 1：啟動 backend 與 frontend，給使用者完整驗收指令**

把以下指令原文貼給使用者（Windows CMD 格式）：

```cmd
REM 1. 啟動後端（會自動跑 migration 補血緣欄位）
cd backend
.venv\Scripts\python.exe -m uvicorn alpha_lab.api.main:app --reload

REM 2. 另一個 terminal 啟動前端
cd frontend
pnpm dev
```

驗收步驟：
1. 先進 `/portfolios` 儲存一個組合（例：balanced），確認列表出現
2. 進任一個股頁（例：`/stocks/2317`），點「加入組合」，選剛儲存的組合，權重 10%，送出
3. 進 `/portfolios`，點新組合（label 形如「原 label + 2317」）
4. 確認追蹤頁：
   - 標題下有「由 組合 #X 分裂 · fork NAV 1.0000」這行小字
   - 卡片區出現「自母組合起報酬」
   - NAV 走勢圖有灰色虛線（母組合段）+ 藍色實線（新組合段），fork 當日有橘色垂直線
5. 確認 schema 驗證：直接 curl `POST /api/portfolios/saved` 帶 symbol 重複或權重 0.8 的 holdings，應該 422

```cmd
REM schema 驗證直接用 curl（Windows CMD）
curl -X POST http://localhost:8000/api/portfolios/saved ^
  -H "Content-Type: application/json" ^
  -d "{\"style\":\"balanced\",\"label\":\"bad\",\"holdings\":[{\"symbol\":\"2330\",\"name\":\"x\",\"weight\":0.5,\"base_price\":600},{\"symbol\":\"2330\",\"name\":\"x\",\"weight\":0.5,\"base_price\":600}]}"
```

預期：422 + `"duplicate symbol"` 訊息。

- [ ] **Step 2：等使用者回報「Phase 7A 驗證通過」**

不可自動 commit 最終狀態。等使用者明確說 OK 再進 Step 3。

- [ ] **Step 3：收到驗收 OK，若前面各 task 已 commit 完則無需 final commit；若有未 commit 殘留用**

```bash
cd g:/codingdata/alpha-lab && rtk git status && rtk git log --oneline -n 15
```

確認 commit 序列合理，結束 Phase 7A。

---

## Self-Review

**1. Spec coverage：**
- ✅ `parent_id` + `parent_nav_at_fork` 血緣欄位 → Task 2
- ✅ `SavedHolding` schema 層 symbol 唯一 + `|sum-1|<1e-6` → Task 3
- ✅ 讓「加入組合」建立的新組合能把前段 NAV 接續顯示為連續曲線 → Task 5 + 9 + 10
- ✅ 「加入組合」流程 probe dialog → 已在 Phase 6 完成（spec 原文第 3 點），不進 Phase 7A

**2. Placeholder scan：** 未用 TBD / "implement later" 等字眼，所有 step 都有實際 code 或 cmd。E2E 的 seed 問題寫了 fallback 指引。

**3. Type consistency：**
- `SavedPortfolioCreate.parent_id?: number | null`（前端）vs `parent_id: int | None = None`（後端）✅
- `PerformanceResponse.parent_points: list[PerformancePoint] | None`（後端）/ `parent_points: PerformancePoint[] | null`（前端）✅
- `buildChartSeries({ points, parentPoints, parentNavAtFork })` 在 Task 9 定義，前端其他處未呼叫 ✅
- `test_save_portfolio_with_parent_stores_lineage` 假設 parent `latest_nav = 1.0`（僅 base_date 一筆），推理正確 ✅
