# Phase 7B.3 — UX 與快取 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓報告可離線查看（IndexedDB 快取），並強化「加入組合」時 symbol 缺報價的 UX 引導。

**Architecture:** 前端用 `idb-keyval` 做報告 IndexedDB 快取，包在自訂 `useReport` hook 裡（fetch 成功時寫入、API 失敗時 fallback 讀取）。後端 `probe_base_date` 擴充 `symbol_statuses` 欄位，為每個缺價 symbol 分類原因（`no_data` / `stale` / `today_missing`），前端 `BaseDateConfirmDialog` 依分類顯示不同引導訊息。

**Tech Stack:** idb-keyval（IndexedDB 輕量 wrapper）、TanStack Query v5、FastAPI、Pydantic v2、pytest、vitest

---

## File Structure

### 新增檔案

| 檔案 | 職責 |
|------|------|
| `frontend/src/lib/reportCache.ts` | IndexedDB 報告快取 CRUD（get / set / list / clear） |
| `frontend/tests/unit/reportCache.test.ts` | reportCache 單元測試 |
| `frontend/tests/unit/useReports.test.ts` | useReport hook 離線 fallback 測試 |
| `backend/tests/portfolios/test_probe_status.py` | symbol_statuses 分類邏輯測試 |

### 修改檔案

| 檔案 | 變更內容 |
|------|---------|
| `frontend/package.json` | 新增 `idb-keyval` 依賴 |
| `frontend/src/hooks/useReports.ts` | `useReport` 整合 IndexedDB（initialData + onSuccess persist + error fallback） |
| `frontend/src/pages/ReportDetailPage.tsx` | 加「已快取」badge |
| `backend/src/alpha_lab/schemas/saved_portfolio.py` | 新增 `SymbolPriceStatus` Literal + `BaseDateProbe.symbol_statuses` |
| `backend/src/alpha_lab/portfolios/service.py` | `probe_base_date` 回傳 symbol_statuses |
| `backend/src/alpha_lab/api/routes/portfolios.py` | 序列化新欄位（Pydantic 自動，無需手動改） |
| `frontend/src/api/types.ts` | `BaseDateProbe` 加 `symbol_statuses` |
| `frontend/src/components/portfolio/BaseDateConfirmDialog.tsx` | 依 symbol_statuses 分組顯示引導 |
| `docs/knowledge/architecture/README.md` | 加 `report-cache.md` 條目 |
| `docs/knowledge/features/tracking/overview.md` | 更新 probe UX 說明 |

---

## Task 1: 報告 IndexedDB 快取 — 工具層

**Files:**
- Create: `frontend/src/lib/reportCache.ts`
- Create: `frontend/tests/unit/reportCache.test.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: 安裝 idb-keyval**

```bash
cd frontend && pnpm add idb-keyval
```

- [ ] **Step 2: 寫 reportCache 的失敗測試**

```typescript
// frontend/tests/unit/reportCache.test.ts
import { afterEach, describe, expect, it } from "vitest";
import {
  clearReportCache,
  getCachedReport,
  listCachedReportIds,
  setCachedReport,
} from "@/lib/reportCache";
import type { ReportDetail } from "@/api/types";

const STUB: ReportDetail = {
  id: "stock-2330-2026-04-01",
  type: "stock",
  title: "台積電分析",
  symbols: ["2330"],
  tags: ["半導體"],
  date: "2026-04-01",
  path: "analysis/stock-2330-2026-04-01.md",
  summary_line: "Q1 展望正面",
  starred: false,
  body_markdown: "# 分析\n內容",
};

afterEach(async () => {
  await clearReportCache();
});

