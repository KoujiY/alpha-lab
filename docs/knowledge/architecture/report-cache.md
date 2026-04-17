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

- [frontend/src/lib/reportCache.ts](../../../frontend/src/lib/reportCache.ts) — IndexedDB CRUD
- [frontend/src/hooks/useReports.ts](../../../frontend/src/hooks/useReports.ts) — `getReportWithCache` + `useReport`

## 修改時注意事項

- `idb-keyval` 的 `createStore` 指定獨立 DB，不與其他 IndexedDB 使用衝突
- 測試環境需 `fake-indexeddb`（devDependency），vitest setup 要 `import "fake-indexeddb/auto"`
- 快取不做自動清理；未來可在 `/settings` 頁加手動清除按鈕
