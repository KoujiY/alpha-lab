# Phase 1.5: 數據抓取擴充 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 沿用 Phase 1 的 collector → upsert → job dispatch pattern，補齊四類進階資料：三大法人買賣超、融資融券、重大訊息、季報三表（合併損益/資產負債/現金流）。同時加上 `scripts/daily_collect.py` 方便一次觸發日例行抓取。

**Architecture:**
- **Schema 擴充**：新增 4 個 SQLAlchemy models（`institutional_trades`、`margin_trades`、`events`、`financial_statements`）與對應 Pydantic schemas。採「寬表 + 原始 JSON」策略處理季報三表（共用 `financial_statements`，以 `statement_type` 區分）。
- **Collector 新增**：沿用 Phase 1 pattern — 純 async 函式輸出 Pydantic list，`httpx.AsyncClient` + `truststore` SSL、respx mock 單元測試。
- **Job dispatch 擴充**：`JobType` 新增 4 個 value，`jobs/service.py::_dispatch` 加對應分支。
- **排程腳本**：`scripts/daily_collect.py` 為 CLI，直接呼叫 job service 的 `create_job + run_job_sync`，不走 API。

**Tech Stack:** SQLAlchemy 2.x、httpx、truststore（解 Python 3.14 + OpenSSL 3 對 TWSE 憑證的問題）、pydantic v2、pytest + respx。

---

## Phase 1.5 工作總覽

| 群組 | 任務數 | 任務 |
|------|--------|------|
| A | 3 | Schema 擴充（4 新 models、schemas、rebuild DB） |
| B | 3 | 三大法人買賣超 collector（T86） |
| C | 3 | 融資融券 collector（MI_MARGN） |
| D | 3 | 重大訊息 collector（t146sb05） |
| E | 4 | 季報三表 collector（income / balance / cashflow） |
| F | 1 | `scripts/daily_collect.py` |
| G | 1 | 知識庫更新 |
| H | 1 | Phase 1.5 驗收 + 最終 commit |

**總計：19 tasks**

## 範圍與邊界

**本 Phase 包含**：
- 4 個新 SQLAlchemy models + Pydantic schemas
- 4 類 collector（三大法人、融資融券、重大訊息、季報三表）
- 對應 upsert runner 函式
- 4 個新 `JobType` value + dispatch 分支
- 單元測試（collectors with respx mock）
- 整合測試（fetch → upsert 端到端）
- `scripts/daily_collect.py` CLI
- 知識庫更新：`architecture/data-models.md`、`architecture/data-flow.md`、`collectors/twse.md`、`collectors/mops.md` + 新 `collectors/events.md`

**本 Phase 不包含**（留後續 Phase）：
- 排程自動化（cron、APScheduler、Windows Task Scheduler 設定）
- Alembic migration（schema 穩定後再引入；Phase 1.5 用 drop + create_all）
- 歷史回補（月營收歷史月份、季報歷史季度）— 目前只抓最新一期
- 個股頁 UI 整合（Phase 2）
- Stock 公司基本資料同步（industry、listed_date 正式來源 — 仍沿用 placeholder）

## Commit 規範（本專案 MANDATORY）

1. **靜態分析必做**：`ruff check .` 與 `mypy src` 必須 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit，給手動驗收指引，等使用者明確「OK」才 commit
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` / `chore` 不混在同一 commit
4. **禁止 scope 括號**：`type: description`，不可寫 `type(scope): description`
5. **同步檢查**：知識庫、spec、USER_GUIDE、E2E 是否需要連動更新
6. **中文亂碼掃描**：完成寫檔後 `grep -r "��"`

---

## Task A1: 新 Pydantic schemas（institutional / margin / event / financial_statement）

**Files:**
- Create: `backend/src/alpha_lab/schemas/institutional.py`
- Create: `backend/src/alpha_lab/schemas/margin.py`
- Create: `backend/src/alpha_lab/schemas/event.py`
- Create: `backend/src/alpha_lab/schemas/financial_statement.py`

- [ ] **Step 1: 建立 `schemas/institutional.py`**

```python
"""三大法人買賣超 Pydantic 模型。

來源：TWSE T86（每日三大法人買賣超日報）
單位：股數（未換算為張數）；net = buy - sell。
"""

from datetime import date

from pydantic import BaseModel, Field


