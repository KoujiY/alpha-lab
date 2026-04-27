# Phase 9 — UI 升級（shadcn/ui + lightweight-charts + 加入組合 wizard + soft limits）

- **Phase**：9
- **計畫日期**：2026-04-18
- **前置 Phase**：Phase 8 已 merge 至 main（PR #3）
- **工作分支**：`claude/phase-9-ui-upgrade-hvSc7`

## 目標（對齊 spec §15 Phase 9）

把 Phase 0～8 累積的「原生 Tailwind + emoji button + recharts 折線 K 線 + 一步到位加入組合」統一升級為：

1. shadcn/ui 元件庫（選幾個高頻的）導入，替換原生 `<button>` / 原生 `<select>` / 自寫 `confirm` dialog
2. K 線圖改用 `lightweight-charts`（取代 `PriceChart` 的 recharts LineChart；OHLCV 一次畫出來）
3. 列表 / 卡片 / 詳情 / header 的動作按鈕改 icon button（lucide-react），搭 `aria-label` + tooltip
4. 「加入組合」升級為兩步 wizard：**選基底** → **預覽 delta-weight + 手動微調 + soft-limit warning** → 建立
5. 三個 soft limit warning（非 hard block）：持股 > 20、單檔 > 40%、單檔 < 0.5%

## 設計取捨與重要決策

### 1. shadcn/ui 範圍（先縮小）

專案只有 ~10 頁 + 30 檔元件，不做「把所有 `<button>` 都換成 `<Button>`」的全量遷移。本 Phase 只遷**高頻、複用率高、或 UX 痛點明顯**的原件：

| shadcn primitive | 替換對象 | 原因 |
|---|---|---|
| `Button` | `StockActions`、`PortfoliosPage` save 區、`PortfolioTrackingPage` 刪除、`ReportsPage` filter/view toggle 等 | 統一焦點 / disabled / variant |
| `Dialog` | `BaseDateConfirmDialog`（現自刻 fixed overlay）、加入組合 wizard、`window.confirm`（刪報告 / 刪組合 / 清快取） | 焦點鎖定、ESC 關閉、A11y |
| `Tooltip` | icon button 的 hover 提示（Phase 9 新增） | 配合 icon button |
| `Select` | `StocksPage` 產業下拉、`SettingsPage` 若有後續需要 | 鍵盤操作、搜尋 |
| `RadioGroup` | `SettingsPage` 教學密度三選一 | 鍵盤操作 |
| `Input` | 只在 wizard 新增「每檔權重微調」用；其他 `<input type="search">` 保留原生（沒有痛點） |

**不做**：`Card`、`Tabs`（`PortfolioTabs` 語意明確、E2E 已依賴目前結構，避開）、`Table`（資料表密度自訂較精準）、`Toast`（目前沒有 toast 需求）。

### 2. shadcn/ui 安裝方式

shadcn 的「CLI init + copy source」模式在 Tailwind v4 下可正常運作（v4 從 `shadcn@2.x` 起被 first-class 支援）。步驟：

1. `pnpm dlx shadcn@latest init`（選：Tailwind v4、RSC=No、alias `@/components/ui`、base color slate）
2. `pnpm dlx shadcn@latest add button dialog tooltip select radio-group`
3. 產生的 source 會落在 `frontend/src/components/ui/`；依賴 `class-variance-authority`、`tailwind-merge`、`clsx`、`@radix-ui/*`、`lucide-react` 由 CLI 自動裝
4. `frontend/src/lib/utils.ts` 放 `cn()` helper（由 CLI 產）
5. Tailwind v4 自動 scan `src/**`，不需要手改 `content` 設定；shadcn 的 CSS variables 會 inject 到 `src/index.css`

**回退方案**：若 shadcn CLI 在當前 pnpm/Tailwind v4 組合下失敗（例如 Radix 與 React 19 相容問題），改走「手動 copy source」：從 shadcn docs 複製元件 tsx 到 `components/ui/`，手動 `pnpm add` 對應 radix/cva 依賴。兩個 path 都保留。

### 3. K 線圖：只換 `PriceChart`

**只遷** `components/stock/PriceChart.tsx`。其他圖表（`RevenueSection`、`InstitutionalSection`、`PerformanceChart`、`ScoreRadar`）**繼續用 recharts**。理由：