describe("reportCache", () => {
  it("returns undefined for unknown id", async () => {
    expect(await getCachedReport("nonexistent")).toBeUndefined();
  });

  it("round-trips a report", async () => {
    await setCachedReport(STUB);
    const result = await getCachedReport(STUB.id);
    expect(result).toEqual(STUB);
  });

  it("lists cached ids", async () => {
    await setCachedReport(STUB);
    const ids = await listCachedReportIds();
    expect(ids).toContain(STUB.id);
  });

  it("clears all cached reports", async () => {
    await setCachedReport(STUB);
    await clearReportCache();
    expect(await getCachedReport(STUB.id)).toBeUndefined();
    expect(await listCachedReportIds()).toHaveLength(0);
  });
});
```

- [ ] **Step 3: 跑測試確認失敗**

```bash
cd frontend && pnpm test -- reportCache
```

Expected: FAIL — `@/lib/reportCache` 模組不存在。

- [ ] **Step 4: 實作 reportCache**

```typescript
// frontend/src/lib/reportCache.ts
import { createStore, del, entries, get, set } from "idb-keyval";
import type { ReportDetail } from "@/api/types";

const store = createStore("alpha-lab-reports", "report-cache");

function key(reportId: string): string {
  return `report:${reportId}`;
}

export async function getCachedReport(
  reportId: string,
): Promise<ReportDetail | undefined> {
  return get<ReportDetail>(key(reportId), store);
}

export async function setCachedReport(report: ReportDetail): Promise<void> {
  await set(key(report.id), report, store);
}

export async function listCachedReportIds(): Promise<string[]> {
  const all = await entries<string, ReportDetail>(store);
  return all.map(([k]) => k.replace(/^report:/, ""));
}

export async function clearReportCache(): Promise<void> {
  const all = await entries<string, ReportDetail>(store);
  for (const [k] of all) {
    await del(k, store);
  }
}
```

- [ ] **Step 5: 跑測試確認通過**

```bash
cd frontend && pnpm test -- reportCache
```

Expected: PASS（注意：vitest + jsdom 環境可能需要 `fake-indexeddb`；若 `idb-keyval` 在 jsdom 無法運作，安裝 `fake-indexeddb` 為 devDependency 並在 vitest setup 中 import）。

若需要 fake-indexeddb：

```bash
cd frontend && pnpm add -D fake-indexeddb
```

在 `vitest.config.ts` 或 `vitest.setup.ts` 頂部加：

```typescript
import "fake-indexeddb/auto";
```

- [ ] **Step 6: 靜態檢查**

```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 errors。

---

## Task 2: useReport hook 整合 IndexedDB 快取

**Files:**
- Modify: `frontend/src/hooks/useReports.ts`
- Create: `frontend/tests/unit/useReports.test.ts`

- [ ] **Step 1: 寫 useReport 離線 fallback 測試**

```typescript
// frontend/tests/unit/useReports.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearReportCache, setCachedReport } from "@/lib/reportCache";
import type { ReportDetail } from "@/api/types";

const STUB: ReportDetail = {
  id: "stock-2330-2026-04-01",
  type: "stock",
  title: "台積電分析",
  symbols: ["2330"],
  tags: ["半導體"],
  date: "2026-04-01",
  path: "analysis/stock-2330-2026-04-01.md",
  summary_line: "Q1 展望正面",
  starred: false,
  body_markdown: "# 分析\n內容",
};

describe("useReport cache integration", () => {
  afterEach(async () => {
    await clearReportCache();
    vi.restoreAllMocks();
  });

  it("getReportWithCache returns API data and persists to cache", async () => {
    const { getReportWithCache } = await import("@/hooks/useReports");
    const mockFetch = vi.fn().mockResolvedValue(STUB);
    const result = await getReportWithCache(STUB.id, mockFetch);
    expect(result).toEqual(STUB);

    const { getCachedReport } = await import("@/lib/reportCache");
    expect(await getCachedReport(STUB.id)).toEqual(STUB);
  });

  it("getReportWithCache returns cached data when API fails", async () => {
    await setCachedReport(STUB);
    const { getReportWithCache } = await import("@/hooks/useReports");
    const mockFetch = vi.fn().mockRejectedValue(new Error("offline"));
    const result = await getReportWithCache(STUB.id, mockFetch);
    expect(result).toEqual(STUB);
  });

  it("getReportWithCache throws when both API and cache miss", async () => {
    const { getReportWithCache } = await import("@/hooks/useReports");
    const mockFetch = vi.fn().mockRejectedValue(new Error("offline"));
    await expect(getReportWithCache("unknown", mockFetch)).rejects.toThrow(
      "offline",
    );
  });
});
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd frontend && pnpm test -- useReports
```

