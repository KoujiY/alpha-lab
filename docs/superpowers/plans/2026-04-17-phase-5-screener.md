# Phase 5：選股篩選器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供多因子篩選介面，讓使用者依 Value / Growth / Dividend / Quality 分數範圍篩選候選股。

**Architecture:** 後端提供兩個 screener 端點（因子 meta + 篩選查詢），直接讀 `scores` 表最新 calc_date。前端新增 `/screener` 頁面，滑桿設定因子分數下限，即時呼叫 API 更新結果表格。scores 為空時顯示引導提示。

**Tech Stack:** FastAPI + SQLAlchemy（後端）、React + TanStack Query + Tailwind CSS（前端）、pytest / vitest / Playwright（測試）

---

## File Structure

### 後端新增

| 檔案 | 職責 |
|------|------|
| `backend/src/alpha_lab/schemas/screener.py` | Pydantic models：FactorMeta、FilterRequest、FilterResult、ScreenerStock |
| `backend/src/alpha_lab/api/routes/screener.py` | FastAPI router：`GET /factors`、`POST /filter` |
| `backend/tests/api/test_screener.py` | 後端整合測試（TestClient） |

### 後端修改

| 檔案 | 變更 |
|------|------|
| `backend/src/alpha_lab/api/main.py` | 新增 `include_router(screener.router)` |

### 前端新增

| 檔案 | 職責 |
|------|------|
| `frontend/src/api/screener.ts` | API client：`fetchFactors`、`filterStocks` |
| `frontend/src/pages/ScreenerPage.tsx` | `/screener` 頁面：滑桿 + 結果表格 |
| `frontend/tests/components/ScreenerPage.test.tsx` | vitest 單元測試 |
| `frontend/tests/e2e/screener.spec.ts` | Playwright E2E 測試 |
| `frontend/tests/e2e/fixtures/screener-factors.json` | factors fixture |
| `frontend/tests/e2e/fixtures/screener-filter.json` | filter 結果 fixture |

### 前端修改

| 檔案 | 變更 |
|------|------|
| `frontend/src/api/types.ts` | 新增 screener 相關 types |
| `frontend/src/App.tsx` | 新增 `/screener` route |
| `frontend/src/layouts/AppLayout.tsx` | header 加「選股篩選」導覽連結 |

### 知識庫新增

| 檔案 | 職責 |
|------|------|
| `docs/knowledge/features/screener/overview.md` | 選股篩選器知識庫條目 |

---

## Task A：後端 Pydantic Schemas + Screener Router

### Task A-1：Screener Pydantic Schemas

**Files:**
- Create: `backend/src/alpha_lab/schemas/screener.py`

- [ ] **Step 1: 建立 screener schemas**

```python
"""選股篩選器 Pydantic schemas。"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class FactorMeta(BaseModel):
    """單一因子的 meta 資訊。"""

    key: str
    label: str
    min_value: float = 0.0
    max_value: float = 100.0
    default_min: float = 0.0
    description: str = ""


class FactorsResponse(BaseModel):
    """GET /api/screener/factors 回應。"""

    factors: list[FactorMeta]


class FactorRange(BaseModel):
    """單一因子的篩選範圍。"""

    key: str
    min_value: float = Field(0.0, ge=0.0, le=100.0)
    max_value: float = Field(100.0, ge=0.0, le=100.0)


class FilterRequest(BaseModel):
    """POST /api/screener/filter 請求。"""

    filters: list[FactorRange] = Field(default_factory=list)
    sort_by: str = "total_score"
    sort_desc: bool = True
    limit: int = Field(50, ge=1, le=200)


class ScreenerStock(BaseModel):
    """篩選結果中的單檔股票。"""

    symbol: str
    name: str
    industry: str | None
    value_score: float | None
    growth_score: float | None
    dividend_score: float | None
    quality_score: float | None
    total_score: float | None


class FilterResponse(BaseModel):
    """POST /api/screener/filter 回應。"""

    calc_date: str
    total_count: int
    stocks: list[ScreenerStock]
```

- [ ] **Step 2: 確認型別檢查通過**

Run: `cd backend && python -m py_compile src/alpha_lab/schemas/screener.py`
Expected: 無輸出（成功）

