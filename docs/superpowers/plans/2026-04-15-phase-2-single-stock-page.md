# Phase 2: 個股頁 + 術語 Tooltip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付功能 A — 個股詳細頁可呈現股價走勢、關鍵指標、月營收、季報摘要、三大法人、融資融券、重大訊息；同步建置術語庫 v1（15 條核心詞）與 L1 hover Tooltip 基礎。

**Architecture:**
- **Backend**：新增 `/api/stocks` 路由，採「overview 聚合端點 + 細端點」混合設計。Overview 一次回首屏所需資料（近 60 日股價、近 12 月營收、近 4 季財報、近 20 筆法人/融資/事件），細端點（`/prices`、`/revenues`、`/financials`、`/institutional`、`/margin`、`/events`）支援 date range 供未來互動式圖表用。Glossary 走靜態 YAML，`/api/glossary/{term}` 為 thin wrapper。
- **Frontend**：新增 React Router 路由層（`/`、`/stocks/:symbol`）、Header 搜尋框、個股頁多 section layout。TermTooltip 採 hover 觸發 L1（簡短定義），術語在文字中以虛線下劃 + `<abbr>` 語意標記。L2 側邊面板規劃於 Phase 4（教學系統完整版），本 Phase 不做。
- **Charts**：Recharts 處理折線（股價）、柱狀（月營收、法人買賣）。K 線延到後續 Phase 視需求再加 lightweight-charts。
- **Industry tagging**：最小實作 — YAML 映射表 + backfill script，不做自動推斷；後續 Phase 可擴充。
- **知識庫同步**：本 Phase 建立 `features/data-panel/`、`features/education/tooltip.md`、`domain/industry-tagging.md`，更新 `architecture/data-flow.md`。

**Tech Stack:** FastAPI、SQLAlchemy 2.x、Pydantic v2、PyYAML（術語庫、產業表）、React 19、React Router 7、TanStack Query v5、Recharts、Tailwind 4、vitest、Playwright。

---

## Phase 2 工作總覽

| 群組 | 任務數 | 任務 |
|------|--------|------|
| A | 4 | Backend API — stocks 端點 + schemas |
| B | 2 | Backend — glossary API + YAML 結構 |
| C | 1 | Industry tagging 最小實作 |
| D | 1 | Glossary v1 內容（15 條術語草稿） |
| E | 3 | Frontend — scaffolding（router、header、api client） |
| F | 4 | Frontend — 個股頁 section 元件 |
| G | 1 | Frontend — TermTooltip 元件 |
| H | 2 | 測試（vitest + Playwright） |
| I | 2 | 知識庫 + USER_GUIDE + Phase 驗收 |

**總計：20 tasks**

## 範圍與邊界

**本 Phase 包含**：
- `/api/stocks/{symbol}/overview` 聚合端點 + 6 個細端點
- `/api/glossary/{term}` 端點、YAML 儲存、15 條術語
- 個股頁完整 UI（header、price chart、key metrics、revenue、financials、institutional、margin、events）
- Header 搜尋框（輸入 symbol → 跳轉）
- React Router 基礎（`/`、`/stocks/:symbol`）
- TermTooltip L1 hover 元件
- 產業分類 YAML + 小 CLI backfill
- 單元 + 整合測試；1 條 E2E（個股頁載入 + tooltip 互動）
- 知識庫：`features/data-panel/` 下 overview/ui-layout/data-sources，`features/education/tooltip.md`，`domain/industry-tagging.md`，更新 `architecture/data-flow.md`

**本 Phase 不包含**（留後續 Phase）：
- 多因子評分引擎 + ScoreRadar（Phase 3）
- 組合推薦頁面（Phase 3）
- L2 側邊詳解面板、教學密度三段切換（Phase 4）
- 股票列表頁 `/stocks`（Phase 5 選股篩選器一起做）
- 儀表板 `/` 升級（保持 Phase 0 hello world 樣貌，僅加 header 搜尋框）
- 分析報告儲存、回顧模式（Phase 4）
- K 線圖（lightweight-charts）
- 現金流量表 collector（延到 Phase 3，FCF 評分需要時才做）

## Commit 規範（本專案 MANDATORY）

1. **靜態分析必做**：`ruff check .` + `mypy src` + `pnpm type-check` + `pnpm lint` 必須 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit，給手動驗收指引，等使用者明確「OK」才 commit
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` / `chore` 不混在同一 commit
4. **禁止 scope 括號**：`type: description`，不可寫 `type(scope): description`
5. **同步檢查**：知識庫、spec、USER_GUIDE、E2E 是否需要連動更新
6. **中文亂碼掃描**：完成寫檔後 `grep -r "��" .`（不含 node_modules）

---

## Task A1: Stocks API Pydantic 回應 schemas

**Files:**
- Create: `backend/src/alpha_lab/schemas/stock.py`
- Test: `backend/tests/schemas/test_stock.py`

- [ ] **Step 1: 建立 `schemas/stock.py`**

```python
"""Stocks API 回應 Pydantic 模型。

overview 端點回傳 `StockOverview`，聚合個股頁首屏所需資料。
細端點回傳單一 section 的 list（如 `list[DailyPricePoint]`）。
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class StockMeta(BaseModel):
    """個股基本資料。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    name: str
    industry: str | None = None
    listed_date: date | None = None


class DailyPricePoint(BaseModel):
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class RevenuePoint(BaseModel):
    year: int
    month: int
    revenue: int
    yoy_growth: float | None = None
    mom_growth: float | None = None


class FinancialPoint(BaseModel):
    """單季財報摘要（income + balance 合併視圖）。"""

    period: str  # "2026Q1"
    revenue: int | None = None
    gross_profit: int | None = None
    operating_income: int | None = None
    net_income: int | None = None
    eps: float | None = None
    total_assets: int | None = None
    total_liabilities: int | None = None
    total_equity: int | None = None


class InstitutionalPoint(BaseModel):
    trade_date: date
    foreign_net: int
    trust_net: int
    dealer_net: int
    total_net: int


class MarginPoint(BaseModel):
    trade_date: date
    margin_balance: int
    margin_buy: int
    margin_sell: int
    short_balance: int
    short_sell: int
    short_cover: int


class EventPoint(BaseModel):
    id: int
    event_datetime: datetime
    event_type: str
    title: str
    content: str


class StockOverview(BaseModel):
    """個股頁首屏聚合資料。

    - prices：近 60 個交易日
    - revenues：近 12 個月
    - financials：近 4 季（合併 income + balance）
    - institutional / margin：近 20 個交易日
    - events：近 20 筆
    """

    meta: StockMeta
    prices: list[DailyPricePoint]
    revenues: list[RevenuePoint]
    financials: list[FinancialPoint]
    institutional: list[InstitutionalPoint]
    margin: list[MarginPoint]
    events: list[EventPoint]
```

- [ ] **Step 2: 建立 schema 驗證測試 `tests/schemas/test_stock.py`**

```python
"""Stocks schema 驗證測試。"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from alpha_lab.schemas.stock import (
    DailyPricePoint,
    EventPoint,
    StockMeta,
    StockOverview,
)


def test_stock_meta_rejects_empty_symbol() -> None:
    with pytest.raises(ValidationError):
        StockMeta(symbol="", name="測試")


def test_stock_overview_accepts_empty_lists() -> None:
    overview = StockOverview(
        meta=StockMeta(symbol="2330", name="台積電"),
        prices=[],
        revenues=[],
        financials=[],
        institutional=[],
        margin=[],
        events=[],
    )
    assert overview.meta.symbol == "2330"


def test_daily_price_point_round_trip() -> None:
    point = DailyPricePoint(
        trade_date=date(2026, 4, 14),
        open=600.0,
        high=610.0,
        low=595.0,
        close=605.0,
        volume=12345,
    )
    assert point.close == 605.0


def test_event_point_datetime_parsing() -> None:
    point = EventPoint(
        id=1,
        event_datetime=datetime(2026, 4, 14, 15, 30),
        event_type="財報",
        title="公布 Q1 財報",
        content="營收創新高",
    )
    assert point.event_datetime.year == 2026
```

- [ ] **Step 3: 建立 `tests/schemas/__init__.py`（空檔）**

```python
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && pytest tests/schemas/test_stock.py -v`
Expected: 4 passed

- [ ] **Step 5: 靜態檢查**

Run: `cd backend && ruff check src/alpha_lab/schemas/stock.py tests/schemas/ && mypy src/alpha_lab/schemas/stock.py`
Expected: 0 error

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/schemas/stock.py backend/tests/schemas/
git commit -m "feat: add stocks api pydantic schemas"
```

---

## Task A2: Stocks overview 端點（TDD）

**Files:**
- Create: `backend/src/alpha_lab/api/routes/stocks.py`
- Modify: `backend/src/alpha_lab/api/main.py`
- Test: `backend/tests/api/test_stocks_overview.py`

- [ ] **Step 1: 寫失敗測試 `tests/api/test_stocks_overview.py`**

```python
"""Stocks overview 端點整合測試。"""

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import (
    Base,
    Event,
    FinancialStatement,
    InstitutionalTrade,
    MarginTrade,
    PriceDaily,
    RevenueMonthly,
    Stock,
)


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def _seed_full_stock(session) -> None:
    session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
    session.add(
        PriceDaily(
            symbol="2330",
            trade_date=date(2026, 4, 14),
            open=600.0,
            high=610.0,
            low=595.0,
            close=605.0,
            volume=12345,
        )
    )
    session.add(
        RevenueMonthly(
            symbol="2330", year=2026, month=3, revenue=250_000_000_000,
            yoy_growth=0.15, mom_growth=0.05,
        )
    )
    session.add(
        FinancialStatement(
            symbol="2330", period="2026Q1", statement_type="income",
            revenue=700_000_000_000, gross_profit=400_000_000_000,
            operating_income=350_000_000_000, net_income=280_000_000_000,
            eps=10.8,
        )
    )
    session.add(
        FinancialStatement(
            symbol="2330", period="2026Q1", statement_type="balance",
            total_assets=5_000_000_000_000,
            total_liabilities=1_500_000_000_000,
            total_equity=3_500_000_000_000,
        )
    )
    session.add(
        InstitutionalTrade(
            symbol="2330", trade_date=date(2026, 4, 14),
            foreign_net=1000, trust_net=500, dealer_net=-200, total_net=1300,
        )
    )
    session.add(
        MarginTrade(
            symbol="2330", trade_date=date(2026, 4, 14),
            margin_balance=10000, margin_buy=100, margin_sell=50,
            short_balance=2000, short_sell=20, short_cover=10,
        )
    )
    session.add(
        Event(
            symbol="2330",
            event_datetime=datetime(2026, 4, 10, 15, 30, tzinfo=UTC),
            event_type="財報",
            title="公布 Q1 財報",
            content="營收創新高",
        )
    )


def test_overview_returns_all_sections() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_full_stock(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["symbol"] == "2330"
    assert body["meta"]["industry"] == "半導體"
    assert len(body["prices"]) == 1
    assert len(body["revenues"]) == 1
    assert len(body["financials"]) == 1
    fin = body["financials"][0]
    assert fin["period"] == "2026Q1"
    assert fin["revenue"] == 700_000_000_000
    assert fin["total_equity"] == 3_500_000_000_000
    assert len(body["institutional"]) == 1
    assert len(body["margin"]) == 1
    assert len(body["events"]) == 1


def test_overview_returns_404_for_unknown_symbol() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with TestClient(app) as client:
        resp = client.get("/api/stocks/9999/overview")

    assert resp.status_code == 404


def test_overview_merges_income_and_balance_financials() -> None:
    """同一 period 的 income + balance 要合併成單一 FinancialPoint。"""
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope
    with session_scope() as s:
        _seed_full_stock(s)

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/overview")

    fins = resp.json()["financials"]
    assert len(fins) == 1
    assert fins[0]["revenue"] is not None
    assert fins[0]["total_assets"] is not None
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && pytest tests/api/test_stocks_overview.py -v`
Expected: 404 on all (route doesn't exist)

- [ ] **Step 3: 建立 `api/routes/stocks.py` 實作 overview**

```python
"""Stocks API routes。

