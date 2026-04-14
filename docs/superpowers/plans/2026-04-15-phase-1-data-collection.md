# Phase 1: 數據抓取（最小管線）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通「抓取 → 落庫 → API 觸發」的端到端管線。完成 SQLAlchemy 基礎建設、一個 TWSE collector（日股價）、一個 MOPS collector（月營收），以及 `POST /api/jobs/collect` + `GET /api/jobs/status/{id}` 用於觸發與追蹤抓取任務。

**Architecture:** 所有寫入走 SQLAlchemy session。Collector 為純函式（input: 參數；output: Pydantic 模型 list），由 job runner 呼叫並負責 upsert。Job 系統用 FastAPI BackgroundTasks 非同步執行，狀態寫入 `jobs` 表讓前端輪詢。

**Tech Stack:** SQLAlchemy 2.x（declarative）、SQLite、httpx（async client）、pydantic v2、FastAPI BackgroundTasks、pytest + respx（httpx mocking）

---

## Phase 1 工作總覽

| 群組 | 任務數 | 任務 |
|------|--------|------|
| A | 4 | SQLAlchemy 基礎建設 + Models + DB 初始化 |
| B | 3 | TWSE 日股價 collector |
| C | 3 | MOPS 月營收 collector |
| D | 3 | Job 系統（service + 2 endpoints） |
| E | 2 | 知識庫（architecture + collectors） |
| F | 2 | Phase 1 驗收與 commit |

**總計：17 tasks**

## 範圍與邊界

**本 Phase 包含**：
- SQLAlchemy engine/session、declarative base
- Models：`stocks`、`prices_daily`、`revenues_monthly`、`jobs`
- DB 初始化（`create_all` 於 app startup）
- TWSE 日股價 collector（單檔 or 多檔 symbols，單日）
- MOPS 月營收 collector（單檔 or 多檔 symbols，單月）
- `POST /api/jobs/collect`（body 指定 type + 參數）
- `GET /api/jobs/status/{job_id}`
- 單元測試（collectors with respx mock）
- 整合測試（TestClient for job API）
- 知識庫：`architecture/data-models.md`、`architecture/data-flow.md`、`collectors/twse.md`、`collectors/mops.md`

**本 Phase 不包含**（Phase 1.5 處理）：
- 三大法人、融資融券
- 季報（合併損益、資產負債、現金流）
- 重大訊息、新聞
- Alembic migration（用 `metadata.create_all` 即可，1.5 評估是否引入）
- 定時排程（cron、APScheduler）

## Commit 規範（本專案 MANDATORY）

1. **靜態分析必做**：`ruff check .` 與 `mypy src` 必須 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit，給使用者手動驗收指引，等使用者明確說「驗證通過」才能 commit
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` / `chore` 不混在同一 commit
4. **禁止 scope 括號**：`type: description`，不可寫 `type(scope): description`
5. **同步檢查**：知識庫、spec、USER_GUIDE、E2E 是否需要連動更新
6. **中文亂碼掃描**：完成寫檔後 Grep `��`

每個 Task 的 commit 前必須先完成該 Task 全部程式碼步驟，並提供手動驗收指引。

---

## Task A1: 新增依賴（httpx、respx、pytest-asyncio）

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 更新 `[project.dependencies]` 加入 httpx**

在 `dependencies` 陣列加入：

```toml
"httpx>=0.27.0",
```

（`sqlalchemy`、`pandas`、`numpy`、`fastapi`、`uvicorn`、`pydantic` 已於 Phase 0 加入，無需重複）

- [ ] **Step 2: 更新 `[project.optional-dependencies].dev` 加入測試依賴**

在 dev 陣列加入：

```toml
"pytest-asyncio>=0.23.0",
"respx>=0.21.0",
```

- [ ] **Step 3: pip install 新依賴**

```bash
cd backend
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

預期：httpx、respx、pytest-asyncio 安裝成功。

- [ ] **Step 4: 驗證 pytest 仍能跑**

```bash
cd backend
.venv/Scripts/python.exe -m pytest
```

預期：Phase 0 的 `test_health.py` 仍 1 passed。

- [ ] **Step 5: 手動驗收指引**

> 請確認 `backend/pyproject.toml` 可讀、`pip install` 無錯、`pytest` 仍通過。回覆「A1 OK」後 commit。

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: add httpx and test deps for phase 1"
```

---

## Task A2: SQLAlchemy engine、session、settings

**Files:**
- Create: `backend/src/alpha_lab/storage/engine.py`
- Create: `backend/src/alpha_lab/storage/__init__.py`（更新）
- Create: `backend/src/alpha_lab/config.py`

- [ ] **Step 1: 建立 `config.py`**

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """應用設定，從環境變數讀取，預設值用於開發。"""

    model_config = SettingsConfigDict(env_prefix="ALPHA_LAB_", env_file=".env")

    # 資料庫：預設指向 repo 根 data/alpha_lab.db
    database_url: str = "sqlite:///../data/alpha_lab.db"

    # HTTP client 設定
    http_timeout_seconds: float = 30.0
    http_user_agent: str = "alpha-lab/0.1.0 (+https://github.com/local)"


def get_settings() -> Settings:
    return Settings()
```

需要在 `pyproject.toml` 補 `pydantic-settings>=2.0.0`（若尚未加入）。

- [ ] **Step 2: 建立 `storage/engine.py`**

```python
"""SQLAlchemy engine 與 session factory。

設計：
- 使用 sync engine（Phase 1 collector 與 job runner 均為 async 函式，
  但對 SQLite 的寫入走 sync session，避免 sqlite+aiosqlite 的併發坑）
- 所有 session 透過 `get_session()` 取得，呼叫端負責 commit / rollback
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False, future=True
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """交易範圍 context manager：自動 commit / rollback。"""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 3: 更新 `storage/__init__.py`** 匯出核心物件

```python
"""Storage 層：SQLAlchemy engine、session、models。"""

from alpha_lab.storage.engine import get_engine, get_session_factory, session_scope

__all__ = ["get_engine", "get_session_factory", "session_scope"]
```

- [ ] **Step 4: 驗證可匯入**

```bash
cd backend
.venv/Scripts/python.exe -c "from alpha_lab.storage import session_scope; print('OK')"
```

預期：印出 `OK`，無 import error。

- [ ] **Step 5: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請確認 `alpha_lab.config.Settings` 與 `storage.session_scope` 可匯入、靜態檢查通過。回覆「A2 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/src/alpha_lab/config.py backend/src/alpha_lab/storage/
git commit -m "feat: add sqlalchemy engine and settings"
```

---

## Task A3: SQLAlchemy Models（stocks、prices_daily、revenues_monthly、jobs）

**Files:**
- Create: `backend/src/alpha_lab/storage/models.py`

- [ ] **Step 1: 先寫 failing test**

`backend/tests/storage/__init__.py`（空）與 `backend/tests/storage/test_models.py`：

```python
"""Models 結構測試：確保 declarative base 註冊所有表、欄位型別正確。"""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage.models import Base, Job, PriceDaily, RevenueMonthly, Stock


def test_base_registers_expected_tables() -> None:
    expected = {"stocks", "prices_daily", "revenues_monthly", "jobs"}
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_create_all_and_insert_stock() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        session.commit()

        fetched = session.get(Stock, "2330")
        assert fetched is not None
        assert fetched.name == "台積電"


def test_price_daily_composite_primary_key() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        session.add(
            PriceDaily(
                symbol="2330",
                trade_date=datetime(2026, 4, 1, tzinfo=UTC).date(),
                open=500.0,
                high=510.0,
                low=499.0,
                close=505.0,
                volume=12345678,
            )
        )
        session.commit()


def test_job_defaults() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        job = Job(job_type="twse_prices", params_json="{}")
        session.add(job)
        session.commit()
        assert job.id is not None
        assert job.status == "pending"
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/storage/test_models.py -v
```