class InstitutionalTrade(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    foreign_net: int = Field(..., description="外資買賣超（股）")
    trust_net: int = Field(..., description="投信買賣超（股）")
    dealer_net: int = Field(..., description="自營商買賣超（股，自行買賣+避險合計）")
    total_net: int = Field(..., description="三大法人合計買賣超（股）")
```

- [ ] **Step 2: 建立 `schemas/margin.py`**

```python
"""融資融券 Pydantic 模型。

來源：TWSE MI_MARGN（每日信用交易統計）
單位：張數；yoy/mom 無（盤中無此指標）。
"""

from datetime import date

from pydantic import BaseModel, Field


class MarginTrade(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    margin_balance: int = Field(..., ge=0, description="融資餘額（張）")
    margin_buy: int = Field(..., ge=0, description="融資買進（張）")
    margin_sell: int = Field(..., ge=0, description="融資賣出（張）")
    short_balance: int = Field(..., ge=0, description="融券餘額（張）")
    short_sell: int = Field(..., ge=0, description="融券賣出（張）")
    short_cover: int = Field(..., ge=0, description="融券買進回補（張）")
```

- [ ] **Step 3: 建立 `schemas/event.py`**

```python
"""重大訊息 Pydantic 模型。

來源：MOPS t146sb05（即時重大訊息）
event_type：MOPS 原始「主旨」或公司自填事件類型；content：訊息全文。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Event(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    event_datetime: datetime = Field(..., description="發言時間（含時分）")
    event_type: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1)
    content: str = Field(default="")
```

- [ ] **Step 4: 建立 `schemas/financial_statement.py`**

```python
"""季報三表 Pydantic 模型。

來源：MOPS t164sb03（合併綜合損益表）、t164sb04（合併資產負債表）、t164sb05（合併現金流量表）
period 格式：`"2026Q1"`；statement_type：income | balance | cashflow。

寬表策略：三表共用同一 schema，各表常用欄位獨立存放；raw_json 保留所有原始項目。
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StatementType(str, Enum):
    INCOME = "income"
    BALANCE = "balance"
    CASHFLOW = "cashflow"


class FinancialStatement(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    period: str = Field(..., pattern=r"^\d{4}Q[1-4]$")
    statement_type: StatementType

    # income
    revenue: int | None = Field(None, description="營業收入（千元）")
    gross_profit: int | None = Field(None, description="營業毛利（千元）")
    operating_income: int | None = Field(None, description="營業利益（千元）")
    net_income: int | None = Field(None, description="本期淨利（千元）")
    eps: float | None = Field(None, description="每股盈餘（元）")

    # balance
    total_assets: int | None = Field(None, description="資產總額（千元）")
    total_liabilities: int | None = Field(None, description="負債總額（千元）")
    total_equity: int | None = Field(None, description="權益總額（千元）")

    # cashflow
    operating_cf: int | None = Field(None, description="營業活動現金流量（千元）")
    investing_cf: int | None = Field(None, description="投資活動現金流量（千元）")
    financing_cf: int | None = Field(None, description="籌資活動現金流量（千元）")

    raw_json: dict[str, Any] = Field(default_factory=dict, description="原始欄位保留")
```

- [ ] **Step 5: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請確認四個 schema 檔案可匯入、靜態檢查 0 error：
> ```bash
> cd backend
> .venv/Scripts/python.exe -c "from alpha_lab.schemas.institutional import InstitutionalTrade; from alpha_lab.schemas.margin import MarginTrade; from alpha_lab.schemas.event import Event; from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType; print('OK')"
> ```
> 回覆「A1 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/schemas/
git commit -m "feat: add pydantic schemas for phase 1.5 data types"
```

---

## Task A2: 新 SQLAlchemy models + 測試

**Files:**
- Modify: `backend/src/alpha_lab/storage/models.py`
- Modify: `backend/src/alpha_lab/storage/__init__.py`
- Create: `backend/tests/storage/test_models_phase15.py`

- [ ] **Step 1: 先寫 failing test**

建立 `backend/tests/storage/test_models_phase15.py`：

```python
"""Phase 1.5 新 models 結構測試。"""

import json
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage.models import (
    Base,
    Event,
    FinancialStatement,
    InstitutionalTrade,
    MarginTrade,
    Stock,
)


def test_new_tables_registered() -> None:
    expected = {
        "institutional_trades",
        "margin_trades",
        "events",
        "financial_statements",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_insert_institutional_trade() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            InstitutionalTrade(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                foreign_net=1000000,
                trust_net=-500000,
                dealer_net=100000,
                total_net=600000,
            )
        )
        session.commit()
        assert session.query(InstitutionalTrade).count() == 1


def test_insert_margin_trade() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            MarginTrade(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                margin_balance=10000,
                margin_buy=500,
                margin_sell=400,
                short_balance=200,
                short_sell=50,
                short_cover=30,
            )
        )
        session.commit()
        assert session.query(MarginTrade).count() == 1


def test_insert_event_autoincrement_id() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        ev = Event(
            symbol="2330",
            event_datetime=datetime(2026, 4, 1, 14, 30, tzinfo=UTC),
            event_type="董事會決議",
            title="通過配息案",
            content="...",
        )
        session.add(ev)
        session.commit()
        assert ev.id is not None


def test_insert_financial_statement_with_raw_json() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            FinancialStatement(
                symbol="2330",
                period="2026Q1",
                statement_type="income",
                revenue=300000000,
                net_income=100000000,
                eps=10.5,
                raw_json_text=json.dumps({"custom_field": 1}),
            )
        )
        session.commit()
        assert session.query(FinancialStatement).count() == 1
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/storage/test_models_phase15.py -v
```

預期：`ImportError`（新 model 尚未定義）。

- [ ] **Step 3: 修改 `storage/models.py` 新增 4 個 model**

在檔案末尾追加（保留既有的 `Stock`、`PriceDaily`、`RevenueMonthly`、`Job`）：

```python
class InstitutionalTrade(Base):
    """三大法人買賣超（TWSE T86）。單位：股。"""

    __tablename__ = "institutional_trades"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    foreign_net: Mapped[int] = mapped_column(Integer, nullable=False)
    trust_net: Mapped[int] = mapped_column(Integer, nullable=False)
    dealer_net: Mapped[int] = mapped_column(Integer, nullable=False)
    total_net: Mapped[int] = mapped_column(Integer, nullable=False)


class MarginTrade(Base):
    """融資融券（TWSE MI_MARGN）。單位：張。"""

    __tablename__ = "margin_trades"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    margin_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_buy: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_sell: Mapped[int] = mapped_column(Integer, nullable=False)
    short_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    short_sell: Mapped[int] = mapped_column(Integer, nullable=False)
    short_cover: Mapped[int] = mapped_column(Integer, nullable=False)


class Event(Base):
    """重大訊息（MOPS t146sb05）。

    主鍵為 autoincrement id — 同公司同時刻可能多則訊息，且內容需保留全文。
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), nullable=False, index=True
    )
    event_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")


class FinancialStatement(Base):
    """季報三表（MOPS t164sb03 / t164sb04 / t164sb05）。

    寬表策略：統一 (symbol, period, statement_type) 主鍵；三類欄位集都 nullable。
    raw_json_text 保留原始項目（SQLite 用 Text 儲存 JSON 字串）。
    """

    __tablename__ = "financial_statements"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    period: Mapped[str] = mapped_column(String(8), primary_key=True)  # "2026Q1"
    statement_type: Mapped[str] = mapped_column(String(16), primary_key=True)

    # income
    revenue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gross_profit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operating_income: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_income: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)

    # balance
    total_assets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_liabilities: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_equity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # cashflow
    operating_cf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investing_cf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financing_cf: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_json_text: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
```

檔案頂部的 import 已有 `Date, DateTime, Float, ForeignKey, Integer, String, Text`，不需補。

- [ ] **Step 4: 更新 `storage/__init__.py` 匯出新 models**

```python
from alpha_lab.storage.engine import get_engine, get_session_factory, session_scope
from alpha_lab.storage.models import (
    Base,
    Event,
    FinancialStatement,
    InstitutionalTrade,
    Job,
    MarginTrade,
    PriceDaily,
    RevenueMonthly,
    Stock,
)

__all__ = [
    "Base",
    "Event",
    "FinancialStatement",
    "InstitutionalTrade",
    "Job",
    "MarginTrade",
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
.venv/Scripts/python.exe -m pytest tests/storage/ -v
```

預期：Phase 1 既有 4 passed + 新增 5 passed = 9 passed。

- [ ] **Step 6: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：0 error。

- [ ] **Step 7: 手動驗收指引**

> 請確認 `pytest tests/storage` 9 passed、靜態檢查 0 error。回覆「A2 OK」後 commit。

- [ ] **Step 8: Commit**

```bash
git add backend/src/alpha_lab/storage/ backend/tests/storage/test_models_phase15.py
git commit -m "feat: add sqlalchemy models for institutional margin events financials"
```

---

## Task A3: Rebuild DB + 確認 create_all 新增表

**Files:**
- Modify: `docs/USER_GUIDE.md`（新增 rebuild 指引）

**背景**：Phase 1.5 新增 4 個 table。`create_all` 對既有 DB 是 no-op（舊表不動），但對從未有這些表的既有 `data/alpha_lab.db` 是**新增**行為。因此 rebuild 不是必要，但若使用者 Phase 1 有實際抓資料累積，想清空重來時需要知道步驟。

- [ ] **Step 1: 更新 `docs/USER_GUIDE.md` 加 rebuild 章節**

在適當位置（例如「開發工具」或「故障排除」章節）加入：

```markdown
## Rebuild 本地資料庫

Phase 1.5 新增 4 個 table（`institutional_trades`、`margin_trades`、`events`、`financial_statements`）。
重啟 uvicorn 會自動 `create_all` 補上新表，舊表資料保留。

若要完全重建（例如測試乾淨起點）：

```bash
# 1. 停掉 uvicorn
# 2. 刪除 DB
rm data/alpha_lab.db

# 3. 重啟 uvicorn，startup 會自動重建全部 7 個 table
cd backend
.venv/Scripts/python.exe -m uvicorn alpha_lab.api.main:app --reload
```

確認 7 個 table 都在：

```bash
.venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); print(sorted([r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')]))"
```

預期輸出：`['events', 'financial_statements', 'institutional_trades', 'jobs', 'margin_trades', 'prices_daily', 'revenues_monthly', 'stocks']`
```

- [ ] **Step 2: 實際跑一次 rebuild 流程驗證**

```bash
cd /g/codingdata/alpha-lab
rm -f data/alpha_lab.db

cd backend
.venv/Scripts/python.exe -c "from alpha_lab.storage.init_db import init_database; init_database(); print('db created')"

.venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); print(sorted([r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')]))"
```

預期：印出 8 個 table（含 `sqlite_sequence` 不在列，實際 7 個業務 table + 可能的 sqlite_sequence）。

- [ ] **Step 3: 亂碼掃描**

```bash
cd /g/codingdata/alpha-lab
grep -r "��" docs/USER_GUIDE.md || echo "clean"
```

預期：`clean`。

- [ ] **Step 4: 手動驗收指引**

> 請閱讀 USER_GUIDE.md 新章節，確認 rebuild 步驟可跑、7 table 都建立。回覆「A3 OK」後 commit。

- [ ] **Step 5: Commit**

```bash
git add docs/USER_GUIDE.md
git commit -m "docs: add db rebuild guide for phase 1.5 schema expansion"
```

---

## Task B1: 三大法人買賣超 collector（fetch）

**Files:**
- Create: `backend/src/alpha_lab/collectors/twse_institutional.py`
- Create: `backend/tests/collectors/test_twse_institutional.py`

**API 參考**：TWSE 三大法人買賣超日報
`https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json`

回傳結構（擷取）：

```json
{
  "stat": "OK",
  "date": "20260401",
  "fields": [
    "證券代號", "證券名稱",
    "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)", "外陸資買賣超股數(不含外資自營商)",
    "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
    "投信買進股數", "投信賣出股數", "投信買賣超股數",
    "自營商買賣超股數",
    "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)", "自營商買賣超股數(自行買賣)",
    "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
    "三大法人買賣超股數"
  ],
  "data": [
    ["2330", "台積電", "1,234,567", "...", "500,000", ..., "600,000"]
  ]
}
```

**欄位對應策略**：
- `foreign_net` = 外陸資買賣超（欄位 index 4）+ 外資自營商買賣超（index 7）
- `trust_net` = 投信買賣超（index 10）
- `dealer_net` = 自營商買賣超合計（index 11）
- `total_net` = 三大法人買賣超（最後欄位）

因欄位順序可能隨 TWSE 版本變動，實作改以「fields 名稱比對」找 index，不硬編碼位置。

- [ ] **Step 1: 先寫 failing test**

```python
"""TWSE 三大法人 collector 單元測試。"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
from alpha_lab.schemas.institutional import InstitutionalTrade

SAMPLE_FIELDS = [
    "證券代號", "證券名稱",
    "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
    "外陸資買賣超股數(不含外資自營商)",
    "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
    "投信買進股數", "投信賣出股數", "投信買賣超股數",
    "自營商買賣超股數",
    "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)", "自營商買賣超股數(自行買賣)",
    "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
    "三大法人買賣超股數",
]

SAMPLE_RESPONSE = {
    "stat": "OK",
    "date": "20260401",
    "fields": SAMPLE_FIELDS,
    "data": [
        [
            "2330", "台積電",
            "1,000,000", "0", "1,000,000",
            "0", "0", "0",
            "0", "500,000", "-500,000",
            "100,000",
            "0", "0", "0",
            "0", "0", "0",
            "600,000",
        ],
    ],
}


@pytest.mark.asyncio
async def test_fetch_institutional_trades_parses_sample() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json=SAMPLE_RESPONSE)

        rows = await fetch_institutional_trades(trade_date=date(2026, 4, 1))

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, InstitutionalTrade)
    assert r.symbol == "2330"
    assert r.trade_date == date(2026, 4, 1)
    assert r.foreign_net == 1_000_000  # 外陸資 + 外資自營商
    assert r.trust_net == -500_000
    assert r.dealer_net == 100_000
    assert r.total_net == 600_000


@pytest.mark.asyncio
async def test_fetch_institutional_trades_filters_symbols() -> None:
    payload = {
        "stat": "OK",
        "fields": SAMPLE_FIELDS,
        "data": [
            ["2330", "台積電"] + ["0"] * 16 + ["100"],
            ["2317", "鴻海"] + ["0"] * 16 + ["200"],
        ],
    }
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json=payload)
        rows = await fetch_institutional_trades(
            trade_date=date(2026, 4, 1), symbols=["2330"]
        )
    assert [r.symbol for r in rows] == ["2330"]


@pytest.mark.asyncio
async def test_fetch_institutional_trades_non_ok_stat_raises() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json={"stat": "查詢無資料", "data": []})
        with pytest.raises(ValueError, match="查詢無資料"):
            await fetch_institutional_trades(trade_date=date(2026, 4, 1))


@pytest.mark.asyncio
async def test_fetch_institutional_trades_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_institutional_trades(trade_date=date(2026, 4, 1))
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse_institutional.py -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 實作 `collectors/twse_institutional.py`**

```python
"""TWSE 三大法人買賣超（T86）collector。

API：https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json
"""

import ssl
from datetime import date

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.institutional import InstitutionalTrade

TWSE_BASE_URL = "https://www.twse.com.tw"
T86_PATH = "/rwd/zh/fund/T86"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_int(s: str) -> int:
    """去千分位後轉 int；空字串或 '-' 視為 0。"""
    if s in ("", "-", "N/A"):
        return 0
    return int(s.replace(",", "").replace("+", ""))


def _find_field_index(fields: list[str], *candidates: str) -> int:
    """回傳第一個完全相符的欄位 index；找不到則拋例外。"""
    for c in candidates:
        if c in fields:
            return fields.index(c)
    raise ValueError(f"required field not found in {fields}: tried {candidates}")


async def fetch_institutional_trades(
    trade_date: date, symbols: list[str] | None = None
) -> list[InstitutionalTrade]:
    """抓取某交易日所有標的的三大法人買賣超。

    Args:
        trade_date: 交易日
        symbols: 若提供，僅回傳清單內代號；None 代表全部。
    """
    settings = get_settings()
    params = {
        "date": trade_date.strftime("%Y%m%d"),
        "selectType": "ALL",
        "response": "json",
    }
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=TWSE_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(T86_PATH, params=params)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("stat") != "OK":
        raise ValueError(f"TWSE T86 returned non-OK stat: {payload.get('stat')}")

    fields: list[str] = payload["fields"]
    idx_symbol = _find_field_index(fields, "證券代號")
    idx_foreign_main = _find_field_index(
        fields, "外陸資買賣超股數(不含外資自營商)", "外資買賣超股數"
    )
    # 「外資自營商買賣超股數」於 2018 年後獨立欄位；舊報表可能無
    try:
        idx_foreign_dealer = _find_field_index(fields, "外資自營商買賣超股數")
    except ValueError:
        idx_foreign_dealer = None
    idx_trust = _find_field_index(fields, "投信買賣超股數")
    idx_dealer_total = _find_field_index(fields, "自營商買賣超股數")
    idx_total = _find_field_index(fields, "三大法人買賣超股數")

    symbol_filter = set(symbols) if symbols else None
    results: list[InstitutionalTrade] = []
    for row in payload.get("data", []):
        symbol = row[idx_symbol].strip()
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        foreign_main = _parse_int(row[idx_foreign_main])
        foreign_dealer = (
            _parse_int(row[idx_foreign_dealer]) if idx_foreign_dealer is not None else 0
        )
        results.append(
            InstitutionalTrade(
                symbol=symbol,
                trade_date=trade_date,
                foreign_net=foreign_main + foreign_dealer,
                trust_net=_parse_int(row[idx_trust]),
                dealer_net=_parse_int(row[idx_dealer_total]),
                total_net=_parse_int(row[idx_total]),
            )
        )
    return results
```

- [ ] **Step 4: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse_institutional.py -v
```

預期：4 passed。

- [ ] **Step 5: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請確認 `pytest tests/collectors/test_twse_institutional.py` 4 passed、靜態檢查 0 error。回覆「B1 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/collectors/twse_institutional.py backend/tests/collectors/test_twse_institutional.py
git commit -m "feat: add twse institutional trades collector"
```

---

## Task B2: 三大法人 upsert + 三大法人 job type 與 dispatch

**Files:**
- Modify: `backend/src/alpha_lab/collectors/runner.py`
- Modify: `backend/src/alpha_lab/jobs/types.py`
- Modify: `backend/src/alpha_lab/jobs/service.py`
- Modify: `backend/src/alpha_lab/collectors/__init__.py`
- Create: `backend/tests/collectors/test_runner_institutional.py`
- Modify: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: 寫 upsert failing test**

建立 `backend/tests/collectors/test_runner_institutional.py`：

```python
"""三大法人 upsert 測試。"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_institutional_trades
from alpha_lab.schemas.institutional import InstitutionalTrade
from alpha_lab.storage.models import Base, InstitutionalTrade as ITRow, Stock


def test_upsert_institutional_trades_inserts_and_updates() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            InstitutionalTrade(
                symbol="2330", trade_date=date(2026, 4, 1),
                foreign_net=1000, trust_net=-500, dealer_net=100, total_net=600,
            ),
        ]
        n = upsert_institutional_trades(session, rows)
        session.commit()
        assert n == 1
        assert session.query(ITRow).count() == 1

        # 同 symbol + date → update
        rows2 = [
            InstitutionalTrade(
                symbol="2330", trade_date=date(2026, 4, 1),
                foreign_net=2000, trust_net=-1000, dealer_net=200, total_net=1200,
            ),
        ]
        n2 = upsert_institutional_trades(session, rows2)
        session.commit()
        assert n2 == 1
        assert session.query(ITRow).count() == 1
        row = session.get(ITRow, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
        assert row is not None
        assert row.foreign_net == 2000
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_institutional.py -v
```

預期：`ImportError: cannot import name 'upsert_institutional_trades'`。

- [ ] **Step 3: 修改 `collectors/runner.py` 加 upsert 函式**

在 `upsert_monthly_revenues` 下方追加：

```python
from alpha_lab.schemas.institutional import InstitutionalTrade as InstitutionalTradeSchema
from alpha_lab.storage.models import InstitutionalTrade as InstitutionalTradeRow


def upsert_institutional_trades(
    session: Session, rows: list[InstitutionalTradeSchema]
) -> int:
    """upsert 三大法人買賣超。回傳寫入筆數。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        existing = session.get(
            InstitutionalTradeRow,
            {"symbol": row.symbol, "trade_date": row.trade_date},
        )
        if existing is None:
            session.add(
                InstitutionalTradeRow(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    foreign_net=row.foreign_net,
                    trust_net=row.trust_net,
                    dealer_net=row.dealer_net,
                    total_net=row.total_net,
                )
            )
        else:
            existing.foreign_net = row.foreign_net
            existing.trust_net = row.trust_net
            existing.dealer_net = row.dealer_net
            existing.total_net = row.total_net
        count += 1
    return count
```

注意：因 `storage.models` 與 `schemas.institutional` 都有 `InstitutionalTrade` 類名，在 runner 中以 `as` 改名避免衝突。

- [ ] **Step 4: 執行 upsert 測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_institutional.py -v
```

預期：1 passed。

- [ ] **Step 5: 擴充 `jobs/types.py` 加 value**

```python
"""Job 類型列舉。新增 collector 時在此加一個 value 並在 service.run_job_sync 分派。"""

from enum import Enum


class JobType(str, Enum):
    TWSE_PRICES = "twse_prices"
    MOPS_REVENUE = "mops_revenue"
    TWSE_INSTITUTIONAL = "twse_institutional"
    TWSE_MARGIN = "twse_margin"
    MOPS_EVENTS = "mops_events"
    MOPS_FINANCIALS = "mops_financials"
```

（後續 Task C/D/E 會用到 margin/events/financials，此步一次把 enum 寫全。）

- [ ] **Step 6: 擴充 `jobs/service.py::_dispatch` 加三大法人分支**

在 `_dispatch` 函式中，`MOPS_REVENUE` 分支下方加：

```python
    if job_type is JobType.TWSE_INSTITUTIONAL:
        from alpha_lab.collectors.twse_institutional import fetch_institutional_trades

        trade_date_str = params["trade_date"]  # "YYYY-MM-DD"
        year, month, day = trade_date_str.split("-")
        symbols = params.get("symbols")
        inst_rows = await fetch_institutional_trades(
            trade_date=date(int(year), int(month), int(day)),
            symbols=symbols,
        )
        with session_factory() as session:
            from alpha_lab.collectors.runner import upsert_institutional_trades
            n = upsert_institutional_trades(session, inst_rows)
            session.commit()
        return f"upserted {n} institutional rows for {trade_date_str}"
```

import 放頂部比較乾淨；為減少循環 import 風險，保留延遲 import 也可。為統一，將 `fetch_institutional_trades`、`upsert_institutional_trades` 搬到頂部 import：

```python
# 檔案頂部原有 imports 下方追加
from alpha_lab.collectors.runner import (
    upsert_daily_prices,
    upsert_institutional_trades,
    upsert_monthly_revenues,
)
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
```

然後 `_dispatch` 函式內直接用。

- [ ] **Step 7: 擴充 `collectors/__init__.py` 匯出**

```python
from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.collectors.twse_institutional import fetch_institutional_trades

__all__ = [
    "fetch_daily_prices",
    "fetch_institutional_trades",
    "fetch_latest_monthly_revenues",
]
```

- [ ] **Step 8: 在 `tests/jobs/test_service.py` 追加 dispatch 測試**

在檔案末尾追加：

```python
@pytest.mark.asyncio
async def test_run_job_sync_twse_institutional_happy_path(session_factory) -> None:
    payload = {
        "stat": "OK",
        "fields": [
            "證券代號", "證券名稱",
            "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
            "外陸資買賣超股數(不含外資自營商)",
            "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
            "投信買進股數", "投信賣出股數", "投信買賣超股數",
            "自營商買賣超股數",
            "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)",
            "自營商買賣超股數(自行買賣)",
            "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
            "三大法人買賣超股數",
        ],
        "data": [
            ["2330", "台積電"] + ["0"] * 16 + ["1000"],
        ],
    }

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_INSTITUTIONAL,
            params={"trade_date": "2026-04-01"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json=payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import InstitutionalTrade as ITRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(ITRow).count() == 1
```

- [ ] **Step 9: 執行全部 jobs + collectors 測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/jobs/ tests/collectors/ -v
```

預期：Phase 1 原有 + 新增全部 passed。

- [ ] **Step 10: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：0 error。

- [ ] **Step 11: 手動驗收指引**

> 請確認測試全 passed、靜態檢查 0 error。回覆「B2 OK」後 commit。

- [ ] **Step 12: Commit**

```bash
git add backend/src/alpha_lab/collectors/ backend/src/alpha_lab/jobs/ backend/tests/
git commit -m "feat: wire twse institutional collector into job dispatch"
```

---

## Task B3: 三大法人 smoke script

**Files:**
- Create: `backend/scripts/smoke_twse_institutional.py`

- [ ] **Step 1: 建立煙霧測試腳本**

```python
"""TWSE 三大法人 collector 真實網路煙霧測試。

用法：python scripts/smoke_twse_institutional.py [YYYY-MM-DD]
若省略日期則用今天（可能尚未收盤，會無資料）。
"""

import asyncio
import sys
from datetime import date

from alpha_lab.collectors.twse_institutional import fetch_institutional_trades


async def main() -> None:
    if len(sys.argv) >= 2:
        y, m, d = sys.argv[1].split("-")
        trade_date = date(int(y), int(m), int(d))
    else:
        trade_date = date.today()

    rows = await fetch_institutional_trades(
        trade_date=trade_date, symbols=["2330", "2317", "0050"]
    )
    print(f"Fetched {len(rows)} rows for {trade_date}")
    for r in rows:
        print(
            f"  {r.symbol} foreign={r.foreign_net:>12,} "
            f"trust={r.trust_net:>10,} dealer={r.dealer_net:>10,} "
            f"total={r.total_net:>12,}"
        )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 手動驗收指引**

> 請手動執行：
> ```bash
> cd backend
> .venv/Scripts/python.exe scripts/smoke_twse_institutional.py 2026-04-11
> ```
> （使用上一個交易日期；若當日無資料會看到 `ValueError: 查詢無資料`，正常。）
>
> 成功應印出 2330/2317/0050 三檔的買賣超數字。回覆「B3 OK」後 commit。

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_twse_institutional.py
git commit -m "chore: add twse institutional smoke script"
```

---

## Task C1: 融資融券 collector（fetch）

**Files:**
- Create: `backend/src/alpha_lab/collectors/twse_margin.py`
- Create: `backend/tests/collectors/test_twse_margin.py`

**API 參考**：TWSE 融資融券餘額
`https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=YYYYMMDD&selectType=ALL&response=json`

回傳結構（擷取）：

```json
{
  "stat": "OK",
  "creditList": {
    "fields": [
      "股票代號", "股票名稱",
      "融資買進", "融資賣出", "現金償還", "前日餘額", "今日餘額", "限額", "融資使用率(%)",
      "融券買進", "融券賣出", "現券償還", "前日餘額", "今日餘額", "限額", "融券使用率(%)",
      "資券互抵", "註記"
    ],
    "data": [
      ["2330", "台積電", "500", "400", "0", "10100", "10200", ..., "50", "30", "0", "220", "200", ...]
    ]
  }
}
```

**注意**：回傳結構可能用 `creditList` 或 `tables[0]` 包裹；實作以「從 fields 找名稱」而非硬編 index。

- [ ] **Step 1: 先寫 failing test**

```python
"""TWSE 融資融券 collector 單元測試。"""

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.twse_margin import fetch_margin_trades
from alpha_lab.schemas.margin import MarginTrade

SAMPLE_FIELDS = [
    "股票代號", "股票名稱",
    "融資買進", "融資賣出", "現金償還", "融資前日餘額", "融資今日餘額", "融資限額", "融資使用率(%)",
    "融券買進", "融券賣出", "現券償還", "融券前日餘額", "融券今日餘額", "融券限額", "融券使用率(%)",
    "資券互抵", "註記",
]

SAMPLE_RESPONSE = {
    "stat": "OK",
    "tables": [
        {
            "fields": SAMPLE_FIELDS,
            "data": [
                [
                    "2330", "台積電",
                    "500", "400", "0", "10100", "10200", "999999", "0.5",
                    "30", "50", "0", "220", "200", "99999", "0.1",
                    "0", "",
                ],
            ],
        }
    ],
}


@pytest.mark.asyncio
async def test_fetch_margin_trades_parses_sample() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=SAMPLE_RESPONSE)

        rows = await fetch_margin_trades(trade_date=date(2026, 4, 1))

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, MarginTrade)
    assert r.symbol == "2330"
    assert r.trade_date == date(2026, 4, 1)
    assert r.margin_buy == 500
    assert r.margin_sell == 400
    assert r.margin_balance == 10200
    assert r.short_sell == 50
    assert r.short_cover == 30
    assert r.short_balance == 200


@pytest.mark.asyncio
async def test_fetch_margin_trades_filters_symbols() -> None:
    payload = {
        "stat": "OK",
        "tables": [
            {
                "fields": SAMPLE_FIELDS,
                "data": [
                    ["2330", "台積電"] + ["0"] * 16,
                    ["2317", "鴻海"] + ["0"] * 16,
                ],
            }
        ],
    }
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=payload)
        rows = await fetch_margin_trades(
            trade_date=date(2026, 4, 1), symbols=["2317"]
        )
    assert [r.symbol for r in rows] == ["2317"]


@pytest.mark.asyncio
async def test_fetch_margin_trades_non_ok_raises() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(
            json={"stat": "查詢無資料"}
        )
        with pytest.raises(ValueError, match="查詢無資料"):
            await fetch_margin_trades(trade_date=date(2026, 4, 1))


@pytest.mark.asyncio
async def test_fetch_margin_trades_http_error() -> None:
    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_margin_trades(trade_date=date(2026, 4, 1))
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse_margin.py -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 實作 `collectors/twse_margin.py`**

```python
"""TWSE 融資融券（MI_MARGN）collector。

API：https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=YYYYMMDD&selectType=ALL&response=json
"""

import ssl
from datetime import date
from typing import Any

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.margin import MarginTrade

TWSE_BASE_URL = "https://www.twse.com.tw"
MI_MARGN_PATH = "/rwd/zh/marginTrading/MI_MARGN"


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _parse_int(s: str) -> int:
    if s in ("", "-", "N/A"):
        return 0
    return int(s.replace(",", "").replace("+", ""))


def _find_credit_table(payload: dict[str, Any]) -> dict[str, Any]:
    """從不同 TWSE 版本的 payload 中抽出個股融資融券表。"""
    if "tables" in payload and isinstance(payload["tables"], list):
        for t in payload["tables"]:
            fields = t.get("fields") or []
            if any("融資" in f for f in fields) and any("融券" in f for f in fields):
                return t
    if "creditList" in payload:
        return payload["creditList"]
    raise ValueError("credit table not found in TWSE MI_MARGN payload")


def _find_idx(fields: list[str], *candidates: str) -> int:
    for c in candidates:
        if c in fields:
            return fields.index(c)
    raise ValueError(f"field not found: tried {candidates}")


async def fetch_margin_trades(
    trade_date: date, symbols: list[str] | None = None
) -> list[MarginTrade]:
    """抓取某交易日所有標的的融資融券餘額。"""
    settings = get_settings()
    params = {
        "date": trade_date.strftime("%Y%m%d"),
        "selectType": "ALL",
        "response": "json",
    }
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=TWSE_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(MI_MARGN_PATH, params=params)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("stat") != "OK":
        raise ValueError(f"TWSE MI_MARGN returned non-OK stat: {payload.get('stat')}")

    table = _find_credit_table(payload)
    fields: list[str] = table["fields"]

    idx_symbol = _find_idx(fields, "股票代號", "證券代號")
    idx_margin_buy = _find_idx(fields, "融資買進")
    idx_margin_sell = _find_idx(fields, "融資賣出")
    idx_margin_balance = _find_idx(fields, "融資今日餘額", "今日餘額")
    idx_short_buy = _find_idx(fields, "融券買進")
    idx_short_sell = _find_idx(fields, "融券賣出")
    idx_short_balance = _find_idx(fields, "融券今日餘額")

    # 融券買進 = 現券回補 / 融券買回 — 本專案視為 cover
    symbol_filter = set(symbols) if symbols else None
    results: list[MarginTrade] = []
    for row in table.get("data", []):
        symbol = row[idx_symbol].strip()
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        results.append(
            MarginTrade(
                symbol=symbol,
                trade_date=trade_date,
                margin_buy=_parse_int(row[idx_margin_buy]),
                margin_sell=_parse_int(row[idx_margin_sell]),
                margin_balance=_parse_int(row[idx_margin_balance]),
                short_sell=_parse_int(row[idx_short_sell]),
                short_cover=_parse_int(row[idx_short_buy]),
                short_balance=_parse_int(row[idx_short_balance]),
            )
        )
    return results
```

- [ ] **Step 4: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_twse_margin.py -v
```

預期：4 passed。

- [ ] **Step 5: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請確認 `pytest tests/collectors/test_twse_margin.py` 4 passed。回覆「C1 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/collectors/twse_margin.py backend/tests/collectors/test_twse_margin.py
git commit -m "feat: add twse margin trading collector"
```

---

## Task C2: 融資融券 upsert + dispatch

**Files:**
- Modify: `backend/src/alpha_lab/collectors/runner.py`
- Modify: `backend/src/alpha_lab/jobs/service.py`
- Modify: `backend/src/alpha_lab/collectors/__init__.py`
- Create: `backend/tests/collectors/test_runner_margin.py`
- Modify: `backend/tests/jobs/test_service.py`

- [ ] **Step 1: 寫 upsert failing test**

`backend/tests/collectors/test_runner_margin.py`：

```python
"""融資融券 upsert 測試。"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_margin_trades
from alpha_lab.schemas.margin import MarginTrade
from alpha_lab.storage.models import Base, MarginTrade as MTRow, Stock


def test_upsert_margin_trades_inserts_and_updates() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            MarginTrade(
                symbol="2330", trade_date=date(2026, 4, 1),
                margin_buy=500, margin_sell=400, margin_balance=10200,
                short_sell=50, short_cover=30, short_balance=200,
            ),
        ]
        assert upsert_margin_trades(session, rows) == 1
        session.commit()
        assert session.query(MTRow).count() == 1

        rows2 = [
            MarginTrade(
                symbol="2330", trade_date=date(2026, 4, 1),
                margin_buy=600, margin_sell=450, margin_balance=10350,
                short_sell=60, short_cover=40, short_balance=220,
            ),
        ]
        assert upsert_margin_trades(session, rows2) == 1
        session.commit()
        r = session.get(MTRow, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
        assert r is not None
        assert r.margin_balance == 10350
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_margin.py -v
```

預期：ImportError。

- [ ] **Step 3: 在 `collectors/runner.py` 加 `upsert_margin_trades`**

在既有函式下方追加：

```python
from alpha_lab.schemas.margin import MarginTrade as MarginTradeSchema
from alpha_lab.storage.models import MarginTrade as MarginTradeRow


def upsert_margin_trades(
    session: Session, rows: list[MarginTradeSchema]
) -> int:
    """upsert 融資融券餘額。回傳寫入筆數。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        existing = session.get(
            MarginTradeRow,
            {"symbol": row.symbol, "trade_date": row.trade_date},
        )
        if existing is None:
            session.add(
                MarginTradeRow(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    margin_buy=row.margin_buy,
                    margin_sell=row.margin_sell,
                    margin_balance=row.margin_balance,
                    short_sell=row.short_sell,
                    short_cover=row.short_cover,
                    short_balance=row.short_balance,
                )
            )
        else:
            existing.margin_buy = row.margin_buy
            existing.margin_sell = row.margin_sell
            existing.margin_balance = row.margin_balance
            existing.short_sell = row.short_sell
            existing.short_cover = row.short_cover
            existing.short_balance = row.short_balance
        count += 1
    return count
```

- [ ] **Step 4: 在 `jobs/service.py::_dispatch` 加 `TWSE_MARGIN` 分支**

在 `TWSE_INSTITUTIONAL` 分支下方追加：

```python
    if job_type is JobType.TWSE_MARGIN:
        from alpha_lab.collectors.twse_margin import fetch_margin_trades
        from alpha_lab.collectors.runner import upsert_margin_trades

        trade_date_str = params["trade_date"]
        year, month, day = trade_date_str.split("-")
        symbols = params.get("symbols")
        margin_rows = await fetch_margin_trades(
            trade_date=date(int(year), int(month), int(day)),
            symbols=symbols,
        )
        with session_factory() as session:
            n = upsert_margin_trades(session, margin_rows)
            session.commit()
        return f"upserted {n} margin rows for {trade_date_str}"
```

（也可把 imports 統一搬到頂部；保持局部 import 也 OK。以和 B2 同樣風格為準。）

- [ ] **Step 5: 更新 `collectors/__init__.py` 匯出 `fetch_margin_trades`**

```python
from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
from alpha_lab.collectors.twse_margin import fetch_margin_trades

__all__ = [
    "fetch_daily_prices",
    "fetch_institutional_trades",
    "fetch_latest_monthly_revenues",
    "fetch_margin_trades",
]
```

- [ ] **Step 6: 在 `tests/jobs/test_service.py` 追加 margin dispatch 測試**

```python
@pytest.mark.asyncio
async def test_run_job_sync_twse_margin_happy_path(session_factory) -> None:
    fields = [
        "股票代號", "股票名稱",
        "融資買進", "融資賣出", "現金償還", "融資前日餘額", "融資今日餘額",
        "融資限額", "融資使用率(%)",
        "融券買進", "融券賣出", "現券償還", "融券前日餘額", "融券今日餘額",
        "融券限額", "融券使用率(%)",
        "資券互抵", "註記",
    ]
    payload = {
        "stat": "OK",
        "tables": [
            {
                "fields": fields,
                "data": [
                    [
                        "2330", "台積電",
                        "500", "400", "0", "10100", "10200", "999999", "0.5",
                        "30", "50", "0", "220", "200", "99999", "0.1",
                        "0", "",
                    ],
                ],
            }
        ],
    }

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_MARGIN,
            params={"trade_date": "2026-04-01"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import MarginTrade as MTRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(MTRow).count() == 1
```

- [ ] **Step 7: 執行全部測試 + 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m pytest -v
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：全 passed、0 error。

- [ ] **Step 8: 手動驗收指引**

> 請確認全測試 passed、靜態檢查 0 error。回覆「C2 OK」後 commit。

- [ ] **Step 9: Commit**

```bash
git add backend/src/alpha_lab/ backend/tests/
git commit -m "feat: wire twse margin collector into job dispatch"
```

---

## Task C3: 融資融券 smoke script

**Files:**
- Create: `backend/scripts/smoke_twse_margin.py`

- [ ] **Step 1: 建立腳本**

```python
"""TWSE 融資融券 collector 煙霧測試。

用法：python scripts/smoke_twse_margin.py [YYYY-MM-DD]
"""

import asyncio
import sys
from datetime import date

from alpha_lab.collectors.twse_margin import fetch_margin_trades


async def main() -> None:
    if len(sys.argv) >= 2:
        y, m, d = sys.argv[1].split("-")
        trade_date = date(int(y), int(m), int(d))
    else:
        trade_date = date.today()

    rows = await fetch_margin_trades(
        trade_date=trade_date, symbols=["2330", "2317", "2454"]
    )
    print(f"Fetched {len(rows)} rows for {trade_date}")
    for r in rows:
        print(
            f"  {r.symbol} 融資餘={r.margin_balance:>8,} "
            f"(買{r.margin_buy:>6,}/賣{r.margin_sell:>6,}) "
            f"融券餘={r.short_balance:>6,} "
            f"(賣{r.short_sell:>5,}/回{r.short_cover:>5,})"
        )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 手動驗收指引**

> 請手動執行 `cd backend && .venv/Scripts/python.exe scripts/smoke_twse_margin.py 2026-04-11`，確認能印出真實餘額數字。回覆「C3 OK」後 commit。

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_twse_margin.py
git commit -m "chore: add twse margin smoke script"
```

---

## Task D1: 重大訊息 collector（fetch）

**Files:**
- Create: `backend/src/alpha_lab/collectors/mops_events.py`
- Create: `backend/tests/collectors/test_mops_events.py`

**API 策略**：MOPS 即時重大訊息頁 `https://mopsov.twse.com.tw/mops/web/ajax_t05st01` 需 POST form data，欄位多、不穩定。改採 TWSE OpenAPI 的即時重大訊息 JSON 端點：

`https://openapi.twse.com.tw/v1/opendata/t187ap04_L`（上市公司即時重大訊息彙總，JSON 陣列）

範例（實際欄位可能略有出入，需以 smoke 驗證）：

```json
[
  {
    "出表日期": "1150411",
    "發言日期": "1150410",
    "發言時間": "143020",
    "公司代號": "2330",
    "公司名稱": "台積電",
    "主旨": "公告本公司董事會決議配息案",
    "符合條款": "第五款",
    "說明": "..."
  }
]
```

- [ ] **Step 1: 先寫 failing test**

```python
"""MOPS events collector 單元測試。"""

from datetime import datetime

import httpx
import pytest
import respx

from alpha_lab.collectors.mops_events import fetch_latest_events
from alpha_lab.schemas.event import Event

SAMPLE_RESPONSE = [
    {
        "出表日期": "1150411",
        "發言日期": "1150410",
        "發言時間": "143020",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "主旨": "公告本公司董事會決議配息案",
        "符合條款": "第五款",
        "說明": "擬配發現金股利每股 11 元",
    },
    {
        "出表日期": "1150411",
        "發言日期": "1150410",
        "發言時間": "090000",
        "公司代號": "2317",
        "公司名稱": "鴻海",
        "主旨": "代子公司公告重訊",
        "符合條款": "第二款",
        "說明": "內容",
    },
]


@pytest.mark.asyncio
async def test_fetch_latest_events_parses_sample() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=SAMPLE_RESPONSE)

        events = await fetch_latest_events()

    assert len(events) == 2
    e = next(x for x in events if x.symbol == "2330")
    assert isinstance(e, Event)
    assert e.event_datetime == datetime(2026, 4, 10, 14, 30, 20)
    assert e.event_type == "第五款"
    assert "配息案" in e.title
    assert "11 元" in e.content


@pytest.mark.asyncio
async def test_fetch_latest_events_filters_symbols() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=SAMPLE_RESPONSE)
        events = await fetch_latest_events(symbols=["2330"])
    assert [e.symbol for e in events] == ["2330"]


@pytest.mark.asyncio
async def test_fetch_latest_events_empty_list_ok() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=[])
        events = await fetch_latest_events()
    assert events == []


@pytest.mark.asyncio
async def test_fetch_latest_events_http_error() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_latest_events()
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops_events.py -v
```

預期：`ModuleNotFoundError`。

- [ ] **Step 3: 實作 `collectors/mops_events.py`**

```python
"""MOPS 重大訊息 collector。

API：https://openapi.twse.com.tw/v1/opendata/t187ap04_L（上市即時重大訊息彙總）

若 TWSE OpenAPI 欄位有差異，此實作以 key 名稱逐個取值，缺欄位時以 empty string fallback。
"""

from datetime import datetime

import httpx

from alpha_lab.config import get_settings
from alpha_lab.schemas.event import Event

OPENAPI_BASE = "https://openapi.twse.com.tw"
EVENTS_PATH = "/v1/opendata/t187ap04_L"


def _roc_date_to_iso(roc: str) -> tuple[int, int, int]:
    """'1150410' → (2026, 4, 10)。"""
    if len(roc) < 5:
        raise ValueError(f"bad ROC date: {roc}")
    roc_year = int(roc[:-4])
    month = int(roc[-4:-2])
    day = int(roc[-2:])
    return roc_year + 1911, month, day


def _hhmmss_to_tuple(s: str) -> tuple[int, int, int]:
    """'143020' → (14, 30, 20)；不足 6 碼左補 0。"""
    s = s.zfill(6)
    return int(s[:2]), int(s[2:4]), int(s[4:6])


async def fetch_latest_events(
    symbols: list[str] | None = None,
) -> list[Event]:
    """抓取最新一批上市重大訊息。

    Args:
        symbols: 若提供，僅回傳清單內代號。
    """
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(
        base_url=OPENAPI_BASE,
        timeout=settings.http_timeout_seconds,
        headers=headers,
    ) as client:
        resp = await client.get(EVENTS_PATH)
        resp.raise_for_status()
        payload = resp.json()

    if not isinstance(payload, list):
        raise ValueError(f"unexpected events payload type: {type(payload)}")

    symbol_filter = set(symbols) if symbols else None
    results: list[Event] = []
    for item in payload:
        symbol = str(item.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue

        roc_d = str(item.get("發言日期", ""))
        hms = str(item.get("發言時間", "000000"))
        if not roc_d:
            continue
        year, month, day = _roc_date_to_iso(roc_d)
        hh, mm, ss = _hhmmss_to_tuple(hms)

        results.append(
            Event(
                symbol=symbol,
                event_datetime=datetime(year, month, day, hh, mm, ss),
                event_type=str(item.get("符合條款") or item.get("主旨") or "其他"),
                title=str(item.get("主旨", "")).strip() or "(無主旨)",
                content=str(item.get("說明", "")).strip(),
            )
        )
    return results
```

- [ ] **Step 4: 執行測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops_events.py -v
```

預期：4 passed。

- [ ] **Step 5: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：0 error。

- [ ] **Step 6: 手動驗收指引**

> 請確認 `pytest tests/collectors/test_mops_events.py` 4 passed。回覆「D1 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/collectors/mops_events.py backend/tests/collectors/test_mops_events.py
git commit -m "feat: add mops material events collector"
```

---

## Task D2: 重大訊息 upsert + dispatch

**Files:**
- Modify: `backend/src/alpha_lab/collectors/runner.py`
- Modify: `backend/src/alpha_lab/jobs/service.py`
- Modify: `backend/src/alpha_lab/collectors/__init__.py`
- Create: `backend/tests/collectors/test_runner_events.py`
- Modify: `backend/tests/jobs/test_service.py`

**Upsert 策略**：events 主鍵是 autoincrement id；用 `(symbol, event_datetime, title)` 三元組查重避免重複插入（同一訊息多次抓取會命中同一筆）。

- [ ] **Step 1: 寫 upsert failing test**

`backend/tests/collectors/test_runner_events.py`：

```python
"""重大訊息 upsert 測試。"""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_events
from alpha_lab.schemas.event import Event
from alpha_lab.storage.models import Base, Event as EventRow, Stock


def test_upsert_events_inserts_new_and_skips_duplicate() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        events = [
            Event(
                symbol="2330",
                event_datetime=datetime(2026, 4, 10, 14, 30, 20),
                event_type="第五款",
                title="配息案",
                content="每股 11 元",
            ),
        ]
        assert upsert_events(session, events) == 1
        session.commit()
        assert session.query(EventRow).count() == 1

        # 再次 upsert 同一則 → 不新增
        assert upsert_events(session, events) == 0
        session.commit()
        assert session.query(EventRow).count() == 1


def test_upsert_events_different_datetime_creates_new_row() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        events = [
            Event(
                symbol="2330", event_datetime=datetime(2026, 4, 10, 14, 30, 20),
                event_type="第五款", title="A", content="",
            ),
            Event(
                symbol="2330", event_datetime=datetime(2026, 4, 11, 9, 0, 0),
                event_type="第五款", title="A", content="",
            ),
        ]
        assert upsert_events(session, events) == 2
        session.commit()
        assert session.query(EventRow).count() == 2
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_events.py -v
```

預期：ImportError。

- [ ] **Step 3: 在 `collectors/runner.py` 加 `upsert_events`**

```python
from alpha_lab.schemas.event import Event as EventSchema
from alpha_lab.storage.models import Event as EventRow


def upsert_events(session: Session, rows: list[EventSchema]) -> int:
    """upsert 重大訊息。以 (symbol, event_datetime, title) 查重。回傳新插入筆數。"""
    inserted = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        # datetime 需為 naive（存 SQLite DateTime）；若 caller 傳 aware 需轉
        dt = row.event_datetime.replace(tzinfo=None) if row.event_datetime.tzinfo else row.event_datetime
        existing = (
            session.query(EventRow)
            .filter(
                EventRow.symbol == row.symbol,
                EventRow.event_datetime == dt,
                EventRow.title == row.title,
            )
            .first()
        )
        if existing is None:
            session.add(
                EventRow(
                    symbol=row.symbol,
                    event_datetime=dt,
                    event_type=row.event_type,
                    title=row.title,
                    content=row.content,
                )
            )
            inserted += 1
        # 既存則 skip（重大訊息不 overwrite，避免修改歷史紀錄）
    return inserted
```

- [ ] **Step 4: 在 `jobs/service.py::_dispatch` 加 `MOPS_EVENTS` 分支**

```python
    if job_type is JobType.MOPS_EVENTS:
        from alpha_lab.collectors.mops_events import fetch_latest_events
        from alpha_lab.collectors.runner import upsert_events

        symbols = params.get("symbols")
        event_rows = await fetch_latest_events(symbols=symbols)
        with session_factory() as session:
            n = upsert_events(session, event_rows)
            session.commit()
        return f"inserted {n} new events"
```

- [ ] **Step 5: 更新 `collectors/__init__.py`**

```python
from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.mops_events import fetch_latest_events
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
from alpha_lab.collectors.twse_margin import fetch_margin_trades

__all__ = [
    "fetch_daily_prices",
    "fetch_institutional_trades",
    "fetch_latest_events",
    "fetch_latest_monthly_revenues",
    "fetch_margin_trades",
]
```

- [ ] **Step 6: 在 `tests/jobs/test_service.py` 追加 events dispatch 測試**

```python
@pytest.mark.asyncio
async def test_run_job_sync_mops_events_happy_path(session_factory) -> None:
    payload = [
        {
            "出表日期": "1150411",
            "發言日期": "1150410",
            "發言時間": "143020",
            "公司代號": "2330",
            "公司名稱": "台積電",
            "主旨": "配息案",
            "符合條款": "第五款",
            "說明": "每股 11 元",
        },
    ]

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.MOPS_EVENTS,
            params={"symbols": ["2330"]},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import Event as EventRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(EventRow).count() == 1
```

- [ ] **Step 7: 全部測試 + 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m pytest -v
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：全 passed、0 error。

- [ ] **Step 8: 手動驗收指引**

> 請確認全測試 passed、靜態 0 error。回覆「D2 OK」後 commit。

- [ ] **Step 9: Commit**

```bash
git add backend/src/alpha_lab/ backend/tests/
git commit -m "feat: wire mops events collector into job dispatch"
```

---

## Task D3: 重大訊息 smoke script

**Files:**
- Create: `backend/scripts/smoke_mops_events.py`

- [ ] **Step 1: 建立腳本**

```python
"""MOPS 重大訊息 collector 煙霧測試。"""

import asyncio

from alpha_lab.collectors.mops_events import fetch_latest_events


async def main() -> None:
    events = await fetch_latest_events(symbols=["2330", "2317", "2454"])
    print(f"Fetched {len(events)} events")
    for e in events[:10]:
        print(f"  {e.event_datetime:%Y-%m-%d %H:%M} [{e.symbol}] {e.event_type}: {e.title[:40]}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 手動驗收指引**

> 請手動執行 `cd backend && .venv/Scripts/python.exe scripts/smoke_mops_events.py`。若當期這些代號沒有重訊也算正常（`0 events`）。若能印出多筆，代表 API 串接成功。回覆「D3 OK」後 commit。
>
> **注意**：若 TWSE OpenAPI 的 `t187ap04_L` 端點實際欄位與範例不一致，此 Task 會在 smoke 階段發現。若發生，先改 collector 欄位映射、補 test case、再 commit。

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/smoke_mops_events.py
git commit -m "chore: add mops events smoke script"
```

---

## Task E1: 季報三表 collector 框架（fetch_financial_statement + income）

**Files:**
- Create: `backend/src/alpha_lab/collectors/mops_financials.py`
- Create: `backend/tests/collectors/test_mops_financials.py`

**API 策略**：MOPS 財報查詢走 `https://mopsov.twse.com.tw/mops/web/ajax_t164sb03`（合併綜合損益表）等端點。這些是 **POST form-encoded** 的老舊介面，回傳是 **HTML table**，解析複雜且不穩定。

**Phase 1.5 折中方案**：採用 TWSE OpenAPI 的彙總端點：
- 合併綜合損益表：`https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci`（上市公司季別綜合損益）
- 合併資產負債表：`https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci`
- 合併現金流量表：`https://openapi.twse.com.tw/v1/opendata/t187ap10_L_ci`

（注意：OpenAPI 端點名稱 TWSE 偶有調整；實作前先用瀏覽器或 curl 確認實際 URL，若異動則改對應路徑並記錄於知識庫 `collectors/mops.md`。）

**本 Task 實作通用框架 + income（綜合損益）單表**，balance/cashflow 留 E2、E3。

- [ ] **Step 1: 先寫 failing test**

```python
"""MOPS 季報 collector 單元測試 — 本 Task 只驗證 income。"""

import pytest
import respx

from alpha_lab.collectors.mops_financials import fetch_income_statement
from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType

SAMPLE_INCOME = [
    {
        "出表日期": "1150515",
        "年度": "115",
        "季別": "1",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "營業收入": "300000000",
        "營業毛利(毛損)": "180000000",
        "營業利益(損失)": "120000000",
        "本期淨利(淨損)": "100000000",
        "基本每股盈餘(元)": "10.50",
    },
    {
        "出表日期": "1150515",
        "年度": "115",
        "季別": "1",
        "公司代號": "2317",
        "公司名稱": "鴻海",
        "營業收入": "500000000",
        "營業毛利(毛損)": "50000000",
        "營業利益(損失)": "20000000",
        "本期淨利(淨損)": "15000000",
        "基本每股盈餘(元)": "2.30",
    },
]


@pytest.mark.asyncio
async def test_fetch_income_statement_parses_sample() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap06_L_ci").respond(json=SAMPLE_INCOME)

        rows = await fetch_income_statement(symbols=["2330"])

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, FinancialStatement)
    assert r.symbol == "2330"
    assert r.period == "2026Q1"
    assert r.statement_type == StatementType.INCOME
    assert r.revenue == 300_000_000
    assert r.gross_profit == 180_000_000
    assert r.operating_income == 120_000_000
    assert r.net_income == 100_000_000
    assert r.eps == 10.50


@pytest.mark.asyncio
async def test_fetch_income_statement_all_symbols_when_none() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap06_L_ci").respond(json=SAMPLE_INCOME)
        rows = await fetch_income_statement(symbols=None)
    assert len(rows) == 2
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops_financials.py -v
```

預期：ModuleNotFoundError。

- [ ] **Step 3: 實作 `collectors/mops_financials.py`**

```python
"""MOPS 季報三表 collector。

資料源：TWSE OpenAPI 彙總端點（v1/opendata/t187ap06/07/10_L_ci）
回傳：list[FinancialStatement]（以 statement_type 區分三表）

注意：TWSE OpenAPI 端點與欄位名偶有調整。若 smoke 測試失敗請先用 curl 確認實際欄位，
再更新欄位映射與測試 sample。
"""

import json
from typing import Any

import httpx

from alpha_lab.config import get_settings
from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType

OPENAPI_BASE = "https://openapi.twse.com.tw"
INCOME_PATH = "/v1/opendata/t187ap06_L_ci"
BALANCE_PATH = "/v1/opendata/t187ap07_L_ci"
CASHFLOW_PATH = "/v1/opendata/t187ap10_L_ci"


def _parse_int_or_none(s: Any) -> int | None:
    if s is None or s == "" or s == "-":
        return None
    try:
        return int(str(s).replace(",", ""))
    except ValueError:
        return None


def _parse_float_or_none(s: Any) -> float | None:
    if s is None or s == "" or s == "-":
        return None
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def _build_period(roc_year: str, quarter: str) -> str:
    """'115', '1' → '2026Q1'"""
    return f"{int(roc_year) + 1911}Q{int(quarter)}"


async def _fetch_payload(path: str) -> list[dict[str, Any]]:
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}
    async with httpx.AsyncClient(
        base_url=OPENAPI_BASE,
        timeout=settings.http_timeout_seconds,
        headers=headers,
    ) as client:
        resp = await client.get(path)
        resp.raise_for_status()
        payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError(f"unexpected financial payload: {type(payload)}")
    return payload


def _filter(symbols: list[str] | None) -> set[str] | None:
    return set(symbols) if symbols else None


async def fetch_income_statement(
    symbols: list[str] | None = None,
) -> list[FinancialStatement]:
    """抓取最新一期全上市公司合併綜合損益表。"""
    payload = await _fetch_payload(INCOME_PATH)
    symbol_filter = _filter(symbols)

    results: list[FinancialStatement] = []
    for item in payload:
        symbol = str(item.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        period = _build_period(str(item.get("年度", "")), str(item.get("季別", "")))
        results.append(
            FinancialStatement(
                symbol=symbol,
                period=period,
                statement_type=StatementType.INCOME,
                revenue=_parse_int_or_none(item.get("營業收入")),
                gross_profit=_parse_int_or_none(item.get("營業毛利(毛損)")),
                operating_income=_parse_int_or_none(item.get("營業利益(損失)")),
                net_income=_parse_int_or_none(item.get("本期淨利(淨損)")),
                eps=_parse_float_or_none(item.get("基本每股盈餘(元)")),
                raw_json=item,
            )
        )
    return results


# Helper: 把 raw_json（dict）序列化，供 runner 寫入 DB。
def serialize_raw(fs: FinancialStatement) -> str:
    return json.dumps(fs.raw_json, ensure_ascii=False)
```

- [ ] **Step 4: 執行測試 + 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops_financials.py -v
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：2 passed、0 error。

- [ ] **Step 5: 手動驗收指引**

> 請確認 test 2 passed、靜態 0 error。回覆「E1 OK」後 commit。

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/collectors/mops_financials.py backend/tests/collectors/test_mops_financials.py
git commit -m "feat: add mops income statement collector"
```

---

## Task E2: 季報 balance + cashflow collector

**Files:**
- Modify: `backend/src/alpha_lab/collectors/mops_financials.py`
- Modify: `backend/tests/collectors/test_mops_financials.py`

- [ ] **Step 1: 寫 failing test（balance + cashflow）**

在 `test_mops_financials.py` 末尾追加：

```python
SAMPLE_BALANCE = [
    {
        "年度": "115", "季別": "1",
        "公司代號": "2330", "公司名稱": "台積電",
        "資產總額": "5000000000",
        "負債總額": "1500000000",
        "權益總額": "3500000000",
    },
]

SAMPLE_CASHFLOW = [
    {
        "年度": "115", "季別": "1",
        "公司代號": "2330", "公司名稱": "台積電",
        "營業活動之淨現金流入(流出)": "150000000",
        "投資活動之淨現金流入(流出)": "-80000000",
        "籌資活動之淨現金流入(流出)": "-40000000",
    },
]


@pytest.mark.asyncio
async def test_fetch_balance_sheet_parses_sample() -> None:
    from alpha_lab.collectors.mops_financials import fetch_balance_sheet

    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap07_L_ci").respond(json=SAMPLE_BALANCE)
        rows = await fetch_balance_sheet(symbols=["2330"])

    assert len(rows) == 1
    r = rows[0]
    assert r.statement_type == StatementType.BALANCE
    assert r.period == "2026Q1"
    assert r.total_assets == 5_000_000_000
    assert r.total_liabilities == 1_500_000_000
    assert r.total_equity == 3_500_000_000


@pytest.mark.asyncio
async def test_fetch_cashflow_statement_parses_sample() -> None:
    from alpha_lab.collectors.mops_financials import fetch_cashflow_statement

    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap10_L_ci").respond(json=SAMPLE_CASHFLOW)
        rows = await fetch_cashflow_statement(symbols=["2330"])

    assert len(rows) == 1
    r = rows[0]
    assert r.statement_type == StatementType.CASHFLOW
    assert r.operating_cf == 150_000_000
    assert r.investing_cf == -80_000_000
    assert r.financing_cf == -40_000_000
```

- [ ] **Step 2: 執行測試確認失敗**

預期：`ImportError`（尚未實作兩個新函式）。

- [ ] **Step 3: 在 `collectors/mops_financials.py` 追加實作**

```python
async def fetch_balance_sheet(
    symbols: list[str] | None = None,
) -> list[FinancialStatement]:
    """抓取最新一期合併資產負債表。"""
    payload = await _fetch_payload(BALANCE_PATH)
    symbol_filter = _filter(symbols)

    results: list[FinancialStatement] = []
    for item in payload:
        symbol = str(item.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        period = _build_period(str(item.get("年度", "")), str(item.get("季別", "")))
        results.append(
            FinancialStatement(
                symbol=symbol,
                period=period,
                statement_type=StatementType.BALANCE,
                total_assets=_parse_int_or_none(item.get("資產總額") or item.get("資產總計")),
                total_liabilities=_parse_int_or_none(
                    item.get("負債總額") or item.get("負債總計")
                ),
                total_equity=_parse_int_or_none(
                    item.get("權益總額") or item.get("權益總計")
                ),
                raw_json=item,
            )
        )
    return results


async def fetch_cashflow_statement(
    symbols: list[str] | None = None,
) -> list[FinancialStatement]:
    """抓取最新一期合併現金流量表。"""
    payload = await _fetch_payload(CASHFLOW_PATH)
    symbol_filter = _filter(symbols)

    results: list[FinancialStatement] = []
    for item in payload:
        symbol = str(item.get("公司代號", "")).strip()
        if not symbol:
            continue
        if symbol_filter is not None and symbol not in symbol_filter:
            continue
        period = _build_period(str(item.get("年度", "")), str(item.get("季別", "")))
        results.append(
            FinancialStatement(
                symbol=symbol,
                period=period,
                statement_type=StatementType.CASHFLOW,
                operating_cf=_parse_int_or_none(
                    item.get("營業活動之淨現金流入(流出)")
                    or item.get("營業活動現金流量")
                ),
                investing_cf=_parse_int_or_none(
                    item.get("投資活動之淨現金流入(流出)")
                    or item.get("投資活動現金流量")
                ),
                financing_cf=_parse_int_or_none(
                    item.get("籌資活動之淨現金流入(流出)")
                    or item.get("籌資活動現金流量")
                ),
                raw_json=item,
            )
        )
    return results
```

- [ ] **Step 4: 執行測試 + 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_mops_financials.py -v
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：4 passed、0 error。

- [ ] **Step 5: 手動驗收指引**

> 請確認全測試 passed、靜態 0 error。回覆「E2 OK」後 commit。

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/collectors/mops_financials.py backend/tests/collectors/test_mops_financials.py
git commit -m "feat: add mops balance sheet and cashflow collectors"
```

---

## Task E3: 季報 upsert（三表共用 runner）

**Files:**
- Modify: `backend/src/alpha_lab/collectors/runner.py`
- Create: `backend/tests/collectors/test_runner_financials.py`

**Upsert 策略**：主鍵 `(symbol, period, statement_type)`；既存同一筆 → 覆寫所有欄位（含 raw_json_text）。因三表共用同一 model，runner 函式是單一 `upsert_financial_statements(rows)`，行為依 `statement_type` 統一處理（各 statement_type 只會填自己那組欄位，其他欄位留 None，覆寫也不影響）。

- [ ] **Step 1: 寫 failing test**

`backend/tests/collectors/test_runner_financials.py`：

```python
"""季報三表 upsert 測試。"""

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.collectors.runner import upsert_financial_statements
from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType
from alpha_lab.storage.models import Base, FinancialStatement as FSRow, Stock


def test_upsert_financial_statements_inserts_three_types() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        rows = [
            FinancialStatement(
                symbol="2330", period="2026Q1",
                statement_type=StatementType.INCOME,
                revenue=300_000_000, net_income=100_000_000, eps=10.5,
                raw_json={"a": 1},
            ),
            FinancialStatement(
                symbol="2330", period="2026Q1",
                statement_type=StatementType.BALANCE,
                total_assets=5_000_000_000, total_liabilities=1_500_000_000,
                total_equity=3_500_000_000, raw_json={"b": 2},
            ),
            FinancialStatement(
                symbol="2330", period="2026Q1",
                statement_type=StatementType.CASHFLOW,
                operating_cf=150_000_000, investing_cf=-80_000_000,
                financing_cf=-40_000_000, raw_json={"c": 3},
            ),
        ]
        assert upsert_financial_statements(session, rows) == 3
        session.commit()
        assert session.query(FSRow).count() == 3

        # raw_json_text 應為序列化後的 JSON 字串
        income_row = session.get(
            FSRow,
            {"symbol": "2330", "period": "2026Q1", "statement_type": "income"},
        )
        assert income_row is not None
        assert json.loads(income_row.raw_json_text) == {"a": 1}


def test_upsert_financial_statements_updates_existing() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()

        assert upsert_financial_statements(
            session,
            [
                FinancialStatement(
                    symbol="2330", period="2026Q1",
                    statement_type=StatementType.INCOME,
                    revenue=100, raw_json={"v": 1},
                ),
            ],
        ) == 1
        session.commit()

        assert upsert_financial_statements(
            session,
            [
                FinancialStatement(
                    symbol="2330", period="2026Q1",
                    statement_type=StatementType.INCOME,
                    revenue=200, raw_json={"v": 2},
                ),
            ],
        ) == 1
        session.commit()

        row = session.get(
            FSRow,
            {"symbol": "2330", "period": "2026Q1", "statement_type": "income"},
        )
        assert row is not None
        assert row.revenue == 200
        assert json.loads(row.raw_json_text) == {"v": 2}
```

- [ ] **Step 2: 執行測試確認失敗**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_financials.py -v
```

預期：ImportError。

- [ ] **Step 3: 在 `collectors/runner.py` 加 `upsert_financial_statements`**

```python
import json as _json_for_fs

from alpha_lab.schemas.financial_statement import (
    FinancialStatement as FSSchema,
    StatementType,
)
from alpha_lab.storage.models import FinancialStatement as FSRow


def upsert_financial_statements(
    session: Session, rows: list[FSSchema]
) -> int:
    """upsert 季報（三表）。回傳寫入筆數（新增 + 更新）。"""
    count = 0
    for row in rows:
        _ensure_stock(session, row.symbol)
        statement_type_value = (
            row.statement_type.value
            if isinstance(row.statement_type, StatementType)
            else str(row.statement_type)
        )
        pk = {
            "symbol": row.symbol,
            "period": row.period,
            "statement_type": statement_type_value,
        }
        existing = session.get(FSRow, pk)
        raw_text = _json_for_fs.dumps(row.raw_json, ensure_ascii=False)
        fields = dict(
            revenue=row.revenue,
            gross_profit=row.gross_profit,
            operating_income=row.operating_income,
            net_income=row.net_income,
            eps=row.eps,
            total_assets=row.total_assets,
            total_liabilities=row.total_liabilities,
            total_equity=row.total_equity,
            operating_cf=row.operating_cf,
            investing_cf=row.investing_cf,
            financing_cf=row.financing_cf,
            raw_json_text=raw_text,
        )
        if existing is None:
            session.add(
                FSRow(
                    symbol=row.symbol,
                    period=row.period,
                    statement_type=statement_type_value,
                    **fields,
                )
            )
        else:
            for k, v in fields.items():
                setattr(existing, k, v)
        count += 1
    return count
```

- [ ] **Step 4: 執行測試 + 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/collectors/test_runner_financials.py -v
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：2 passed、0 error。

- [ ] **Step 5: 手動驗收指引**

> 請確認測試 passed、靜態 0 error。回覆「E3 OK」後 commit。

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/collectors/runner.py backend/tests/collectors/test_runner_financials.py
git commit -m "feat: add upsert logic for financial statements"
```

---

## Task E4: 季報 job type dispatch + smoke script

**Files:**
- Modify: `backend/src/alpha_lab/jobs/service.py`
- Modify: `backend/src/alpha_lab/collectors/__init__.py`
- Modify: `backend/tests/jobs/test_service.py`
- Create: `backend/scripts/smoke_mops_financials.py`

**Job 參數設計**：`MOPS_FINANCIALS` 一次抓三表，params 可選 `{"types": ["income", "balance", "cashflow"]}`（預設全抓）+ `{"symbols": [...]}`。

- [ ] **Step 1: 在 `jobs/service.py::_dispatch` 加 `MOPS_FINANCIALS` 分支**

```python
    if job_type is JobType.MOPS_FINANCIALS:
        from alpha_lab.collectors.mops_financials import (
            fetch_balance_sheet,
            fetch_cashflow_statement,
            fetch_income_statement,
        )
        from alpha_lab.collectors.runner import upsert_financial_statements

        symbols = params.get("symbols")
        types = set(params.get("types") or ["income", "balance", "cashflow"])

        total_rows: list = []
        if "income" in types:
            total_rows += await fetch_income_statement(symbols=symbols)
        if "balance" in types:
            total_rows += await fetch_balance_sheet(symbols=symbols)
        if "cashflow" in types:
            total_rows += await fetch_cashflow_statement(symbols=symbols)

        with session_factory() as session:
            n = upsert_financial_statements(session, total_rows)
            session.commit()
        return f"upserted {n} financial statement rows ({sorted(types)})"
```

- [ ] **Step 2: 更新 `collectors/__init__.py`**

```python
from alpha_lab.collectors.mops import fetch_latest_monthly_revenues
from alpha_lab.collectors.mops_events import fetch_latest_events
from alpha_lab.collectors.mops_financials import (
    fetch_balance_sheet,
    fetch_cashflow_statement,
    fetch_income_statement,
)
from alpha_lab.collectors.twse import fetch_daily_prices
from alpha_lab.collectors.twse_institutional import fetch_institutional_trades
from alpha_lab.collectors.twse_margin import fetch_margin_trades

__all__ = [
    "fetch_balance_sheet",
    "fetch_cashflow_statement",
    "fetch_daily_prices",
    "fetch_income_statement",
    "fetch_institutional_trades",
    "fetch_latest_events",
    "fetch_latest_monthly_revenues",
    "fetch_margin_trades",
]
```

- [ ] **Step 3: 在 `tests/jobs/test_service.py` 追加季報 dispatch 測試**

```python
@pytest.mark.asyncio
async def test_run_job_sync_mops_financials_happy_path(session_factory) -> None:
    income_payload = [
        {
            "年度": "115", "季別": "1",
            "公司代號": "2330", "公司名稱": "台積電",
            "營業收入": "300000000",
            "營業毛利(毛損)": "180000000",
            "營業利益(損失)": "120000000",
            "本期淨利(淨損)": "100000000",
            "基本每股盈餘(元)": "10.50",
        },
    ]

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.MOPS_FINANCIALS,
            params={"symbols": ["2330"], "types": ["income"]},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap06_L_ci").respond(json=income_payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import FinancialStatement as FSRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(FSRow).count() == 1
```

- [ ] **Step 4: 建立 smoke script**

```python
"""MOPS 季報三表 collector 煙霧測試。"""

import asyncio

from alpha_lab.collectors.mops_financials import (
    fetch_balance_sheet,
    fetch_cashflow_statement,
    fetch_income_statement,
)


async def main() -> None:
    symbols = ["2330", "2317"]

    income = await fetch_income_statement(symbols=symbols)
    print(f"\n[Income] {len(income)} rows")
    for r in income:
        print(
            f"  {r.symbol} {r.period} rev={r.revenue:,} "
            f"ni={r.net_income:,} eps={r.eps}"
        )

    balance = await fetch_balance_sheet(symbols=symbols)
    print(f"\n[Balance] {len(balance)} rows")
    for r in balance:
        print(
            f"  {r.symbol} {r.period} assets={r.total_assets:,} "
            f"liab={r.total_liabilities:,} equity={r.total_equity:,}"
        )

    cashflow = await fetch_cashflow_statement(symbols=symbols)
    print(f"\n[Cashflow] {len(cashflow)} rows")
    for r in cashflow:
        print(
            f"  {r.symbol} {r.period} op={r.operating_cf:,} "
            f"inv={r.investing_cf:,} fin={r.financing_cf:,}"
        )


if __name__ == "__main__":
    asyncio.run(main())
```

檔案放 `backend/scripts/smoke_mops_financials.py`。

- [ ] **Step 5: 全部測試 + 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m pytest -v
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：全 passed（含新 dispatch test）、0 error。

- [ ] **Step 6: 手動驗收指引**

> 1. `pytest -v` 全 passed、`ruff` / `mypy` 0 error。
> 2. 手動執行 `cd backend && .venv/Scripts/python.exe scripts/smoke_mops_financials.py`，確認能印出三表資料。
>    - **若欄位名與實作不符**：OpenAPI 實際欄位偶爾會微調，smoke 階段會揭露。若發現，修正 `mops_financials.py` 欄位映射、補測試 sample、重跑測試，再 commit。
> 3. 回覆「E4 OK」後 commit。

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/ backend/tests/ backend/scripts/smoke_mops_financials.py
git commit -m "feat: wire mops financials collector into job dispatch"
```

---

## Task F1: `scripts/daily_collect.py` CLI

**Files:**
- Create: `backend/scripts/daily_collect.py`

**設計**：
- CLI 參數：`--date YYYY-MM-DD`（預設今天）、`--symbols 2330,2317`（可省，代表全體）
- 執行：按順序觸發「三大法人 + 融資融券 + 重大訊息」三個 daily job；月營收/季報不列入 daily（發布頻率不同）
- 每個 job 直接呼叫 `create_job` + `await run_job_sync`，共用主 SQLite DB（非 in-memory）
- 印出每個 job 的 status 與 result_summary

- [ ] **Step 1: 建立 `backend/scripts/daily_collect.py`**

```python
"""每日例行抓取 CLI。

用法：
    python scripts/daily_collect.py                 # 今天、全體上市
    python scripts/daily_collect.py --date 2026-04-11
    python scripts/daily_collect.py --symbols 2330,2317 --date 2026-04-11

會依序跑：三大法人 → 融資融券 → 重大訊息。
月營收、季報不列入 daily，請手動觸發對應 job。
"""

import argparse
import asyncio
from datetime import date, datetime

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.engine import get_session_factory
from alpha_lab.storage.init_db import init_database
from alpha_lab.storage.models import Job


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="alpha-lab daily collect")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="trade date YYYY-MM-DD, default today",
    )
    p.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="comma-separated symbols, default ALL",
    )
    return p.parse_args()