Expected: FAIL — `getReportWithCache` 不存在。

- [ ] **Step 3: 實作 useReport IndexedDB 整合**

```typescript
// frontend/src/hooks/useReports.ts
import { useQuery } from "@tanstack/react-query";

import { getReport, listReports, type ListReportsParams } from "@/api/reports";
import type { ReportDetail } from "@/api/types";
import { getCachedReport, setCachedReport } from "@/lib/reportCache";

export function useReports(params?: ListReportsParams) {
  return useQuery({
    queryKey: [
      "reports",
      "list",
      params?.type ?? null,
      params?.tag ?? null,
      params?.symbol ?? null,
      params?.query ?? null,
    ],
    queryFn: () => listReports(params),
    staleTime: 30 * 1000,
  });
}

export async function getReportWithCache(
  reportId: string,
  fetchFn: (id: string) => Promise<ReportDetail> = getReport,
): Promise<ReportDetail> {
  try {
    const report = await fetchFn(reportId);
    await setCachedReport(report).catch(() => {});
    return report;
  } catch (err) {
    const cached = await getCachedReport(reportId);
    if (cached) return cached;
    throw err;
  }
}

export function useReport(reportId: string | null) {
  return useQuery({
    queryKey: ["reports", "detail", reportId],
    queryFn: () => {
      if (reportId === null) {
        throw new Error("reportId is required");
      }
      return getReportWithCache(reportId);
    },
    enabled: reportId !== null,
    staleTime: 60 * 1000,
  });
}
```

- [ ] **Step 4: 跑測試確認通過**

```bash
cd frontend && pnpm test -- useReports reportCache
```

Expected: PASS。

- [ ] **Step 5: 靜態檢查**

```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 errors。

---

## Task 3: ReportDetailPage 快取狀態 badge

**Files:**
- Modify: `frontend/src/pages/ReportDetailPage.tsx`

- [ ] **Step 1: 讀取現有 ReportDetailPage 結構**

讀 `frontend/src/pages/ReportDetailPage.tsx` 確認佈局後再修改。

- [ ] **Step 2: 加入快取狀態 badge**

在報告標題旁加一個 `[已快取]` / `[未快取]` 小 badge。用 `useEffect` 檢查 `getCachedReport(reportId)` 結果。

```typescript
// 在 ReportDetailPage 元件內新增：
import { useEffect, useState } from "react";
import { getCachedReport } from "@/lib/reportCache";

// 元件內部
const [isCached, setIsCached] = useState(false);
useEffect(() => {
  if (!reportId) return;
  getCachedReport(reportId).then((c) => setIsCached(c !== undefined));
}, [reportId, data]); // data 變化時重新檢查

// JSX（標題旁）：
{isCached && (
  <span
    className="ml-2 rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] text-emerald-300"
    data-testid="cache-badge"
  >
    已快取
  </span>
)}
```

- [ ] **Step 3: 靜態檢查**

```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 errors。

---

## Task 4: 後端 probe_base_date 擴充 symbol_statuses

**Files:**
- Modify: `backend/src/alpha_lab/schemas/saved_portfolio.py`
- Modify: `backend/src/alpha_lab/portfolios/service.py`
- Create: `backend/tests/portfolios/test_probe_status.py`

- [ ] **Step 1: 寫 symbol_statuses 分類的失敗測試**

