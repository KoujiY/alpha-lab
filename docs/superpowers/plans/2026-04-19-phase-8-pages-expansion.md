# Phase 8 — 頁面擴充 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 補齊三個導覽欄缺口：(1) `/stocks` 全市場股票瀏覽列表（搜尋 + 產業篩選 + 收藏），(2) `/settings` 集中管理 localStorage 偏好（教學密度、收藏清單、報告快取清理），(3) `/reports` 新增「時間軸」瀏覽模式（依月份分組、保留現有 grid 為預設）。

**Architecture:**
- 後端僅 1 處小改：`GET /api/stocks` 的 `limit` 上限從 500 提升到 3000，足以一次載入全市場（~2000 檔）。其餘所有改動在前端。
- 前端不引入新元件庫（shadcn 留 Phase 9）；維持純 Tailwind + 既有 hand-coded pattern。
- Settings 不重構既有 `TutorialModeContext`；Settings 頁直接消費 `useTutorialMode` + `favorites.ts` + `reportCache.ts`，避免擴大改動。
- Reports 時間軸用「依月份分組」實作（純前端 group-by），view mode 偏好寫 `localStorage`（key: `alpha-lab:reports-view-mode`）；不影響既有 API。

**Tech Stack:** React 19、React Router v6、TanStack Query v5、Tailwind v4、Vitest、Playwright；後端 FastAPI + SQLAlchemy（僅一個 `Query(le=...)` 數值改動）。

---

## File Structure

### 新增檔案

| 檔案 | 職責 |
|------|------|
| `frontend/src/pages/StocksPage.tsx` | `/stocks` 瀏覽列表頁主元件 |
| `frontend/src/pages/SettingsPage.tsx` | `/settings` 偏好管理頁 |
| `frontend/src/hooks/useStocks.ts` | `useStocks(q?)` TanStack Query hook |
| `frontend/src/hooks/useFavorites.ts` | 反應式收藏 hook（包 `favorites.ts`，提供 React state） |
| `frontend/src/lib/reportTimeline.ts` | `groupReportsByMonth(reports)` 純函式 |
| `frontend/src/components/reports/ReportTimeline.tsx` | Timeline view 容器（月份分組 + sticky heading，直接重用 `ReportCard`） |
| `frontend/tests/lib/reportTimeline.test.ts` | groupReportsByMonth 單元測試 |
| `frontend/tests/lib/useFavorites.test.ts` | useFavorites hook 單元測試 |
| `frontend/tests/components/SettingsPage.test.tsx` | SettingsPage 元件測試（補 review 回饋後加入：快取清空流程、unknown symbol fallback） |
| `frontend/tests/e2e/stocks-list.spec.ts` | `/stocks` E2E |
| `frontend/tests/e2e/settings.spec.ts` | `/settings` E2E |
| `frontend/tests/e2e/fixtures/stocks-list.json` | stocks list fixture |
| `docs/knowledge/features/stocks/README.md` | features/stocks 知識庫子資料夾 README |
| `docs/knowledge/features/stocks/browse-list.md` | `/stocks` 列表頁知識條目 |
| `docs/knowledge/features/settings.md` | `/settings` 偏好管理知識條目 |

### 修改檔案

| 檔案 | 變更內容 |
|------|---------|
| `backend/src/alpha_lab/api/routes/stocks.py` | `list_stocks` 的 `limit` `Query(..., le=500)` → `le=3000` |
| `backend/tests/api/test_stocks.py` | 加 `?limit=3000` 不噴 422 的 case |
| `frontend/src/App.tsx` | 加 `/stocks`、`/settings` 兩條 route |
| `frontend/src/layouts/AppLayout.tsx` | nav 加「股票」「設定」兩個連結 |
| `frontend/src/api/stocks.ts` | `searchStocks` 預設 limit 改可選；新增 `listAllStocks(q?)` 包成 `limit=3000` 呼叫 |
| `frontend/src/pages/ReportsPage.tsx` | 加 view mode toggle（grid / timeline）、整合 `groupReportsByMonth` |
| `frontend/src/components/reports/ReportCard.tsx` | 抽出 inner content 以便 timeline 模式重用（不改 props） |
| `frontend/tests/e2e/reports.spec.ts` | 加「切換時間軸 view」case |
| `docs/knowledge/features/reports/viewer.md` | 補時間軸 view mode 說明 |
| `docs/knowledge/index.md` | 加 features/stocks 與 features/settings 連結 |
| `docs/USER_GUIDE.md` | 補 `/stocks` 與 `/settings` 的使用說明 |
| `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` | Phase 8 狀態列改「✅ 完成（YYYY-MM-DD）」（Phase 完成 commit 時改） |