async def _run_one(
    label: str,
    job_type: JobType,
    params: dict,
    session_factory,
) -> None:
    with session_factory() as session:
        job = create_job(session, job_type=job_type, params=params)
        session.commit()
        job_id = job.id

    print(f"\n[{label}] job_id={job_id} params={params}")
    started = datetime.now()
    await run_job_sync(job_id=job_id, session_factory=session_factory)
    elapsed = (datetime.now() - started).total_seconds()

    with session_factory() as session:
        done = session.get(Job, job_id)
        assert done is not None
        status = done.status
        summary = done.result_summary or done.error_message or ""
    print(f"  → {status} ({elapsed:.1f}s) {summary}")


async def main() -> None:
    args = _parse_args()
    init_database()
    session_factory = get_session_factory()

    if args.date:
        y, m, d = args.date.split("-")
        trade_date = date(int(y), int(m), int(d))
    else:
        trade_date = date.today()
    trade_date_str = trade_date.strftime("%Y-%m-%d")

    symbols = args.symbols.split(",") if args.symbols else None

    print(f"=== daily_collect trade_date={trade_date_str} symbols={symbols or 'ALL'} ===")

    await _run_one(
        "TWSE institutional",
        JobType.TWSE_INSTITUTIONAL,
        {"trade_date": trade_date_str, "symbols": symbols},
        session_factory,
    )
    await _run_one(
        "TWSE margin",
        JobType.TWSE_MARGIN,
        {"trade_date": trade_date_str, "symbols": symbols},
        session_factory,
    )
    await _run_one(
        "MOPS events",
        JobType.MOPS_EVENTS,
        {"symbols": symbols},
        session_factory,
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check scripts/
.venv/Scripts/python.exe -m mypy scripts/daily_collect.py
```

若 `scripts/` 不在 mypy 的 `packages` 範圍，跳過 mypy 檢查即可（Phase 1 scripts 亦未納 mypy）。預期 ruff 0 error。

- [ ] **Step 3: 手動驗收指引**

> 請手動執行：
> ```bash
> cd backend
> .venv/Scripts/python.exe scripts/daily_collect.py --date 2026-04-11 --symbols 2330,2317,0050
> ```
> 應看到三段輸出（三大法人 / 融資融券 / 重大訊息），前兩個 status=completed，第三個若當期無此三檔重訊也是 completed（inserted 0）。
>
> 驗證 DB：
> ```bash
> .venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); print('institutional:', c.execute('SELECT COUNT(*) FROM institutional_trades').fetchone()); print('margin:', c.execute('SELECT COUNT(*) FROM margin_trades').fetchone()); print('events:', c.execute('SELECT COUNT(*) FROM events').fetchone())"
> ```
>
> 回覆「F1 OK」後 commit。

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/daily_collect.py
git commit -m "feat: add daily_collect cli for batch data collection"
```