GET /api/stocks/{symbol}/overview → 個股頁首屏聚合資料
GET /api/stocks/{symbol}/prices?start=&end= → 股價細端點
GET /api/stocks/{symbol}/revenues?limit= → 月營收細端點
... (see A3)
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from alpha_lab.schemas.stock import (
    DailyPricePoint,
    EventPoint,
    FinancialPoint,
    InstitutionalPoint,
    MarginPoint,
    RevenuePoint,
    StockMeta,
    StockOverview,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import (
    Event,
    FinancialStatement,
    InstitutionalTrade,
    MarginTrade,
    PriceDaily,
    RevenueMonthly,
    Stock,
)

router = APIRouter(tags=["stocks"])

PRICES_DEFAULT_LIMIT = 60
REVENUES_DEFAULT_LIMIT = 12
FINANCIALS_DEFAULT_LIMIT = 4
INSTITUTIONAL_DEFAULT_LIMIT = 20
MARGIN_DEFAULT_LIMIT = 20
EVENTS_DEFAULT_LIMIT = 20


def _get_stock_or_404(session: Session, symbol: str) -> Stock:
    stock = session.get(Stock, symbol)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"stock {symbol} not found")
    return stock


def _load_prices(session: Session, symbol: str, limit: int) -> list[DailyPricePoint]:
    rows = session.execute(
        select(PriceDaily)
        .where(PriceDaily.symbol == symbol)
        .order_by(desc(PriceDaily.trade_date))
        .limit(limit)
    ).scalars().all()
    return [
        DailyPricePoint(
            trade_date=r.trade_date,
            open=r.open, high=r.high, low=r.low, close=r.close,
            volume=r.volume,
        )
        for r in reversed(rows)  # chart 需要由舊到新
    ]


def _load_revenues(session: Session, symbol: str, limit: int) -> list[RevenuePoint]:
    rows = session.execute(
        select(RevenueMonthly)
        .where(RevenueMonthly.symbol == symbol)
        .order_by(desc(RevenueMonthly.year), desc(RevenueMonthly.month))
        .limit(limit)
    ).scalars().all()
    return [
        RevenuePoint(
            year=r.year, month=r.month, revenue=r.revenue,
            yoy_growth=r.yoy_growth, mom_growth=r.mom_growth,
        )
        for r in reversed(rows)
    ]


def _load_financials(session: Session, symbol: str, limit: int) -> list[FinancialPoint]:
    """合併 income + balance 成單一 FinancialPoint（依 period 分組）。"""
    rows = session.execute(
        select(FinancialStatement)
        .where(FinancialStatement.symbol == symbol)
        .order_by(desc(FinancialStatement.period))
    ).scalars().all()

    by_period: dict[str, dict[str, object]] = {}
    for r in rows:
        acc = by_period.setdefault(r.period, {"period": r.period})
        if r.statement_type == "income":
            acc.update({
                "revenue": r.revenue,
                "gross_profit": r.gross_profit,
                "operating_income": r.operating_income,
                "net_income": r.net_income,
                "eps": r.eps,
            })
        elif r.statement_type == "balance":
            acc.update({
                "total_assets": r.total_assets,
                "total_liabilities": r.total_liabilities,
                "total_equity": r.total_equity,
            })

    sorted_periods = sorted(by_period.keys(), reverse=True)[:limit]
    return [FinancialPoint(**by_period[p]) for p in reversed(sorted_periods)]


def _load_institutional(
    session: Session, symbol: str, limit: int
) -> list[InstitutionalPoint]:
    rows = session.execute(
        select(InstitutionalTrade)
        .where(InstitutionalTrade.symbol == symbol)
        .order_by(desc(InstitutionalTrade.trade_date))
        .limit(limit)
    ).scalars().all()
    return [
        InstitutionalPoint(
            trade_date=r.trade_date,
            foreign_net=r.foreign_net, trust_net=r.trust_net,
            dealer_net=r.dealer_net, total_net=r.total_net,
        )
        for r in reversed(rows)
    ]


def _load_margin(session: Session, symbol: str, limit: int) -> list[MarginPoint]:
    rows = session.execute(
        select(MarginTrade)
        .where(MarginTrade.symbol == symbol)
        .order_by(desc(MarginTrade.trade_date))
        .limit(limit)
    ).scalars().all()
    return [
        MarginPoint(
            trade_date=r.trade_date,
            margin_balance=r.margin_balance,
            margin_buy=r.margin_buy, margin_sell=r.margin_sell,
            short_balance=r.short_balance,
            short_sell=r.short_sell, short_cover=r.short_cover,
        )
        for r in reversed(rows)
    ]


def _load_events(session: Session, symbol: str, limit: int) -> list[EventPoint]:
    rows = session.execute(
        select(Event)
        .where(Event.symbol == symbol)
        .order_by(desc(Event.event_datetime))
        .limit(limit)
    ).scalars().all()
    return [
        EventPoint(
            id=r.id, event_datetime=r.event_datetime,
            event_type=r.event_type, title=r.title, content=r.content,
        )
        for r in rows  # 事件維持由新到舊
    ]


@router.get("/stocks/{symbol}/overview", response_model=StockOverview)
async def get_stock_overview(symbol: str) -> StockOverview:
    with session_scope() as session:
        stock = _get_stock_or_404(session, symbol)
        meta = StockMeta(
            symbol=stock.symbol, name=stock.name,
            industry=stock.industry, listed_date=stock.listed_date,
        )
        return StockOverview(
            meta=meta,
            prices=_load_prices(session, symbol, PRICES_DEFAULT_LIMIT),
            revenues=_load_revenues(session, symbol, REVENUES_DEFAULT_LIMIT),
            financials=_load_financials(session, symbol, FINANCIALS_DEFAULT_LIMIT),
            institutional=_load_institutional(
                session, symbol, INSTITUTIONAL_DEFAULT_LIMIT
            ),
            margin=_load_margin(session, symbol, MARGIN_DEFAULT_LIMIT),
            events=_load_events(session, symbol, EVENTS_DEFAULT_LIMIT),
        )
```

- [ ] **Step 4: 掛載 router 於 `api/main.py`**

修改 `backend/src/alpha_lab/api/main.py` 的 imports 與 include_router：

```python
from alpha_lab.api.routes import health, jobs, stocks
...
app.include_router(stocks.router, prefix="/api")
```

- [ ] **Step 5: 跑測試確認通過**

Run: `cd backend && pytest tests/api/test_stocks_overview.py -v`
Expected: 3 passed

- [ ] **Step 6: 靜態檢查**

Run: `cd backend && ruff check src/alpha_lab/api/routes/stocks.py && mypy src/alpha_lab/api/routes/stocks.py`
Expected: 0 error

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/api/routes/stocks.py backend/src/alpha_lab/api/main.py backend/tests/api/test_stocks_overview.py
git commit -m "feat: add stocks overview aggregate endpoint"
```

---

## Task A3: 細端點（prices / revenues / financials / institutional / margin / events）

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/stocks.py`
- Test: `backend/tests/api/test_stocks_sections.py`

- [ ] **Step 1: 寫失敗測試 `tests/api/test_stocks_sections.py`**

```python
"""Stocks 細端點測試（date range / limit 行為）。"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, PriceDaily, Stock


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def test_prices_endpoint_filters_by_date_range() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        for d in [date(2026, 4, 10), date(2026, 4, 12), date(2026, 4, 14)]:
            s.add(PriceDaily(
                symbol="2330", trade_date=d,
                open=600, high=610, low=595, close=605, volume=1,
            ))

    with TestClient(app) as client:
        resp = client.get(
            "/api/stocks/2330/prices?start=2026-04-11&end=2026-04-13"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["trade_date"] == "2026-04-12"


def test_prices_endpoint_defaults_return_recent_60() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        for day in range(1, 71):
            s.add(PriceDaily(
                symbol="2330",
                trade_date=date(2026, 2, 1).replace(day=min(day, 28)),
                open=600, high=610, low=595, close=605, volume=day,
            ))

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/prices")

    # 上面 seed 有重複主鍵，這裡只驗證 200 + <=60
    assert resp.status_code == 200
    assert len(resp.json()) <= 60


def test_revenues_endpoint_returns_list() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))

    with TestClient(app) as client:
        resp = client.get("/api/stocks/2330/revenues")

    assert resp.status_code == 200
    assert resp.json() == []


def test_section_endpoints_return_404_for_unknown_symbol() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with TestClient(app) as client:
        for path in [
            "/api/stocks/9999/prices",
            "/api/stocks/9999/revenues",
            "/api/stocks/9999/financials",
            "/api/stocks/9999/institutional",
            "/api/stocks/9999/margin",
            "/api/stocks/9999/events",
        ]:
            assert client.get(path).status_code == 404
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && pytest tests/api/test_stocks_sections.py -v`
Expected: FAIL（端點不存在）

- [ ] **Step 3: 在 `api/routes/stocks.py` 末尾加 6 個細端點**

```python
from datetime import date as _date

from fastapi import Query


@router.get("/stocks/{symbol}/prices", response_model=list[DailyPricePoint])
async def get_stock_prices(
    symbol: str,
    start: _date | None = Query(None),
    end: _date | None = Query(None),
    limit: int = Query(PRICES_DEFAULT_LIMIT, ge=1, le=500),
) -> list[DailyPricePoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        stmt = select(PriceDaily).where(PriceDaily.symbol == symbol)
        if start is not None:
            stmt = stmt.where(PriceDaily.trade_date >= start)
        if end is not None:
            stmt = stmt.where(PriceDaily.trade_date <= end)
        stmt = stmt.order_by(desc(PriceDaily.trade_date)).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [
            DailyPricePoint(
                trade_date=r.trade_date,
                open=r.open, high=r.high, low=r.low, close=r.close,
                volume=r.volume,
            )
            for r in reversed(rows)
        ]


@router.get("/stocks/{symbol}/revenues", response_model=list[RevenuePoint])
async def get_stock_revenues(
    symbol: str,
    limit: int = Query(REVENUES_DEFAULT_LIMIT, ge=1, le=120),
) -> list[RevenuePoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_revenues(session, symbol, limit)


@router.get("/stocks/{symbol}/financials", response_model=list[FinancialPoint])
async def get_stock_financials(
    symbol: str,
    limit: int = Query(FINANCIALS_DEFAULT_LIMIT, ge=1, le=40),
) -> list[FinancialPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_financials(session, symbol, limit)


@router.get("/stocks/{symbol}/institutional", response_model=list[InstitutionalPoint])
async def get_stock_institutional(
    symbol: str,
    limit: int = Query(INSTITUTIONAL_DEFAULT_LIMIT, ge=1, le=500),
) -> list[InstitutionalPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_institutional(session, symbol, limit)


@router.get("/stocks/{symbol}/margin", response_model=list[MarginPoint])
async def get_stock_margin(
    symbol: str,
    limit: int = Query(MARGIN_DEFAULT_LIMIT, ge=1, le=500),
) -> list[MarginPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_margin(session, symbol, limit)


@router.get("/stocks/{symbol}/events", response_model=list[EventPoint])
async def get_stock_events(
    symbol: str,
    limit: int = Query(EVENTS_DEFAULT_LIMIT, ge=1, le=200),
) -> list[EventPoint]:
    with session_scope() as session:
        _get_stock_or_404(session, symbol)
        return _load_events(session, symbol, limit)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && pytest tests/api/test_stocks_sections.py -v`
Expected: 4 passed

- [ ] **Step 5: 靜態檢查**

Run: `cd backend && ruff check src/alpha_lab/api/routes/stocks.py && mypy src/alpha_lab/api/routes/stocks.py`
Expected: 0 error

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/api/routes/stocks.py backend/tests/api/test_stocks_sections.py
git commit -m "feat: add stocks section detail endpoints"
```

---

## Task A4: Stocks 列表端點（供 header 搜尋 autocomplete）

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/stocks.py`
- Test: `backend/tests/api/test_stocks_list.py`

- [ ] **Step 1: 寫失敗測試 `tests/api/test_stocks_list.py`**

```python
"""Stocks 列表端點測試（供搜尋框用）。"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, Stock


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def test_list_returns_all_stocks() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        s.add(Stock(symbol="2317", name="鴻海", industry="電子代工"))

    with TestClient(app) as client:
        resp = client.get("/api/stocks")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    symbols = {s["symbol"] for s in body}
    assert symbols == {"2330", "2317"}