預期：`ModuleNotFoundError: No module named 'alpha_lab.storage.models'`。

- [ ] **Step 3: 實作 `storage/models.py`**

```python
"""SQLAlchemy declarative models。

Phase 1 scope:
- Stock: 股票基本資料
- PriceDaily: 日股價（TWSE 來源）
- RevenueMonthly: 月營收（MOPS 來源）
- Job: 抓取任務紀錄

Phase 1.5 將新增：FinancialStatement、InstitutionalTrade、MarginTrade、Event
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Stock(Base):
    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    listed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    prices: Mapped[list["PriceDaily"]] = relationship(back_populates="stock")
    revenues: Mapped[list["RevenueMonthly"]] = relationship(back_populates="stock")


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

    stock: Mapped[Stock] = relationship(back_populates="prices")


class RevenueMonthly(Base):
    __tablename__ = "revenues_monthly"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, primary_key=True)
    revenue: Mapped[int] = mapped_column(Integer, nullable=False)  # 千元
    yoy_growth: Mapped[float | None] = mapped_column(Float, nullable=True)  # %
    mom_growth: Mapped[float | None] = mapped_column(Float, nullable=True)  # %

    stock: Mapped[Stock] = relationship(back_populates="revenues")


class Job(Base):
    """抓取任務紀錄。

    status 生命週期：pending → running → (completed | failed)
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4: 更新 `storage/__init__.py`** 匯出 models

```python
from alpha_lab.storage.engine import get_engine, get_session_factory, session_scope
from alpha_lab.storage.models import Base, Job, PriceDaily, RevenueMonthly, Stock

__all__ = [
    "Base",
    "Job",
    "PriceDaily",
    "RevenueMonthly",
    "Stock",
    "get_engine",
    "get_session_factory",
    "session_scope",
]
```

- [ ] **Step 5: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/storage/test_models.py -v
```

預期：4 passed。

- [ ] **Step 6: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 7: 手動驗收指引**

> 請確認 `pytest tests/storage` 4 passed、靜態檢查 0 error。回覆「A3 OK」後 commit。

- [ ] **Step 8: Commit**

```bash
git add backend/src/alpha_lab/storage/ backend/tests/storage/
git commit -m "feat: add sqlalchemy models for stocks prices revenues jobs"
```

---

## Task A4: DB 初始化（app startup hook）

**Files:**
- Modify: `backend/src/alpha_lab/api/main.py`
- Create: `backend/src/alpha_lab/storage/init_db.py`

- [ ] **Step 1: 建立 `init_db.py`**

```python
"""Phase 1 採用 SQLAlchemy `create_all` 自動建表。

Phase 1.5 若 schema 變動頻繁，再評估引入 Alembic。
"""

from pathlib import Path

from alpha_lab.storage.engine import get_engine
from alpha_lab.storage.models import Base


def init_database() -> None:
    """建立所有表（若已存在則跳過）。

    同時確保 sqlite 檔案所在資料夾存在。
    """
    engine = get_engine()
    url = str(engine.url)
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(engine)
```

- [ ] **Step 2: 修改 `api/main.py` 在 startup 時呼叫**

找到現有的 FastAPI app 初始化，改為使用 lifespan context manager：

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpha_lab.api.routes import health
from alpha_lab.storage.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_database()
    yield


app = FastAPI(title="alpha-lab API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
```

（保留既有 `health` router include，上述是完整替換範例）

- [ ] **Step 3: 手動啟動 uvicorn 驗證**

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn alpha_lab.api.main:app --reload
```

預期：startup log 看到 FastAPI 啟動，`data/alpha_lab.db` 自動建立於 repo 根的 `data/`。

用 SQLite CLI 驗證：

```bash
.venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); print([r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')])"
```

預期輸出包含 `['stocks', 'prices_daily', 'revenues_monthly', 'jobs']`。

- [ ] **Step 4: 驗證 Phase 0 health check 仍可用**

```bash
curl http://127.0.0.1:8000/api/health
```

預期：`{"status":"ok","version":"0.1.0","timestamp":"..."}`。

- [ ] **Step 5: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請啟動 uvicorn 確認 `data/alpha_lab.db` 被建立、4 個表都在、`/api/health` 仍正常回應。回覆「A4 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/api/main.py backend/src/alpha_lab/storage/init_db.py
git commit -m "feat: auto create tables on app startup"
```

---

## Task B1: TWSE 日股價 collector（schema + client）

**Files:**
- Create: `backend/src/alpha_lab/collectors/twse.py`
- Create: `backend/src/alpha_lab/schemas/price.py`

**API 參考**：TWSE 個股日成交資訊
`https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=YYYYMMDD&stockNo=SYMBOL&response=json`

回傳結構（擷取）：

```json
{
  "stat": "OK",
  "date": "20260401",
  "title": "...",
  "fields": ["日期","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"],
  "data": [
    ["115/04/01","12345678","6234567890","500.00","510.00","499.00","505.00","+2.00","45678"],
    ...
  ]
}
```

- [ ] **Step 1: 先寫 failing test**

`backend/tests/collectors/__init__.py`（空）與 `backend/tests/collectors/test_twse.py`：

```python
"""TWSE collector 單元測試（使用 respx mock httpx）。"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.schemas.price import DailyPrice

SAMPLE_RESPONSE = {
    "stat": "OK",
    "date": "20260401",
    "fields": [
        "日期", "成交股數", "成交金額", "開盤價", "最高價",
        "最低價", "收盤價", "漲跌價差", "成交筆數",
    ],
    "data": [
        ["115/04/01", "12,345,678", "6,234,567,890", "500.00",
         "510.00", "499.00", "505.00", "+2.00", "45,678"],
    ],
}


@pytest.mark.asyncio
async def test_fetch_daily_prices_parses_sample() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=SAMPLE_RESPONSE)

        results = await fetch_daily_prices(symbol="2330", year_month=date(2026, 4, 1))

    assert len(results) == 1
    p = results[0]
    assert isinstance(p, DailyPrice)
    assert p.symbol == "2330"
    assert p.trade_date == date(2026, 4, 1)
    assert p.open == 500.0
    assert p.close == 505.0
    assert p.volume == 12345678


@pytest.mark.asyncio
async def test_fetch_daily_prices_raises_on_non_ok_stat() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(
            json={"stat": "查詢無資料", "data": []}
        )

        with pytest.raises(ValueError, match="查詢無資料"):
            await fetch_daily_prices(symbol="9999", year_month=date(2026, 4, 1))


@pytest.mark.asyncio
async def test_fetch_daily_prices_raises_on_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(500)

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_daily_prices(symbol="2330", year_month=date(2026, 4, 1))
```

需在 `backend/pyproject.toml` 的 `[tool.pytest.ini_options]` 加 `asyncio_mode = "auto"`。

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse.py -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 實作 `schemas/price.py`**

```python
"""日股價 Pydantic 模型。"""

from datetime import date

from pydantic import BaseModel, Field


class DailyPrice(BaseModel):
    """單一股票單日 OHLCV。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: int = Field(..., ge=0)
```

- [ ] **Step 4: 實作 `collectors/twse.py`**

```python
"""TWSE 資料抓取。

Phase 1: 日股價（STOCK_DAY）
Phase 1.5 將新增：三大法人、融資融券
"""

from datetime import date

import httpx

from alpha_lab.config import get_settings
from alpha_lab.schemas.price import DailyPrice

TWSE_BASE_URL = "https://www.twse.com.tw"
STOCK_DAY_PATH = "/rwd/zh/afterTrading/STOCK_DAY"


def _roc_date_to_iso(roc: str) -> date:
    """民國日期字串（例：'115/04/01'）轉西元 date。"""
    parts = roc.split("/")
    if len(parts) != 3:
        raise ValueError(f"bad ROC date: {roc}")
    year = int(parts[0]) + 1911
    return date(year, int(parts[1]), int(parts[2]))


def _parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def _parse_float(s: str) -> float:
    return float(s.replace(",", ""))


async def fetch_daily_prices(symbol: str, year_month: date) -> list[DailyPrice]:
    """抓取單一股票、單一月份的每日 OHLCV。

    TWSE API 以月為單位回傳該月所有交易日。`year_month` 只會使用年月。
    """
    settings = get_settings()
    params = {
        "date": year_month.strftime("%Y%m01"),
        "stockNo": symbol,
        "response": "json",
    }
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=TWSE_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
    ) as client:
        resp = await client.get(STOCK_DAY_PATH, params=params)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("stat") != "OK":
        raise ValueError(f"TWSE returned non-OK stat: {payload.get('stat')}")

    results: list[DailyPrice] = []
    for row in payload.get("data", []):
        # fields: 日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數
        results.append(
            DailyPrice(
                symbol=symbol,
                trade_date=_roc_date_to_iso(row[0]),
                open=_parse_float(row[3]),
                high=_parse_float(row[4]),
                low=_parse_float(row[5]),
                close=_parse_float(row[6]),
                volume=_parse_int(row[1]),
            )
        )
    return results