### Task A-2：Screener Router

**Files:**
- Create: `backend/src/alpha_lab/api/routes/screener.py`
- Modify: `backend/src/alpha_lab/api/main.py`

- [ ] **Step 1: 建立 screener router**

```python
"""/api/screener 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from alpha_lab.analysis.portfolio import latest_calc_date
from alpha_lab.analysis.weights import weighted_total, STYLE_WEIGHTS
from alpha_lab.schemas.screener import (
    FactorMeta,
    FactorRange,
    FactorsResponse,
    FilterRequest,
    FilterResponse,
    ScreenerStock,
)
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Score, Stock

from sqlalchemy import select

router = APIRouter(prefix="/screener", tags=["screener"])

FACTOR_DEFINITIONS: list[FactorMeta] = [
    FactorMeta(key="value_score", label="價值 Value", description="PE、PB 等估值指標"),
    FactorMeta(key="growth_score", label="成長 Growth", description="營收 YoY、EPS YoY"),
    FactorMeta(key="dividend_score", label="股息 Dividend", description="殖利率、配息穩定度"),
    FactorMeta(key="quality_score", label="品質 Quality", description="ROE、毛利率、負債比、FCF"),
    FactorMeta(key="total_score", label="總分 Total", description="四因子加權平均"),
]

VALID_SORT_KEYS = {f.key for f in FACTOR_DEFINITIONS}


@router.get("/factors", response_model=FactorsResponse)
async def get_factors() -> FactorsResponse:
    return FactorsResponse(factors=FACTOR_DEFINITIONS)


@router.post("/filter", response_model=FilterResponse)
async def filter_stocks(req: FilterRequest) -> FilterResponse:
    with session_scope() as session:
        calc_date = latest_calc_date(session)
        if calc_date is None:
            raise HTTPException(
                status_code=409,
                detail="no scores available; run POST /api/jobs/collect with job_type='score' first",
            )

        stmt = (
            select(Score, Stock)
            .join(Stock, Stock.symbol == Score.symbol)
            .where(Score.calc_date == calc_date)
        )
        rows = session.execute(stmt).all()

    # 篩選
    results: list[ScreenerStock] = []
    for score, stock in rows:
        # 對每個 filter 條件檢查
        if not _passes_filters(score, req.filters):
            continue

        # 以 balanced 權重算 total（與 scores 表一致）
        total = weighted_total(
            score.value_score,
            score.growth_score,
            score.dividend_score,
            score.quality_score,
            STYLE_WEIGHTS["balanced"],
        )

        results.append(
            ScreenerStock(
                symbol=stock.symbol,
                name=stock.name,
                industry=stock.industry,
                value_score=score.value_score,
                growth_score=score.growth_score,
                dividend_score=score.dividend_score,
                quality_score=score.quality_score,
                total_score=total,
            )
        )

    # 排序
    sort_key = req.sort_by if req.sort_by in VALID_SORT_KEYS else "total_score"
    results.sort(
        key=lambda s: getattr(s, sort_key) if getattr(s, sort_key) is not None else -1.0,
        reverse=req.sort_desc,
    )

    return FilterResponse(
        calc_date=calc_date.isoformat(),
        total_count=len(results),
        stocks=results[: req.limit],
    )


def _passes_filters(score: Score, filters: list[FactorRange]) -> bool:
    for f in filters:
        val = getattr(score, f.key, None)
        if val is None:
            return False
        if val < f.min_value or val > f.max_value:
            return False
    return True
```

- [ ] **Step 2: 在 main.py 註冊 router**

在 `backend/src/alpha_lab/api/main.py` 加入 import 和 include_router：

```python
# import 新增
from alpha_lab.api.routes import (
    education,
    glossary,
    health,
    jobs,
    portfolios,
    reports,
    screener,   # ← 新增
    stocks,
)

# include_router 新增
app.include_router(screener.router, prefix="/api")
```

- [ ] **Step 3: 靜態檢查**

Run: `cd backend && ruff check src/alpha_lab/schemas/screener.py src/alpha_lab/api/routes/screener.py && mypy src/alpha_lab/schemas/screener.py src/alpha_lab/api/routes/screener.py`
Expected: 0 errors

