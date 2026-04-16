---
domain: features/reports/viewer
updated: 2026-04-16
related: [storage.md, ../portfolio/recommender.md]
---

# Reports 前端 /reports 列表 + 細節（Phase 4 / Phase 6 擴充）

## 目的

把 Claude Code 分析 SOP 寫入的報告暴露給使用者瀏覽 / 回顧；配合「儲存此次推薦為報告」按鈕形成閉環：推薦 → 存檔 → 回顧。

## 現行實作

- **Route**：`/reports`（列表）、`/reports/:reportId`（細節），在 `App.tsx` 定義
- **列表頁 `ReportsPage`**：
  - 讀 `GET /api/reports`，以 type filter 按鈕切換（全部 / 個股 / 組合 / 事件 / 研究）
  - Phase 6：頂部搜尋輸入框（`data-testid="reports-search"`）透過 `q` query param 過濾；與 type filter 可組合
  - Loading / error / empty 三態；用 grid 2 欄顯示 `ReportCard`
- **卡片 `ReportCard`**：
  - 顯示 type badge + date + symbols + title + summary_line + tags
  - 主體是 `<Link to="/reports/:id">`；動作列（`star-toggle` / `delete-report`）獨立於 link 外，避免整張卡吃掉按鈕點擊
  - Phase 6：`onToggleStar` / `onDelete` 為**可選** props — 未傳入時動作列不渲染（保留 Phase 4 舊測試相容）
- **細節頁 `ReportDetailPage`**：
  - `useParams()` 拿 reportId → `useReport(id)` → `MarkdownRender source={body_markdown}`
  - 頂部「← 回列表」回 `/reports`
  - Phase 6：標題列旁提供 ★ 收藏切換與「刪除」按鈕；刪除後 `navigate("/reports")` 並 invalidate `["reports"]` cache
- **Markdown 渲染**：共用 `components/MarkdownRender.tsx`（react-markdown + remark-gfm），與 L2 Panel 同一套
- **Cache key**：`useReports` 的 key 為 `["reports", "list", type, tag, symbol, query]`，四個 filter 任一變化都會重抓；mutation 完成後 `invalidateQueries(["reports"])` 一次掃掉整個子樹

## 關鍵檔案

- [frontend/src/api/client.ts](../../../../frontend/src/api/client.ts) — `apiGet` / `apiPost` / `apiPatch` / `apiDelete` 共通 helpers
- [frontend/src/api/reports.ts](../../../../frontend/src/api/reports.ts) — `listReports` / `getReport` / `updateReport` / `deleteReport`
- [frontend/src/api/types.ts](../../../../frontend/src/api/types.ts) — `ReportMeta` / `ReportDetail` / `ReportUpdate`
- [frontend/src/hooks/useReports.ts](../../../../frontend/src/hooks/useReports.ts) — `useReports` / `useReport`
- [frontend/src/pages/ReportsPage.tsx](../../../../frontend/src/pages/ReportsPage.tsx)
- [frontend/src/pages/ReportDetailPage.tsx](../../../../frontend/src/pages/ReportDetailPage.tsx)
- [frontend/src/components/reports/ReportCard.tsx](../../../../frontend/src/components/reports/ReportCard.tsx)
- [frontend/src/components/MarkdownRender.tsx](../../../../frontend/src/components/MarkdownRender.tsx)
- [frontend/src/layouts/AppLayout.tsx](../../../../frontend/src/layouts/AppLayout.tsx) — header 「回顧」連結
- [frontend/tests/components/ReportCard.test.tsx](../../../../frontend/tests/components/ReportCard.test.tsx)
- [frontend/tests/e2e/reports.spec.ts](../../../../frontend/tests/e2e/reports.spec.ts) — 列表 / 詳情 / 搜尋 / 星號 / 刪除 E2E

## 修改時注意事項

- 新 report type 要同時改三處：`api/types.ts::ReportType`、`ReportsPage::TYPE_OPTIONS`、`ReportCard::TYPE_BADGE`。
- 細節頁不做獨立快取，吃 `useReport`（staleTime 60s）；報告全文搜尋目前走後端 `q` query param（Phase 6 in-memory），離線快取 / service worker 改由 Phase 7+ 視需求決定。
- Markdown 元件覆寫在 `MarkdownRender`，改樣式就改那一檔；不要在各頁各自覆寫。
- `ReportCard` 的 Link `to` 有 `encodeURIComponent(meta.id)`，後端 `GET /api/reports/{id}` 也接 encoded id → 新 id 規則若包含非 ASCII / `/` 要測 decode 是否正確。
- **★ / 刪除動作列目前是純文字按鈕**，屬 Phase 6 過渡實作；Phase 8 UI 升級會換成 icon button（見 spec §15 Phase 8），但 `data-testid="star-toggle"` / `data-testid="delete-report"` **保留不變**以維持 E2E。
- 新增動作按鈕時要把 click 事件 `stopPropagation`，避免 `<Link>` 或 `<li>` 的 click handler 吃掉（目前 `ReportCard` 已經把動作列獨立於 `<Link>` 外，寫新按鈕前要維持這個結構）。
- mutation 後一律 `invalidateQueries(["reports"])`（整棵子樹），而不是僅 invalidate 單筆；同頁有多種 filter 時才不會出現殘影。