---

## Task 1: `/stocks` 全市場瀏覽列表頁

**Goal:** 讓使用者可以瀏覽 / 搜尋 / 依產業篩選 / 收藏全市場上市股票，點擊任一檔可跳到既有 `/stocks/:symbol` 個股頁。

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/stocks.py`
- Modify: `backend/tests/api/test_stocks.py`
- Modify: `frontend/src/api/stocks.ts`
- Create: `frontend/src/hooks/useStocks.ts`
- Create: `frontend/src/pages/StocksPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Create: `frontend/tests/e2e/stocks-list.spec.ts`
- Create: `frontend/tests/e2e/fixtures/stocks-list.json`

### Steps

- [ ] **Step 1.1：後端 limit 上限調整 + 失敗測試**
  - 先在 `test_stocks.py` 加一個 `test_list_stocks_accepts_limit_3000`：呼叫 `GET /api/stocks?limit=3000`，預期 200。
  - 跑 `pytest backend/tests/api/test_stocks.py -k accepts_limit_3000`，預期 422（FastAPI validation）→ FAIL。
  - 改 `routes/stocks.py` 的 `Query(LIST_DEFAULT_LIMIT, ge=1, le=500)` → `le=3000`。
  - 再跑 → PASS。
  - `ruff check . && mypy src && pytest backend/tests/api/test_stocks.py`。

- [ ] **Step 1.2：前端 API helper 擴充**
  - `frontend/src/api/stocks.ts` 新增 `listAllStocks(q?: string)` → `searchStocks(q ?? "", 3000)` 的薄包裝（保留語意：列表頁要全量；搜尋頁要 top-N）。
  - 不動既有 `searchStocks` 簽名以免影響 `HeaderSearch`。

- [ ] **Step 1.3：`useStocks` hook**
  - `frontend/src/hooks/useStocks.ts`：
    ```ts
    export function useStocks(q?: string) {
      return useQuery({
        queryKey: ["stocks", "list", q ?? ""],
        queryFn: () => listAllStocks(q),
        staleTime: 5 * 60 * 1000, // 公司基本資料一天才更新
      });
    }
    ```
  - 不寫單測（薄 wrapper，行為由 E2E 涵蓋）。

- [ ] **Step 1.4：`useFavorites` 反應式 hook**
  - 既有 `favorites.ts` 是同步 read/write，UI 切換後不會自動 re-render。新增 `useFavorites`：
    ```ts
    export function useFavorites() {
      const [favorites, setFavorites] = useState<string[]>(() => readFavorites());
      const toggle = useCallback((symbol: string) => {
        setFavorites(toggleFavorite(symbol));
      }, []);
      return { favorites, isFavorite: (s: string) => favorites.includes(s), toggle };
    }
    ```
  - 跨頁同步用 `storage` event listener（同 tab 內由 setState 自動同步）。
  - 寫 `useFavorites.test.ts`：mock `localStorage`、初始空、toggle 加入、再 toggle 移除、`storage` event 觸發 sync。
  - 跑 `pnpm test -- useFavorites` → 先 FAIL（hook 不存在）→ 實作 → PASS。