### Task A-3：後端整合測試

**Files:**
- Create: `backend/tests/api/test_screener.py`

- [ ] **Step 1: 撰寫整合測試**

```python
"""Screener API 整合測試。"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from alpha_lab.api.main import app
from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Base, Score, Stock

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seed_scores():
    """在 test DB 植入 3 檔股票 + scores。"""
    with session_scope() as session:
        for tbl in reversed(Base.metadata.sorted_tables):
            session.execute(tbl.delete())
        session.commit()

        stocks = [
            Stock(symbol="2330", name="台積電", industry="半導體"),
            Stock(symbol="2454", name="聯發科", industry="半導體"),
            Stock(symbol="2317", name="鴻海", industry="電子零組件"),
        ]
        session.add_all(stocks)
        session.flush()

        calc = date(2026, 4, 17)
        scores = [
            Score(symbol="2330", calc_date=calc, value_score=60, growth_score=80, dividend_score=50, quality_score=90, total_score=70),
            Score(symbol="2454", calc_date=calc, value_score=40, growth_score=95, dividend_score=30, quality_score=70, total_score=58.75),
            Score(symbol="2317", calc_date=calc, value_score=75, growth_score=50, dividend_score=70, quality_score=60, total_score=63.75),
        ]
        session.add_all(scores)
        session.commit()
    yield


class TestGetFactors:
    def test_returns_five_factors(self):
        resp = client.get("/api/screener/factors")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["factors"]) == 5
        keys = [f["key"] for f in data["factors"]]
        assert "value_score" in keys
        assert "total_score" in keys

    def test_factor_has_label_and_range(self):
        resp = client.get("/api/screener/factors")
        factor = resp.json()["factors"][0]
        assert "label" in factor
        assert factor["min_value"] == 0.0
        assert factor["max_value"] == 100.0


class TestPostFilter:
    def test_no_filters_returns_all(self):
        resp = client.post("/api/screener/filter", json={"filters": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 3
        assert len(data["stocks"]) == 3

    def test_filter_by_growth_min_70(self):
        resp = client.post(
            "/api/screener/filter",
            json={"filters": [{"key": "growth_score", "min_value": 70}]},
        )
        data = resp.json()
        symbols = [s["symbol"] for s in data["stocks"]]
        assert "2330" in symbols  # growth=80
        assert "2454" in symbols  # growth=95
        assert "2317" not in symbols  # growth=50

    def test_filter_multiple_factors(self):
        resp = client.post(
            "/api/screener/filter",
            json={
                "filters": [
                    {"key": "value_score", "min_value": 50},
                    {"key": "quality_score", "min_value": 80},
                ]
            },
        )
        data = resp.json()
        symbols = [s["symbol"] for s in data["stocks"]]
        assert symbols == ["2330"]  # value=60 ≥50 且 quality=90 ≥80

    def test_sort_by_growth_asc(self):
        resp = client.post(
            "/api/screener/filter",
            json={"filters": [], "sort_by": "growth_score", "sort_desc": False},
        )
        symbols = [s["symbol"] for s in resp.json()["stocks"]]
        assert symbols == ["2317", "2330", "2454"]

    def test_limit(self):
        resp = client.post(
            "/api/screener/filter",
            json={"filters": [], "limit": 2},
        )
        assert len(resp.json()["stocks"]) == 2

    def test_no_scores_returns_409(self):
        # 清空 scores
        with session_scope() as session:
            session.execute(Score.__table__.delete())
            session.commit()
        resp = client.post("/api/screener/filter", json={"filters": []})
        assert resp.status_code == 409

    def test_result_includes_stock_info(self):
        resp = client.post("/api/screener/filter", json={"filters": []})
        stock = resp.json()["stocks"][0]
        assert "name" in stock
        assert "industry" in stock
        assert "value_score" in stock
```

- [ ] **Step 2: 跑測試確認全部通過**

Run: `cd backend && python -m pytest tests/api/test_screener.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 errors

---

## Task B：前端 Types + API Client

### Task B-1：前端 Types 與 API Client

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/api/screener.ts`

- [ ] **Step 1: 在 types.ts 末尾新增 screener types**