```python
# backend/tests/portfolios/test_probe_status.py
"""probe_base_date symbol_statuses 分類測試。"""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from alpha_lab.portfolios.service import probe_base_date
from alpha_lab.storage.models import PriceDaily, Stock


@pytest.fixture()
def _seed_stocks(db_session: Session) -> None:
    """建立測試用 Stock + PriceDaily。"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    old_date = today - timedelta(days=30)

    # 2330：今日有報價
    db_session.add(Stock(symbol="2330", name="台積電"))
    db_session.add(
        PriceDaily(
            symbol="2330",
            trade_date=today,
            open=100,
            high=105,
            low=99,
            close=103,
            volume=50000,
        )
    )

    # 2317：昨日有報價、今日無（today_missing）
    db_session.add(Stock(symbol="2317", name="鴻海"))
    db_session.add(
        PriceDaily(
            symbol="2317",
            trade_date=yesterday,
            open=90,
            high=92,
            low=89,
            close=91,
            volume=30000,
        )
    )

    # 3008：30 天前有報價、之後無（stale）
    db_session.add(Stock(symbol="3008", name="大立光"))
    db_session.add(
        PriceDaily(
            symbol="3008",
            trade_date=old_date,
            open=2000,
            high=2050,
            low=1980,
            close=2010,
            volume=500,
        )
    )

    # 6666：完全無報價（no_data）— 只建 Stock，不建 PriceDaily

    db_session.add(Stock(symbol="6666", name="虛擬股"))

    db_session.commit()


@pytest.mark.usefixtures("_seed_stocks")
class TestProbeSymbolStatuses:
    def test_today_missing(self) -> None:
        """昨日有價、今日無 → today_missing。"""
        _, missing, statuses = probe_base_date(["2317"], date.today())
        assert "2317" in missing
        assert statuses["2317"] == "today_missing"

    def test_stale(self) -> None:
        """最近報價 > 7 天前 → stale。"""
        _, missing, statuses = probe_base_date(["3008"], date.today())
        assert "3008" in missing
        assert statuses["3008"] == "stale"

    def test_no_data(self) -> None:
        """完全無報價 → no_data。"""
        _, missing, statuses = probe_base_date(["6666"], date.today())
        assert "6666" in missing
        assert statuses["6666"] == "no_data"

    def test_available_not_in_statuses(self) -> None:
        """今日有報價的 symbol 不出現在 statuses。"""
        _, missing, statuses = probe_base_date(["2330"], date.today())
        assert "2330" not in missing
        assert "2330" not in statuses

    def test_mixed(self) -> None:
        """多 symbol 混合場景。"""
        _, missing, statuses = probe_base_date(
            ["2330", "2317", "3008", "6666"], date.today()
        )
        assert "2330" not in missing
        assert statuses.get("2317") == "today_missing"
        assert statuses.get("3008") == "stale"
        assert statuses.get("6666") == "no_data"
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
cd backend && python -m pytest tests/portfolios/test_probe_status.py -v
```

Expected: FAIL — `probe_base_date` 回傳 2-tuple，測試解包成 3-tuple 失敗。

- [ ] **Step 3: 修改 schema 加 symbol_statuses**

在 `backend/src/alpha_lab/schemas/saved_portfolio.py` 修改：

```python
# 在檔案頂部的 import 區加入 Literal
from typing import Literal

# BaseDateProbe class 內新增欄位：
SymbolPriceStatus = Literal["no_data", "stale", "today_missing"]

class BaseDateProbe(BaseModel):
    """..."""
    target_date: date_type
    resolved_date: date_type | None
    today_available: bool
    missing_today_symbols: list[str]
    symbol_statuses: dict[str, SymbolPriceStatus]
```

- [ ] **Step 4: 修改 service.py probe_base_date 回傳 symbol_statuses**

在 `backend/src/alpha_lab/portfolios/service.py` 修改 `probe_base_date`：

