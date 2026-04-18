---
domain: features/settings
updated: 2026-04-18
related: [education/tutorial-mode.md, stocks/browse-list.md, reports/viewer.md, architecture/report-cache.md]
---

# `/settings` 偏好管理頁（Phase 8）

## 目的

把原本散落在各頁 localStorage 的偏好集中在一個頁面，讓使用者能一處完成「調教學密度 / 查看與清收藏 / 清空離線報告快取」。補齊 spec §9.1 `/settings` 導覽缺口。

## 現行實作

- **不引入新的 `SettingsContext` / `UserPreferencesContext`**。Settings 頁直接消費三個既有 source of truth：
  - 教學密度 → `useTutorialMode()`（`TutorialModeContext`）
  - 收藏清單 → `useFavorites()`（包 `favorites.ts`）
  - 離線報告快取 → `listCachedReportIds()` / `clearReportCache()`（`lib/reportCache.ts`）
- **三個 section**（皆為純 Tailwind card）：
  1. **教學密度**：三顆 radio（完整 / 精簡 / 關閉）。切換即時呼叫 `setMode(value)`，header `TutorialModeToggle` 會同步（共用 Context）。
  2. **收藏股票**：列出 `favorites` 每一筆，顯示代號 + 名稱（從 `useStocks()` 查 `symbol→name`；載入中顯示「（載入中…）」）+ 「移除」按鈕。空清單顯示導引去 `/stocks` 加星。
  3. **離線報告快取**：顯示「已快取 N 篇」（mount 時 `listCachedReportIds()` 取一次存 state）+ 「清空快取」按鈕（`window.confirm` 二次確認後 `clearReportCache()` 並更新計數）。計數 0 時按鈕 disabled。

## 關鍵檔案

- [frontend/src/pages/SettingsPage.tsx](../../../frontend/src/pages/SettingsPage.tsx) — 三段 section
- [frontend/src/contexts/TutorialModeContext.ts](../../../frontend/src/contexts/TutorialModeContext.ts)、[frontend/src/contexts/TutorialModeProvider.tsx](../../../frontend/src/contexts/TutorialModeProvider.tsx)
- [frontend/src/hooks/useFavorites.ts](../../../frontend/src/hooks/useFavorites.ts)、[frontend/src/lib/favorites.ts](../../../frontend/src/lib/favorites.ts)
- [frontend/src/lib/reportCache.ts](../../../frontend/src/lib/reportCache.ts)
- [frontend/tests/e2e/settings.spec.ts](../../../frontend/tests/e2e/settings.spec.ts) — 4 個 E2E（section 顯示、tutorial mode 同步、收藏增刪、快取計數）

## 修改時注意事項

- **新增偏好項目的 SOP**：
  1. 先加 source of truth（Context 或 lib helper），讓實際使用該偏好的地方可以消費
  2. 在 `SettingsPage` 加對應的 section 顯示 / 編輯 UI
  3. **只有當該偏好需要跨頁共享且有複雜同步邏輯時，才考慮抽 `SettingsContext`**。目前 3 項偏好各自有 context / hook，集中容器只會是薄殼，價值低於它帶來的耦合。
- **收藏 row 會短暫顯示「（載入中…）」**：因為 `useStocks` 需要 HTTP 一次。若使用者進 `/settings` 前沒先逛過 `/stocks`，第一次載入會看到 placeholder 一秒。若體感差可以考慮預載（例如 `AppLayout` mount 時預先 `queryClient.prefetchQuery`），但會讓首頁多一個不必要的請求，目前不做。
- **`window.confirm` UX**：Phase 9 已改走 shadcn `AlertDialog`（testid：`cache-clear-confirm` / `cache-clear-cancel` / `cache-clear-proceed`）；原 `cache-clear`（觸發按鈕）、`cache-count`（計數）testid 保留；教學密度三顆 radio 改走 shadcn `RadioGroup`，testid `tutorial-option-full/compact/off` 保留不變；E2E 要用 `click()` 而非 `check()`（Radix RadioGroupItem 是 button，不是 HTML radio）。
- **不新增 `hasAnyPreferencesChanged` 類聚合狀態**：每個 section 的 state 都獨立寫 localStorage；不做跨 section diff / save-all。Phase 8 僅當「偏好中心」使用。