```typescript
// --- Screener ---

export interface FactorMeta {
  key: string;
  label: string;
  min_value: number;
  max_value: number;
  default_min: number;
  description: string;
}

export interface FactorsResponse {
  factors: FactorMeta[];
}

export interface FactorRange {
  key: string;
  min_value: number;
  max_value: number;
}

export interface ScreenerStock {
  symbol: string;
  name: string;
  industry: string | null;
  value_score: number | null;
  growth_score: number | null;
  dividend_score: number | null;
  quality_score: number | null;
  total_score: number | null;
}

export interface FilterResponse {
  calc_date: string;
  total_count: number;
  stocks: ScreenerStock[];
}
```

- [ ] **Step 2: 建立 screener API client**

```typescript
// frontend/src/api/screener.ts
import { apiGet, apiPost } from "./client";
import type { FactorsResponse, FilterResponse, FactorRange } from "./types";

export function fetchFactors(): Promise<FactorsResponse> {
  return apiGet<FactorsResponse>("/api/screener/factors");
}

export interface FilterParams {
  filters: FactorRange[];
  sort_by?: string;
  sort_desc?: boolean;
  limit?: number;
}

export function filterStocks(params: FilterParams): Promise<FilterResponse> {
  return apiPost<FilterResponse>("/api/screener/filter", undefined, params);
}
```

- [ ] **Step 3: 擴充 apiPost 支援 JSON body**

目前 `apiPost` 只支援 query params，需要加上 JSON body 支援。修改 `frontend/src/api/client.ts`：

```typescript
export async function apiPost<T>(
  path: string,
  params?: Record<string, string>,
  body?: unknown,
): Promise<T> {
  const query = params ? `?${new URLSearchParams(params).toString()}` : "";
  const response = await fetch(`${API_BASE}${path}${query}`, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}
```

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && pnpm type-check`
Expected: 0 errors

---

## Task C：前端 ScreenerPage

### Task C-1：ScreenerPage 元件

**Files:**
- Create: `frontend/src/pages/ScreenerPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 建立 ScreenerPage**