- [ ] **Step 1.5：`StocksPage` 元件**
  - Layout：上方搜尋框（受控 input，debounce 200ms）+ 產業 select（從 query data 動態取 distinct industry，加「全部」選項）；下方表格 5 欄：☆ / 代號 / 名稱 / 產業 / 上市日期。
  - 點 row 名稱 → `<Link to={\`/stocks/\${symbol}\`}>`。
  - ☆ 欄位接 `useFavorites().toggle`，視覺與 `ReportCard` 的 star 一致（★/☆）。
  - 顯示「共 N 檔（已收藏 M 檔）」摘要。
  - 排序：先依「是否收藏」降冪、再依 symbol 升冪（簡單 stable sort）。
  - 載入 / 錯誤 / 空狀態文案沿用 `ReportsPage` pattern。
  - `data-testid="stocks-page"`、表格 row `data-testid="stock-row-${symbol}"`、收藏按鈕 `data-testid="fav-toggle-${symbol}"`。

- [ ] **Step 1.6：Route + nav link**
  - `App.tsx` 加 `<Route path="/stocks" element={<StocksPage />} />`，注意要放在 `/stocks/:symbol` 之前（react-router v6 會比對最具體的，但一般習慣靜態優先）。
  - `AppLayout.tsx` nav 加 `<Link to="/stocks">股票</Link>`，放在「組合推薦」之前。

- [ ] **Step 1.7：E2E**
  - Fixture `stocks-list.json`：5 檔 sample（2330 台積電 / 2317 鴻海 / 2454 聯發科 / 2412 中華電 / 6505 台塑化），含不同產業。
  - `stocks-list.spec.ts` 三個 case：
    1. 列表渲染、搜尋「2330」只剩台積電
    2. 點 row 跳轉 `/stocks/2330`
    3. 收藏按鈕 toggle 後重新載入頁面狀態仍在（`localStorage` round-trip）
  - 跑 `pnpm e2e -- stocks-list`。

- [ ] **Step 1.8：靜態 + 使用者驗收**
  - `pnpm type-check && pnpm lint && pnpm test && pnpm e2e`。
  - 後端 `ruff check . && mypy src && pytest`。
  - 給使用者驗收指引（CMD 格式）：
    ```cmd
    REM 後端
    cd backend && .venv\Scripts\python.exe -m uvicorn alpha_lab.api.main:app --reload
    REM 前端（另開 cmd）
    cd frontend && pnpm dev
    REM 開瀏覽器到 http://localhost:5173/stocks
    REM 操作：搜尋、產業篩選、收藏 toggle、點 row 跳轉
    ```
  - 等使用者回「Task 1 OK」才 commit。

---

## Task 2: `/settings` 偏好管理頁

**Goal:** 集中呈現目前散落的 localStorage 偏好；讓使用者一個頁面就能調教學密度、清收藏、清報告快取。

**設計原則：** 不引入新的 `SettingsContext`/`UserPreferencesContext`。Settings 頁直接消費既有 source of truth：
- 教學密度 → `useTutorialMode()`（已存在）
- 收藏清單 → `useFavorites()`（Task 1 新增）
- 報告快取 → 直接呼叫 `listCachedReportIds()` / `clearReportCache()`（既有 `lib/reportCache.ts`）

理由：避免重構既有 `TutorialModeContext`（已被 toggle 與 page 多處消費），降低 Phase 8 風險。若未來 settings 項目暴增到 5+ 種再考慮抽 context。