- `lightweight-charts` 專為金融 OHLC / volume 設計，長條圖 / 雷達 / NAV 曲線用它只會更慢更囉嗦
- `PriceChart` 目前只畫 close 折線，遷移後順便升級為 OHLC K 線（`prices` overview 已回傳 OHLCV）
- `PerformanceChart` 的 NAV 曲線 + parent 虛線 + fork 垂直線有複雜自訂邏輯（`performanceChartSeries.ts`），recharts 繼續用較穩

`lightweight-charts` v4.x（MIT、tree-shakeable、~35KB gz）是安全選擇。新元件：

- 路徑：`frontend/src/components/stock/PriceChart.tsx`（就地改）
- API：同樣吃 `DailyPricePoint[]`（已含 OHLCV），不動上游
- Chart type：candlestick（預設）；若資料少於 10 筆退回折線 fallback
- Section `aria-label="股價走勢"` 不變，E2E 仍用 `getByRole('region', {name: "股價走勢"})` 取得

### 4. Icon button 遷移與 `data-testid` 保留

所有現有的動作按鈕改 icon button（lucide-react），但**所有 `data-testid` 一字不改**。對照表：

| 位置 | 現在 | 遷移後 icon + label |
|---|---|---|
| `StockActions` 收藏 | `☆ 收藏` / `★ 已收藏` | `<Star>` / `<StarFill>` + `aria-label` + tooltip「收藏」/「取消收藏」 |
| `StockActions` 加入組合 | 文字「加入組合」 | `<FolderPlus>` + 文字（保留文字，因為較隱晦） |
| `ReportCard` / `ReportDetailPage` star/delete | `☆/★` + 文字「刪除」 | `<Star>` / `<StarFill>` / `<Trash2>` + tooltip |
| `ReportsPage` view toggle | `🔲 卡片` / `📅 時間軸` | `<LayoutGrid>` / `<CalendarDays>` icon + tooltip；label 收進 tooltip |
| `SettingsPage` 收藏移除 | 文字「移除」 | `<X>` icon + tooltip「移除收藏」 |
| `PortfolioTrackingPage` 刪除 | 文字「刪除」 | `<Trash2>` icon + tooltip |
| `StocksPage` row 收藏 | `☆ / ★` | `<Star>` icon（保留文字尺寸） |

Icon button 統一用 `components/ui/icon-button.tsx` wrapper（包 `Button variant="ghost" size="icon"` + Tooltip + `aria-label`），外層仍是 shadcn Button，所以 `data-testid` 透過 `asChild` 或 prop spread 傳下去。

### 5. 「加入組合」Wizard UI

把 `StockActions` 裡的 popover（目前是 inline dropdown + 一個 weight input + 直接 POST）改成 modal 兩步 wizard：

**Step 1 — 選基底**：列已儲存組合（含目前持股數摘要）；可選「建立全新組合」（目前沒有此能力，本 Phase 不做，只留介面 hook，標 TODO）。

**Step 2 — 預覽 + 微調**：
- 呼叫 `buildMergedHoldings({ existing, symbol, name, delta: 10% })` 產出預覽
- 顯示完整權重表：`symbol / name / 原權重 / 套用後權重 / 變動百分比 / 手動覆寫 input`
- **手動覆寫**：每列一個 `<Input type="number">`；改一列，其餘持股按比例 re-normalize 到 sum=100%（不包括使用者正在改的那列；若使用者改超過 100%，顯示紅色 warning）
- **Soft-limit warnings**（見下節）即時顯示
- 按「確定建立」→ 呼叫原有 `saveRecommendedPortfolio(..., { allowFallback: false })` flow（包含 probe base-date → 彈 `BaseDateConfirmDialog`）

**結構**：
- `components/portfolio/AddToPortfolioWizard.tsx`（新檔）
- `lib/weightAdjust.ts`（新檔）：`rebalanceAfterEdit(existing, editedSymbol, editedWeight): SavedHolding[]` 純函式 + 單元測試
- `lib/softLimits.ts`（新檔）：`checkSoftLimits(holdings): SoftLimitWarning[]` 純函式 + 單元測試