```

- [ ] **Step 5: 更新 `collectors/__init__.py`** 匯出

```python
from alpha_lab.collectors.twse import fetch_daily_prices

__all__ = ["fetch_daily_prices"]
```

- [ ] **Step 6: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse.py -v
```

預期：3 passed。

- [ ] **Step 7: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 8: 手動驗收指引**

> 請確認 `pytest tests/collectors/test_twse.py` 3 passed、靜態檢查 0 error。回覆「B1 OK」後 commit。

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/src/alpha_lab/schemas/price.py backend/src/alpha_lab/collectors/ backend/tests/collectors/
git commit -m "feat: add twse daily price collector"
```

---

## Task B2: TWSE collector upsert 到 DB

**Files:**
- Create: `backend/src/alpha_lab/collectors/runner.py`
- Modify: `backend/tests/collectors/test_twse.py`（追加 upsert 整合測試）

- [ ] **Step 1: 先寫 failing test**

在 `test_twse.py` 追加：

```python
from alpha_lab.collectors.runner import upsert_daily_prices
from alpha_lab.storage.models import Base, PriceDaily, Stock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_upsert_daily_prices_inserts_new_rows() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                open=500.0, high=510.0, low=499.0, close=505.0, volume=1000,
            ),
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 2),
                open=505.0, high=512.0, low=504.0, close=510.0, volume=2000,
            ),
        ]
        inserted = upsert_daily_prices(session, rows)
        session.commit()

        assert inserted == 2
        assert session.query(PriceDaily).count() == 2


def test_upsert_daily_prices_updates_existing_row() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            PriceDaily(
                symbol="2330", trade_date=date(2026, 4, 1),
                open=100.0, high=100.0, low=100.0, close=100.0, volume=1,
            )
        )
        session.commit()

        updated = upsert_daily_prices(
            session,
            [DailyPrice(
                symbol="2330", trade_date=date(2026, 4, 1),
                open=500.0, high=510.0, low=499.0, close=505.0, volume=1000,
            )],
        )
        session.commit()

        assert updated == 1
        row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
        assert row is not None
        assert row.close == 505.0
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse.py::test_upsert_daily_prices_inserts_new_rows -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 實作 `collectors/runner.py`**

```python
"""Collector 執行層：把 Pydantic 輸出 upsert 到 DB。

Stock 主資料採「若不存在就建立 placeholder」策略（name 用 symbol）；
正式的公司基本資料同步未在 Phase 1 範圍內。
"""

from sqlalchemy.orm import Session

from alpha_lab.schemas.price import DailyPrice
from alpha_lab.schemas.revenue import MonthlyRevenue
from alpha_lab.storage.models import PriceDaily, RevenueMonthly, Stock


def _ensure_stock(session: Session, symbol: str) -> None:
    existing = session.get(Stock, symbol)
    if existing is None:
        session.add(Stock(symbol=symbol, name=symbol))


def upsert_daily_prices(session: Session, rows: list[DailyPrice]) -> int:
    """upsert 日股價。回傳寫入筆數（新增 + 更新）。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        existing = session.get(
            PriceDaily, {"symbol": row.symbol, "trade_date": row.trade_date}
        )
        if existing is None:
            session.add(
                PriceDaily(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                )
            )
        else:
            existing.open = row.open
            existing.high = row.high
            existing.low = row.low
            existing.close = row.close
            existing.volume = row.volume
        count += 1
    return count


def upsert_monthly_revenues(session: Session, rows: list[MonthlyRevenue]) -> int:
    """upsert 月營收。回傳寫入筆數。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        existing = session.get(
            RevenueMonthly,
            {"symbol": row.symbol, "year": row.year, "month": row.month},
        )
        if existing is None:
            session.add(
                RevenueMonthly(
                    symbol=row.symbol,
                    year=row.year,
                    month=row.month,
                    revenue=row.revenue,
                    yoy_growth=row.yoy_growth,
                    mom_growth=row.mom_growth,
                )
            )
        else:
            existing.revenue = row.revenue
            existing.yoy_growth = row.yoy_growth
            existing.mom_growth = row.mom_growth
        count += 1
    return count
```

（`schemas/revenue.py` 於 Task C1 建立，這裡 import 在 C1 前執行會失敗；Task 順序保證 C1 後才跑整合測試。或可先建立一個 placeholder `schemas/revenue.py`。為避免循環依賴，**於本 Step 同時建立最小版 `schemas/revenue.py`**）

追加建立 `backend/src/alpha_lab/schemas/revenue.py`：

```python
"""月營收 Pydantic 模型（Task B2 建立最小版，C1 會擴充註解/驗證）。"""

from pydantic import BaseModel, Field


class MonthlyRevenue(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    year: int = Field(..., ge=1990, le=2100)
    month: int = Field(..., ge=1, le=12)
    revenue: int = Field(..., ge=0)  # 千元
    yoy_growth: float | None = None
    mom_growth: float | None = None
```

- [ ] **Step 4: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse.py -v
```

預期：全部 5 passed（3 fetch + 2 upsert）。

- [ ] **Step 5: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請確認 `pytest tests/collectors/test_twse.py` 5 passed。回覆「B2 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/collectors/runner.py backend/src/alpha_lab/schemas/revenue.py backend/tests/collectors/test_twse.py
git commit -m "feat: add upsert logic for prices and revenues"
```

---

## Task B3: TWSE collector 真實網路煙霧測試（可選、手動執行）

**Files:**
- Create: `backend/scripts/smoke_twse.py`

- [ ] **Step 1: 建立手動煙霧測試腳本**