```tsx
// frontend/src/pages/ScreenerPage.tsx
import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { fetchFactors, filterStocks } from "@/api/screener";
import type { FactorRange, ScreenerStock } from "@/api/types";

export function ScreenerPage() {
  const { data: factorsData, isLoading: factorsLoading } = useQuery({
    queryKey: ["screener-factors"],
    queryFn: fetchFactors,
  });

  const [ranges, setRanges] = useState<Record<string, number>>({});
  const [sortBy, setSortBy] = useState("total_score");
  const [sortDesc, setSortDesc] = useState(true);

  const filterMutation = useMutation({
    mutationFn: (filters: FactorRange[]) =>
      filterStocks({ filters, sort_by: sortBy, sort_desc: sortDesc }),
  });

  const handleFilter = useCallback(() => {
    if (!factorsData) return;
    const filters: FactorRange[] = factorsData.factors
      .filter((f) => (ranges[f.key] ?? 0) > 0)
      .map((f) => ({
        key: f.key,
        min_value: ranges[f.key] ?? 0,
        max_value: 100,
      }));
    filterMutation.mutate(filters);
  }, [factorsData, ranges, sortBy, sortDesc, filterMutation]);

  const handleSliderChange = useCallback(
    (key: string, value: number) => {
      setRanges((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleSort = useCallback(
    (key: string) => {
      if (sortBy === key) {
        setSortDesc((prev) => !prev);
      } else {
        setSortBy(key);
        setSortDesc(true);
      }
    },
    [sortBy],
  );

  if (factorsLoading) {
    return <p className="text-slate-400">載入因子資訊…</p>;
  }

  if (!factorsData) {
    return null;
  }

  return (
    <div className="w-full space-y-6">
      <h1 className="text-2xl font-bold">選股篩選器</h1>

      {/* 因子滑桿區 */}
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 space-y-4">
        <h2 className="text-sm font-semibold text-slate-400">篩選條件（最低分數）</h2>
        {factorsData.factors
          .filter((f) => f.key !== "total_score")
          .map((factor) => (
            <div key={factor.key} className="flex items-center gap-4">
              <label className="w-32 text-sm text-slate-300" htmlFor={`slider-${factor.key}`}>
                {factor.label}
              </label>
              <input
                id={`slider-${factor.key}`}
                type="range"
                min={0}
                max={100}
                step={5}
                value={ranges[factor.key] ?? 0}
                onChange={(e) => handleSliderChange(factor.key, Number(e.target.value))}
                className="flex-1 accent-sky-500"
                data-testid={`slider-${factor.key}`}
              />
              <span className="w-10 text-right text-sm tabular-nums text-slate-300">
                {ranges[factor.key] ?? 0}
              </span>
            </div>
          ))}
        <button
          type="button"
          onClick={handleFilter}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
          data-testid="screener-filter-btn"
        >
          篩選
        </button>
      </div>

      {/* 結果區 */}
      {filterMutation.isPending && (
        <p className="text-slate-400">篩選中…</p>
      )}

      {filterMutation.isError && (
        <div className="rounded-lg border border-amber-700 bg-amber-900/30 p-4">
          <p className="text-amber-300">
            {filterMutation.error instanceof Error &&
            filterMutation.error.message.includes("409")
              ? "尚無評分資料。請先執行評分計算（POST /api/jobs/collect，job_type='score'）。"
              : `篩選失敗：${filterMutation.error instanceof Error ? filterMutation.error.message : "未知錯誤"}`}
          </p>
        </div>
      )}

      {filterMutation.data && (
        <div className="space-y-2">
          <p className="text-sm text-slate-500">
            計算日：{filterMutation.data.calc_date}　
            共 {filterMutation.data.total_count} 檔符合
          </p>
          {filterMutation.data.stocks.length === 0 ? (
            <p className="text-slate-400">沒有符合條件的股票，請調低篩選門檻。</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="screener-results">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-slate-400">
                    <th className="py-2 pr-4">代號</th>
                    <th className="py-2 pr-4">名稱</th>
                    <th className="py-2 pr-4">產業</th>
                    <SortHeader label="價值" sortKey="value_score" current={sortBy} desc={sortDesc} onClick={handleSort} />
                    <SortHeader label="成長" sortKey="growth_score" current={sortBy} desc={sortDesc} onClick={handleSort} />
                    <SortHeader label="股息" sortKey="dividend_score" current={sortBy} desc={sortDesc} onClick={handleSort} />
                    <SortHeader label="品質" sortKey="quality_score" current={sortBy} desc={sortDesc} onClick={handleSort} />
                    <SortHeader label="總分" sortKey="total_score" current={sortBy} desc={sortDesc} onClick={handleSort} />
                  </tr>
                </thead>
                <tbody>
                  {filterMutation.data.stocks.map((stock) => (
                    <StockRow key={stock.symbol} stock={stock} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SortHeaderProps {
  label: string;
  sortKey: string;
  current: string;
  desc: boolean;
  onClick: (key: string) => void;
}

function SortHeader({ label, sortKey, current, desc, onClick }: SortHeaderProps) {
  const arrow = current === sortKey ? (desc ? " ▼" : " ▲") : "";
  return (
    <th
      className="cursor-pointer py-2 pr-4 select-none hover:text-sky-300"
      onClick={() => onClick(sortKey)}
    >
      {label}{arrow}
    </th>
  );
}

function StockRow({ stock }: { stock: ScreenerStock }) {
  const fmt = (v: number | null) =>
    v !== null ? v.toFixed(1) : "—";
  return (
    <tr className="border-b border-slate-800 hover:bg-slate-800/50">
      <td className="py-2 pr-4">
        <Link to={`/stocks/${stock.symbol}`} className="text-sky-400 hover:underline">
          {stock.symbol}
        </Link>
      </td>
      <td className="py-2 pr-4">{stock.name}</td>
      <td className="py-2 pr-4 text-slate-400">{stock.industry ?? "—"}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.value_score)}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.growth_score)}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.dividend_score)}</td>
      <td className="py-2 pr-4 tabular-nums">{fmt(stock.quality_score)}</td>
      <td className="py-2 pr-4 tabular-nums font-medium">{fmt(stock.total_score)}</td>
    </tr>
  );
}
```

- [ ] **Step 2: 在 App.tsx 新增 route**