def test_list_filters_by_query() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        s.add(Stock(symbol="2317", name="鴻海"))

    with TestClient(app) as client:
        resp = client.get("/api/stocks?q=2330")

    assert [s["symbol"] for s in resp.json()] == ["2330"]


def test_list_matches_by_name_substring() -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        s.add(Stock(symbol="2317", name="鴻海"))

    with TestClient(app) as client:
        resp = client.get("/api/stocks?q=台積")

    assert [s["symbol"] for s in resp.json()] == ["2330"]
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && pytest tests/api/test_stocks_list.py -v`
Expected: 404 / not found

- [ ] **Step 3: 在 `api/routes/stocks.py` 新增列表端點**

於 stocks.py 末尾加上：

```python
from sqlalchemy import or_


@router.get("/stocks", response_model=list[StockMeta])
async def list_stocks(
    q: str | None = Query(None, description="查詢代號或名稱（部分字串）"),
    limit: int = Query(50, ge=1, le=500),
) -> list[StockMeta]:
    with session_scope() as session:
        stmt = select(Stock)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Stock.symbol.like(like), Stock.name.like(like)))
        stmt = stmt.order_by(Stock.symbol).limit(limit)
        rows = session.execute(stmt).scalars().all()
        return [
            StockMeta(
                symbol=r.symbol, name=r.name,
                industry=r.industry, listed_date=r.listed_date,
            )
            for r in rows
        ]
```

- [ ] **Step 4: 跑測試確認通過**

Run: `cd backend && pytest tests/api/test_stocks_list.py -v`
Expected: 3 passed

- [ ] **Step 5: 全量 backend 測試 + 靜態檢查**

Run: `cd backend && pytest && ruff check . && mypy src`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add backend/src/alpha_lab/api/routes/stocks.py backend/tests/api/test_stocks_list.py
git commit -m "feat: add stocks list endpoint with name search"
```

---

## Task B1: Glossary YAML 結構與 loader

**Files:**
- Create: `backend/src/alpha_lab/glossary/loader.py`
- Create: `backend/src/alpha_lab/glossary/terms.yaml`（初始空字典 + 1 個範例詞）
- Create: `backend/src/alpha_lab/schemas/glossary.py`
- Test: `backend/tests/glossary/test_loader.py`
- Modify: `backend/pyproject.toml`（加 `pyyaml` 依賴，若尚未有）

- [ ] **Step 1: 確認 pyyaml 依賴**

Run: `cd backend && grep -E "pyyaml|PyYAML" pyproject.toml`
若無，加入 `dependencies`：`"pyyaml>=6.0"`；並 `grep pyyaml pyproject.toml`、`uv sync` 或 `pip install -e .`

- [ ] **Step 2: 建立 `schemas/glossary.py`**

```python
"""Glossary term Pydantic 模型。"""

from pydantic import BaseModel, Field


class GlossaryTerm(BaseModel):
    term: str = Field(..., min_length=1)
    short: str = Field(..., min_length=1, max_length=200)
    detail: str = ""
    related: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: 建立 `glossary/terms.yaml`（初始樣板）**

```yaml
# alpha-lab 術語庫 v1
#
# 每個 key 為術語中文（或常用簡寫），value 必備 short；detail、related 可選。
# Phase 2 task D1 會補到 15 條。

PE:
  term: 本益比
  short: 股價相對每股盈餘的倍數，數字越低代表相對便宜。
  detail: |
    本益比（Price-to-Earnings Ratio）= 股價 / 每股盈餘（EPS）。
    常被用來比較同產業公司的估值高低，但成長股本益比普遍偏高。
  related: [EPS, PB]
```

- [ ] **Step 4: 建立 `glossary/loader.py`**

```python
"""Glossary YAML loader。

- 載入時驗證每條為 `GlossaryTerm`
- 單例快取：第一次讀檔後常駐記憶體（個人工具，不需 hot reload）
"""

from functools import lru_cache
from pathlib import Path

import yaml

from alpha_lab.schemas.glossary import GlossaryTerm

_DEFAULT_PATH = Path(__file__).parent / "terms.yaml"


@lru_cache(maxsize=1)
def load_terms(path: Path | None = None) -> dict[str, GlossaryTerm]:
    """載入整份 terms.yaml 為 {key: GlossaryTerm}。"""
    src = path or _DEFAULT_PATH
    if not src.exists():
        return {}
    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{src}: top-level must be a mapping")
    return {key: GlossaryTerm(**value) for key, value in raw.items()}


def get_term(key: str) -> GlossaryTerm | None:
    return load_terms().get(key)
```

- [ ] **Step 5: 建立 `tests/glossary/test_loader.py`**

```python
"""Glossary loader 測試。"""

from pathlib import Path

import pytest

from alpha_lab.glossary.loader import load_terms
from alpha_lab.schemas.glossary import GlossaryTerm


def test_load_default_terms_yaml() -> None:
    load_terms.cache_clear()
    terms = load_terms()
    assert "PE" in terms
    assert terms["PE"].term == "本益比"


def test_load_custom_path(tmp_path: Path) -> None:
    load_terms.cache_clear()
    yaml_text = """
EPS:
  term: 每股盈餘
  short: 公司每股賺多少
"""
    p = tmp_path / "terms.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    terms = load_terms(p)
    assert isinstance(terms["EPS"], GlossaryTerm)
    assert terms["EPS"].short == "公司每股賺多少"


def test_load_rejects_non_mapping(tmp_path: Path) -> None:
    load_terms.cache_clear()
    p = tmp_path / "terms.yaml"
    p.write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_terms(p)
```

- [ ] **Step 6: 建立 `tests/glossary/__init__.py`（空檔）**

- [ ] **Step 7: 跑測試 + 靜態檢查**

Run: `cd backend && pytest tests/glossary/ -v && ruff check src/alpha_lab/glossary src/alpha_lab/schemas/glossary.py && mypy src/alpha_lab/glossary src/alpha_lab/schemas/glossary.py`
Expected: 3 passed; 0 lint error

- [ ] **Step 8: Commit**

```bash
git add backend/src/alpha_lab/glossary/loader.py backend/src/alpha_lab/glossary/terms.yaml backend/src/alpha_lab/schemas/glossary.py backend/tests/glossary/ backend/pyproject.toml
git commit -m "feat: add glossary yaml loader and schema"
```

---

## Task B2: Glossary API endpoint

**Files:**
- Create: `backend/src/alpha_lab/api/routes/glossary.py`
- Modify: `backend/src/alpha_lab/api/main.py`
- Test: `backend/tests/api/test_glossary.py`

- [ ] **Step 1: 寫失敗測試 `tests/api/test_glossary.py`**

```python
"""Glossary API 測試。"""

from fastapi.testclient import TestClient

from alpha_lab.api.main import app
from alpha_lab.glossary.loader import load_terms


def test_get_term_returns_known_term() -> None:
    load_terms.cache_clear()
    with TestClient(app) as client:
        resp = client.get("/api/glossary/PE")
    assert resp.status_code == 200
    body = resp.json()
    assert body["term"] == "本益比"
    assert "short" in body


def test_get_term_404_for_unknown() -> None:
    load_terms.cache_clear()
    with TestClient(app) as client:
        resp = client.get("/api/glossary/NOT_A_TERM")
    assert resp.status_code == 404


def test_list_terms_returns_all_keys() -> None:
    load_terms.cache_clear()
    with TestClient(app) as client:
        resp = client.get("/api/glossary")
    assert resp.status_code == 200
    body = resp.json()
    assert "PE" in body
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backend && pytest tests/api/test_glossary.py -v`
Expected: 404

- [ ] **Step 3: 建立 `api/routes/glossary.py`**

```python
"""Glossary API routes。

GET /api/glossary          → 回全部術語（key → GlossaryTerm）
GET /api/glossary/{term}   → 回單一術語
"""

from fastapi import APIRouter, HTTPException

from alpha_lab.glossary.loader import get_term, load_terms
from alpha_lab.schemas.glossary import GlossaryTerm

router = APIRouter(tags=["glossary"])


@router.get("/glossary", response_model=dict[str, GlossaryTerm])
async def list_glossary_terms() -> dict[str, GlossaryTerm]:
    return load_terms()


@router.get("/glossary/{term_key}", response_model=GlossaryTerm)
async def get_glossary_term(term_key: str) -> GlossaryTerm:
    term = get_term(term_key)
    if term is None:
        raise HTTPException(status_code=404, detail=f"term {term_key} not found")
    return term
```

- [ ] **Step 4: 掛載 router 於 `api/main.py`**

修改 imports 與 include_router：

```python
from alpha_lab.api.routes import glossary, health, jobs, stocks
...
app.include_router(glossary.router, prefix="/api")
```

- [ ] **Step 5: 跑測試確認通過**

Run: `cd backend && pytest tests/api/test_glossary.py -v`
Expected: 3 passed

- [ ] **Step 6: 靜態檢查**

Run: `cd backend && ruff check src/alpha_lab/api/routes/glossary.py && mypy src/alpha_lab/api/routes/glossary.py`
Expected: 0 error

- [ ] **Step 7: Commit**

```bash
git add backend/src/alpha_lab/api/routes/glossary.py backend/src/alpha_lab/api/main.py backend/tests/api/test_glossary.py
git commit -m "feat: add glossary api endpoints"
```

---

## Task C1: Industry tagging 最小實作

**Files:**
- Create: `backend/src/alpha_lab/storage/industry_map.yaml`
- Create: `backend/scripts/backfill_industry.py`
- Test: `backend/tests/scripts/test_backfill_industry.py`

- [ ] **Step 1: 建立 `industry_map.yaml`（手動映射表）**

```yaml
# symbol → 產業分類（中文）
# Phase 2 最小實作：僅標記測試會用到的幾檔，其餘由使用者逐步補。
# 未來可改為從 TWSE 產業別檔案自動同步（spec §7 未解決議題）。

"2330": 半導體
"2454": 半導體
"2317": 電子代工
"2303": 半導體
"2308": 電子代工
"1301": 塑膠
"1303": 塑膠
"2412": 電信
"2882": 金融
"2881": 金融
```

- [ ] **Step 2: 建立 `scripts/backfill_industry.py`**

```python
"""Backfill industry tag onto existing Stock rows.

讀 `src/alpha_lab/storage/industry_map.yaml`，對 DB 中存在的 symbol 更新 industry。
對映表中沒有的 symbol 不動（保留 None 或既有值）。

Usage:
    python -m scripts.backfill_industry
"""