```python
"""TWSE collector 真實網路煙霧測試。

用法：
    python scripts/smoke_twse.py

會實際打 TWSE API 抓 2330 本月資料並印出前 3 筆。
若 TWSE 改 API 規格，此腳本可快速 reproduce。
"""

import asyncio
from datetime import date

from alpha_lab.collectors.twse import fetch_daily_prices


async def main() -> None:
    today = date.today()
    rows = await fetch_daily_prices(symbol="2330", year_month=today)
    print(f"Fetched {len(rows)} rows for 2330 in {today:%Y-%m}")
    for row in rows[:3]:
        print(f"  {row.trade_date} O={row.open} H={row.high} L={row.low} C={row.close} V={row.volume}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 手動驗收指引**

> 請手動執行 `cd backend && .venv/Scripts/python.exe scripts/smoke_twse.py`，確認能印出真實資料（若當月無交易資料會 raise ValueError，正常）。回覆「B3 OK」後 commit。
>
> 注意：TWSE 對短時間多次請求會擋；若要多次跑，等 1 分鐘。

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_twse.py
git commit -m "chore: add twse smoke test script"
```

---

## Task C1: MOPS 月營收 collector（schema + client）

**Files:**
- Modify: `backend/src/alpha_lab/schemas/revenue.py`（補 docstring）
- Create: `backend/src/alpha_lab/collectors/mops.py`

**API 參考**：公開資訊觀測站月營收
`https://mopsov.twse.com.tw/nas/t21/sii/t21sc03_<YEAR-1911>_<MONTH>_0.html`（HTML 表格）

或使用 MOPS 提供的彙總 API：
`https://openapi.twse.com.tw/v1/opendata/t187ap05_L`（全體上市公司最新一期月營收，JSON）

**決策**：Phase 1 採後者（JSON 更穩定），但只取「最新月」；若要抓歷史月份則需改用 HTML 解析，留 Phase 1.5 處理。

範例 JSON 結構：

```json
[
  {
    "出表日期": "1150410",
    "資料年月": "11503",
    "公司代號": "2330",
    "公司名稱": "台積電",
    "營業收入-當月營收": "300000000",
    "營業收入-上月營收": "280000000",
    "營業收入-去年當月營收": "250000000",
    "營業收入-上月比較增減(%)": "7.14",
    "營業收入-去年同月增減(%)": "20.00"
  }
]
```

- [ ] **Step 1: 先寫 failing test**

`backend/tests/collectors/test_mops.py`：

```python
"""MOPS collector 單元測試。"""

import pytest
import respx

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.schemas.revenue import MonthlyRevenue

SAMPLE_RESPONSE = [
    {
        "出表日期": "1150410",
        "資料年月": "11503",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "營業收入-當月營收": "300000000",
        "營業收入-上月營收": "280000000",
        "營業收入-去年當月營收": "250000000",
        "營業收入-上月比較增減(%)": "7.14",
        "營業收入-去年同月增減(%)": "20.00",
    },
    {
        "出表日期": "1150410",
        "資料年月": "11503",
        "公司代號": "2317",
        "公司名稱": "鴻海",
        "營業收入-當月營收": "500000000",
        "營業收入-上月營收": "510000000",
        "營業收入-去年當月營收": "450000000",
        "營業收入-上月比較增減(%)": "-1.96",
        "營業收入-去年同月增減(%)": "11.11",
    },
]


@pytest.mark.asyncio
async def test_fetch_latest_monthly_revenues_parses_sample() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=SAMPLE_RESPONSE)

        results = await fetch_latest_monthly_revenues(symbols=["2330", "2317"])

    assert len(results) == 2
    tsmc = next(r for r in results if r.symbol == "2330")
    assert isinstance(tsmc, MonthlyRevenue)
    assert tsmc.year == 2026
    assert tsmc.month == 3
    assert tsmc.revenue == 300000000
    assert tsmc.yoy_growth == 20.00


@pytest.mark.asyncio
async def test_fetch_latest_monthly_revenues_filters_symbols() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=SAMPLE_RESPONSE)

        results = await fetch_latest_monthly_revenues(symbols=["2330"])

    assert len(results) == 1
    assert results[0].symbol == "2330"


@pytest.mark.asyncio
async def test_fetch_latest_monthly_revenues_all_when_symbols_none() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=SAMPLE_RESPONSE)

        results = await fetch_latest_monthly_revenues(symbols=None)

    assert len(results) == 2
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops.py -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 補齊 `schemas/revenue.py` 註解**

```python
"""月營收 Pydantic 模型。

資料來源：MOPS 公開資訊觀測站，每月 10 日後各公司公告前一月營收。
單位：revenue 為「千元」（MOPS 原始欄位單位），yoy/mom 為百分比（%）。
"""

from pydantic import BaseModel, Field


class MonthlyRevenue(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    year: int = Field(..., ge=1990, le=2100, description="西元年")
    month: int = Field(..., ge=1, le=12)
    revenue: int = Field(..., ge=0, description="當月營收（千元）")
    yoy_growth: float | None = Field(None, description="去年同月比，%")
    mom_growth: float | None = Field(None, description="上月比，%")
```

- [ ] **Step 4: 實作 `collectors/mops.py`**

```python
"""MOPS 資料抓取。

Phase 1: 月營收（openapi.twse.com.tw 的 t187ap05_L，最新一期全上市公司）
Phase 1.5 將新增：季報、重大訊息
"""

import httpx

from alpha_lab.config import get_settings
from alpha_lab.schemas.revenue import MonthlyRevenue

MOPS_OPENAPI_BASE = "https://openapi.twse.com.tw"
MONTHLY_REVENUE_PATH = "/v1/opendata/t187ap05_L"


def _parse_year_month(roc_ym: str) -> tuple[int, int]:
    """'11503' → (2026, 3)。"""
    if len(roc_ym) < 4:
        raise ValueError(f"bad ROC year-month: {roc_ym}")
    roc_year = int(roc_ym[:-2])
    month = int(roc_ym[-2:])
    return roc_year + 1911, month


def _parse_optional_float(s: str) -> float | None:
    if s in ("", "-", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


async def fetch_latest_monthly_revenues(
    symbols: list[str] | None = None,
) -> list[MonthlyRevenue]:
    """抓取最新一期全上市公司月營收。

    Args:
        symbols: 若提供，僅回傳清單內代號；None 代表全部。
    """
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=MOPS_OPENAPI_BASE,
        timeout=settings.http_timeout_seconds,
        headers=headers,
    ) as client:
        resp = await client.get(MONTHLY_REVENUE_PATH)
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, list):
        raise ValueError(f"unexpected MOPS payload type: {type(payload)}")

    symbol_filter = set(symbols) if symbols else None
    results: list[MonthlyRevenue] = []
    for item in payload:
        symbol = item.get("公司代號", "")
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        year, month = _parse_year_month(item["資料年月"])
        results.append(
            MonthlyRevenue(
                symbol=symbol,
                year=year,
                month=month,
                revenue=int(item["營業收入-當月營收"]),
                yoy_growth=_parse_optional_float(item.get("營業收入-去年同月增減(%)", "")),
                mom_growth=_parse_optional_float(item.get("營業收入-上月比較增減(%)", "")),
            )
        )
    return results
```

- [ ] **Step 5: 更新 `collectors/__init__.py`**

```python
from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.twse import fetch_daily_prices

__all__ = ["fetch_daily_prices", "fetch_latest_monthly_revenues"]
```

- [ ] **Step 6: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops.py -v
```

預期：3 passed。

- [ ] **Step 7: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 8: 手動驗收指引**

> 請確認 `pytest tests/collectors/test_mops.py` 3 passed。回覆「C1 OK」後 commit。