```tsx
import { ScreenerPage } from "@/pages/ScreenerPage";

// 在 Routes 內新增：
<Route path="/screener" element={<ScreenerPage />} />
```

- [ ] **Step 3: 在 AppLayout.tsx header 新增導覽連結**

在「組合推薦」連結後面加入：

```tsx
<Link to="/screener" className="text-sm text-slate-300 hover:text-sky-300">
  選股篩選
</Link>
```

- [ ] **Step 4: 型別檢查 + lint**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 errors

---

## Task D：前端測試

### Task D-1：vitest 單元測試

**Files:**
- Create: `frontend/tests/components/ScreenerPage.test.tsx`

- [ ] **Step 1: 撰寫單元測試**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ScreenerPage } from "@/pages/ScreenerPage";

const mockFactors = {
  factors: [
    { key: "value_score", label: "價值 Value", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "growth_score", label: "成長 Growth", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "dividend_score", label: "股息 Dividend", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "quality_score", label: "品質 Quality", min_value: 0, max_value: 100, default_min: 0, description: "" },
    { key: "total_score", label: "總分 Total", min_value: 0, max_value: 100, default_min: 0, description: "" },
  ],
};

const mockFilterResult = {
  calc_date: "2026-04-17",
  total_count: 2,
  stocks: [
    { symbol: "2330", name: "台積電", industry: "半導體", value_score: 60, growth_score: 80, dividend_score: 50, quality_score: 90, total_score: 70 },
    { symbol: "2454", name: "聯發科", industry: "半導體", value_score: 40, growth_score: 95, dividend_score: 30, quality_score: 70, total_score: 58.75 },
  ],
};