**`data-testid` 保留 / 新增**：
- 保留：`add-to-portfolio`（觸發按鈕）、`pick-portfolio-${id}`（step1 選組合）
- 保留：`save-confirm-dialog` / `save-confirm-cancel` / `save-confirm-proceed`（base-date dialog，wizard step 2 之後觸發）
- 新增：`wizard-step-1` / `wizard-step-2` / `wizard-back` / `wizard-confirm` / `wizard-weight-input-${symbol}` / `wizard-warning-${code}`

### 6. Soft limit warnings

`lib/softLimits.ts`：

```ts
type SoftLimitCode = "too_many_holdings" | "single_weight_too_high" | "weight_too_small";
interface SoftLimitWarning {
  code: SoftLimitCode;
  message: string;
  symbols?: string[];
}

checkSoftLimits(holdings): SoftLimitWarning[]
```

規則：
- `holdings.length > 20` → `too_many_holdings`
- 任一 `weight > 0.40` → `single_weight_too_high`（列出 symbols）
- 任一 `weight < 0.005` → `weight_too_small`（列出 symbols）

顯示位置：
- **加入組合 wizard step 2** 下方（即時反映使用者微調）
- **儲存推薦組合**（`PortfoliosPage` save button 按下時用預 check，若有 warning 先彈 `Dialog` 顯示，有「仍要儲存」/「取消」選項）

**不包含**：`PortfolioTrackingPage` 已儲存組合的事後警告（未來 Phase 可加；本 Phase 聚焦新增流程）。

## 與 Phase 8 產物的相依

**不能改動**：
- `data-testid`：`favorite-toggle` / `add-to-portfolio` / `pick-portfolio-*` / `star-toggle` / `delete-report` / `view-grid` / `view-timeline` / `cache-clear` / `cache-count` / `delete-portfolio` / `save-portfolio-report` / `save-portfolio-button` / `save-confirm-*` / `settings-tutorial` / `favorite-row-*` / `favorite-remove-*` / `stocks-search` / `stocks-industry` / `stock-row-*` / `fav-toggle-*` / `reports-search`
- `aria-label="XX"` 的 section 名稱（`stock-page.spec.ts` 用 `getByRole('region', { name: 'XX' })`）
- `groupReportsByMonth` signature（`lib/reportTimeline.ts`）
- `buildMergedHoldings` signature（wizard 會呼叫）
- `useFavorites` hook API
- `TutorialModeContext` 值

**會被遷移 / 重寫（內部實作換但對外介面不變）**：
- `StockActions` 的 picker popover → 改成 wizard dialog（但對外仍是 `<StockActions meta={meta}>`）
- `BaseDateConfirmDialog` → 用 shadcn Dialog 重寫 body，但 `data-testid` 不動、props 不動
- `SettingsPage` 教學密度三顆 radio → shadcn RadioGroup，`data-testid="tutorial-option-*"` 保留
- `SettingsPage` 清快取的 `window.confirm` → shadcn AlertDialog，`data-testid="cache-clear"` 保留；新增 `data-testid="cache-clear-confirm"`
- `ReportsPage` view toggle 與刪除 `window.confirm` → icon button + shadcn AlertDialog；testid 保留

## Task 拆分

拆成四個 task，**Task 9A 必須最先做**（建立 shadcn 基礎設施；之後任務依賴它）：

### Task 9A — shadcn 基礎設施 + icon button 遷移（主要做前端）

**前後端**：前端 only。

**範圍**：
1. init shadcn，add `button`、`dialog`、`tooltip`、`select`、`radio-group`、`alert-dialog`（額外；清快取 / 刪除類用）
2. 裝 `lucide-react`（shadcn 會裝，二次確認版本）
3. 新增 `components/ui/IconButton.tsx` wrapper（Button + Tooltip + aria-label）
4. 依上表遷移所有 icon button 位置（`StockActions` 收藏按鈕、`ReportCard` star+delete、`ReportDetailPage` star+delete、`PortfolioTrackingPage` delete、`StocksPage` fav toggle、`ReportsPage` view toggle、`SettingsPage` favorite-remove 與 cache-clear）
5. 把 `BaseDateConfirmDialog` 遷到 shadcn `Dialog`，`data-testid` 不動；把 `SettingsPage` 教學 radio 遷到 `RadioGroup`；把 `StocksPage` 產業下拉遷到 `Select`
6. 把 `window.confirm`（刪報告 / 刪組合 / 清快取）替換為 shadcn `AlertDialog`