- [ ] **Step 9: Commit**

```bash
git add backend/src/alpha_lab/collectors/ backend/src/alpha_lab/schemas/revenue.py backend/tests/collectors/test_mops.py
git commit -m "feat: add mops monthly revenue collector"
```

---

## Task C2: MOPS smoke 腳本（可選）

**Files:**
- Create: `backend/scripts/smoke_mops.py`

- [ ] **Step 1: 建立煙霧測試腳本**

```python
"""MOPS collector 真實網路煙霧測試。"""

import asyncio

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues


async def main() -> None:
    rows = await fetch_latest_monthly_revenues(symbols=["2330", "2317", "0050"])
    print(f"Fetched {len(rows)} rows")
    for row in rows:
        print(f"  {row.symbol} {row.year}-{row.month:02d}: rev={row.revenue:,}k yoy={row.yoy_growth}%")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 手動驗收指引**

> 請手動執行 `python scripts/smoke_mops.py`，確認能打到真實 MOPS API。回覆「C2 OK」後 commit。

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_mops.py
git commit -m "chore: add mops smoke test script"
```

---

## Task C3: Collector runner 端到端整合測試

**Files:**
- Create: `backend/tests/collectors/test_runner_integration.py`

- [ ] **Step 1: 寫測試**

```python
"""Collector runner 端到端測試：mock HTTP + 真 SQLite 驗證完整流程。"""

from datetime import date

import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.runner import upsert_daily_prices, upsert_monthly_revenues
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.storage.models import Base, PriceDaily, RevenueMonthly


@pytest.mark.asyncio
async def test_twse_fetch_then_upsert_end_to_end() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    twse_payload = {
        "stat": "OK",
        "fields": ["日期","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"],
        "data": [
            ["115/04/01", "1000", "0", "100", "110", "99", "105", "+5", "1"],
        ],
    }

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=twse_payload)
        rows = await fetch_daily_prices(symbol="2330", year_month=date(2026, 4, 1))

    with SessionLocal() as session:
        n = upsert_daily_prices(session, rows)
        session.commit()
        assert n == 1
        assert session.query(PriceDaily).count() == 1


@pytest.mark.asyncio
async def test_mops_fetch_then_upsert_end_to_end() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    mops_payload = [{
        "資料年月": "11503",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "營業收入-當月營收": "300000000",
        "營業收入-上月比較增減(%)": "5.5",
        "營業收入-去年同月增減(%)": "20.0",
    }]

    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap05_L").respond(json=mops_payload)
        rows = await fetch_latest_monthly_revenues(symbols=["2330"])

    with SessionLocal() as session:
        n = upsert_monthly_revenues(session, rows)
        session.commit()
        assert n == 1
        assert session.query(RevenueMonthly).count() == 1
```

- [ ] **Step 2: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_integration.py -v
```

預期：2 passed。

- [ ] **Step 3: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 4: 手動驗收指引**

> 請確認整合測試 2 passed。回覆「C3 OK」後 commit。

- [ ] **Step 5: Commit**

```bash
git add backend/tests/collectors/test_runner_integration.py
git commit -m "test: add end-to-end collector runner integration tests"
```

---

## Task D1: Job service（enqueue、run、update status）

**Files:**
- Create: `backend/src/alpha_lab/jobs/__init__.py`
- Create: `backend/src/alpha_lab/jobs/service.py`
- Create: `backend/src/alpha_lab/jobs/types.py`
- Create: `backend/tests/jobs/__init__.py`
- Create: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: 先寫 failing test**

```python
"""Job service 單元測試。"""

from datetime import date

import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Base, Job, PriceDaily


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def test_create_job_returns_pending(session_factory) -> None:
    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        assert job.id is not None
        assert job.status == "pending"
        assert job.job_type == "twse_prices"


@pytest.mark.asyncio
async def test_run_job_sync_twse_prices_happy_path(session_factory) -> None:
    twse_payload = {
        "stat": "OK",
        "fields": ["日期","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"],
        "data": [["115/04/01", "1000", "0", "100", "110", "99", "105", "+5", "1"]],
    }

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=twse_payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.finished_at is not None
        assert session.query(PriceDaily).count() == 1


@pytest.mark.asyncio
async def test_run_job_sync_marks_failed_on_error(session_factory) -> None:
    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(500)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        failed = session.get(Job, job_id)
        assert failed is not None
        assert failed.status == "failed"
        assert failed.error_message is not None
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/jobs/ -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 實作 `jobs/types.py`**

```python
"""Job 類型列舉。新增 collector 時在此加一個 value 並在 service.run_job_sync 分派。"""

from enum import Enum


class JobType(str, Enum):
    TWSE_PRICES = "twse_prices"
    MOPS_REVENUE = "mops_revenue"
```

- [ ] **Step 4: 實作 `jobs/service.py`**

```python
"""Job service：建立 job、執行 job、更新狀態。

執行模型：
- run_job_sync 是 async 函式，在 FastAPI BackgroundTasks 中排程（單程序單執行緒）
- 適合本地個人工具；未來若要併發可改 Celery / RQ
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.runner import upsert_daily_prices, upsert_monthly_revenues
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Job

logger = logging.getLogger(__name__)


def create_job(
    session: Session, *, job_type: JobType, params: dict[str, Any]
) -> Job:
    """建立 pending 狀態的 job。呼叫端負責 commit。"""
    job = Job(
        job_type=job_type.value,
        params_json=json.dumps(params, ensure_ascii=False),
        status="pending",
    )
    session.add(job)
    session.flush()  # 產生 id
    return job


async def run_job_sync(
    *, job_id: int, session_factory: sessionmaker[Session]
) -> None:
    """執行 job。失敗會把狀態寫回 DB 但不 re-raise（背景任務不應中斷 app）。"""
    with session_factory() as session:
        job = session.get(Job, job_id)
        if job is None:
            logger.error("job %s not found", job_id)
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        session.commit()
        params = json.loads(job.params_json)
        job_type = JobType(job.job_type)

    try:
        summary = await _dispatch(job_type, params, session_factory)
        with session_factory() as session:
            job = session.get(Job, job_id)
            assert job is not None
            job.status = "completed"
            job.result_summary = summary
            job.finished_at = datetime.utcnow()
            session.commit()
    except Exception as exc:  # noqa: BLE001 — 背景任務需統一捕捉
        logger.exception("job %s failed", job_id)
        with session_factory() as session:
            job = session.get(Job, job_id)
            assert job is not None
            job.status = "failed"
            job.error_message = f"{type(exc).__name__}: {exc}"
            job.finished_at = datetime.utcnow()
            session.commit()


async def _dispatch(
    job_type: JobType,
    params: dict[str, Any],
    session_factory: sessionmaker[Session],
) -> str:
    if job_type is JobType.TWSE_PRICES:
        symbol = params["symbol"]
        year_month_str = params["year_month"]  # "YYYY-MM"
        year, month = year_month_str.split("-")
        from datetime import date

        rows = await fetch_daily_prices(
            symbol=symbol, year_month=date(int(year), int(month), 1)
        )
        with session_factory() as session:
            n = upsert_daily_prices(session, rows)
            session.commit()
        return f"upserted {n} price rows for {symbol} {year_month_str}"

    if job_type is JobType.MOPS_REVENUE:
        symbols = params.get("symbols")
        rows = await fetch_latest_monthly_revenues(symbols=symbols)
        with session_factory() as session:
            n = upsert_monthly_revenues(session, rows)
            session.commit()
        return f"upserted {n} revenue rows"

    raise ValueError(f"unknown job type: {job_type}")
```