```python
STALE_THRESHOLD_DAYS = 7

def probe_base_date(
    symbols: list[str], target_date: date_type
) -> tuple[date_type | None, list[str], dict[str, str]]:
    """檢查 target_date 當日哪些 symbols 缺報價，回傳分類狀態。

    回傳 (resolved_date, missing_today_symbols, symbol_statuses)：
    - resolved_date：所有 symbols 都有報價、且 <= target_date 的最大交易日
    - missing_today_symbols：在 target_date 當日缺報價的 symbol 清單
    - symbol_statuses：每個缺報價 symbol 的原因分類
      - "no_data"：該 symbol 在 DB 完全無報價紀錄
      - "stale"：有報價但最新報價距 target_date > 7 天
      - "today_missing"：有近期報價但今日無
    """

    with session_scope() as session:
        resolved = _resolve_common_base_date(session, symbols, target_date)
        missing_today: list[str] = []
        statuses: dict[str, str] = {}
        for sym in symbols:
            has_today = session.scalar(
                select(PriceDaily.trade_date)
                .where(PriceDaily.symbol == sym)
                .where(PriceDaily.trade_date == target_date)
            )
            if has_today is not None:
                continue
            missing_today.append(sym)
            latest = session.scalar(
                select(PriceDaily.trade_date)
                .where(PriceDaily.symbol == sym)
                .where(PriceDaily.trade_date <= target_date)
                .order_by(PriceDaily.trade_date.desc())
                .limit(1)
            )
            if latest is None:
                statuses[sym] = "no_data"
            elif (target_date - latest).days > STALE_THRESHOLD_DAYS:
                statuses[sym] = "stale"
            else:
                statuses[sym] = "today_missing"
        return resolved, missing_today, statuses
```

- [ ] **Step 5: 修改 API route 以適應新的 3-tuple 回傳**

在 `backend/src/alpha_lab/api/routes/portfolios.py` 修改 probe endpoint，將 `probe_base_date` 的第三個回傳值傳入 `BaseDateProbe`：

```python
# 原本大約是：
# resolved, missing = probe_base_date(symbols_list, today)
# 改為：
resolved, missing, statuses = probe_base_date(symbols_list, today)
# BaseDateProbe(..., symbol_statuses=statuses)
```

- [ ] **Step 6: 跑測試確認通過**

```bash
cd backend && python -m pytest tests/portfolios/test_probe_status.py -v
```

Expected: PASS。

- [ ] **Step 7: 跑既有 probe 相關測試確認無回歸**

```bash
cd backend && python -m pytest tests/ -k probe -v
```

Expected: PASS（既有測試可能需要更新解包數量）。

- [ ] **Step 8: 靜態檢查**

```bash
cd backend && ruff check . && mypy src
```

Expected: 0 errors。

---

## Task 5: 前端 BaseDateConfirmDialog 分類引導

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/portfolio/BaseDateConfirmDialog.tsx`
- Modify: `frontend/src/components/stock/StockActions.tsx`（若需要傳遞 newSymbol）

- [ ] **Step 1: 更新前端 BaseDateProbe 型別**

在 `frontend/src/api/types.ts` 修改：

```typescript
export type SymbolPriceStatus = "no_data" | "stale" | "today_missing";

export interface BaseDateProbe {
  target_date: string;
  resolved_date: string | null;
  today_available: boolean;
  missing_today_symbols: string[];
  symbol_statuses: Record<string, SymbolPriceStatus>;
}
```

- [ ] **Step 2: 增強 BaseDateConfirmDialog 分類顯示**

修改 `frontend/src/components/portfolio/BaseDateConfirmDialog.tsx`：

```tsx
import type { BaseDateProbe, SymbolPriceStatus } from "@/api/types";

export interface BaseDateConfirmDialogProps {
  open: boolean;
  probe: BaseDateProbe | null;
  onCancel: () => void;
  onProceed: () => void;
}

const STATUS_LABELS: Record<SymbolPriceStatus, { label: string; hint: string; color: string }> = {
  no_data: {
    label: "無任何報價紀錄",
    hint: "此股票尚未抓取過資料，請先點 nav「更新報價」執行資料蒐集。",
    color: "text-red-300",
  },
  stale: {
    label: "報價已過時（可能停牌 / 下市）",
    hint: "最近的報價已超過 7 天，該股票可能停牌或下市。",
    color: "text-orange-300",
  },
  today_missing: {
    label: "今日尚未有收盤價",
    hint: "TWSE 通常於交易日 14:00 後公告，盤中或非交易日可能尚未有資料。",
    color: "text-amber-300",
  },
};