---

## Task G1: 知識庫同步更新

**Files:**
- Modify: `docs/knowledge/architecture/data-models.md`
- Modify: `docs/knowledge/architecture/data-flow.md`
- Modify: `docs/knowledge/collectors/twse.md`
- Modify: `docs/knowledge/collectors/mops.md`
- Create: `docs/knowledge/collectors/events.md`

- [ ] **Step 1: 更新 `architecture/data-models.md`**

把 `updated:` 改為當天日期；表格追加 4 個新 table：

```markdown
---
domain: architecture
updated: 2026-04-15
related: [data-flow.md, ../collectors/twse.md, ../collectors/mops.md, ../collectors/events.md]
---

# 資料模型

## 目的

記錄 SQLAlchemy models 與 Pydantic schemas 的總覽，供 Claude 修改資料結構時參考。

## 現行實作（Phase 1.5 完成）

### SQLAlchemy Models（`backend/src/alpha_lab/storage/models.py`）

| Table | 主鍵 | 來源 | Phase |
|-------|------|------|-------|
| `stocks` | symbol | collector 隱性建立 | 1 |
| `prices_daily` | (symbol, trade_date) | TWSE STOCK_DAY | 1 |
| `revenues_monthly` | (symbol, year, month) | MOPS t187ap05_L | 1 |
| `jobs` | id (autoincrement) | API 觸發 | 1 |
| `institutional_trades` | (symbol, trade_date) | TWSE T86 | 1.5 |
| `margin_trades` | (symbol, trade_date) | TWSE MI_MARGN | 1.5 |
| `events` | id (autoincrement) | TWSE OpenAPI t187ap04_L | 1.5 |
| `financial_statements` | (symbol, period, statement_type) | TWSE OpenAPI t187ap06/07/10 | 1.5 |

### Pydantic Schemas

| 檔案 | 用途 |
|------|------|
| `schemas/health.py` | `/api/health` 回傳 |
| `schemas/price.py` | `DailyPrice` |
| `schemas/revenue.py` | `MonthlyRevenue` |
| `schemas/institutional.py` | `InstitutionalTrade` |
| `schemas/margin.py` | `MarginTrade` |
| `schemas/event.py` | `Event` |
| `schemas/financial_statement.py` | `FinancialStatement` + `StatementType` enum |
| `schemas/job.py` | Job API request/response |

### 設計原則

- Collector 輸出 Pydantic 物件 → runner 負責 upsert 到 SQLAlchemy model
- Pydantic schemas 是「API / collector 邊界」的合約；SQLAlchemy models 是「持久層」的實體
- `financial_statements` 採「寬表 + raw_json_text」策略：常用欄位獨立存放，原始完整欄位以 JSON 字串保留供未來擴充
- `events` 主鍵為 autoincrement id（同公司同時刻可能多則），以 (symbol, event_datetime, title) 查重
- `Stock` 在 collector 隱性建立 placeholder（name=symbol）；正式公司資料同步在 Phase 2+

## 關鍵檔案

- [backend/src/alpha_lab/storage/models.py](../../../backend/src/alpha_lab/storage/models.py)
- [backend/src/alpha_lab/storage/engine.py](../../../backend/src/alpha_lab/storage/engine.py)
- [backend/src/alpha_lab/schemas/](../../../backend/src/alpha_lab/schemas/)

## 修改時注意事項

- 新增 table：加到 `models.py`、用 `create_all` 自動建表；**Phase 2 若 schema 再有破壞性變動，應引入 Alembic**
- 新增欄位：nullable 可直接加；既存 DB 會 no-op，需 drop 或手動 ALTER
- 主鍵選擇：時間序列用 composite；事件/任務類（`jobs`、`events`）用 autoincrement
- `financial_statements` 增加新表類型時：擴充 `StatementType` enum + 對應 nullable 欄位 + runner fields dict
```