- [ ] **Step 5: `jobs/__init__.py`**

```python
from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType

__all__ = ["JobType", "create_job", "run_job_sync"]
```

- [ ] **Step 6: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/jobs/ -v
```

預期：3 passed。

- [ ] **Step 7: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 8: 手動驗收指引**

> 請確認 `pytest tests/jobs` 3 passed。回覆「D1 OK」後 commit。

- [ ] **Step 9: Commit**

```bash
git add backend/src/alpha_lab/jobs/ backend/tests/jobs/
git commit -m "feat: add job service with sync runner"
```

---

## Task D2: Job API endpoints（POST /api/jobs/collect、GET /api/jobs/status/{id}）

**Files:**
- Create: `backend/src/alpha_lab/api/routes/jobs.py`
- Create: `backend/src/alpha_lab/schemas/job.py`
- Modify: `backend/src/alpha_lab/api/main.py`
- Create: `backend/tests/api/test_jobs.py`

- [ ] **Step 1: 先寫 failing test**

```python
"""Job API 整合測試。"""

import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import Base


def _override_engine(test_engine) -> None:
    """把 storage/engine 模組的全域改指向 in-memory engine，供 test 用。"""
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(bind=test_engine, future=True)


def test_post_collect_returns_job_id_and_status_pending() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    twse_payload = {
        "stat": "OK",
        "fields": ["日期","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"],
        "data": [["115/04/01", "1000", "0", "100", "110", "99", "105", "+5", "1"]],
    }

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=twse_payload)
        with TestClient(app) as client:
            resp = client.post(
                "/api/jobs/collect",
                json={
                    "type": "twse_prices",
                    "params": {"symbol": "2330", "year_month": "2026-04"},
                },
            )
            assert resp.status_code == 202
            body = resp.json()
            assert "id" in body
            assert body["status"] in ("pending", "running", "completed")

            status_resp = client.get(f"/api/jobs/status/{body['id']}")
            assert status_resp.status_code == 200
            status = status_resp.json()
            assert status["id"] == body["id"]
            assert status["status"] in ("pending", "running", "completed")


def test_get_status_404_for_missing_job() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with TestClient(app) as client:
        resp = client.get("/api/jobs/status/99999")
        assert resp.status_code == 404


def test_post_collect_rejects_unknown_type() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with TestClient(app) as client:
        resp = client.post(
            "/api/jobs/collect",
            json={"type": "unknown_type", "params": {}},
        )
        assert resp.status_code == 422
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/api/test_jobs.py -v
```

預期：endpoint 不存在，404。

- [ ] **Step 3: 建立 `schemas/job.py`**

```python
"""Job API Pydantic schemas。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from alpha_lab.jobs.types import JobType


class JobCreateRequest(BaseModel):
    type: JobType
    params: dict[str, Any] = {}


class JobResponse(BaseModel):
    id: int
    job_type: str
    status: str
    result_summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 實作 `api/routes/jobs.py`**

```python
"""Jobs API routes。

POST /api/jobs/collect → 建立 job，排程背景執行
GET  /api/jobs/status/{id} → 查詢 job 狀態
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.schemas.job import JobCreateRequest, JobResponse
from alpha_lab.storage.engine import get_session_factory, session_scope
from alpha_lab.storage.models import Job

router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs/collect",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_collect_job(
    payload: JobCreateRequest, background_tasks: BackgroundTasks
) -> JobResponse:
    with session_scope() as session:
        job = create_job(session, job_type=payload.type, params=payload.params)
        session.flush()
        response = JobResponse.model_validate(job)

    background_tasks.add_task(
        run_job_sync,
        job_id=response.id,
        session_factory=get_session_factory(),
    )
    return response


@router.get("/jobs/status/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int) -> JobResponse:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"job {job_id} not found")
        return JobResponse.model_validate(job)
```

- [ ] **Step 5: 修改 `api/main.py` 註冊 router**

在 `app.include_router(health.router, prefix="/api")` 下方加：

```python
from alpha_lab.api.routes import jobs  # 與 health 同層
app.include_router(jobs.router, prefix="/api")
```

- [ ] **Step 6: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/api/test_jobs.py -v
```

預期：3 passed。

- [ ] **Step 7: 跑完整 pytest 確認沒破壞既有**

```bash
cd backend
.venv/Scripts/python.exe -m pytest
```

預期：全部 passed（Phase 0 的 health + Phase 1 新增的全部）。

- [ ] **Step 8: `ruff check .` 與 `mypy src`**

預期：0 error。

- [ ] **Step 9: 手動驗收指引**

> 請啟動 uvicorn，用 curl 測：
> ```bash
> curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>   -H "Content-Type: application/json" \
>   -d '{"type":"mops_revenue","params":{"symbols":["2330"]}}'
> ```
> 應回傳 202 + job id，等幾秒後：
> ```bash
> curl http://127.0.0.1:8000/api/jobs/status/1
> ```
> 應回傳 status=completed。
>
> 回覆「D2 OK」後 commit。

- [ ] **Step 10: Commit**

```bash
git add backend/src/alpha_lab/api/ backend/src/alpha_lab/schemas/job.py backend/tests/api/test_jobs.py
git commit -m "feat: add jobs api endpoints"
```

---

## Task D3: 前端 API client（TypeScript types + 薄 wrapper）

**Files:**
- Create: `frontend/src/api/jobs.ts`
- Create: `frontend/src/api/types.ts`

- [ ] **Step 1: 建立 TS 型別**

```typescript
// frontend/src/api/types.ts
export type JobType = 'twse_prices' | 'mops_revenue';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface JobResponse {
  id: number;
  job_type: string;
  status: JobStatus;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface JobCreateRequest {
  type: JobType;
  params: Record<string, unknown>;
}
```

- [ ] **Step 2: 建立 API wrapper**

```typescript
// frontend/src/api/jobs.ts
import type { JobCreateRequest, JobResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';

export async function createCollectJob(req: JobCreateRequest): Promise<JobResponse> {
  const resp = await fetch(`${API_BASE}/api/jobs/collect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`createCollectJob failed: ${resp.status}`);
  }
  return resp.json();
}

export async function getJobStatus(id: number): Promise<JobResponse> {
  const resp = await fetch(`${API_BASE}/api/jobs/status/${id}`);
  if (!resp.ok) {
    throw new Error(`getJobStatus failed: ${resp.status}`);
  }
  return resp.json();
}
```

- [ ] **Step 3: `tsc --noEmit` 與 `pnpm lint`**

```bash
cd frontend
pnpm type-check
pnpm lint
```

預期：0 error。

- [ ] **Step 4: 手動驗收指引**

> 此 Task 只建 API client，未做 UI。請確認型別檢查通過。回覆「D3 OK」後 commit。
>
> 備註：UI 整合留到 Phase 2（個股頁會用到抓取觸發），Phase 1.5 可視需要加「資料管理」後台頁。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add frontend api client for jobs"
```

---

## Task E1: 知識庫 architecture 條目

**Files:**
- Create: `docs/knowledge/architecture/data-models.md`
- Create: `docs/knowledge/architecture/data-flow.md`

- [ ] **Step 1: 寫 `data-models.md`**