vi.mock("@/api/screener", () => ({
  fetchFactors: vi.fn(() => Promise.resolve(mockFactors)),
  filterStocks: vi.fn(() => Promise.resolve(mockFilterResult)),
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ScreenerPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ScreenerPage", () => {
  it("renders factor sliders (excluding total_score)", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("價值 Value")).toBeInTheDocument();
    });
    // total_score 不顯示滑桿
    expect(screen.queryByText("總分 Total")).not.toBeInTheDocument();
    expect(screen.getByTestId("slider-value_score")).toBeInTheDocument();
  });

  it("shows results after clicking filter button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("screener-filter-btn")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("screener-filter-btn"));
    await waitFor(() => {
      expect(screen.getByText("台積電")).toBeInTheDocument();
      expect(screen.getByText("聯發科")).toBeInTheDocument();
    });
  });

  it("displays heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "選股篩選器" })).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: 跑 vitest**

Run: `cd frontend && pnpm test -- --run tests/components/ScreenerPage.test.tsx`
Expected: 全部 PASS

### Task D-2：Playwright E2E 測試

**Files:**
- Create: `frontend/tests/e2e/fixtures/screener-factors.json`
- Create: `frontend/tests/e2e/fixtures/screener-filter.json`
- Create: `frontend/tests/e2e/screener.spec.ts`

- [ ] **Step 1: 建立 E2E fixtures**

`screener-factors.json`:
```json
{
  "factors": [
    { "key": "value_score", "label": "價值 Value", "min_value": 0, "max_value": 100, "default_min": 0, "description": "PE、PB 等估值指標" },
    { "key": "growth_score", "label": "成長 Growth", "min_value": 0, "max_value": 100, "default_min": 0, "description": "營收 YoY、EPS YoY" },
    { "key": "dividend_score", "label": "股息 Dividend", "min_value": 0, "max_value": 100, "default_min": 0, "description": "殖利率、配息穩定度" },
    { "key": "quality_score", "label": "品質 Quality", "min_value": 0, "max_value": 100, "default_min": 0, "description": "ROE、毛利率、負債比、FCF" },
    { "key": "total_score", "label": "總分 Total", "min_value": 0, "max_value": 100, "default_min": 0, "description": "四因子加權平均" }
  ]
}
```

`screener-filter.json`:
```json
{
  "calc_date": "2026-04-17",
  "total_count": 3,
  "stocks": [
    { "symbol": "2330", "name": "台積電", "industry": "半導體", "value_score": 60, "growth_score": 80, "dividend_score": 50, "quality_score": 90, "total_score": 70 },
    { "symbol": "2317", "name": "鴻海", "industry": "電子零組件", "value_score": 75, "growth_score": 50, "dividend_score": 70, "quality_score": 60, "total_score": 63.75 },
    { "symbol": "2454", "name": "聯發科", "industry": "半導體", "value_score": 40, "growth_score": 95, "dividend_score": 30, "quality_score": 70, "total_score": 58.75 }
  ]
}
```

- [ ] **Step 2: 撰寫 E2E spec**

```typescript
// frontend/tests/e2e/screener.spec.ts
import { test, expect, type Route } from "@playwright/test";

import factors from "./fixtures/screener-factors.json" with { type: "json" };
import filterResult from "./fixtures/screener-filter.json" with { type: "json" };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/screener/factors", (route: Route) =>
    route.fulfill({ json: factors })
  );
  await page.route("**/api/screener/filter", (route: Route) =>
    route.fulfill({ json: filterResult })
  );
  await page.route("**/api/health", (route: Route) =>
    route.fulfill({ json: { status: "ok" } })
  );
});

test("screener page shows factor sliders", async ({ page }) => {
  await page.goto("/screener");
  await expect(page.getByRole("heading", { name: "選股篩選器" })).toBeVisible();
  await expect(page.getByText("價值 Value")).toBeVisible();
  await expect(page.getByText("成長 Growth")).toBeVisible();
  await expect(page.getByText("品質 Quality")).toBeVisible();
});

test("screener filter button triggers search and shows results", async ({ page }) => {
  await page.goto("/screener");
  await page.getByTestId("screener-filter-btn").click();
  await expect(page.getByText("台積電")).toBeVisible();
  await expect(page.getByText("鴻海")).toBeVisible();
  await expect(page.getByText("聯發科")).toBeVisible();
  await expect(page.getByText("共 3 檔符合")).toBeVisible();
});

test("screener result stock links to stock page", async ({ page }) => {
  await page.goto("/screener");
  await page.getByTestId("screener-filter-btn").click();
  await expect(page.getByText("台積電")).toBeVisible();
  const link = page.getByRole("link", { name: "2330" });
  await expect(link).toHaveAttribute("href", "/stocks/2330");
});

test("screener nav link exists in header", async ({ page }) => {
  await page.goto("/screener");
  await expect(page.getByRole("link", { name: "選股篩選" })).toBeVisible();
});

test("screener shows 409 guidance when no scores", async ({ page }) => {
  await page.route("**/api/screener/filter", (route: Route) =>
    route.fulfill({ status: 409, json: { detail: "no scores available" } })
  );
  await page.goto("/screener");
  await page.getByTestId("screener-filter-btn").click();
  await expect(page.getByText("尚無評分資料")).toBeVisible();
});
```

- [ ] **Step 3: 跑 E2E**

Run: `cd frontend && pnpm e2e -- screener.spec.ts`
Expected: 全部 PASS

---

## Task E：知識庫 + 靜態檢查 + 驗收指引

### Task E-1：知識庫條目

**Files:**
- Create: `docs/knowledge/features/screener/overview.md`
- Modify: `docs/knowledge/architecture/data-flow.md`（加 Phase 5 段落）

- [ ] **Step 1: 建立 screener 知識庫**

```markdown
---
domain: features/screener
updated: 2026-04-17
related: [../../domain/factors.md, ../../domain/scoring.md, ../../architecture/data-flow.md]
---

# 選股篩選器

## 目的

提供多因子條件篩選介面，讓使用者依 Value / Growth / Dividend / Quality 分數範圍篩選候選股。

## 現行實作（Phase 5）

### 後端

- **GET /api/screener/factors**：回傳五個因子 meta（key / label / 範圍 / 說明），純靜態定義
- **POST /api/screener/filter**：接收 `FilterRequest`（filters + sort_by + limit），讀 `scores` 最新 calc_date，逐 row 檢查是否通過所有 filter，回傳 `FilterResponse`
- scores 為空時回 409，與 portfolios/recommend 一致
- total_score 在 filter response 以 balanced 權重 runtime 算出，與 `scores.total_score` 一致

### 前端

- `/screener` 頁面：四個因子滑桿（排除 total_score）+ 篩選按鈕 → 結果表格
- 結果表格欄位可排序（點擊 header 切換升降序）
- 股票代號可點擊跳轉個股頁
- 409 時顯示「尚無評分資料」引導提示

## 關鍵檔案

- [backend/src/alpha_lab/schemas/screener.py](../../../../backend/src/alpha_lab/schemas/screener.py)
- [backend/src/alpha_lab/api/routes/screener.py](../../../../backend/src/alpha_lab/api/routes/screener.py)
- [frontend/src/pages/ScreenerPage.tsx](../../../../frontend/src/pages/ScreenerPage.tsx)
- [frontend/src/api/screener.ts](../../../../frontend/src/api/screener.ts)

## 修改時注意事項

- 新增因子 → 在 router 的 `FACTOR_DEFINITIONS` 加 `FactorMeta`，前端自動適配
- 改排序邏輯 → 後端 `_passes_filters` + sort lambda
- 若改為即時篩選（去掉按鈕）→ 前端改用 useQuery + debounce 取代 useMutation
```

- [ ] **Step 2: 在 data-flow.md 加 Phase 5 段落**

在 `## Phase 4 新增：報告寫入 / 讀取` 後面加入：

```markdown
## Phase 5 新增：選股篩選器

```
GET /api/screener/factors → 靜態 FACTOR_DEFINITIONS → FactorsResponse

POST /api/screener/filter (FilterRequest)
  → screener.py::filter_stocks
    → latest_calc_date(session)
    → SELECT scores + stocks WHERE calc_date = latest
    → _passes_filters（逐 row 過濾）
    → weighted_total（balanced 權重算 total）
    → 排序 + limit → FilterResponse
```

前端：`/screener` → fetchFactors + filterStocks → ScreenerPage（滑桿 + 結果表格）
```

### Task E-2：全面靜態檢查 + 使用者驗收指引

- [ ] **Step 1: 後端靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 errors

- [ ] **Step 2: 前端靜態檢查**

Run: `cd frontend && pnpm type-check && pnpm lint`
Expected: 0 errors

- [ ] **Step 3: 全部測試**

Run: `cd backend && python -m pytest tests/api/test_screener.py -v`
Run: `cd frontend && pnpm test -- --run`
Run: `cd frontend && pnpm e2e`
Expected: 全部 PASS

- [ ] **Step 4: 提供使用者驗收指引**

```cmd
REM === Phase 5 驗收指引 ===

REM 1. 啟動後端
cd backend
.venv\Scripts\activate
uvicorn alpha_lab.api.main:app --reload

REM 2. 另開 terminal 啟動前端
cd frontend
pnpm dev

REM 3. 開瀏覽器 http://localhost:5173/screener
REM    - 應看到「選股篩選器」標題
REM    - 四個因子滑桿（價值/成長/股息/品質）
REM    - 調整滑桿後按「篩選」→ 下方出現結果表格
REM    - 若 scores 為空，按篩選會出現「尚無評分資料」提示

REM 4. 驗證 header 導覽
REM    - header 有「選股篩選」連結
REM    - 點擊可跳轉到 /screener

REM 5. 驗證結果互動
REM    - 結果表格各欄位可點擊排序
REM    - 股票代號可點擊跳轉個股頁
```

---

## 驗收標準總結

| 項目 | 標準 |
|------|------|
| `GET /api/screener/factors` | 回傳 5 個因子 meta |
| `POST /api/screener/filter` | 接受 filters + sort + limit，回傳篩選結果 |
| scores 為空 | 回 409 + 前端顯示引導提示 |
| `/screener` 頁面 | 滑桿 + 篩選按鈕 + 結果表格 |
| 結果排序 | 點擊 header 可切換升降序 |
| 導覽 | header 有「選股篩選」連結 |
| 後端靜態檢查 | `ruff check .` + `mypy src` 0 errors |
| 前端靜態檢查 | `tsc --noEmit` + `pnpm lint` 0 errors |
| 後端測試 | `test_screener.py` 全 PASS |
| 前端測試 | vitest + Playwright 全 PASS |
| 知識庫 | `features/screener/overview.md` 已建立 |