- [ ] **Step 2: 更新 `architecture/data-flow.md`**

把「新增 collector」章節更新，反映新 Job Types；並在 dispatch 圖示中列出 6 個 JobType。

```markdown
---
domain: architecture
updated: 2026-04-15
related: [data-models.md, ../collectors/twse.md, ../collectors/mops.md, ../collectors/events.md]
---

# 資料流

## 目的

描述「外部資料源 → collector → SQLite → API → UI」完整路徑。

## 現行實作（Phase 1.5 完成）

### 端到端流程

```
使用者 / CLI (scripts/daily_collect.py) / 排程
   │  POST /api/jobs/collect  或  create_job + run_job_sync
   ▼
Job runner (jobs/service.py)
   │  status=running → dispatch by JobType ↓
   ▼
Collector (collectors/*.py)
   │  httpx + truststore SSL → TWSE / MOPS / OpenAPI
   │  回傳 list[Pydantic schema]
   ▼
Upsert runner (collectors/runner.py)
   │  SQLAlchemy session → SQLite (data/alpha_lab.db)
   ▼
Job runner
   │  status=completed, result_summary 寫回 jobs 表
   ▼
API 輪詢 / CLI 印出結果
```

### JobType 與 collector 對應

| JobType | collector 函式 | 落庫 table |
|---------|---------------|-----------|
| `twse_prices` | `fetch_daily_prices` | `prices_daily` |
| `mops_revenue` | `fetch_latest_monthly_revenues` | `revenues_monthly` |
| `twse_institutional` | `fetch_institutional_trades` | `institutional_trades` |
| `twse_margin` | `fetch_margin_trades` | `margin_trades` |
| `mops_events` | `fetch_latest_events` | `events` |
| `mops_financials` | `fetch_income_statement` / `fetch_balance_sheet` / `fetch_cashflow_statement` | `financial_statements` |

### Session 管理原則

- 每個「邏輯工作單元」用一次 `session_scope()` context manager
- Job runner 把 read、write、執行 collector 分成獨立 session，避免長交易
- Collector 本身不碰 DB，純函式 → 方便測試

### 錯誤處理

- Collector 拋例外 → `run_job_sync` 捕捉、寫 `job.error_message`、`status=failed`、**不** re-raise
- HTTP 錯誤 → `resp.raise_for_status()` 自然拋 `httpx.HTTPStatusError`
- 資料驗證錯誤 → Pydantic `ValidationError`，當成 collector 異常處理

### 批次入口：`scripts/daily_collect.py`

- CLI 封裝「三大法人 + 融資融券 + 重大訊息」三類 daily job
- 不走 HTTP API，直接呼叫 `create_job` + `run_job_sync`
- 未來若要排程，以 OS cron / Windows 排程器呼叫此腳本（Phase 1.5 不做排程本身）

## 關鍵檔案

- [backend/src/alpha_lab/jobs/service.py](../../../backend/src/alpha_lab/jobs/service.py)
- [backend/src/alpha_lab/jobs/types.py](../../../backend/src/alpha_lab/jobs/types.py)
- [backend/src/alpha_lab/collectors/runner.py](../../../backend/src/alpha_lab/collectors/runner.py)
- [backend/src/alpha_lab/api/routes/jobs.py](../../../backend/src/alpha_lab/api/routes/jobs.py)
- [backend/scripts/daily_collect.py](../../../backend/scripts/daily_collect.py)

## 修改時注意事項

- 新增 collector：
  1. 在 `collectors/` 新增模組（fetch 函式輸出 Pydantic list）
  2. 在 `schemas/` 建立對應 Pydantic model
  3. 在 `storage/models.py` 建立對應 SQLAlchemy model + 更新 `__init__.py`
  4. 在 `collectors/runner.py` 加對應 upsert 函式
  5. 在 `jobs/types.py::JobType` 加一個 value
  6. 在 `jobs/service.py::_dispatch` 加分支
  7. （可選）在 `scripts/daily_collect.py` 追加一個 `_run_one` 呼叫
  8. 更新對應 `collectors/<source>.md` 知識庫 + 本檔 JobType 對應表
- 改 job 執行模型（例如要併發）：
  - 現在是 FastAPI BackgroundTasks（單程序），改 Celery/RQ 需同步改 `service.run_job_sync` 入口與 session factory 傳遞
- 排程：目前無 APScheduler / cron 整合；Phase 2+ 再評估
```

- [ ] **Step 3: 更新 `collectors/twse.md`**

```markdown
---
domain: collectors/twse
updated: 2026-04-15
related: [mops.md, events.md, ../architecture/data-flow.md, ../architecture/data-models.md]
---

# TWSE Collector

## 目的

抓取台灣證券交易所（TWSE）公開資料。

## 現行實作（Phase 1.5 完成）

### 端點總覽

| 用途 | URL | 模組 |
|------|-----|------|
| 個股日成交資訊 | `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=YYYYMMDD&stockNo=SYMBOL&response=json` | `collectors/twse.py` |
| 三大法人買賣超 | `https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json` | `collectors/twse_institutional.py` |
| 融資融券餘額 | `https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=YYYYMMDD&selectType=ALL&response=json` | `collectors/twse_margin.py` |

### 已實作函式

- `fetch_daily_prices(symbol, year_month) -> list[DailyPrice]` — 個股當月 OHLCV
- `fetch_institutional_trades(trade_date, symbols=None) -> list[InstitutionalTrade]` — 某交易日全體或指定代號
- `fetch_margin_trades(trade_date, symbols=None) -> list[MarginTrade]` — 某交易日全體或指定代號

### 已知坑

- TWSE 對短時間多次請求會擋 IP；smoke 測試需手動節流（1 分鐘以上）
- 成交股數、買賣超股數均含千分位逗號，需 `_parse_int` 統一處理
- ROC 年份轉換：`115 + 1911 = 2026`
- **欄位順序會隨年份變動**：三大法人 2018 年後多出「外資自營商」獨立欄位；implementation 以「從 fields 名稱找 index」避開硬編位置
- 融資融券 payload 包裹結構有 `tables` 與 `creditList` 兩種版本，`_find_credit_table` 兩者都能處理
- 欄位單位：股價是「元」、三大法人是「股」、融資融券是「張」— 入庫前不統一，由應用層換算

### Phase 2+ 規劃新增

- 除權息（TWTB4U / dividend history）
- 逐筆日交易歷史（盤中輪廓）
- 個股公司基本資料正式同步

## 關鍵檔案

- [backend/src/alpha_lab/collectors/twse.py](../../../backend/src/alpha_lab/collectors/twse.py)
- [backend/src/alpha_lab/collectors/twse_institutional.py](../../../backend/src/alpha_lab/collectors/twse_institutional.py)
- [backend/src/alpha_lab/collectors/twse_margin.py](../../../backend/src/alpha_lab/collectors/twse_margin.py)
- [backend/src/alpha_lab/schemas/price.py](../../../backend/src/alpha_lab/schemas/price.py)
- [backend/src/alpha_lab/schemas/institutional.py](../../../backend/src/alpha_lab/schemas/institutional.py)
- [backend/src/alpha_lab/schemas/margin.py](../../../backend/src/alpha_lab/schemas/margin.py)
- [backend/tests/collectors/test_twse.py](../../../backend/tests/collectors/test_twse.py)
- [backend/tests/collectors/test_twse_institutional.py](../../../backend/tests/collectors/test_twse_institutional.py)
- [backend/tests/collectors/test_twse_margin.py](../../../backend/tests/collectors/test_twse_margin.py)
- [backend/scripts/smoke_twse.py](../../../backend/scripts/smoke_twse.py)
- [backend/scripts/smoke_twse_institutional.py](../../../backend/scripts/smoke_twse_institutional.py)
- [backend/scripts/smoke_twse_margin.py](../../../backend/scripts/smoke_twse_margin.py)

## 修改時注意事項

- 改 URL 或參數：同步更新對應 respx.mock 路徑
- 新增欄位：擴充 schema + model + upsert runner 三處
- TWSE 若改回傳格式：優先以 `_find_idx` / `_find_credit_table` 等名稱查詢式存取，而非 index 位置
```

- [ ] **Step 4: 更新 `collectors/mops.md`**

```markdown
---
domain: collectors/mops
updated: 2026-04-15
related: [twse.md, events.md, ../architecture/data-flow.md]
---

# MOPS Collector

## 目的

抓取公開資訊觀測站（MOPS）相關資料，包含月營收、季報、重大訊息。

## 現行實作（Phase 1.5 完成）

### 端點總覽

| 用途 | URL | 模組 |
|------|-----|------|
| 最新月營收（全上市） | `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` | `collectors/mops.py` |
| 合併綜合損益表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci` | `collectors/mops_financials.py` |
| 合併資產負債表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci` | `collectors/mops_financials.py` |
| 合併現金流量表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap10_L_ci` | `collectors/mops_financials.py` |
| 重大訊息 | 見 [events.md](events.md) | `collectors/mops_events.py` |

### 已實作函式

- `fetch_latest_monthly_revenues(symbols=None)` — 最新月營收
- `fetch_income_statement(symbols=None)` — 最新季合併綜合損益
- `fetch_balance_sheet(symbols=None)` — 最新季合併資產負債
- `fetch_cashflow_statement(symbols=None)` — 最新季合併現金流量

### 資料單位與欄位

- 月營收 `revenue`：千元（MOPS 原始單位）
- 季報數值（revenue / profit / 資產 / 現金流）：皆為**千元**
- `eps`：元（每股盈餘原始單位）
- yoy / mom growth：百分比（%），可能為 `null`

### 季報寬表策略

三表共用 `FinancialStatement` Pydantic + `financial_statements` table，以 `statement_type` 區分：
- `income`：填 `revenue / gross_profit / operating_income / net_income / eps`
- `balance`：填 `total_assets / total_liabilities / total_equity`
- `cashflow`：填 `operating_cf / investing_cf / financing_cf`

`raw_json_text` 欄位保留完整原始欄位（JSON 字串），供未來新 factor / 新指標使用。

### 已知坑

- `資料年月` 格式 `"11503"` = 民國 115 年 3 月；季報以 `年度` + `季別` 兩欄位合成 `period = "2026Q1"`
- 部分欄位可能為空字串或 `"-"`，以 `_parse_int_or_none` / `_parse_float_or_none` 處理
- **OpenAPI 端點名稱偶有調整**：`t187ap06/07/10_L_ci` 若未來變動，改對應常數並同步本檔
- OpenAPI 只回「最新一期」；歷史月份 / 歷史季度需改走 mopsov.twse.com.tw 的 POST form 介面，Phase 1.5 不做
- 欄位中文含全形括號（`"營業毛利(毛損)"`），需逐字匹配；字串值需 UTF-8 安全處理

### Phase 2+ 規劃新增

- 歷史季度 / 歷史月份回補（爬 mopsov POST 介面或下載年度壓縮檔）
- 股利政策（配息 / 配股歷史）
- 董監事持股變動

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops.py](../../../backend/src/alpha_lab/collectors/mops.py)
- [backend/src/alpha_lab/collectors/mops_financials.py](../../../backend/src/alpha_lab/collectors/mops_financials.py)
- [backend/src/alpha_lab/schemas/revenue.py](../../../backend/src/alpha_lab/schemas/revenue.py)
- [backend/src/alpha_lab/schemas/financial_statement.py](../../../backend/src/alpha_lab/schemas/financial_statement.py)
- [backend/tests/collectors/test_mops.py](../../../backend/tests/collectors/test_mops.py)
- [backend/tests/collectors/test_mops_financials.py](../../../backend/tests/collectors/test_mops_financials.py)
- [backend/scripts/smoke_mops.py](../../../backend/scripts/smoke_mops.py)
- [backend/scripts/smoke_mops_financials.py](../../../backend/scripts/smoke_mops_financials.py)

## 修改時注意事項

- MOPS / OpenAPI 欄位名稱含特殊字元（全形括號），必須逐字匹配；建議優先用 `.get(key)` 並提供 fallback key
- 新增表類型：擴充 `StatementType` enum + `FinancialStatement` schema nullable 欄位 + `mops_financials.py` 新 fetch 函式 + `runner.upsert_financial_statements` fields dict + `_dispatch` MOPS_FINANCIALS 分支 types 清單
- 歷史回補功能若要加：獨立新模組（`mops_history.py`），不要把 HTML 解析混入 OpenAPI 模組
```

- [ ] **Step 5: 新建 `collectors/events.md`**

```markdown
---
domain: collectors/events
updated: 2026-04-15
related: [twse.md, mops.md, ../architecture/data-flow.md]
---

# 重大訊息 Collector

## 目的

抓取上市公司即時重大訊息，供個股頁、事件回顧與因子計算使用。

## 現行實作（Phase 1.5 完成）

### 端點

| 用途 | URL | 模組 |
|------|-----|------|
| 上市即時重大訊息 | `https://openapi.twse.com.tw/v1/opendata/t187ap04_L` | `collectors/mops_events.py` |

### 已實作函式

- `fetch_latest_events(symbols=None) -> list[Event]` — 最新一批即時重訊
  - `symbols=None`：回傳全體
  - `event_datetime` 由「發言日期」+「發言時間」合併（民國日期轉西元、HHMMSS 補 0）

### 資料模型

- `events` table：主鍵 autoincrement `id`（同公司同時刻可能多則）
- 查重：以 `(symbol, event_datetime, title)` 三元組判斷是否已存在，已存則 skip（不 overwrite）

### 已知坑

- MOPS 原始「即時重訊」頁 `t05st01` 需 POST form，解析 HTML，**不推薦**；本實作改用 OpenAPI 彙總端點
- OpenAPI `t187ap04_L` 只回「最新一批」，不回全歷史；歷史事件需爬 mopsov 的對照表
- 欄位可能變動：`符合條款` / `主旨` / `說明` 有時會以不同 key 名出現；實作以 `.get(key, fallback)` 處理
- 上櫃（OTC）公司的重訊未包含；Phase 2+ 再評估加入 TPEx 對應端點

### Phase 2+ 規劃

- 上櫃（TPEx）重訊
- 歷史事件回補
- 事件分類（財務、營運、股權、訴訟…）供因子使用

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops_events.py](../../../backend/src/alpha_lab/collectors/mops_events.py)
- [backend/src/alpha_lab/schemas/event.py](../../../backend/src/alpha_lab/schemas/event.py)
- [backend/tests/collectors/test_mops_events.py](../../../backend/tests/collectors/test_mops_events.py)
- [backend/scripts/smoke_mops_events.py](../../../backend/scripts/smoke_mops_events.py)

## 修改時注意事項

- 改欄位映射：同步更新 respx 測試的 sample payload
- 擴充查重規則：`upsert_events` 以 `(symbol, event_datetime, title)` 判斷；若 title 會在事後補充，改以 `(symbol, event_datetime, event_type)`
- 加入 OTC 重訊：新模組 `collectors/tpex_events.py`，不要把兩源混入同一函式
```

- [ ] **Step 6: 掃描亂碼**

```bash
cd /g/codingdata/alpha-lab
grep -r "��" docs/knowledge/ || echo "clean"
```

預期：`clean`。

- [ ] **Step 7: 手動驗收指引**

> 請閱讀五份知識庫 md，確認內容與 Phase 1.5 實作一致。特別檢查：
> - `data-models.md` 的 table 清單是否完整（共 8 table）
> - `data-flow.md` 的 JobType 對應表是否含 6 個 value
> - `twse.md` / `mops.md` / `events.md` 的端點 URL 與實作一致
>
> 回覆「G1 OK」後 commit。

- [ ] **Step 8: Commit**

```bash
git add docs/knowledge/
git commit -m "docs: sync knowledge base for phase 1.5 collectors"
```

---

## Task H1: Phase 1.5 全面驗收 + 最終 commit

- [x] **Step 1: Backend 靜態檢查**

```bash
cd backend
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy src
```

預期：兩者 0 error。

- [x] **Step 2: Backend 全部測試**

```bash
cd backend
.venv/Scripts/python.exe -m pytest -v
```

預期（estimate）：
- Phase 0 health: 1
- Phase 1 storage models: 4
- Phase 1 TWSE prices fetch + upsert: 5
- Phase 1 MOPS revenue: 3
- Phase 1 runner integration: 2
- Phase 1 jobs service: 3
- Phase 1 jobs API: 3
- Phase 1.5 storage models: 5
- Phase 1.5 TWSE institutional: 4
- Phase 1.5 runner institutional: 1
- Phase 1.5 jobs service 新增: 1
- Phase 1.5 TWSE margin: 4
- Phase 1.5 runner margin: 1
- Phase 1.5 jobs service 新增: 1
- Phase 1.5 MOPS events: 4
- Phase 1.5 runner events: 2
- Phase 1.5 jobs service 新增: 1
- Phase 1.5 MOPS financials: 4
- Phase 1.5 runner financials: 2
- Phase 1.5 jobs service 新增: 1

共 ~52 tests，全 passed。

- [ ] **Step 3: Frontend 靜態檢查 + 測試（沿用 Phase 1，不應有破壞）**

```bash
cd frontend
pnpm type-check
pnpm lint
pnpm test
pnpm e2e
```

預期：全 green。

- [ ] **Step 4: 手動端到端煙霧（使用者驗收核心）**

> 使用者手動執行（假設 TWSE / MOPS 當下可用）：
>
> 1. 啟動 backend：
>    ```bash
>    cd backend
>    .venv/Scripts/python.exe -m uvicorn alpha_lab.api.main:app --reload
>    ```
> 2. 觸發四類新 job（最近交易日請替換）：
>    ```bash
>    curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>      -H "Content-Type: application/json" \
>      -d '{"type":"twse_institutional","params":{"trade_date":"2026-04-11","symbols":["2330","2317"]}}'
>
>    curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>      -H "Content-Type: application/json" \
>      -d '{"type":"twse_margin","params":{"trade_date":"2026-04-11","symbols":["2330","2317"]}}'
>
>    curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>      -H "Content-Type: application/json" \
>      -d '{"type":"mops_events","params":{"symbols":["2330","2317"]}}'
>
>    curl -X POST http://127.0.0.1:8000/api/jobs/collect \
>      -H "Content-Type: application/json" \
>      -d '{"type":"mops_financials","params":{"symbols":["2330","2317"],"types":["income","balance","cashflow"]}}'
>    ```
> 3. 等數秒，查詢 status：`curl http://127.0.0.1:8000/api/jobs/status/<id>` — 應全 `completed`
> 4. 查 DB 每個表筆數：
>    ```bash
>    .venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); [print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ['institutional_trades','margin_trades','events','financial_statements']]"
>    ```
> 5. 測 `daily_collect.py`：
>    ```bash
>    .venv/Scripts/python.exe scripts/daily_collect.py --date 2026-04-11 --symbols 2330,2317
>    ```

- [x] **Step 5: 亂碼掃描**

```bash
cd /g/codingdata/alpha-lab
grep -r "��" backend/src backend/tests backend/scripts docs/knowledge docs/USER_GUIDE.md || echo "clean"
```

預期：`clean`。

- [x] **Step 6: 更新 spec 標註 Phase 1.5 完成**

修改 `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` §15 表格：
- Phase 1.5「狀態」欄改為 `✅ 完成（YYYY-MM-DD）`（當日日期）

```bash
git add docs/superpowers/specs/2026-04-14-alpha-lab-design.md
git commit -m "docs: mark phase 1.5 as complete"
```

- [ ] **Step 7: 確認 working tree 乾淨**

```bash
cd /g/codingdata/alpha-lab
rtk git status
```

預期：`nothing to commit, working tree clean`。

- [ ] **Step 8: （可選）打 tag**

```bash
git tag -a phase-1.5-complete -m "Phase 1.5: data collection expansion complete"
```

- [ ] **Step 9: 最終回報**

> Phase 1.5（數據抓取擴充）完成。commit 數：預計 ~15-17 個。
>
> **新增能力**：
> - 三大法人買賣超、融資融券每日抓取
> - 重大訊息即時抓取
> - 季報三表（損益 / 資產負債 / 現金流）抓取
> - `scripts/daily_collect.py` 一鍵跑三類 daily job
>
> **知識庫已同步**：`data-models.md` / `data-flow.md` / `twse.md` / `mops.md` / 新增 `events.md`。
>
> 停在這裡等指示。下一步預期進 Phase 2（個股頁 + 術語 Tooltip）。依 JIT 原則，Phase 2 計畫等使用者明確指示後再撰寫。

---

## 回到全專案視角：後續 Phase 銜接

Phase 1.5 完成後可做的選擇：

1. **Phase 2（個股頁 + 術語 Tooltip）**：個股頁可一次呈現股價、月營收、季報、三大法人、融資融券、重大訊息全部 Phase 1+1.5 累積的資料。
2. **先累積真實資料**：跑幾天 `daily_collect.py`，驗證管線穩定性、修補邊界狀況（TWSE / OpenAPI 欄位調整、假日無資料、休市處理）後再進 Phase 2。
3. **補做排程自動化**：Windows Task Scheduler / cron 設定文件；嚴格來說不是 Phase 1.5 範圍但價值高。

Phase 轉換前等使用者明確指示，遵守 `.claude/CLAUDE.md` JIT 原則。