```markdown
---
domain: architecture
updated: 2026-04-15
related: [data-flow.md, ../collectors/twse.md, ../collectors/mops.md]
---

# 資料模型

## 目的

記錄 SQLAlchemy models 與 Pydantic schemas 的總覽，供 Claude 修改資料結構時參考。

## 現行實作（Phase 1）

### SQLAlchemy Models（`backend/src/alpha_lab/storage/models.py`）

| Table | 主鍵 | 來源 | Phase |
|-------|------|------|-------|
| `stocks` | symbol | 手動/collector 隱性建立 | 1 |
| `prices_daily` | (symbol, trade_date) | TWSE STOCK_DAY | 1 |
| `revenues_monthly` | (symbol, year, month) | MOPS t187ap05_L | 1 |
| `jobs` | id (autoincrement) | API 觸發 | 1 |

**Phase 1.5 規劃新增**：`financial_statements`、`institutional_trades`、`margin_trades`、`events`。

### Pydantic Schemas

| 檔案 | 用途 |
|------|------|
| `schemas/health.py` | `/api/health` 回傳 |
| `schemas/price.py` | `DailyPrice`（collector 輸出） |
| `schemas/revenue.py` | `MonthlyRevenue`（collector 輸出） |
| `schemas/job.py` | Job API request/response |

### 設計原則

- Collector 輸出 Pydantic 物件 → runner 負責 upsert 到 SQLAlchemy model
- Pydantic schemas 是「API / collector 邊界」的合約；SQLAlchemy models 是「持久層」的實體
- `Stock` 在 collector 隱性建立 placeholder（name=symbol）；正式公司資料同步在 Phase 1.5 或 2

## 關鍵檔案

- [backend/src/alpha_lab/storage/models.py](../../../backend/src/alpha_lab/storage/models.py)
- [backend/src/alpha_lab/storage/engine.py](../../../backend/src/alpha_lab/storage/engine.py)
- [backend/src/alpha_lab/schemas/](../../../backend/src/alpha_lab/schemas/)

## 修改時注意事項

- 新增 table：加到 `models.py`、用 `create_all` 自動建表；Phase 1.5 若要變更現有欄位，考慮引入 Alembic
- 新增欄位：若是 nullable 可直接加，`create_all` 對既存表是 no-op，需 drop DB 或手動 ALTER
- 主鍵選擇：時間序列（`prices_daily`、`revenues_monthly`）用 composite；事件/任務類（`jobs`）用 autoincrement
```

- [ ] **Step 2: 寫 `data-flow.md`**

```markdown
---
domain: architecture
updated: 2026-04-15
related: [data-models.md, ../collectors/twse.md, ../collectors/mops.md]
---

# 資料流

## 目的

描述「外部資料源 → collector → SQLite → API → UI」完整路徑。

## 現行實作（Phase 1）

### 端到端流程

```
使用者/排程
   │  POST /api/jobs/collect
   ▼
FastAPI route (api/routes/jobs.py)
   │  create_job (jobs 表 status=pending)
   │  background_tasks.add_task(run_job_sync)
   ▼
Job runner (jobs/service.py)
   │  status=running
   │  dispatch by JobType →
   ▼
Collector (collectors/twse.py or mops.py)
   │  httpx.AsyncClient → TWSE/MOPS API
   │  回傳 list[DailyPrice] or list[MonthlyRevenue]
   ▼
Upsert runner (collectors/runner.py)
   │  SQLAlchemy session → SQLite (data/alpha_lab.db)
   ▼
Job runner
   │  status=completed, result_summary 寫回 jobs 表
   ▼
使用者 GET /api/jobs/status/{id} 輪詢
```

### Session 管理原則

- 每個「邏輯工作單元」用一次 `session_scope()` context manager
- Job runner 把 read（取參數）、write（更新 status）、執行 collector 分成獨立 session，避免長交易
- Collector 本身不碰 DB，純函式 → 方便測試

### 錯誤處理

- Collector 拋例外 → `run_job_sync` 捕捉、寫 `job.error_message`、`status=failed`、**不** re-raise（背景任務不中斷 app）
- HTTP 錯誤 → `resp.raise_for_status()` 自然拋 `httpx.HTTPStatusError`
- 資料驗證錯誤 → Pydantic `ValidationError`，當成 collector 異常處理

## 關鍵檔案

- [backend/src/alpha_lab/jobs/service.py](../../../backend/src/alpha_lab/jobs/service.py)
- [backend/src/alpha_lab/collectors/runner.py](../../../backend/src/alpha_lab/collectors/runner.py)
- [backend/src/alpha_lab/api/routes/jobs.py](../../../backend/src/alpha_lab/api/routes/jobs.py)

## 修改時注意事項

- 新增 collector：
  1. 在 `collectors/` 新增模組
  2. 在 `jobs/types.py` 的 `JobType` 加一個值
  3. 在 `jobs/service.py::_dispatch` 加分支
  4. 在 `collectors/runner.py` 加對應 upsert
  5. 更新 `collectors/<source>.md` 知識庫
- 改 job 執行模型（例如要併發）：
  - 現在是 FastAPI BackgroundTasks（單程序），改 Celery/RQ 需同步改 `service.run_job_sync` 入口與 session factory 傳遞
- Phase 1.5 若要加排程：建議獨立 `backend/scripts/daily_collect.py`，由 OS cron 觸發，不走 API
```

- [ ] **Step 3: `grep "��"` 掃描亂碼**

```bash
cd /g/codingdata/alpha-lab
grep -r "��" docs/knowledge/architecture/ || echo "clean"
```

預期：`clean`。

- [ ] **Step 4: 手動驗收指引**

> 請閱讀 `data-models.md` 與 `data-flow.md`，確認內容符合實作。回覆「E1 OK」後 commit。

- [ ] **Step 5: Commit**

```bash
git add docs/knowledge/architecture/
git commit -m "docs: add architecture knowledge entries for phase 1"
```

---

## Task E2: 知識庫 collectors 條目

**Files:**
- Create: `docs/knowledge/collectors/twse.md`
- Create: `docs/knowledge/collectors/mops.md`

- [ ] **Step 1: 寫 `twse.md`**

```markdown
---
domain: collectors/twse
updated: 2026-04-15
related: [mops.md, ../architecture/data-flow.md, ../architecture/data-models.md]
---

# TWSE Collector

## 目的

抓取台灣證券交易所（TWSE）公開資料。

## 現行實作（Phase 1）

### 端點

| 用途 | URL | 備註 |
|------|-----|------|
| 個股日成交資訊 | `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=YYYYMMDD&stockNo=SYMBOL&response=json` | 以月為單位回傳該月所有交易日 |

### 已實作函式

- `fetch_daily_prices(symbol, year_month) -> list[DailyPrice]`
  - 回傳當月所有交易日的 OHLCV
  - 民國日期自動轉西元
  - `stat != "OK"` 會拋 `ValueError`

### 已知坑

- TWSE 對短時間多次請求會擋 IP；smoke 測試需手動節流
- 成交股數含逗號，需去逗號後 int
- 漲跌價差欄位有 `+`/`-` 符號，Phase 1 未解析（未入庫）
- ROC 年份轉換：`115 + 1911 = 2026`

### Phase 1.5 規劃新增

- 三大法人買賣超（T86 報表）
- 融資融券（MI_MARGN）
- 除權息（TWTB4U / dividend table）

## 關鍵檔案

- [backend/src/alpha_lab/collectors/twse.py](../../../backend/src/alpha_lab/collectors/twse.py)
- [backend/src/alpha_lab/schemas/price.py](../../../backend/src/alpha_lab/schemas/price.py)
- [backend/tests/collectors/test_twse.py](../../../backend/tests/collectors/test_twse.py)
- [backend/scripts/smoke_twse.py](../../../backend/scripts/smoke_twse.py)

## 修改時注意事項

- 改 URL 或參數：同步更新測試的 `respx.mock` 路徑
- 新增欄位：擴充 `DailyPrice` schema + `PriceDaily` model + `upsert_daily_prices`
- TWSE 若改回傳格式（欄位順序變動），`data` index 存取邏輯要改
```

