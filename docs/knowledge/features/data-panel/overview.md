---
domain: features/data-panel
updated: 2026-04-15
related: [ui-layout.md, data-sources.md, ../../architecture/data-flow.md]
---

# 功能 A：個股數據面板

## 目的

讓使用者透過 `/stocks/:symbol` 一次看完個股的核心資訊：基本資料、股價走勢、月營收、季報摘要、三大法人、融資融券、重大訊息。所有資料皆來自本地 SQLite（Phase 1 + 1.5 抓取落庫）。

## 現行實作

- **Backend**：`api/routes/stocks.py` 提供 1 個聚合端點 + 6 個細端點 + 1 個列表端點
  - `GET /api/stocks/{symbol}/overview`：個股頁首屏一次載入
  - `GET /api/stocks/{symbol}/{prices,revenues,financials,institutional,margin,events}`：細端點（支援 `limit`、prices 另支援 `start`/`end`）
  - `GET /api/stocks?q=`：列表 + 模糊搜尋（symbol / name substring）
- **Frontend**：`pages/StockPage.tsx` 用 `useStockOverview` hook 一次拉 overview，再分派給各 section 元件渲染

## 關鍵檔案

- [backend/src/alpha_lab/api/routes/stocks.py](../../../backend/src/alpha_lab/api/routes/stocks.py)
- [backend/src/alpha_lab/schemas/stock.py](../../../backend/src/alpha_lab/schemas/stock.py)
- [frontend/src/pages/StockPage.tsx](../../../frontend/src/pages/StockPage.tsx)
- [frontend/src/hooks/useStockOverview.ts](../../../frontend/src/hooks/useStockOverview.ts)
- [frontend/src/components/stock/](../../../frontend/src/components/stock/)

## 修改時注意事項

- Overview 一次聚合 7 個 section；加新 section 時兩邊同步：backend `_load_*` helper + schema、frontend types + section 元件
- `_load_financials` 會把 income + balance 合併成單一 `FinancialPoint`（以 period 為 key）。若未來補 cashflow（Phase 3），要在這裡加第三類欄位合併
- 個股頁預設載入量：prices 60、revenues 12、financials 4、institutional/margin/events 20；量級對應 spec §10 的 UI 尺寸
- 列表端點目前走 LIKE 模糊匹配，無全文索引。若股票數破萬再考慮換方案
