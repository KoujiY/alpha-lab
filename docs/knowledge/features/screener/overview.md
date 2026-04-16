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

- **GET /api/screener/factors**：回傳五個因子 meta（key / label / 範圍 / 說明），純靜態定義於 `FACTOR_DEFINITIONS`
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