**驗收**：
- `pnpm type-check` / `pnpm lint` / `pnpm test` / `pnpm e2e` 全綠
- 視覺：收藏按鈕是圖標、hover 有 tooltip；刪除彈出 AlertDialog（非 window.confirm）
- 所有既有 `data-testid` 仍然能 query 到

**Commit**：
- `chore: add shadcn/ui primitives and lucide-react`
- `refactor: migrate action buttons to icon buttons`
- `refactor: replace window.confirm with shadcn AlertDialog`

### Task 9B — K 線圖改用 lightweight-charts

**前後端**：前端 only。

**範圍**：
1. `pnpm add lightweight-charts`
2. 重寫 `components/stock/PriceChart.tsx`：OHLCV candlestick（上層 candlestick、下層 volume bar）；container resize 用 `ResizeObserver`
3. 維持 `section aria-label="股價走勢"`；若 `points.length === 0` 顯示空資料占位；若 `< 10` 退回折線 fallback
4. 新增 `frontend/tests/components/PriceChart.test.tsx`（unit；驗證空資料占位顯示）—不驗視覺，lightweight-charts 走 `canvas` 無 DOM 可 assert

**驗收**：K 線圖可視、volume bar 可視；E2E `stock-page.spec.ts` 維持通過（只 assert heading / regions，不 assert chart 內部）。

**Commit**：`feat: migrate price chart to lightweight-charts`

### Task 9C — AddToPortfolio Wizard + soft-limit warnings

**前後端**：前端 only（後端已有 `saveRecommendedPortfolio` / `probeBaseDate` 所需 API；不動）。

**範圍**：
1. 新 `lib/weightAdjust.ts`：`rebalanceAfterEdit` 純函式 + unit test
2. 新 `lib/softLimits.ts`：`checkSoftLimits` 純函式 + unit test
3. 新 `components/portfolio/AddToPortfolioWizard.tsx`：shadcn Dialog + 兩步；step 2 裡引用 `rebalanceAfterEdit` / `checkSoftLimits` / `buildMergedHoldings`
4. 改 `StockActions`：`add-to-portfolio` 按鈕現在 open Wizard（不再是 inline popover）。舊的 weight input / remainder hint 移到 wizard step 2
5. 改 `PortfoliosPage`：`handleSaveClick` 在呼叫 `probeBaseDate` 之前先 `checkSoftLimits`；若有 warning，先彈 shadcn Dialog（新 `SoftLimitWarningDialog` 元件）讓使用者「仍要儲存」或「取消」
6. 新 E2E `frontend/tests/e2e/portfolio-wizard.spec.ts`：
   - 開 wizard、選 base、預覽權重、手動改一檔看 re-normalize、觸發 soft limit（塞 21 檔 / 50% / 0.1% 三情境）、按確認 → 最終 POST

**驗收**：
- wizard 能完整走完；預覽數字加總仍 = 100%
- soft limit warning 出現但不阻擋儲存
- 既有 `stock-actions.spec.ts`「加入組合：今日報價不齊」test 需要小改（因為 wizard step 2 多一步 `wizard-confirm`），在這個 task 一起修

**Commit**：
- `feat: add weight adjust and soft limit helpers`
- `feat: add two-step add-to-portfolio wizard with soft limit warnings`
- `test: update stock-actions e2e for wizard flow`

### Task 9D — Docs / knowledge / spec 同步

**前後端**：docs only。

**範圍**：
1. 更新 `docs/knowledge/features/portfolio/recommender.md`、`weights.md`、新增 `features/portfolio/wizard.md`
2. 更新 `docs/knowledge/features/data-panel/ui-layout.md`（K 線段）
3. 更新 `docs/knowledge/features/reports/viewer.md`（icon button / AlertDialog 段）
4. 更新 `docs/knowledge/features/settings.md`（shadcn RadioGroup / AlertDialog）
5. 更新 `docs/knowledge/features/stocks/browse-list.md`（icon button）
6. `docs/USER_GUIDE.md`：加入組合流程章節更新成 wizard
7. `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` Phase 9 row 狀態改 `✅ 完成（2026-04-20）`

**Commit**：`docs: sync knowledge base and guide for Phase 9`

## 風險 / 未解