function groupByStatus(
  symbols: string[],
  statuses: Record<string, SymbolPriceStatus>,
): Record<SymbolPriceStatus, string[]> {
  const groups: Record<SymbolPriceStatus, string[]> = {
    no_data: [],
    stale: [],
    today_missing: [],
  };
  for (const sym of symbols) {
    const status = statuses[sym] ?? "today_missing";
    groups[status].push(sym);
  }
  return groups;
}

export function BaseDateConfirmDialog({
  open,
  probe,
  onCancel,
  onProceed,
}: BaseDateConfirmDialogProps) {
  if (!open || !probe) return null;

  const groups = groupByStatus(
    probe.missing_today_symbols,
    probe.symbol_statuses,
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      data-testid="save-confirm-dialog"
    >
      <div className="max-w-md rounded border border-slate-700 bg-slate-900 p-5 shadow-xl">
        <h3 className="mb-2 text-base font-semibold text-amber-300">
          部分持股報價不齊
        </h3>

        {(["no_data", "stale", "today_missing"] as const).map((status) => {
          const syms = groups[status];
          if (syms.length === 0) return null;
          const info = STATUS_LABELS[status];
          return (
            <div key={status} className="mb-3" data-testid={`status-group-${status}`}>
              <p className={`text-sm font-medium ${info.color}`}>{info.label}</p>
              <p className="break-all font-mono text-sm text-slate-200">
                {syms.join("、")}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">{info.hint}</p>
            </div>
          );
        })}

        {probe.resolved_date ? (
          <p className="mb-4 text-sm text-slate-300">
            可以以最近所有持股都有報價的日期{" "}
            <strong className="text-slate-100">{probe.resolved_date}</strong>{" "}
            為基準儲存；或先「取消」再補抓報價。
          </p>
        ) : (
          <p className="mb-4 text-sm text-red-300">
            找不到任何「全持股都有報價」的歷史日期，請先補抓報價後再試。
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            data-testid="save-confirm-cancel"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onProceed}
            disabled={probe.resolved_date === null}
            className="rounded border border-amber-500 bg-amber-500/10 px-3 py-1.5 text-sm text-amber-200 hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            data-testid="save-confirm-proceed"
          >
            以 {probe.resolved_date ?? "—"} 為基準繼續
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 靜態檢查**

```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 errors。

---

## Task 6: 既有測試修復 + 新增整合測試

**Files:**
- Modify: `backend/tests/api/test_portfolios_saved.py`（若 probe API 測試解包數量不符）
- Modify: `backend/tests/portfolios/test_service.py`（若 probe 呼叫處需配合 3-tuple）
- Modify: `frontend/tests/e2e/stock-actions.spec.ts`（若 mock probe response 缺新欄位）

- [ ] **Step 1: 修復後端既有 probe 測試**

搜尋所有呼叫 `probe_base_date` 的測試，確認解包改為 3-tuple：

```bash
cd backend && grep -rn "probe_base_date" tests/
```

每個呼叫處從 `resolved, missing = probe_base_date(...)` 改為 `resolved, missing, statuses = probe_base_date(...)`。

API 測試中 mock 的 probe response JSON 若缺 `symbol_statuses`，補上空 dict `{}`。

- [ ] **Step 2: 修復前端 E2E mock**

在 `frontend/tests/e2e/stock-actions.spec.ts` 中，mock probe endpoint 回應需補上 `symbol_statuses`：

```typescript
// 原本的 mock response 形如：
// { target_date: "...", resolved_date: "...", today_available: false, missing_today_symbols: [...] }
// 加上：
// symbol_statuses: { "2317": "today_missing" }
```

- [ ] **Step 3: 跑全部測試**

```bash
cd backend && python -m pytest tests/ -v
cd frontend && pnpm test
```

Expected: ALL PASS。

- [ ] **Step 4: 全面靜態檢查**

```bash
cd backend && ruff check . && mypy src
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 errors。

---

## Task 7: 知識庫 + docs 同步

**Files:**
- Modify: `docs/knowledge/architecture/README.md`
- Create: `docs/knowledge/architecture/report-cache.md`
- Modify: `docs/knowledge/features/tracking/overview.md`
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（Phase 7B.3 狀態更新）

- [ ] **Step 1: 建立 report-cache.md 知識庫條目**

```markdown
---
domain: architecture
updated: 2026-04-18
related: [storage.md]
---

# 報告離線快取（Report Offline Cache）

## 目的

讓使用者在後端未啟動時仍可查看先前瀏覽過的報告。

## 現行實作

前端使用 `idb-keyval` 將 `ReportDetail` 存入 IndexedDB：

- **DB 名稱**：`alpha-lab-reports`，object store `report-cache`
- **Key 格式**：`report:{reportId}`
- **寫入時機**：`useReport` hook 的 `getReportWithCache` 在 API fetch 成功後自動寫入
- **讀取時機**：API fetch 失敗時 fallback 從 IndexedDB 讀取
- **ReportDetailPage** 顯示「已快取」badge 標示快取狀態

## 關鍵檔案

- [frontend/src/lib/reportCache.ts](../../frontend/src/lib/reportCache.ts) — IndexedDB CRUD
- [frontend/src/hooks/useReports.ts](../../frontend/src/hooks/useReports.ts) — `getReportWithCache` + `useReport`

## 修改時注意事項

- `idb-keyval` 的 `createStore` 指定獨立 DB，不與其他 IndexedDB 使用衝突
- 測試環境需 `fake-indexeddb`（devDependency），vitest setup 要 `import "fake-indexeddb/auto"`
- 快取不做自動清理；未來可在 `/settings` 頁加手動清除按鈕
```

- [ ] **Step 2: 更新 architecture/README.md**

在條目表格加入：

```markdown
| `report-cache.md` | 報告 IndexedDB 離線快取機制 | Phase 7B.3 |
```

- [ ] **Step 3: 更新 tracking/overview.md probe UX 說明**

補充 `probe_base_date` 現在回傳 `symbol_statuses`（`no_data` / `stale` / `today_missing`），`BaseDateConfirmDialog` 依分類分組顯示不同引導訊息。

- [ ] **Step 4: 更新設計 spec Phase 7B.3 狀態**

將 Phase 7B.3 從 `未開始` 改為 `✅ 完成（日期）`，並簡述交付物。

- [ ] **Step 5: 檢查 USER_GUIDE.md 是否需更新**

離線快取為自動行為（用戶無需操作），通常不需更新。若需提及，在「報告」章節補一句「已瀏覽過的報告會自動快取，離線時仍可查看」。

---

## Task 8: Commit

- [ ] **Step 1: 中文亂碼掃描**

```bash
grep -r "��" frontend/src backend/src docs/knowledge
```

Expected: 無結果。

- [ ] **Step 2: 給使用者手動驗收指引**

提供 CMD 格式的驗收步驟（見 CLAUDE.md 規範）。

- [ ] **Step 3: 等使用者確認後 commit**

拆成兩個 commit：

```bash
# 1. feat commit（功能實作）
git add frontend/src/lib/reportCache.ts frontend/src/hooks/useReports.ts \
  frontend/src/pages/ReportDetailPage.tsx frontend/src/api/types.ts \
  frontend/src/components/portfolio/BaseDateConfirmDialog.tsx \
  backend/src/alpha_lab/schemas/saved_portfolio.py \
  backend/src/alpha_lab/portfolios/service.py \
  backend/src/alpha_lab/api/routes/portfolios.py \
  frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat: add report IndexedDB cache and enhanced probe symbol statuses"

# 2. docs commit（知識庫 + spec 同步）
git add docs/
git commit -m "docs: sync knowledge base and docs for Phase 7B.3"

# 3. test commit（新增測試）
git add frontend/tests/ backend/tests/
git commit -m "test: add report cache and probe status tests"
```
