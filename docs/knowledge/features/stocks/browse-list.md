---
domain: features/stocks
updated: 2026-04-19
related: [../data-panel/overview.md, ../../collectors/twse-stock-info.md]
---

# `/stocks` 股票瀏覽列表頁（Phase 8）

## 目的

讓使用者在個股詳細頁之外，能以「全市場列表」視角瀏覽 / 搜尋 / 依產業篩選 / 收藏上市股票，並從列表直接跳到個股頁做深入分析。補齊 spec §9.1 `/stocks` 導覽缺口。

## 現行實作

- **資料源**：`GET /api/stocks?q=...&limit=...`，讀 SQLite `stocks` 表（`symbol / name / industry / listed_date`）。列表頁以 `limit=3000` 一次載入全市場（~2000 檔）。`industry` 欄位已由 Pre-Phase 4 `twse_stock_info` collector 以中文字串寫入（「半導體業」「金融保險業」等），不需前端做 code→name 映射。
- **列表頁**：`frontend/src/pages/StocksPage.tsx`。上方搜尋框（符合 symbol 或 name substring）+ 產業 select（從載入的資料動態收斂 distinct industry，加「全部」選項）。下方表格 5 欄：☆收藏 / 代號（mono 字型）/ 名稱（Link 到 `/stocks/:symbol`）/ 產業 / 上市日期。
- **排序**：已收藏的 row 置頂，再依 symbol 字典序升冪（stable）。
- **計數摘要**：`共 N 檔（已收藏 M 檔）`。
- **收藏**：透過 `useFavorites` hook 操作 `localStorage['alpha-lab:favorites']`（存 symbol 陣列）；hook 同時訂閱 `storage` event，跨 tab 同步變更。
- **資料快取**：`useStocks` 用 TanStack Query，`staleTime = 5 min`（公司基本資料一天只會由 `daily_collect` 更新一次）。

## 關鍵檔案

- [frontend/src/pages/StocksPage.tsx](../../../../frontend/src/pages/StocksPage.tsx) — 列表頁元件
- [frontend/src/hooks/useStocks.ts](../../../../frontend/src/hooks/useStocks.ts) — TanStack Query wrapper
- [frontend/src/hooks/useFavorites.ts](../../../../frontend/src/hooks/useFavorites.ts) — 反應式收藏 hook
- [frontend/src/lib/favorites.ts](../../../../frontend/src/lib/favorites.ts) — localStorage 存取底層（同步 API）
- [frontend/src/api/stocks.ts](../../../../frontend/src/api/stocks.ts) — `searchStocks(q, limit)` 與 `listAllStocks(q?)`
- [backend/src/alpha_lab/api/routes/stocks.py](../../../../backend/src/alpha_lab/api/routes/stocks.py) — `list_stocks` 端點（`limit` 上限 3000）
- [frontend/tests/e2e/stocks-list.spec.ts](../../../../frontend/tests/e2e/stocks-list.spec.ts) — 列表 E2E（搜尋、產業篩選、點擊跳頁、收藏 persist）
- [frontend/tests/lib/useFavorites.test.ts](../../../../frontend/tests/lib/useFavorites.test.ts) — 收藏 hook 單元測試

## 修改時注意事項

- **全量載入假設**：limit=3000 是在「上市約 2000 檔」前提下夠用；若未來擴充 OTC（上櫃約 800 檔）、興櫃或已下市公司，單次 payload 會超過可接受大小，需改 cursor-based 或虛擬捲動。
- **`stocks.industry` 中文化依賴 Pre-Phase 4 collector**：若停用 `twse_stock_info` 或 upstream API 欄位命名改動，`industry` 可能變成空字串或英文代碼，產業 select 會失效。修 collector 時要同步跑列表頁回歸。
- **收藏 localStorage key `alpha-lab:favorites`**：同時被 `/stocks` 的 `useFavorites`、`/settings` 收藏管理、個股頁 `StockActions` 的「收藏」按鈕共用。改 key 需要三處一起搬 + migration 讀舊 key 寫新 key。
- **排序 stability**：目前「收藏置頂」邏輯用 sort callback 手寫。若未來加其他排序條件（例如依市值），要注意 JS `Array.sort` 是 stable（ES2019+），但 compound 條件仍建議明確用 tuple 比較。
- **搜尋是前端 filter，不打後端**：進頁面時一次載入全市場後，輸入搜尋框是對 memory 做 substring match；不會打 `?q=` 到後端。HeaderSearch（不同元件）才是打 `?q=` 的 top-N。
