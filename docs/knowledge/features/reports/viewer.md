---
domain: features/reports/viewer
updated: 2026-04-17
related: [storage.md, ../portfolio/recommender.md]
---

# Reports 前端 /reports 列表 + 細節（Phase 4）

## 目的

把 Claude Code 分析 SOP 寫入的報告暴露給使用者瀏覽 / 回顧；配合「儲存此次推薦為報告」按鈕形成閉環：推薦 → 存檔 → 回顧。

## 現行實作

- **Route**：`/reports`（列表）、`/reports/:reportId`（細節），在 `App.tsx` 定義
- **列表頁 `ReportsPage`**：
  - 讀 `GET /api/reports`，以 type filter 按鈕切換（全部 / 個股 / 組合 / 事件 / 研究）
  - Loading / error / empty 三態；用 grid 2 欄顯示 `ReportCard`
- **卡片 `ReportCard`**：
  - 顯示 type badge + date + symbols + title + summary_line + tags
  - 整張卡是 `<Link to="/reports/:id">`
- **細節頁 `ReportDetailPage`**：
  - `useParams()` 拿 reportId → `useReport(id)` → `MarkdownRender source={body_markdown}`
  - 頂部「← 回列表」回 `/reports`
- **Markdown 渲染**：共用 `components/MarkdownRender.tsx`（react-markdown + remark-gfm），與 L2 Panel 同一套

## 關鍵檔案

- [frontend/src/api/reports.ts](../../../../frontend/src/api/reports.ts) — `listReports` / `getReport`
- [frontend/src/hooks/useReports.ts](../../../../frontend/src/hooks/useReports.ts) — `useReports` / `useReport`
- [frontend/src/pages/ReportsPage.tsx](../../../../frontend/src/pages/ReportsPage.tsx)
- [frontend/src/pages/ReportDetailPage.tsx](../../../../frontend/src/pages/ReportDetailPage.tsx)
- [frontend/src/components/reports/ReportCard.tsx](../../../../frontend/src/components/reports/ReportCard.tsx)
- [frontend/src/components/MarkdownRender.tsx](../../../../frontend/src/components/MarkdownRender.tsx)
- [frontend/src/layouts/AppLayout.tsx](../../../../frontend/src/layouts/AppLayout.tsx) — header 「回顧」連結
- [frontend/tests/components/ReportCard.test.tsx](../../../../frontend/tests/components/ReportCard.test.tsx)

## 修改時注意事項

- 新 report type 要同時改三處：`api/types.ts::ReportType`、`ReportsPage::TYPE_OPTIONS`、`ReportCard::TYPE_BADGE`。
- 細節頁不做獨立快取，吃 `useReport`（staleTime 60s）；若要離線瀏覽 / 全文搜，日後再接 service worker 或搜尋 index。
- Markdown 元件覆寫在 `MarkdownRender`，改樣式就改那一檔；不要在各頁各自覆寫。
- `ReportCard` 的 Link `to` 有 `encodeURIComponent(meta.id)`，後端 `GET /api/reports/{id}` 也接 encoded id → 新 id 規則若包含非 ASCII / `/` 要測 decode 是否正確。