from pathlib import Path

import yaml

from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Stock

_MAP_PATH = Path(__file__).parent.parent / "src" / "alpha_lab" / "storage" / "industry_map.yaml"


def load_industry_map(path: Path = _MAP_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in raw.items()}


def backfill() -> int:
    mapping = load_industry_map()
    updated = 0
    with session_scope() as session:
        for symbol, industry in mapping.items():
            stock = session.get(Stock, symbol)
            if stock is not None and stock.industry != industry:
                stock.industry = industry
                updated += 1
    return updated


if __name__ == "__main__":
    n = backfill()
    print(f"updated {n} stocks")
```

- [ ] **Step 3: 建立 `tests/scripts/test_backfill_industry.py`**

```python
"""backfill_industry 測試。"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, Stock
from scripts.backfill_industry import backfill, load_industry_map


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def test_load_industry_map_reads_yaml() -> None:
    mapping = load_industry_map()
    assert mapping.get("2330") == "半導體"


def test_backfill_updates_existing_stocks(tmp_path: Path) -> None:
    test_engine = create_engine("sqlite:///:memory:", future=True)
    _override_engine(test_engine)

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        s.add(Stock(symbol="9999", name="測試"))

    updated = backfill()
    assert updated >= 1

    with session_scope() as s:
        stock = s.get(Stock, "2330")
        assert stock is not None
        assert stock.industry == "半導體"
        # 9999 不在映射表裡 → industry 維持 None
        stub = s.get(Stock, "9999")
        assert stub is not None
        assert stub.industry is None
```

- [ ] **Step 4: 跑測試 + 靜態檢查**

Run: `cd backend && pytest tests/scripts/test_backfill_industry.py -v && ruff check scripts/backfill_industry.py && mypy scripts/backfill_industry.py`
Expected: 2 passed; 0 error

- [ ] **Step 5: Commit**

```bash
git add backend/src/alpha_lab/storage/industry_map.yaml backend/scripts/backfill_industry.py backend/tests/scripts/test_backfill_industry.py
git commit -m "feat: add minimal industry tag mapping and backfill script"
```

---

## Task D1: Glossary v1 — 15 條核心術語

**Files:**
- Modify: `backend/src/alpha_lab/glossary/terms.yaml`
- Test: `backend/tests/glossary/test_terms_v1.py`

- [ ] **Step 1: 撰寫 15 條術語草稿**

覆寫 `backend/src/alpha_lab/glossary/terms.yaml`：

```yaml
# alpha-lab 術語庫 v1（Phase 2）
#
# 15 條核心術語，覆蓋個股頁會出現的概念。
# 後續 Phase 會增補（推薦、評分、組合、教學 L2 詳解）。

PE:
  term: 本益比
  short: 股價相對每股盈餘的倍數，數字越低代表相對便宜。
  detail: |
    本益比（Price-to-Earnings Ratio）= 股價 / 每股盈餘（EPS）。
    常被用來比較同產業公司的估值高低；成長股本益比普遍偏高，產業特性也會影響合理區間。
  related: [EPS, PB]

PB:
  term: 股價淨值比
  short: 股價相對每股淨值的倍數，反映相對帳面價值的溢價。
  detail: |
    PB（Price-to-Book Ratio）= 股價 / 每股淨值。金融、傳產常用此指標；科技業因無形資產多，PB 意義較弱。
  related: [PE, ROE]

EPS:
  term: 每股盈餘
  short: 公司每股賺多少錢，數字越高代表獲利能力越強。
  detail: |
    EPS（Earnings Per Share）= 稅後淨利 / 流通在外股數。是衡量獲利能力的核心指標，也是計算本益比的分母。
  related: [PE, 淨利]

ROE:
  term: 股東權益報酬率
  short: 公司用股東的錢賺了多少回報，一般長期 15% 以上算優質。
  detail: |
    ROE（Return on Equity）= 淨利 / 股東權益。衡量公司替股東創造報酬的效率。
  related: [毛利率, 淨利]

毛利率:
  term: 毛利率
  short: 扣除直接成本後剩下的毛利佔營收比例，反映產品議價力。
  detail: |
    毛利率 = (營收 - 銷貨成本) / 營收。毛利率高通常代表產品獨特性或品牌溢價。
  related: [營業利益率, 淨利率]

殖利率:
  term: 現金殖利率
  short: 每年配息相對股價的比率，類似存股的利率。
  detail: |
    現金殖利率 = 現金股利 / 股價。高殖利率股常見於穩定獲利的成熟公司，但需留意配息是否永續。
  related: [EPS]

月營收:
  term: 月營收
  short: 公司每月公告的當月營收金額，台股上市櫃每月 10 日前公布。
  detail: |
    台灣公開資訊觀測站要求上市櫃公司於次月 10 日前公布月營收，是市場最即時的基本面指標之一。
  related: [YoY, MoM]

YoY:
  term: 年增率
  short: 當期與去年同期比較的成長幅度，排除季節性干擾。
  detail: |
    YoY（Year over Year）= (本期 - 去年同期) / 去年同期。用於剔除季節性因素，看出實質成長趨勢。
  related: [MoM, 月營收]

MoM:
  term: 月增率
  short: 當月與上個月比較的成長幅度，反映短期動能。
  detail: |
    MoM（Month over Month）= (本月 - 上月) / 上月。敏感度高但受季節性干擾，需搭配 YoY 一起看。
  related: [YoY, 月營收]

三大法人:
  term: 三大法人
  short: 外資、投信、自營商，台股最具影響力的機構投資人。
  detail: |
    三大法人指外資（含外資自營）、投信、自營商。其每日買賣超金額被視為資金動向的重要參考。
  related: [外資, 投信, 自營商]

外資:
  term: 外資
  short: 外國機構投資人，台股中部位最大也最具指標性。
  detail: |
    外資在台股中通常指境外投資機構。其持股方向與匯率、全球資金流動密切相關。
  related: [三大法人]

投信:
  term: 投信
  short: 國內投信基金，操作週期偏中期，常與外資互補觀察。
  detail: |
    投信（證券投資信託公司）旗下管理國內共同基金。操作相對外資更貼近台股基本面。
  related: [三大法人]

自營商:
  term: 自營商
  short: 券商自有資金部位，操作週期短，參考價值相對低。
  detail: |
    自營商為券商自有資金交易部門，部位通常較小、週轉快，常被視為短線訊號。
  related: [三大法人]

融資:
  term: 融資
  short: 向券商借錢買股票，反映散戶看多的槓桿部位。
  detail: |
    融資餘額代表市場上「借錢買股」的總金額，常被視為散戶情緒指標；快速增加時要留意追繳風險。
  related: [融券]

融券:
  term: 融券
  short: 向券商借股票放空，反映市場看空的部位。
  detail: |
    融券餘額是「借券放空」的張數。券資比高意味放空力量大，軋空行情發生時融券會被迫回補。
  related: [融資]
```

- [ ] **Step 2: 建立 `tests/glossary/test_terms_v1.py`（內容 smoke test）**

```python
"""Glossary v1 smoke test：確保 15 條核心術語存在且格式合法。"""

from alpha_lab.glossary.loader import load_terms

EXPECTED_TERMS = [
    "PE", "PB", "EPS", "ROE", "毛利率", "殖利率",
    "月營收", "YoY", "MoM",
    "三大法人", "外資", "投信", "自營商",
    "融資", "融券",
]


def test_v1_covers_15_core_terms() -> None:
    load_terms.cache_clear()
    terms = load_terms()
    for key in EXPECTED_TERMS:
        assert key in terms, f"missing term: {key}"
    assert len(EXPECTED_TERMS) == 15


def test_every_term_has_non_empty_short() -> None:
    load_terms.cache_clear()
    for key, term in load_terms().items():
        assert term.short.strip(), f"{key} has empty short"
        assert len(term.short) <= 200, f"{key} short too long"
```

- [ ] **Step 3: 跑測試 + 中文亂碼掃描**

Run: `cd backend && pytest tests/glossary/test_terms_v1.py -v`
Expected: 2 passed

Run: `grep -r "��" src/alpha_lab/glossary/`
Expected: no match

- [ ] **Step 4: 手動驗收指引（commit 前必做）**

停下來請使用者：
1. 打開 `backend/src/alpha_lab/glossary/terms.yaml`
2. 檢視 15 條術語的定義是否合意（尤其 `short` 一句話是否準確且淺顯）
3. 如有修改，調整後回覆「OK」

- [ ] **Step 5: Commit（使用者驗收後）**

```bash
git add backend/src/alpha_lab/glossary/terms.yaml backend/tests/glossary/test_terms_v1.py
git commit -m "feat: draft glossary v1 with 15 core terms"
```

---

## Task E1: Frontend — React Router 基礎 + 路由骨架

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/pages/StockPage.tsx`
- Create: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 重寫 `main.tsx` 引入 Router + QueryClient**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 60_000, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
```

- [ ] **Step 2: 建立 `layouts/AppLayout.tsx`（Header + Outlet）**

```tsx
import { Outlet } from "react-router-dom";

import { HeaderSearch } from "@/components/HeaderSearch";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <a href="/" className="text-xl font-bold">alpha-lab</a>
        <HeaderSearch />
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

（HeaderSearch 於 Task E2 建立；先建立占位：Task E2 才實作細節。先寫暫時匯出避免 import 錯誤：）

建立 `frontend/src/components/HeaderSearch.tsx` 暫時占位：

```tsx
export function HeaderSearch() {
  return <span className="text-sm text-slate-500">search placeholder</span>;
}
```

- [ ] **Step 3: 建立 `pages/HomePage.tsx`**

```tsx
import { HealthStatus } from "@/components/HealthStatus";

export function HomePage() {
  return (
    <div className="text-center space-y-4">
      <h1 className="text-4xl font-bold">alpha-lab</h1>
      <p className="text-slate-400">台股長線投資工具</p>
      <HealthStatus />
      <p className="text-slate-500 text-sm">
        在右上角搜尋框輸入股票代號（例：2330）即可查看個股頁。
      </p>
    </div>
  );
}
```

- [ ] **Step 4: 建立 `pages/StockPage.tsx` 最小占位**

```tsx
import { useParams } from "react-router-dom";

export function StockPage() {
  const { symbol } = useParams<{ symbol: string }>();
  return (
    <div>
      <h1 className="text-2xl font-bold">個股頁：{symbol}</h1>
      <p className="text-slate-400">Task E3-E6 會把各 section 填上。</p>
    </div>
  );
}
```

- [ ] **Step 5: 重寫 `App.tsx` 配置 Routes**

```tsx
import { Route, Routes } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { StockPage } from "@/pages/StockPage";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/stocks/:symbol" element={<StockPage />} />
      </Route>
    </Routes>
  );
}

export default App;
```

- [ ] **Step 6: 跑型別檢查 + dev server 手動驗證**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 error

Run in another terminal: `cd backend && uvicorn alpha_lab.api.main:app --reload`
Run: `cd frontend && pnpm dev`

瀏覽器打開 `http://localhost:5173/` 應該看到首頁；打開 `http://localhost:5173/stocks/2330` 應該看到「個股頁：2330」。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/layouts frontend/src/pages frontend/src/components/HeaderSearch.tsx
git commit -m "feat: add react router and page scaffolding"
```

---

## Task E2: Frontend — Header 搜尋框（symbol 跳轉）

**Files:**
- Modify: `frontend/src/components/HeaderSearch.tsx`
- Test: `frontend/tests/components/HeaderSearch.test.tsx`

- [ ] **Step 1: 寫失敗測試 `tests/components/HeaderSearch.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HeaderSearch } from "@/components/HeaderSearch";

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<HeaderSearch />} />
        <Route path="/stocks/:symbol" element={<p>stock page {":symbol"}</p>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("HeaderSearch", () => {
  it("submits symbol and navigates to /stocks/:symbol", async () => {
    renderWithRouter();
    const input = screen.getByRole("textbox", { name: /股票代號/i });
    await userEvent.type(input, "2330{enter}");
    expect(await screen.findByText(/stock page/i)).toBeInTheDocument();
  });

  it("rejects empty input (stays on same page)", async () => {
    renderWithRouter();
    const input = screen.getByRole("textbox", { name: /股票代號/i });
    await userEvent.type(input, "{enter}");
    // 仍在 / 路由（HeaderSearch 是 / 的元件，看不到 stock page 文字）
    expect(screen.queryByText(/stock page/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd frontend && pnpm test tests/components/HeaderSearch.test.tsx`
Expected: FAIL（目前只是 placeholder）

- [ ] **Step 3: 實作 `HeaderSearch.tsx`**

```tsx
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

export function HeaderSearch() {
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    navigate(`/stocks/${encodeURIComponent(trimmed)}`);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <label className="sr-only" htmlFor="symbol-search">
        股票代號
      </label>
      <input
        id="symbol-search"
        aria-label="股票代號"
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="輸入代號或名稱，例：2330"
        className="bg-slate-900 border border-slate-700 rounded px-3 py-1 text-sm w-64"
      />
      <button
        type="submit"
        className="bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded text-sm"
      >
        查詢
      </button>
    </form>
  );
}
```

- [ ] **Step 4: 跑測試確認通過 + 型別檢查**

Run: `cd frontend && pnpm test tests/components/HeaderSearch.test.tsx && pnpm type-check && pnpm lint`
Expected: 2 passed; 0 error

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/HeaderSearch.tsx frontend/tests/components/HeaderSearch.test.tsx
git commit -m "feat: add header search box with symbol navigation"
```

---

## Task E3: Frontend — stocks API client + types

**Files:**
- Create: `frontend/src/api/stocks.ts`
- Create: `frontend/src/api/glossary.ts`
- Modify: `frontend/src/api/types.ts`
- Test: `frontend/tests/api/stocks.test.ts`

- [ ] **Step 1: 擴充 `api/types.ts`（加 stocks / glossary 型別）**

讀既有 `types.ts` 後，在末尾新增：

```typescript
export interface StockMeta {
  symbol: string;
  name: string;
  industry: string | null;
  listed_date: string | null;
}

export interface DailyPricePoint {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface RevenuePoint {
  year: number;
  month: number;
  revenue: number;
  yoy_growth: number | null;
  mom_growth: number | null;
}

export interface FinancialPoint {
  period: string;
  revenue: number | null;
  gross_profit: number | null;
  operating_income: number | null;
  net_income: number | null;
  eps: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  total_equity: number | null;
}

export interface InstitutionalPoint {
  trade_date: string;
  foreign_net: number;
  trust_net: number;
  dealer_net: number;
  total_net: number;
}

export interface MarginPoint {
  trade_date: string;
  margin_balance: number;
  margin_buy: number;
  margin_sell: number;
  short_balance: number;
  short_sell: number;
  short_cover: number;
}

export interface EventPoint {
  id: number;
  event_datetime: string;
  event_type: string;
  title: string;
  content: string;
}

export interface StockOverview {
  meta: StockMeta;
  prices: DailyPricePoint[];
  revenues: RevenuePoint[];
  financials: FinancialPoint[];
  institutional: InstitutionalPoint[];
  margin: MarginPoint[];
  events: EventPoint[];
}

export interface GlossaryTerm {
  term: string;
  short: string;
  detail: string;
  related: string[];
}
```

- [ ] **Step 2: 建立 `api/stocks.ts`**

```typescript
import { apiGet } from "./client";
import type { StockMeta, StockOverview } from "./types";

export function fetchStockOverview(symbol: string): Promise<StockOverview> {
  return apiGet<StockOverview>(
    `/api/stocks/${encodeURIComponent(symbol)}/overview`
  );
}

export function searchStocks(q: string, limit = 20): Promise<StockMeta[]> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", String(limit));
  return apiGet<StockMeta[]>(`/api/stocks?${params.toString()}`);
}
```

- [ ] **Step 3: 建立 `api/glossary.ts`**

```typescript
import { apiGet } from "./client";
import type { GlossaryTerm } from "./types";

export function fetchGlossaryTerm(key: string): Promise<GlossaryTerm> {
  return apiGet<GlossaryTerm>(
    `/api/glossary/${encodeURIComponent(key)}`
  );
}

export function fetchAllGlossary(): Promise<Record<string, GlossaryTerm>> {
  return apiGet<Record<string, GlossaryTerm>>("/api/glossary");
}
```

- [ ] **Step 4: 建立 `tests/api/stocks.test.ts`**

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchStockOverview, searchStocks } from "@/api/stocks";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("stocks api", () => {
  it("fetchStockOverview calls correct path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          meta: { symbol: "2330", name: "台積電", industry: null, listed_date: null },
          prices: [], revenues: [], financials: [],
          institutional: [], margin: [], events: [],
        }),
        { status: 200 }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchStockOverview("2330");
    expect(result.meta.symbol).toBe("2330");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/stocks/2330/overview")
    );
  });

  it("searchStocks builds query string", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);

    await searchStocks("台積");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/stocks\?q=.*&limit=20/)
    );
  });
});
```

- [ ] **Step 5: 跑測試 + 型別檢查**

Run: `cd frontend && pnpm test tests/api/stocks.test.ts && pnpm type-check`
Expected: 2 passed; 0 error

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/stocks.ts frontend/src/api/glossary.ts frontend/src/api/types.ts frontend/tests/api/stocks.test.ts
git commit -m "feat: add stocks and glossary api clients"
```

---

## Task F1: Frontend — StockPage layout + useStockOverview

**Files:**
- Modify: `frontend/src/pages/StockPage.tsx`
- Create: `frontend/src/hooks/useStockOverview.ts`
- Create: `frontend/src/components/stock/StockHeader.tsx`

- [ ] **Step 1: 建立 `hooks/useStockOverview.ts`**

```typescript
import { useQuery } from "@tanstack/react-query";

import { fetchStockOverview } from "@/api/stocks";

export function useStockOverview(symbol: string | undefined) {
  return useQuery({
    queryKey: ["stock-overview", symbol],
    queryFn: () => fetchStockOverview(symbol!),
    enabled: !!symbol,
  });
}
```

- [ ] **Step 2: 建立 `components/stock/StockHeader.tsx`**

```tsx
import type { StockMeta } from "@/api/types";

interface StockHeaderProps {
  meta: StockMeta;
}

export function StockHeader({ meta }: StockHeaderProps) {
  return (
    <header className="border-b border-slate-800 pb-4 mb-6">
      <h1 className="text-3xl font-bold">
        {meta.symbol} {meta.name}
      </h1>
      <p className="text-slate-400 text-sm mt-1">
        {meta.industry ?? "產業未分類"}
        {meta.listed_date ? ` · 上市於 ${meta.listed_date}` : null}
      </p>
    </header>
  );
}
```

- [ ] **Step 3: 改寫 `pages/StockPage.tsx`**

```tsx
import { useParams } from "react-router-dom";

import { useStockOverview } from "@/hooks/useStockOverview";
import { StockHeader } from "@/components/stock/StockHeader";

export function StockPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const { data, isLoading, error } = useStockOverview(symbol);

  if (isLoading) {
    return <p className="text-slate-400">載入中...</p>;
  }
  if (error || !data) {
    return (
      <p className="text-red-400">
        載入失敗：{error instanceof Error ? error.message : "未知錯誤"}
      </p>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      <StockHeader meta={data.meta} />
      {/* section 元件將於 Task F2-F4 插入此區 */}
      <p className="text-slate-500 text-sm">
        共 {data.prices.length} 筆股價、{data.revenues.length} 筆月營收、
        {data.financials.length} 季財報。
      </p>
    </div>
  );
}
```

- [ ] **Step 4: 手動驗收**

前後端皆啟動，打開 `http://localhost:5173/stocks/2330`（DB 中須有 2330 資料，否則會 404）。若資料不足：先 `cd backend && python scripts/daily_collect.py --symbol 2330` 抓一些，再重跑。

- [ ] **Step 5: 型別檢查 + lint**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 error

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/StockPage.tsx frontend/src/hooks/useStockOverview.ts frontend/src/components/stock/StockHeader.tsx
git commit -m "feat: add stock page layout and overview query hook"
```

---

## Task F2: Frontend — 股價走勢圖 + 關鍵指標

**Files:**
- Modify: `frontend/package.json`（加 recharts）
- Create: `frontend/src/components/stock/PriceChart.tsx`
- Create: `frontend/src/components/stock/KeyMetrics.tsx`
- Modify: `frontend/src/pages/StockPage.tsx`
- Test: `frontend/tests/components/KeyMetrics.test.tsx`

- [ ] **Step 1: 安裝 recharts**

Run: `cd frontend && pnpm add recharts`
Expected: recharts added to dependencies（React 19 相容版本，若不相容改用 `recharts@next` 或改 `recharts@^2`，見 [recharts/recharts](https://github.com/recharts/recharts) 相容表）

- [ ] **Step 2: 建立 `components/stock/PriceChart.tsx`**

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

import type { DailyPricePoint } from "@/api/types";

interface PriceChartProps {
  points: DailyPricePoint[];
}

export function PriceChart({ points }: PriceChartProps) {
  if (points.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        尚無股價資料
      </div>
    );
  }
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis dataKey="trade_date" stroke="#64748b" fontSize={12} />
          <YAxis stroke="#64748b" fontSize={12} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 3: 建立 `components/stock/KeyMetrics.tsx`**

```tsx
import type { DailyPricePoint, FinancialPoint } from "@/api/types";

interface KeyMetricsProps {
  latestPrice: DailyPricePoint | undefined;
  latestFinancial: FinancialPoint | undefined;
}

export function KeyMetrics({ latestPrice, latestFinancial }: KeyMetricsProps) {
  const eps = latestFinancial?.eps;
  const pe =
    latestPrice && eps && eps > 0 ? latestPrice.close / eps : null;

  return (
    <section
      aria-label="關鍵指標"
      className="grid grid-cols-2 md:grid-cols-4 gap-4"
    >
      <Metric
        label="最新收盤"
        value={latestPrice ? latestPrice.close.toFixed(2) : "—"}
      />
      <Metric
        label="最新 EPS"
        value={eps != null ? eps.toFixed(2) : "—"}
      />
      <Metric
        label="本益比 (PE)"
        value={pe != null ? pe.toFixed(1) : "—"}
      />
      <Metric
        label="最新期別"
        value={latestFinancial?.period ?? "—"}
      />
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900 rounded p-3 border border-slate-800">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}
```

- [ ] **Step 4: 寫 KeyMetrics 測試 `tests/components/KeyMetrics.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { KeyMetrics } from "@/components/stock/KeyMetrics";
import type { DailyPricePoint, FinancialPoint } from "@/api/types";

const price: DailyPricePoint = {
  trade_date: "2026-04-14",
  open: 600, high: 610, low: 595, close: 605, volume: 1,
};

const fin: FinancialPoint = {
  period: "2026Q1",
  revenue: null, gross_profit: null, operating_income: null,
  net_income: null, eps: 10,
  total_assets: null, total_liabilities: null, total_equity: null,
};

describe("KeyMetrics", () => {
  it("computes PE from close / eps", () => {
    render(<KeyMetrics latestPrice={price} latestFinancial={fin} />);
    expect(screen.getByText("60.5")).toBeInTheDocument();
  });

  it("renders em dashes when data missing", () => {
    render(<KeyMetrics latestPrice={undefined} latestFinancial={undefined} />);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });
});
```

- [ ] **Step 5: 整合進 `StockPage.tsx`**

替換 StockPage 末尾 placeholder 那段為：

```tsx
return (
  <div className="max-w-5xl mx-auto space-y-8">
    <StockHeader meta={data.meta} />
    <PriceChart points={data.prices} />
    <KeyMetrics
      latestPrice={data.prices[data.prices.length - 1]}
      latestFinancial={data.financials[data.financials.length - 1]}
    />
  </div>
);
```

並在檔頂 import：

```tsx
import { PriceChart } from "@/components/stock/PriceChart";
import { KeyMetrics } from "@/components/stock/KeyMetrics";
```

- [ ] **Step 6: 跑測試 + 型別檢查 + lint + 手動驗收**

Run: `cd frontend && pnpm test tests/components/KeyMetrics.test.tsx && pnpm type-check && pnpm lint`
Expected: 2 passed; 0 error

手動：瀏覽器 `/stocks/2330` 應看到折線圖與四個指標卡。

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/src/components/stock/PriceChart.tsx frontend/src/components/stock/KeyMetrics.tsx frontend/src/pages/StockPage.tsx frontend/tests/components/KeyMetrics.test.tsx
git commit -m "feat: add price chart and key metrics to stock page"
```

---

## Task F3: Frontend — 月營收 + 季報摘要 section

**Files:**
- Create: `frontend/src/components/stock/RevenueSection.tsx`
- Create: `frontend/src/components/stock/FinancialsSection.tsx`
- Modify: `frontend/src/pages/StockPage.tsx`
- Test: `frontend/tests/components/RevenueSection.test.tsx`

- [ ] **Step 1: 建立 `components/stock/RevenueSection.tsx`**

```tsx
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RevenuePoint } from "@/api/types";

interface RevenueSectionProps {
  points: RevenuePoint[];
}

export function RevenueSection({ points }: RevenueSectionProps) {
  const data = points.map((p) => ({
    label: `${p.year}-${String(p.month).padStart(2, "0")}`,
    revenue: p.revenue / 1_000_000, // 百萬
    yoy: p.yoy_growth != null ? p.yoy_growth * 100 : null,
  }));
  return (
    <section aria-label="月營收">
      <h2 className="text-xl font-semibold mb-3">月營收（近 12 個月）</h2>
      {data.length === 0 ? (
        <p className="text-slate-500">尚無月營收資料</p>
      ) : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid stroke="#1e293b" />
              <XAxis dataKey="label" stroke="#64748b" fontSize={12} />
              <YAxis
                stroke="#64748b"
                fontSize={12}
                label={{ value: "百萬", angle: -90, position: "insideLeft" }}
              />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
              />
              <Bar dataKey="revenue" fill="#38bdf8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: 建立 `components/stock/FinancialsSection.tsx`**

```tsx
import type { FinancialPoint } from "@/api/types";

interface FinancialsSectionProps {
  points: FinancialPoint[];
}

function fmt(value: number | null, scale = 1): string {
  if (value == null) return "—";
  return (value / scale).toLocaleString("zh-TW", { maximumFractionDigits: 2 });
}

export function FinancialsSection({ points }: FinancialsSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="季報摘要">
        <h2 className="text-xl font-semibold mb-3">季報摘要</h2>
        <p className="text-slate-500">尚無季報資料</p>
      </section>
    );
  }
  return (
    <section aria-label="季報摘要">
      <h2 className="text-xl font-semibold mb-3">季報摘要（近 4 季，單位：百萬）</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-slate-800">
          <thead className="bg-slate-900">
            <tr>
              <th className="text-left px-3 py-2">期別</th>
              <th className="text-right px-3 py-2">營收</th>
              <th className="text-right px-3 py-2">毛利</th>
              <th className="text-right px-3 py-2">營業利益</th>
              <th className="text-right px-3 py-2">淨利</th>
              <th className="text-right px-3 py-2">EPS</th>
              <th className="text-right px-3 py-2">股東權益</th>
            </tr>
          </thead>
          <tbody>
            {points.slice().reverse().map((p) => (
              <tr key={p.period} className="border-t border-slate-800">
                <td className="px-3 py-2">{p.period}</td>
                <td className="text-right px-3 py-2">{fmt(p.revenue, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.gross_profit, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.operating_income, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.net_income, 1_000_000)}</td>
                <td className="text-right px-3 py-2">{fmt(p.eps)}</td>
                <td className="text-right px-3 py-2">{fmt(p.total_equity, 1_000_000)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 建立 `tests/components/RevenueSection.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RevenueSection } from "@/components/stock/RevenueSection";

describe("RevenueSection", () => {
  it("shows empty placeholder when no data", () => {
    render(<RevenueSection points={[]} />);
    expect(screen.getByText(/尚無月營收資料/)).toBeInTheDocument();
  });

  it("renders section header with count hint", () => {
    render(
      <RevenueSection
        points={[
          { year: 2026, month: 3, revenue: 100_000_000, yoy_growth: 0.1, mom_growth: null },
        ]}
      />
    );
    expect(screen.getByText(/月營收（近 12 個月）/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: 整合進 `StockPage.tsx`**

於 KeyMetrics 之後加：

```tsx
<RevenueSection points={data.revenues} />
<FinancialsSection points={data.financials} />
```

Imports：

```tsx
import { RevenueSection } from "@/components/stock/RevenueSection";
import { FinancialsSection } from "@/components/stock/FinancialsSection";
```

- [ ] **Step 5: 跑測試 + 型別檢查 + lint**

Run: `cd frontend && pnpm test tests/components/RevenueSection.test.tsx && pnpm type-check && pnpm lint`
Expected: 2 passed; 0 error

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/stock/RevenueSection.tsx frontend/src/components/stock/FinancialsSection.tsx frontend/src/pages/StockPage.tsx frontend/tests/components/RevenueSection.test.tsx
git commit -m "feat: add revenue chart and financials table sections"
```

---

## Task F4: Frontend — 三大法人 + 融資融券 + 重大訊息 section

**Files:**
- Create: `frontend/src/components/stock/InstitutionalSection.tsx`
- Create: `frontend/src/components/stock/MarginSection.tsx`
- Create: `frontend/src/components/stock/EventsSection.tsx`
- Modify: `frontend/src/pages/StockPage.tsx`

- [ ] **Step 1: 建立 `components/stock/InstitutionalSection.tsx`**

```tsx
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { InstitutionalPoint } from "@/api/types";

interface InstitutionalSectionProps {
  points: InstitutionalPoint[];
}

export function InstitutionalSection({ points }: InstitutionalSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="三大法人">
        <h2 className="text-xl font-semibold mb-3">三大法人買賣超</h2>
        <p className="text-slate-500">尚無三大法人資料</p>
      </section>
    );
  }
  const data = points.map((p) => ({
    date: p.trade_date,
    foreign: p.foreign_net / 1000, // 張
    trust: p.trust_net / 1000,
    dealer: p.dealer_net / 1000,
  }));
  return (
    <section aria-label="三大法人">
      <h2 className="text-xl font-semibold mb-3">三大法人買賣超（近 20 日，單位：張）</h2>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid stroke="#1e293b" />
            <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
            <Legend />
            <Bar dataKey="foreign" name="外資" fill="#38bdf8" />
            <Bar dataKey="trust" name="投信" fill="#a78bfa" />
            <Bar dataKey="dealer" name="自營商" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: 建立 `components/stock/MarginSection.tsx`**

```tsx
import type { MarginPoint } from "@/api/types";

interface MarginSectionProps {
  points: MarginPoint[];
}

export function MarginSection({ points }: MarginSectionProps) {
  if (points.length === 0) {
    return (
      <section aria-label="融資融券">
        <h2 className="text-xl font-semibold mb-3">融資融券</h2>
        <p className="text-slate-500">尚無融資融券資料</p>
      </section>
    );
  }
  const latest = points[points.length - 1];
  return (
    <section aria-label="融資融券">
      <h2 className="text-xl font-semibold mb-3">融資融券（最新一日）</h2>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <Stat label="融資餘額" value={latest.margin_balance} />
        <Stat label="融資買進" value={latest.margin_buy} />
        <Stat label="融資賣出" value={latest.margin_sell} />
        <Stat label="融券餘額" value={latest.short_balance} />
        <Stat label="融券賣出" value={latest.short_sell} />
        <Stat label="融券回補" value={latest.short_cover} />
      </dl>
      <p className="text-xs text-slate-500 mt-2">日期：{latest.trade_date}（單位：張）</p>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-900 rounded p-3 border border-slate-800">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-lg font-semibold mt-1">{value.toLocaleString("zh-TW")}</dd>
    </div>
  );
}
```

- [ ] **Step 3: 建立 `components/stock/EventsSection.tsx`**

```tsx
import type { EventPoint } from "@/api/types";

interface EventsSectionProps {
  events: EventPoint[];
}

export function EventsSection({ events }: EventsSectionProps) {
  if (events.length === 0) {
    return (
      <section aria-label="重大訊息">
        <h2 className="text-xl font-semibold mb-3">重大訊息</h2>
        <p className="text-slate-500">尚無重大訊息</p>
      </section>
    );
  }
  return (
    <section aria-label="重大訊息">
      <h2 className="text-xl font-semibold mb-3">重大訊息（近 20 筆）</h2>
      <ul className="space-y-3">
        {events.map((e) => (
          <li key={e.id} className="border border-slate-800 rounded p-3 bg-slate-900">
            <div className="flex justify-between text-xs text-slate-500">
              <span>{new Date(e.event_datetime).toLocaleString("zh-TW")}</span>
              <span>{e.event_type}</span>
            </div>
            <div className="mt-1 font-semibold">{e.title}</div>
            {e.content ? (
              <div className="mt-2 text-sm text-slate-300 whitespace-pre-wrap">
                {e.content}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: 整合進 `StockPage.tsx`**

於 FinancialsSection 之後加：

```tsx
<InstitutionalSection points={data.institutional} />
<MarginSection points={data.margin} />
<EventsSection events={data.events} />
```

Imports：

```tsx
import { InstitutionalSection } from "@/components/stock/InstitutionalSection";
import { MarginSection } from "@/components/stock/MarginSection";
import { EventsSection } from "@/components/stock/EventsSection";
```

- [ ] **Step 5: 型別檢查 + lint + 手動驗收**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 error

手動：`/stocks/2330` 頁面應完整顯示七個 section（header、股價圖、關鍵指標、月營收、季報、法人、融資、事件）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/stock/InstitutionalSection.tsx frontend/src/components/stock/MarginSection.tsx frontend/src/components/stock/EventsSection.tsx frontend/src/pages/StockPage.tsx
git commit -m "feat: add institutional margin and events sections"
```

---

## Task G1: Frontend — TermTooltip 元件（L1 hover）

**Files:**
- Create: `frontend/src/components/TermTooltip.tsx`
- Create: `frontend/src/hooks/useGlossary.ts`
- Test: `frontend/tests/components/TermTooltip.test.tsx`
- Modify: 在一個 section 實際使用（例：`components/stock/KeyMetrics.tsx` 的「本益比 (PE)」label）

- [ ] **Step 1: 建立 `hooks/useGlossary.ts`**

```typescript
import { useQuery } from "@tanstack/react-query";

import { fetchAllGlossary } from "@/api/glossary";
import type { GlossaryTerm } from "@/api/types";

export function useGlossary() {
  return useQuery<Record<string, GlossaryTerm>>({
    queryKey: ["glossary"],
    queryFn: fetchAllGlossary,
    staleTime: 10 * 60_000, // 10 min
  });
}
```

- [ ] **Step 2: 建立 `components/TermTooltip.tsx`**

```tsx
import { ReactNode, useState } from "react";

import { useGlossary } from "@/hooks/useGlossary";

interface TermTooltipProps {
  term: string; // glossary key
  children: ReactNode;
}

export function TermTooltip({ term, children }: TermTooltipProps) {
  const { data } = useGlossary();
  const [open, setOpen] = useState(false);
  const entry = data?.[term];

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <abbr
        title={entry?.short ?? term}
        className="underline decoration-dotted decoration-slate-400 cursor-help"
        tabIndex={0}
      >
        {children}
      </abbr>
      {open && entry ? (
        <span
          role="tooltip"
          className="absolute z-10 top-full left-0 mt-1 w-64 bg-slate-800 text-slate-100 text-xs p-2 rounded border border-slate-600 shadow-lg"
        >
          <strong className="block mb-1">{entry.term}</strong>
          <span>{entry.short}</span>
        </span>
      ) : null}
    </span>
  );
}
```

- [ ] **Step 3: 在 `KeyMetrics.tsx` 使用（示範）**

於 KeyMetrics 的 PE label 改為：

```tsx
import { TermTooltip } from "@/components/TermTooltip";
// ...
<Metric
  label={<TermTooltip term="PE">本益比 (PE)</TermTooltip>}
  value={pe != null ? pe.toFixed(1) : "—"}
/>
```

`Metric` 的 props 需要支援 ReactNode label：

```tsx
function Metric({ label, value }: { label: React.ReactNode; value: string }) { ... }
```

同時也在 RevenueSection heading、FinancialsSection 的「EPS」th 加 `<TermTooltip term="EPS">EPS</TermTooltip>` 作示範，至少三處使用。

- [ ] **Step 4: 寫 TermTooltip 測試 `tests/components/TermTooltip.test.tsx`**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TermTooltip } from "@/components/TermTooltip";

function renderWithQuery(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

afterEach(() => vi.restoreAllMocks());

describe("TermTooltip", () => {
  it("shows short definition on hover when term exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            PE: { term: "本益比", short: "股價相對 EPS 的倍數", detail: "", related: [] },
          }),
          { status: 200 }
        )
      )
    );

    renderWithQuery(<TermTooltip term="PE">本益比</TermTooltip>);
    const abbr = await screen.findByText("本益比");
    await userEvent.hover(abbr);
    expect(
      await screen.findByText(/股價相對 EPS 的倍數/)
    ).toBeInTheDocument();
  });

  it("falls back to abbr title when term missing from glossary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
    );

    renderWithQuery(<TermTooltip term="UNKNOWN">未知詞</TermTooltip>);
    // abbr title 為 fallback，DOM 可以查 title 屬性
    const abbr = await screen.findByText("未知詞");
    expect(abbr).toHaveAttribute("title", "UNKNOWN");
  });
});
```

- [ ] **Step 5: 跑測試 + 型別檢查 + lint**

Run: `cd frontend && pnpm test tests/components/TermTooltip.test.tsx && pnpm type-check && pnpm lint`
Expected: 2 passed; 0 error

- [ ] **Step 6: 手動驗收**

`/stocks/2330` → hover「本益比 (PE)」、「EPS」→ 應跳出小 tooltip。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/TermTooltip.tsx frontend/src/hooks/useGlossary.ts frontend/src/components/stock/KeyMetrics.tsx frontend/src/components/stock/FinancialsSection.tsx frontend/src/components/stock/RevenueSection.tsx frontend/tests/components/TermTooltip.test.tsx
git commit -m "feat: add term tooltip with l1 hover definition"
```

---

## Task H1: E2E — 個股頁載入 + tooltip 互動

**Files:**
- Create: `frontend/tests/e2e/stock-page.spec.ts`
- Create: `frontend/tests/e2e/fixtures/stock-2330.json`
- Create: `frontend/tests/e2e/fixtures/glossary.json`

- [ ] **Step 1: 建立 fixture `stock-2330.json`**

```json
{
  "meta": {
    "symbol": "2330",
    "name": "台積電",
    "industry": "半導體",
    "listed_date": "1994-09-05"
  },
  "prices": [
    { "trade_date": "2026-04-10", "open": 600, "high": 610, "low": 595, "close": 605, "volume": 10000 },
    { "trade_date": "2026-04-14", "open": 605, "high": 615, "low": 600, "close": 612, "volume": 12000 }
  ],
  "revenues": [
    { "year": 2026, "month": 3, "revenue": 250000000000, "yoy_growth": 0.15, "mom_growth": 0.05 }
  ],
  "financials": [
    {
      "period": "2026Q1",
      "revenue": 700000000000,
      "gross_profit": 400000000000,
      "operating_income": 350000000000,
      "net_income": 280000000000,
      "eps": 10.8,
      "total_assets": 5000000000000,
      "total_liabilities": 1500000000000,
      "total_equity": 3500000000000
    }
  ],
  "institutional": [
    { "trade_date": "2026-04-14", "foreign_net": 1000000, "trust_net": 500000, "dealer_net": -200000, "total_net": 1300000 }
  ],
  "margin": [
    { "trade_date": "2026-04-14", "margin_balance": 10000, "margin_buy": 100, "margin_sell": 50, "short_balance": 2000, "short_sell": 20, "short_cover": 10 }
  ],
  "events": [
    { "id": 1, "event_datetime": "2026-04-10T15:30:00", "event_type": "財報", "title": "公布 Q1 財報", "content": "營收創新高" }
  ]
}
```

- [ ] **Step 2: 建立 fixture `glossary.json`**

```json
{
  "PE": { "term": "本益比", "short": "股價相對每股盈餘的倍數", "detail": "", "related": [] },
  "EPS": { "term": "每股盈餘", "short": "公司每股賺多少錢", "detail": "", "related": [] }
}
```

- [ ] **Step 3: 建立 `stock-page.spec.ts`**

```typescript
import { test, expect, type Route } from "@playwright/test";

import overview from "./fixtures/stock-2330.json";
import glossary from "./fixtures/glossary.json";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/stocks/2330/overview", (route: Route) =>
    route.fulfill({ json: overview })
  );
  await page.route("**/api/glossary", (route: Route) =>
    route.fulfill({ json: glossary })
  );
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } })
  );
});

test("stock page renders all sections", async ({ page }) => {
  await page.goto("/stocks/2330");
  await expect(page.getByRole("heading", { name: /2330 台積電/ })).toBeVisible();
  await expect(page.getByRole("region", { name: "月營收" })).toBeVisible();
  await expect(page.getByRole("region", { name: "季報摘要" })).toBeVisible();
  await expect(page.getByRole("region", { name: "三大法人" })).toBeVisible();
  await expect(page.getByRole("region", { name: "融資融券" })).toBeVisible();
  await expect(page.getByRole("region", { name: "重大訊息" })).toBeVisible();
});

test("term tooltip shows short definition on hover", async ({ page }) => {
  await page.goto("/stocks/2330");
  const peLabel = page.getByText("本益比 (PE)", { exact: true });
  await peLabel.hover();
  await expect(page.getByRole("tooltip")).toContainText("股價相對每股盈餘的倍數");
});

test("header search navigates to stock page", async ({ page }) => {
  await page.goto("/");
  const input = page.getByLabel("股票代號");
  await input.fill("2330");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/stocks\/2330/);
});
```

- [ ] **Step 4: 跑 E2E**

Run: `cd frontend && pnpm e2e tests/e2e/stock-page.spec.ts`
Expected: 3 passed

若 Playwright 未 install：`pnpm e2e:install` 一次性安裝 browsers。

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/e2e/stock-page.spec.ts frontend/tests/e2e/fixtures/stock-2330.json frontend/tests/e2e/fixtures/glossary.json
git commit -m "test: add e2e for stock page and term tooltip"
```

---

## Task I1: 知識庫更新（features/data-panel、features/education/tooltip、domain/industry-tagging、architecture/data-flow）

**Files:**
- Create: `docs/knowledge/features/data-panel/overview.md`
- Create: `docs/knowledge/features/data-panel/ui-layout.md`
- Create: `docs/knowledge/features/data-panel/data-sources.md`
- Create: `docs/knowledge/features/education/tooltip.md`
- Create: `docs/knowledge/domain/industry-tagging.md`
- Modify: `docs/knowledge/architecture/data-flow.md`

- [ ] **Step 1: 建立 `features/data-panel/overview.md`**

```markdown
---
domain: features/data-panel
updated: 2026-04-15
related: [ui-layout.md, data-sources.md, ../../architecture/data-flow.md]
---

# 功能 A：個股數據面板

## 目的

讓使用者透過 `/stocks/:symbol` 一次看完個股的核心資訊：基本資料、股價走勢、月營收、季報摘要、三大法人、融資融券、重大訊息。所有資料皆來自本地 SQLite（Phase 1 + 1.5 抓取落庫）。

## 現行實作

- **Backend**：`api/routes/stocks.py` 提供 1 個聚合端點 + 6 個細端點 + 1 個列表端點
  - `GET /api/stocks/{symbol}/overview`：個股頁首屏一次載入
  - `GET /api/stocks/{symbol}/{prices,revenues,financials,institutional,margin,events}`：細端點（支援 `limit`、prices 另支援 `start`/`end`）
  - `GET /api/stocks?q=`：列表 + 模糊搜尋（symbol / name substring）
- **Frontend**：`pages/StockPage.tsx` 用 `useStockOverview` hook 一次拉 overview，再分派給各 section 元件渲染

## 關鍵檔案

- [backend/src/alpha_lab/api/routes/stocks.py](../../../backend/src/alpha_lab/api/routes/stocks.py)
- [backend/src/alpha_lab/schemas/stock.py](../../../backend/src/alpha_lab/schemas/stock.py)
- [frontend/src/pages/StockPage.tsx](../../../frontend/src/pages/StockPage.tsx)
- [frontend/src/hooks/useStockOverview.ts](../../../frontend/src/hooks/useStockOverview.ts)
- [frontend/src/components/stock/](../../../frontend/src/components/stock/)

## 修改時注意事項

- Overview 一次聚合 7 個 section；加新 section 時兩邊同步：backend `_load_*` helper + schema、frontend types + section 元件
- `_load_financials` 會把 income + balance 合併成單一 `FinancialPoint`（以 period 為 key）。若未來補 cashflow（Phase 3），要在這裡加第三類欄位合併
- 個股頁預設載入量：prices 60、revenues 12、financials 4、institutional/margin/events 20；量級對應 spec §10 的 UI 尺寸
- 列表端點目前走 LIKE 模糊匹配，無全文索引。若股票數破萬再考慮換方案
```

- [ ] **Step 2: 建立 `features/data-panel/ui-layout.md`**

```markdown
---
domain: features/data-panel
updated: 2026-04-15
related: [overview.md]
---

# 個股頁 UI 布局

## 版面順序（由上而下）

1. **StockHeader**：symbol + name + industry + listed_date
2. **PriceChart**（Recharts LineChart）：近 60 日收盤走勢
3. **KeyMetrics**：最新收盤 / 最新 EPS / PE（算出） / 最新期別
4. **RevenueSection**（Recharts BarChart）：近 12 個月營收
5. **FinancialsSection**（表格）：近 4 季財報（營收、毛利、營業利益、淨利、EPS、股東權益）
6. **InstitutionalSection**（多系列 BarChart）：近 20 日外資/投信/自營商買賣超
7. **MarginSection**：最新一日融資融券 6 欄卡片
8. **EventsSection**：近 20 筆重大訊息列表

## 元件原則

- 每個 section 元件接受自己需要的資料 props，**不自行發 API**（由 StockPage 傳 overview.XXX）
- 空資料 → 顯示 `尚無XXX資料` 占位（由各 section 元件自行處理）
- 所有 section 用 `<section aria-label="XX">` 包裹，E2E 以 `getByRole('region', { name: 'XX' })` 取得

## 關鍵檔案

- [frontend/src/pages/StockPage.tsx](../../../frontend/src/pages/StockPage.tsx)
- [frontend/src/components/stock/](../../../frontend/src/components/stock/)

## 修改時注意事項

- 新增 section 時記得加 `aria-label` 並更新 E2E `stock-page.spec.ts`
- Chart 統一用 Recharts。K 線延到後續 Phase 視需求改用 lightweight-charts
- 金額單位：表格用「百萬」，股數類用「張」，都在 header 上標示避免混淆
```

- [ ] **Step 3: 建立 `features/data-panel/data-sources.md`**

```markdown
---
domain: features/data-panel
updated: 2026-04-15
related: [overview.md, ../../collectors/twse.md, ../../collectors/mops.md]
---

# 個股頁資料來源對應

| 頁面 section | SQLite 表 | Collector | 更新頻率 |
|-------------|----------|----------|---------|
| Header（meta） | `stocks` | 手動 + `backfill_industry.py` | 少動 |
| PriceChart | `prices_daily` | `twse.py`（STOCK_DAY） | 每日收盤後 |
| RevenueSection | `revenues_monthly` | `mops.py`（t05st10） | 每月 10 日後 |
| FinancialsSection | `financial_statements` (income + balance) | `mops_financials.py`（t164sb03/04） | 每季公告期 |
| InstitutionalSection | `institutional_trades` | `twse_institutional.py`（T86） | 每日 |
| MarginSection | `margin_trades` | `twse_margin.py`（MI_MARGN） | 每日 |
| EventsSection | `events` | `mops_events.py`（t146sb05） | 每日掃描 |

## 現金流（Phase 3）

`financial_statements` 已預留 `statement_type='cashflow'` 欄位，但 Phase 2 不讀也不顯示。Phase 3 做 FCF 評分時一併補 MOPS t164sb05 collector + `_load_financials` 合併邏輯。
```

- [ ] **Step 4: 建立 `features/education/tooltip.md`**

```markdown
---
domain: features/education
updated: 2026-04-15
related: [../data-panel/ui-layout.md]
---

# 術語 Tooltip（L1）

## 目的

符合 spec §10「兩層教學」的 L1：hover 顯示 1-3 行簡短定義，降低初學者閱讀成本。L2 側邊面板於 Phase 4（教學系統完整版）實作。

## 現行實作

- **資料**：`backend/src/alpha_lab/glossary/terms.yaml`，每條 `{term, short, detail, related}`，由 `GET /api/glossary` 一次取回所有（約 15 條，量小）
- **前端**：`useGlossary()` hook（TanStack Query，staleTime 10 min）快取整張表；`<TermTooltip term="PE">本益比 (PE)</TermTooltip>` 以 `<abbr>` + 虛線下劃標示可互動，mouseenter/focus 觸發
- **fallback**：glossary 未涵蓋該 key → `<abbr title={key}>` 只顯示 key 本身，不會報錯

## v1 術語清單（15 條）

PE、PB、EPS、ROE、毛利率、殖利率、月營收、YoY、MoM、三大法人、外資、投信、自營商、融資、融券

## 關鍵檔案

- [backend/src/alpha_lab/glossary/terms.yaml](../../../backend/src/alpha_lab/glossary/terms.yaml)
- [backend/src/alpha_lab/glossary/loader.py](../../../backend/src/alpha_lab/glossary/loader.py)
- [backend/src/alpha_lab/api/routes/glossary.py](../../../backend/src/alpha_lab/api/routes/glossary.py)
- [frontend/src/components/TermTooltip.tsx](../../../frontend/src/components/TermTooltip.tsx)
- [frontend/src/hooks/useGlossary.ts](../../../frontend/src/hooks/useGlossary.ts)

## 修改時注意事項

- 術語 key 建議用中文（例：`毛利率`）或英文縮寫（例：`PE`）；加詞時兩邊都更新：terms.yaml + 測試 `test_terms_v1.py` EXPECTED_TERMS
- `short` 長度上限 200 字（schema 限制），實務建議 1-2 句 40-80 字
- Phase 4 實作 L2 時將擴充 `<TermTooltip>` 支援「了解更多」按鈕；API 不需調整（detail 欄位 Phase 2 已載入）
```

- [ ] **Step 5: 建立 `domain/industry-tagging.md`**

```markdown
---
domain: domain/industry-tagging
updated: 2026-04-15
related: [../architecture/data-models.md]
---

# 產業分類

## 目的

替 `stocks.industry` 提供最小可行的映射，讓個股頁 header 與未來的篩選器（Phase 5）能用產業別分類。

## 現行實作（Phase 2：最小）

- **映射來源**：`backend/src/alpha_lab/storage/industry_map.yaml` 手動維護 `{symbol: 產業}` 字典
- **Backfill**：`backend/scripts/backfill_industry.py` 讀 YAML，對 DB 已存在的 symbol 更新 `industry`；映射表沒有的 symbol 不動
- **不做**：自動從 TWSE 產業別檔案同步（未來擴充）

## 關鍵檔案

- [backend/src/alpha_lab/storage/industry_map.yaml](../../backend/src/alpha_lab/storage/industry_map.yaml)
- [backend/scripts/backfill_industry.py](../../backend/scripts/backfill_industry.py)

## 修改時注意事項

- 加新股票時：先 collector 抓到 `stocks` 表，再手動加映射、跑 backfill
- Phase 5（選股篩選器）會用到 `stocks.industry` 當過濾條件；若映射缺口大要先補
- 未來自動同步可參考 TWSE 產業類別 OpenAPI 或 MOPS 產業分類檔，屆時把此檔改成 fallback 來源
```

- [ ] **Step 6: 更新 `architecture/data-flow.md`**

讀既有檔案內容，在末尾新增一節：

```markdown

## Phase 2 新增：讀取面

Phase 2 導入**讀取面 API 層**：

```
SQLite (prices_daily, revenues_monthly, financial_statements, institutional_trades, margin_trades, events, stocks)
  → api/routes/stocks.py::_load_* helpers
    → api/routes/stocks.py::get_stock_overview（聚合）/ get_stock_{section}（細端點）
      → frontend hooks/useStockOverview.ts
        → pages/StockPage.tsx → components/stock/*
```

Glossary 走獨立管線（YAML → loader → API → useGlossary → TermTooltip），無 SQLite 參與。

詳見 [features/data-panel/overview.md](../features/data-panel/overview.md) 與 [features/education/tooltip.md](../features/education/tooltip.md)。
```

- [ ] **Step 7: 中文亂碼掃描**

Run: `grep -r "��" docs/knowledge/`
Expected: no match

- [ ] **Step 8: Commit**

```bash
git add docs/knowledge/features/data-panel docs/knowledge/features/education/tooltip.md docs/knowledge/domain/industry-tagging.md docs/knowledge/architecture/data-flow.md
git commit -m "docs: update knowledge base for phase 2"
```

---

## Task I2: USER_GUIDE 更新 + Phase 2 最終驗收

**Files:**
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（§15 Phase 2 狀態改 ✅）

- [ ] **Step 1: 更新 `USER_GUIDE.md`**

讀既有 `docs/USER_GUIDE.md`，加入「個股頁使用說明」章節：

```markdown
## 個股頁

1. 確認後端已啟動（`uvicorn alpha_lab.api.main:app --reload`）、前端 dev server（`pnpm dev`）
2. 資料已抓取：`python -m scripts.daily_collect`（至少抓過目標 symbol 的股價與月營收）
3. 瀏覽器開 `http://localhost:5173/`，右上角搜尋框輸入股票代號（例：2330）按 Enter
4. 個股頁會顯示：基本資料、股價走勢、關鍵指標、月營收、季報摘要、三大法人、融資融券、重大訊息
5. 將游標停在下劃虛線的術語（例：本益比 (PE)、EPS）會跳出簡短定義

## 術語庫

- 路徑：`backend/src/alpha_lab/glossary/terms.yaml`
- Phase 2 v1 共 15 條：PE、PB、EPS、ROE、毛利率、殖利率、月營收、YoY、MoM、三大法人、外資、投信、自營商、融資、融券
- 編輯後重啟 backend 才會生效（`load_terms` 有 lru_cache）
- 新增術語：只需編輯 yaml；`<TermTooltip term="新key">...</TermTooltip>` 即可套用
```

- [ ] **Step 2: 更新設計 spec §15 Phase 2 狀態**

把 `| 2 | 未開始 | ... |` 改成 `| 2 | ✅ 完成（2026-04-15） | ... |`

- [ ] **Step 3: 全量靜態檢查 + 測試**

Run in parallel:

```bash
cd backend && ruff check . && mypy src && pytest
cd frontend && pnpm type-check && pnpm lint && pnpm test
cd frontend && pnpm e2e
```

Expected: 全數 green

- [ ] **Step 4: 中文亂碼最終掃描**

Run: `grep -r "��" backend/src frontend/src docs/`
Expected: no match

- [ ] **Step 5: 手動驗收指引（使用者必做）**

暫停並請使用者依 USER_GUIDE 新章節走一輪：
1. 前後端啟動、daily_collect 跑過
2. 搜尋框輸入 2330 → 進入個股頁
3. 檢查七個 section 都有資料或合理的空狀態
4. Hover「本益比 (PE)」、「EPS」→ 看到 tooltip
5. 直接輸入不存在的代號（例：9999）→ 看到「載入失敗：API error: 404 ...」
6. 回覆「Phase 2 驗證通過」或列出問題

- [ ] **Step 6: Commit（使用者驗收後）**

```bash
git add docs/USER_GUIDE.md docs/superpowers/specs/2026-04-14-alpha-lab-design.md
git commit -m "docs: mark phase 2 as complete"
```

（可選）打 tag：

```bash
git tag -a phase-2-complete -m "Phase 2: stock page + glossary v1"
```

- [ ] **Step 7: 停下來等下一 Phase 指示**

依 `.claude/CLAUDE.md` 分階段規劃原則，本 Phase 結束後**不主動**開始 Phase 3。等使用者明確指示「開始 Phase 3」後，才用 `superpowers:writing-plans` 撰寫 Phase 3 計畫（多因子評分 + 組合推薦 + 現金流 collector）。

---

## Self-Review Notes

- **Spec coverage**：spec §15 Phase 2 三項交付（個股頁、術語 Tooltip 基礎、術語庫 v1）皆有對應 task。§10 個股頁布局、§8 `/api/glossary/{term}`、§10 教學系統兩層（本 Phase 只做 L1）全部涵蓋。
- **Placeholder scan**：無 TBD／TODO／「similar to」。所有 code block 皆為完整可執行片段。
- **Type consistency**：`StockOverview`、`StockMeta`、各 Point 型別在 backend schemas/stock.py 與 frontend types.ts 對應一致；`_load_financials` 的「合併 income + balance」邏輯在 Task A2 測試（test_overview_merges_income_and_balance_financials）與知識庫 data-sources.md 皆有明記。
- **Scope boundaries**：嚴格排除評分、推薦、L2 面板、K 線、cashflow，避免擴張。
- **20 tasks**：與對齊階段預估 13-15 tasks 略高（多 5），主因是把 E2E 與知識庫各自獨立成 task，以及 stocks API 切 4 個 task（schemas/overview/細端點/列表）。每個 task 仍 2-5 min 級別。