**Files:**
- Create: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppLayout.tsx`
- Create: `frontend/tests/e2e/settings.spec.ts`

### Steps

- [ ] **Step 2.1：`SettingsPage` 元件骨架**
  - 三個 section card：
    1. **教學密度**（顯示目前 mode + 三顆 radio 按鈕：完整 / 精簡 / 關閉，點擊呼叫 `setMode`）
    2. **收藏股票**（列出 `favorites`，每筆一個 row：代號 + 名稱（要 `useStocks` 拿名稱對應）+「移除」按鈕；空清單顯示提示文案）
    3. **離線報告快取**（顯示「已快取 N 篇」 + 「清空」按鈕；按下二次確認後呼叫 `clearReportCache()` 並刷新計數）
  - `data-testid="settings-page"`，每 section 用 `<section data-testid="settings-tutorial">` 等標識。

- [ ] **Step 2.2：收藏 row 顯示名稱**
  - 用 Task 1 的 `useStocks()`（不傳 q）取全表，用 `Map<symbol, name>` 對應。
  - 若 stocks 還沒載入完，顯示「2330（載入中...）」fallback。

- [ ] **Step 2.3：報告快取計數**
  - `useEffect` mount 時 `listCachedReportIds()` 取一次，存 local state。
  - 「清空」按鈕：`window.confirm("確定清空所有離線報告快取？")` → `await clearReportCache()` → setCount(0)。

- [ ] **Step 2.4：Route + nav link**
  - `App.tsx` 加 `<Route path="/settings" element={<SettingsPage />} />`。
  - `AppLayout.tsx` nav 加 `<Link to="/settings">設定</Link>`，放在「回顧」之後（最右側功能列）。
  - 既有 nav 右側的 `TutorialModeToggle`、`NavUpdatePricesButton`、`HeaderSearch` 不動（它們是「快捷操作」，與「設定頁」並存合理）。

- [ ] **Step 2.5：E2E**
  - `settings.spec.ts` 三個 case：
    1. 切換教學密度 radio → header 的 `TutorialModeToggle` 文字同步變化（驗證 context 共用）
    2. 從個股頁收藏 2330 → 進 settings 看到該筆 → 按移除 → 清單變空
    3. 「清空快取」按鈕點擊後計數歸零（mock 一次 `getReport` 呼叫先寫入 IndexedDB）
  - 跑 `pnpm e2e -- settings`。

- [ ] **Step 2.6：靜態 + 使用者驗收**
  - `pnpm type-check && pnpm lint && pnpm test && pnpm e2e`。
  - 驗收指引（CMD）：
    ```cmd
    cd frontend && pnpm dev
    REM 開 http://localhost:5173/settings
    REM 操作：切換教學密度、收藏與移除、清空報告快取
    ```
  - 等使用者回「Task 2 OK」才 commit。

---

## Task 3: `/reports` 時間軸瀏覽模式

**Goal:** 在現有報告列表上加「時間軸」view mode，依月份分組，左側顯示月份標籤，右側垂直列出該月報告卡。Grid 仍為預設，Timeline 為可選。

**設計：**
- View mode 狀態存 `localStorage`（key `alpha-lab:reports-view-mode`，值 `"grid" | "timeline"`）
- 分組邏輯為純函式 `groupReportsByMonth(reports) -> Array<{ month: "YYYY-MM", items: ReportMeta[] }>`，排序：月份降冪、月份內保留 API 原排序（已依 date desc）
- Timeline UI 用 CSS Grid 兩欄（`grid-cols-[120px_1fr]`），月份標籤 sticky top（`position: sticky`）
- 不新增後端 API，不影響現有 filter/search（toggle 只改渲染方式）

**Files:**
- Create: `frontend/src/lib/reportTimeline.ts`
- Create: `frontend/tests/unit/reportTimeline.test.ts`
- Modify: `frontend/src/pages/ReportsPage.tsx`
- Modify: `frontend/tests/e2e/reports.spec.ts`

### Steps

- [ ] **Step 3.1：`groupReportsByMonth` 失敗測試**
  - `frontend/tests/unit/reportTimeline.test.ts`：
    ```ts
    it("groups reports by YYYY-MM, sorted desc", () => {
      const reports = [
        { id: "a", date: "2026-04-15", ... } as ReportMeta,
        { id: "b", date: "2026-04-01", ... },
        { id: "c", date: "2026-03-20", ... },
      ];
      expect(groupReportsByMonth(reports)).toEqual([
        { month: "2026-04", items: [reports[0], reports[1]] },
        { month: "2026-03", items: [reports[2]] },
      ]);
    });

    it("preserves within-month order from input", () => { ... });
    it("returns empty array for empty input", () => { ... });
    ```
  - 跑 `pnpm test -- reportTimeline` → FAIL（module 不存在）。

- [ ] **Step 3.2：實作 `groupReportsByMonth`**
  - `frontend/src/lib/reportTimeline.ts`：
    ```ts
    import type { ReportMeta } from "@/api/types";

    export interface ReportMonthGroup {
      month: string; // "YYYY-MM"
      items: ReportMeta[];
    }

    export function groupReportsByMonth(reports: ReportMeta[]): ReportMonthGroup[] {
      const map = new Map<string, ReportMeta[]>();
      for (const r of reports) {
        const month = r.date.slice(0, 7);
        const bucket = map.get(month) ?? [];
        bucket.push(r);
        map.set(month, bucket);
      }
      return [...map.entries()]
        .sort(([a], [b]) => (a < b ? 1 : -1))
        .map(([month, items]) => ({ month, items }));
    }
    ```
  - 跑測試 → PASS。

- [ ] **Step 3.3：View mode 狀態管理**
  - 在 `ReportsPage.tsx` 加：
    ```ts
    const VIEW_KEY = "alpha-lab:reports-view-mode";
    type ViewMode = "grid" | "timeline";

    function readInitialView(): ViewMode {
      if (typeof window === "undefined") return "grid";
      const raw = window.localStorage.getItem(VIEW_KEY);
      return raw === "timeline" ? "timeline" : "grid";
    }

    const [viewMode, setViewMode] = useState<ViewMode>(readInitialView);
    useEffect(() => {
      window.localStorage.setItem(VIEW_KEY, viewMode);
    }, [viewMode]);
    ```

- [ ] **Step 3.4：View toggle UI**
  - 放在搜尋框右側（或 type filter 同一排的最右）：
    ```tsx
    <div className="flex rounded border border-slate-700 text-xs">
      <button
        aria-pressed={viewMode === "grid"}
        onClick={() => setViewMode("grid")}
        className={...}
        data-testid="view-grid"
      >
        🔲 卡片
      </button>
      <button
        aria-pressed={viewMode === "timeline"}
        onClick={() => setViewMode("timeline")}
        className={...}
        data-testid="view-timeline"
      >
        📅 時間軸
      </button>
    </div>
    ```

- [ ] **Step 3.5：Timeline 渲染分支**
  - `ReportsPage.tsx` 在 `data && data.length > 0` 分支內：
    ```tsx
    {viewMode === "grid" ? (
      <ul className="grid gap-3 md:grid-cols-2">...</ul>
    ) : (
      <TimelineView reports={data} onToggleStar={...} onDelete={...} />
    )}
    ```
  - `TimelineView` 可直接寫在同檔，或抽成 `frontend/src/components/reports/ReportTimeline.tsx`（建議抽出，~50 行內）：
    ```tsx
    const groups = groupReportsByMonth(reports);
    return (
      <div className="space-y-6" data-testid="reports-timeline">
        {groups.map((g) => (
          <section key={g.month}>
            <h2 className="sticky top-0 bg-slate-950 py-2 text-sm font-semibold text-slate-400">
              {g.month}
            </h2>
            <ul className="space-y-2">
              {g.items.map((meta) => (
                <ReportCard key={meta.id} meta={meta} onToggleStar={...} onDelete={...} />
              ))}
            </ul>
          </section>
        ))}
      </div>
    );
    ```
  - 如果抽元件，File Structure 表要加上 `frontend/src/components/reports/ReportTimeline.tsx`。

- [ ] **Step 3.6：E2E**
  - `reports.spec.ts` 補一個 case：
    1. 進 `/reports`，預設是 grid（`view-grid` aria-pressed=true）
    2. 點「📅 時間軸」→ `reports-timeline` 可見，月份 heading `2026-04` / `2026-03` 都有
    3. Reload 頁面 → 仍在 timeline（localStorage 生效）
  - 跑 `pnpm e2e -- reports`。

- [ ] **Step 3.7：靜態 + 使用者驗收**
  - `pnpm type-check && pnpm lint && pnpm test && pnpm e2e`。
  - 驗收指引（CMD）：
    ```cmd
    cd frontend && pnpm dev
    REM 開 http://localhost:5173/reports
    REM 操作：切換卡片/時間軸、reload 驗證偏好、月份 sticky header
    ```
  - 等使用者回「Task 3 OK」才 commit。

---

## Task 4: 知識庫與使用者文件同步

**Goal:** 依 CLAUDE.md §「知識庫（MANDATORY）」規範，把 Phase 8 產生的新功能落進 `docs/knowledge/`；更新 `USER_GUIDE.md` 與設計 spec 的 Phase 表。

**Files:**
- Create: `docs/knowledge/features/stocks/README.md`
- Create: `docs/knowledge/features/stocks/browse-list.md`
- Create: `docs/knowledge/features/settings.md`
- Modify: `docs/knowledge/features/reports/viewer.md`
- Modify: `docs/knowledge/index.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`

### Steps

- [ ] **Step 4.1：`features/stocks/` 子資料夾**
  - README.md：簡介此 domain 涵蓋「股票列表瀏覽 / 搜尋」，列出子條目。
  - `browse-list.md`：依專案 frontmatter 範本撰寫，內容包含：
    - **目的**：讓使用者全市場瀏覽 / 搜尋 / 依產業篩選 / 收藏。
    - **現行實作**：前端 `StocksPage` + `useStocks`；後端沿用 `GET /api/stocks`；limit 上限 3000；收藏存 `alpha-lab:favorites`（localStorage）。
    - **關鍵檔案**：列出 `pages/StocksPage.tsx` / `hooks/useStocks.ts` / `hooks/useFavorites.ts` / `api/stocks.ts` / 後端 `routes/stocks.py`。
    - **修改時注意事項**：全量載入設計假設 ~2000 檔可接受，若未來 symbol 數暴增需改 cursor-based 或虛擬捲動；收藏 key `alpha-lab:favorites` 與 `/settings` 頁共用，改 key 要一起搬。

- [ ] **Step 4.2：`features/settings.md`**
  - 目的、現行實作（聚合 tutorial-mode / favorites / reportCache 三 source；不自建 context）、關鍵檔案、修改時注意（新增 settings 項目的 SOP：加到 SettingsPage + 若跨頁共用才考慮抽 context）。

- [ ] **Step 4.3：`features/reports/viewer.md` 補時間軸說明**
  - 新增一節「View mode：grid / timeline」，說明 `groupReportsByMonth` 與 `alpha-lab:reports-view-mode` 偏好 key。

- [ ] **Step 4.4：`knowledge/index.md`**
  - 在目錄樹中加入 `features/stocks/`、`features/settings.md` 兩個入口。

- [ ] **Step 4.5：`USER_GUIDE.md`**
  - 加「股票瀏覽（`/stocks`）」「設定（`/settings`）」「分析回顧時間軸」三段使用說明。
  - 維持既有 Windows CMD / 瀏覽器操作語氣。

- [ ] **Step 4.6：設計 spec Phase 表**
  - `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` 第 476 行 Phase 8 狀態：「未開始」→「✅ 完成（YYYY-MM-DD）」，交付物列描述對齊實作（`/stocks` 表格 + 收藏 / `/settings` 偏好中心 / `/reports` 時間軸 view mode / `alpha-lab:reports-view-mode` localStorage）。
  - 此 step 在 Phase 8 最終 commit 時做（前三個 task 的知識庫同步 commit 時不動 spec 表）。

- [ ] **Step 4.7：commit 分類**
  - `feat:` commit 只含功能程式碼與必要測試
  - `docs:` commit 收斂所有知識庫、USER_GUIDE、spec 變更
  - 每 Task 的 `feat` commit 獨立，最後收一個 `docs: sync knowledge base and docs for Phase 8` 總 commit
  - 禁止 scope 括號、禁止 `feat(stocks):` 這類寫法（CLAUDE.md §Commit 前檢查 規則 4）

---

## Phase 完成節點

1. Task 1 / 2 / 3 / 4 全部驗收通過
2. 全部靜態檢查通過（frontend `tsc --noEmit` + `pnpm lint`；backend `ruff check . && mypy src`）
3. 全部測試通過（frontend `pnpm test && pnpm e2e`；backend `pytest`）
4. 中文亂碼掃描 `grep -r "��" .` 無命中
5. 使用者回「Phase 8 驗證通過」
6. `docs: sync ...` 收尾 commit + 更新 spec Phase 表
7. 等使用者指示下一個 Phase（Phase 9：UI 升級），才啟動 Phase 9 計畫撰寫

---

## 已知風險與決策備忘

- **全量載入 vs pagination**：選擇一次載入 3000 檔是為了實作簡單 + 體驗流暢（~200KB JSON）。若日後 symbol 數暴增或要支援 OTC / 興櫃，需改 cursor / virtualized scroll。
- **不抽 `SettingsContext`**：目前只有 3 項偏好，抽 context 價值低、會動到既有 `TutorialModeContext` 用法。當偏好項目 ≥ 5 或需跨 tab 同步複雜邏輯時再考慮。
- **Timeline sticky header 深色背景**：用 `bg-slate-950`（layout 根色）以確保 sticky 時不透字，若日後背景改色要同步更新。
- **Favorites 跨 tab 同步**：`useFavorites` 用 `storage` event 做同步；若 Phase 9 改 shadcn 後還是 localStorage，可沿用；改成 IndexedDB 才需要重寫。
- **Phase 9 預留空間**：此 Phase 產出的 icon 佔位（☆、🔲、📅）全走 emoji，Phase 9 會改 icon button（lucide-react 等）。命名 / 結構不擋 Phase 9 遷移。

---

## 與 spec 的落差備忘

對照 `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` 時注意的幾個點，先在此備檔避免未來 Claude 以為是遺漏：

- **「回顧模式三種瀏覽方式」解讀（spec §10，第 376 行）**
  Spec 原文列「時間軸 / 列表 / 搜尋 三種瀏覽方式」。本 Phase 採「列表（grid）+ 時間軸」兩個顯式 view mode toggle，**搜尋視為永遠存在的頂部篩選列**而非第三種 view。理由：獨立「搜尋頁」與「列表頁帶搜尋框」UX 體感重疊、對 local 工具價值低；若未來需求明確再擴第三模式。

- **路由命名 `/history` vs `/reports`（spec §9.1，第 325-326 行）**
  Spec 寫 `/history` / `/history/:reportId`，但 Phase 4 實作落地為 `/reports` / `/reports/:reportId`。此偏離為 Phase 4 既成事實，本 Phase 沿用既有 `/reports`，不做 route rename（會動到既存報告 URL、IndexedDB 快取 key 形式、所有 E2E），非 Phase 8 造成亦非 Phase 8 要解決。若未來要統一，需單獨 migration phase。

- **Phase 4 遺留 TODO「TWSE 產業代碼→中文名稱映射表」（spec §15 Phase 4 列，第 468 行）**
  Phase 4 備註「留待 Phase 5/6 再補」，但 Pre-Phase 4 的 `twse_stock_info` collector（TWSE OpenAPI `t187ap03_L`）回傳的「產業別」本身就是中文字串（如「半導體業」「金融保險業」），已 upsert 進 `stocks.industry`。**此 TODO 實質上已由 Pre-Phase 4 解決**。本 Phase 的 `/stocks` 產業 filter 直接消費 `stocks.industry` 原值，不需額外 mapping 表。建議 Phase 8 最終 commit 時，順手把 spec 第 468 行的 TODO 文字改為「產業別已於 Pre-Phase 4 隨 `twse_stock_info` collector 中文化寫入 `stocks.industry`」。

- **HomePage 未更動**
  本 Phase 僅在 nav 加 `/stocks` `/settings` 連結，不觸碰 `HomePage`。Spec 無強制要求首頁列新頁面；若視覺上希望首頁顯示新 quick-link 卡片屬於 polish，留待 Phase 9 UI 升級一併處理。