- [ ] **Step 2: 寫 `mops.md`**

```markdown
---
domain: collectors/mops
updated: 2026-04-15
related: [twse.md, ../architecture/data-flow.md]
---

# MOPS Collector

## 目的

抓取公開資訊觀測站（MOPS）資料。

## 現行實作（Phase 1）

### 端點

| 用途 | URL | 備註 |
|------|-----|------|
| 最新月營收（全上市） | `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` | 只回傳「最新一期」；要抓歷史需走 HTML |

### 已實作函式

- `fetch_latest_monthly_revenues(symbols=None) -> list[MonthlyRevenue]`
  - `symbols=None` 代表回傳全上市；傳 list 則過濾
  - 資料年月（民國）自動轉西元

### 資料單位與欄位

- `revenue`：千元（MOPS 原始單位）
- `yoy_growth` / `mom_growth`：百分比（%），可能為 `null`（MOPS 欄位空字串）

### 已知坑

- `資料年月` 格式 `"11503"` = 民國 115 年 3 月
- 部分欄位可能為空字串或 `"-"`，以 `_parse_optional_float` 處理
- Open API 不含歷史月份；Phase 1.5 要補歷史月需改爬 HTML 或用 `t21sc03` 檔下載

### Phase 1.5 規劃新增

- 季報（合併損益 `t164sb03`、資產負債、現金流 `t164sb05`）
- 重大訊息（`t146sb05`）
- 月營收歷史月份

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops.py](../../../backend/src/alpha_lab/collectors/mops.py)
- [backend/src/alpha_lab/schemas/revenue.py](../../../backend/src/alpha_lab/schemas/revenue.py)
- [backend/tests/collectors/test_mops.py](../../../backend/tests/collectors/test_mops.py)
- [backend/scripts/smoke_mops.py](../../../backend/scripts/smoke_mops.py)

## 修改時注意事項

- MOPS 欄位名稱含中文且有特殊字元（如 `"營業收入-當月營收"`），要逐字匹配
- 新增欄位：擴充 `MonthlyRevenue` + `RevenueMonthly` + upsert
- Open API 有時會回傳空陣列（每月 10 日前新月份尚未公告），需 handle
```

- [ ] **Step 3: 掃描亂碼**

```bash
cd /g/codingdata/alpha-lab
grep -r "��" docs/knowledge/collectors/ || echo "clean"
```

預期：`clean`。

- [ ] **Step 4: 手動驗收指引**

> 請閱讀兩個 md，確認內容與實作一致。回覆「E2 OK」後 commit。

- [ ] **Step 5: Commit**

```bash
git add docs/knowledge/collectors/
git commit -m "docs: add twse and mops collector knowledge entries"
```

---

## Task F1: Phase 1 全面驗收（靜態檢查 + 測試 + 煙霧）

- [ ] **Step 1: Backend 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：兩者 0 error。

- [ ] **Step 2: Backend 全部單元 + 整合測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest -v
```

預期：全部 passed（大致：1 health + 4 models + 5 twse + 3 mops + 2 runner + 3 jobs + 3 jobs-api = ~21 tests）。

- [ ] **Step 3: Frontend 靜態檢查 + 測試**

```bash
cd frontend
pnpm type-check
pnpm lint
pnpm test
```

預期：全部 0 error / passed。

- [ ] **Step 4: E2E（沿用 Phase 0）**

```bash
cd frontend
pnpm e2e
```

預期：Phase 0 的 3 tests 仍 passed。

- [ ] **Step 5: 手動煙霧**

> 使用者手動執行：
> 1. 啟動 backend：`cd backend && .venv/Scripts/python.exe -m uvicorn alpha_lab.api.main:app --reload`
> 2. 執行：
>    ```bash
>    curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>      -H "Content-Type: application/json" \
>      -d '{"type":"mops_revenue","params":{"symbols":["2330","2317"]}}'
>    ```
> 3. 等 3 秒，查：`curl http://127.0.0.1:8000/api/jobs/status/1`
> 4. 確認 status=completed、result_summary 有 `upserted N revenue rows`
> 5. 用 SQLite CLI 確認 `revenues_monthly` 有 2 筆：
>    ```bash
>    .venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); print(c.execute('SELECT * FROM revenues_monthly').fetchall())"
>    ```
>
> 若 TWSE prices 也想驗：
>    ```bash
>    curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>      -H "Content-Type: application/json" \
>      -d '{"type":"twse_prices","params":{"symbol":"2330","year_month":"2026-04"}}'
>    ```

- [ ] **Step 6: 亂碼掃描**

```bash
cd /g/codingdata/alpha-lab
grep -r "��" backend/src backend/tests docs/knowledge || echo "clean"
```

預期：`clean`。

- [ ] **Step 7: 回報驗收結果給使用者**

> Phase 1 全部檢查項目：
> - [x] Backend ruff / mypy 0 error
> - [x] Backend pytest 全 green（~21 tests）
> - [x] Frontend tsc / lint / vitest / playwright 全 green
> - [x] 手動 curl 端到端煙霧成功
> - [x] 中文亂碼掃描 clean
>
> 請確認後回覆「Phase 1 驗證通過」，我會進行最終 commit（若有未 commit 的 WIP）並停在這裡等下一步指示。

---

## Task F2: Phase 1 最終 commit

- [ ] **Step 1: 確認 working tree 乾淨**

```bash
cd /g/codingdata/alpha-lab
rtk git status
```

預期：`nothing to commit, working tree clean`（前面 Task 都 commit 過）。

若還有未 commit 的漏網之魚，依 CLAUDE.md commit type 規範拆分提交。

- [ ] **Step 2: 更新 spec 標註 Phase 1 完成**

修改 `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` §15 表格：
- Phase 1 「狀態」欄改為 `✅ 完成（YYYY-MM-DD）`
- Phase 1.5 「狀態」欄改為 `進行中` 或保留 `未開始`（依使用者下一步決定）

```bash
git add docs/superpowers/specs/2026-04-14-alpha-lab-design.md
git commit -m "docs: mark phase 1 as complete"
```

- [ ] **Step 3: 最終回報**

> Phase 1（最小管線）完成。commit 數：預計 ~12-14 個（A1~E2 加 F2 最後補 spec）。
>
> 停在這裡等指示。下一步可能是：
> - **Phase 1.5 開始**：我會撰寫擴充 collectors 的計畫
> - **先跑真實資料**：用現有 API 抓一週資料當 smoke、回報問題
> - **其他調整**

---

## 回到全專案視角：後續 Phase 銜接

Phase 1 完成後可做的選擇：

1. **Phase 1.5（最自然的下一步）**：補齊季報、三大法人、重大訊息等 collector，schema 增表。完成後個股頁（Phase 2）可一次呈現完整資料。
2. **直接進 Phase 2 並接受資料缺口**：但會違反「選 A + 等 1.5 完成再做 Phase 2」的協議，不建議。
3. **先用一段時間累積真實資料**：每日手動跑 job，驗證管線穩定性、發現 TWSE/MOPS 邊界狀況。Phase 1.5 再進。

無論哪條路，Phase 轉換前等使用者明確指示，遵守 `.claude/CLAUDE.md` 的 JIT 原則。