1. **shadcn CLI 在 Tailwind v4 + React 19 下的相容性**：官方自 2025 中起支援，實測再看；若爆就走手動 copy。
2. **lightweight-charts 的 server-side rendering**：只在 `useEffect` 裡 init，SSR 不受影響；Vite build 不會觸發。
3. **Wizard 的 weight re-normalize 體感**：使用者輸入 50%，其他 9 檔按比例縮放；若原本只有 1 檔 100%，公式要 guard 除零（`rebalanceAfterEdit` 必須 handle）。
4. **soft limit 是 warning 不是 block**：必須明確在 UI 上讓使用者有「仍要儲存」的路徑；不得誤擋合法用例（例如使用者就是想 ETF-like 持 25 檔）。
5. **icon button A11y**：每顆都必須有 `aria-label`（不是只有 tooltip；tooltip 對螢幕閱讀器不夠）。Unit test 加 `getByRole('button', { name: '...' })` assert。

## 檢查清單（Phase 結束前）

- [ ] Task 9A / 9B / 9C 三個 task 使用者各自驗收通過再 commit
- [ ] `pnpm type-check` 0 error
- [ ] `pnpm lint` 0 error
- [ ] `pnpm test`、`pnpm e2e` 全綠
- [ ] 所有列出的 `data-testid` 仍存在
- [ ] knowledge / spec / USER_GUIDE 同步
- [ ] 最後 push & 開 PR

---

## 2026-04-18 補充：review 後追補範圍

第一輪驗收 / review 後發現兩類遺漏，已在同一 PR 內補齊：

**A. Spec 缺口（plan 承諾過但第一輪漏做）**

- `AddToPortfolioWizard` step 1 `pick-portfolio-*` 原為裸 `<button>` → 改 shadcn `Button variant="outline"`
- `AddToPortfolioWizard` step 2 權重 input 原為裸 `<input type="number">` → 改 shadcn `Input`（新 scaffold `components/ui/input.tsx`）

**B. Plan 沒列入但第一輪時評估應一起遷的遺留元件**

- `HoldingsTable` 查看理由 toggle → Button ghost
- `ReportsPage` type filter 6 按鈕 → Button with `aria-pressed`
- `ScreenerPage` factor sliders → shadcn `Slider`（新 scaffold）、篩選按鈕 → Button
- `NavUpdatePricesButton` 狀態面板 → shadcn `Popover`（新 scaffold）+ PopoverAnchor 驅動
- `TutorialModeToggle` → Button secondary（保留 data-mode / testid）
- `L2Panel` 關閉鈕 → IconButton(X)

**C. Code quality 清掃（/review 掃出來的）**

- `button.tsx` 分離 `buttonVariants` 到 `lib/buttonVariants.ts`，消 `react-refresh/only-export-components` warning
- `AddToPortfolioWizard` 把 `weightInputs` map + `previewHoldings` 雙 state 收斂為單一 `editing = { symbol, raw }`；非數字輸入顯示 `wizard-input-invalid` 琥珀提示（不 silent fallback）
- 新增 `normalizeToOne` 純函式 + 單元測試 + `wizard-auto-normalize` 按鈕，確保 `isWeightSumValid` 浮點累積時 confirm 不會卡死
- `PortfoliosPage` 抽 `toSavedHoldings(portfolio)` helper，消三處重複 `holdings.map`
- `PriceChart` `createChart` options 移除與 `autoSize` 衝突的 `width/height`
- `tests/setup.ts` 新增 `ResizeObserver` / `Element.prototype.hasPointerCapture` / `scrollIntoView` stub，讓 Radix Slider / Popover 在 jsdom 不炸

**新 shadcn primitives**：`Input` / `Popover` / `Slider`，加上既有 7 個總計 10 個原件落在 `components/ui/`。

**統計**：
- `grep "<button" src/ --exclude components/ui/` 回 0（除 wizard 表格 `<thead>` 這類 markup，無互動裸 button）
- `grep window.confirm src/` 回 0
- unit 84 tests pass；type-check / lint 0 error / 0 warning
- E2E 仍受限於環境 Playwright browser 下載 block，需使用者本機 `pnpm e2e` 驗收

---

**備註**：此計畫是 Phase 9 的 Just-in-Time plan；Phase 10+ 不預先規劃。
