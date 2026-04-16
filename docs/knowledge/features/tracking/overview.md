---
domain: features/tracking
updated: 2026-04-17
related: [../portfolio/recommender.md, ../../architecture/data-models.md, ../../architecture/data-flow.md]
---

# 組合追蹤

## 目的

讓使用者將推薦頁的組合「存下來」，之後可觀察 NAV 累積走勢與累積報酬。

## 現行實作（Phase 6）

### 後端

**資料表（`backend/src/alpha_lab/storage/models.py`）：**

- **`portfolios_saved`**（主鍵：`id` autoincrement）：儲存一份已保存組合；`holdings_json` 以 JSON 字串存放 `list[{symbol, name, weight, base_price}]`，`base_date` 記錄儲存當天日期，`style` / `label` 來自推薦風格。
- **`portfolio_snapshots`**（複合主鍵：`portfolio_id + snapshot_date`）：每次呼叫 `GET .../performance` 時 upsert 最新一筆 NAV，目前為預留快取用途，前端不直接讀取。

**API 端點（`/api/portfolios/saved`）：**

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/portfolios/saved` | 儲存組合；`base_date` 由後端取 `date.today()` |
| GET | `/api/portfolios/saved` | 列出全部已儲存組合（metadata，不含 holdings 明細） |
| GET | `/api/portfolios/saved/{id}` | 取單筆詳細（含 holdings 明細） |
| DELETE | `/api/portfolios/saved/{id}` | 刪除組合；成功 204，不存在 404 |
| GET | `/api/portfolios/saved/{id}/performance` | 計算並回傳 NAV 走勢 |

**`save_portfolio`（`portfolios/service.py`）：**

- 遍歷 `payload.holdings`；若 `base_price <= 0`，從 `prices_daily.close` 查詢 `(symbol, base_date)` 自動補值
- 找不到收盤價 → 拋 `ValueError` → route 層回 HTTP 400
- 補值後將 holdings 序列化為 JSON 字串一併存入 `portfolios_saved`

**NAV 公式（`compute_performance`）：**

```
nav(t) = Σ( weight_i × price_i(t) / base_price_i )
```

- `weight_i`：儲存時的 softmax 權重（小數，合計 1.0）
- `base_price_i`：儲存時從 `prices_daily` 取到的收盤價
- 計算範圍：`trade_date >= base_date`，只取所有持股當日都有收盤價的日期（取交集），缺價日直接跳過
- 最後一個 `nav(t)` 即 `latest_nav`；`total_return = latest_nav - 1.0`

### 前端

**`/portfolios` 推薦頁（`PortfoliosPage.tsx`）：**

- 每個 tab（style）的持股列表下方有「儲存此組合」按鈕
- 點擊呼叫 `POST /api/portfolios/saved`，成功後重新載入頁底「已儲存組合」清單
- 「已儲存組合」清單由 `SavedPortfolioList.tsx` 渲染，每項顯示 label / style / base_date / 持股數；點擊跳轉 `/portfolios/:id`

**`/portfolios/:id` 追蹤詳細頁（`PortfolioTrackingPage.tsx`）：**

- 上方顯示：累積報酬（`total_return` 百分比格式，正負以顏色區分）、base_date、style
- NAV 走勢圖（`PerformanceChart.tsx`）：recharts `LineChart`，X 軸為日期，Y 軸為 NAV 值
- 持股明細表：symbol / name / 權重 / base_price
- 右上「刪除追蹤組合」按鈕 → 視窗確認 → `DELETE /api/portfolios/saved/{id}` → 跳回 `/portfolios`

**API client：**`frontend/src/api/savedPortfolios.ts`，包含 `listSavedPortfolios`、`getSavedPortfolio`、`saveRecommendedPortfolio`、`deleteSavedPortfolio`、`fetchPerformance`。

## 關鍵檔案

- [backend/src/alpha_lab/portfolios/service.py](../../../../backend/src/alpha_lab/portfolios/service.py)
- [backend/src/alpha_lab/schemas/saved_portfolio.py](../../../../backend/src/alpha_lab/schemas/saved_portfolio.py)
- [backend/src/alpha_lab/api/routes/portfolios.py](../../../../backend/src/alpha_lab/api/routes/portfolios.py)
- [backend/src/alpha_lab/storage/models.py](../../../../backend/src/alpha_lab/storage/models.py)（`SavedPortfolio`、`PortfolioSnapshot` 類別）
- [frontend/src/api/savedPortfolios.ts](../../../../frontend/src/api/savedPortfolios.ts)
- [frontend/src/pages/PortfolioTrackingPage.tsx](../../../../frontend/src/pages/PortfolioTrackingPage.tsx)
- [frontend/src/components/portfolio/PerformanceChart.tsx](../../../../frontend/src/components/portfolio/PerformanceChart.tsx)
- [frontend/src/components/portfolio/SavedPortfolioList.tsx](../../../../frontend/src/components/portfolio/SavedPortfolioList.tsx)
- [frontend/tests/e2e/portfolio-tracking.spec.ts](../../../../frontend/tests/e2e/portfolio-tracking.spec.ts)

## 修改時注意事項

- **新增 NAV 對基準的呈現**（例如與大盤比較）：須在 `compute_performance` 額外查詢基準指數，並擴充 `PerformanceResponse` schema 與前端 `PerformanceChart` 的資料系列。
- **改 `base_date` 邏輯**：目前固定取 `date.today()`（由 route 傳入），若改成讓使用者自選 base_date，需同步更新 `SavedPortfolioCreate` schema 和 route 參數。
- **`portfolio_snapshots` 擴充**：目前 `compute_performance` 僅 upsert 最新一筆作快取；若未來要用它做批次 NAV 更新（排程），需修改 upsert 邏輯為逐日寫入，並在 `jobs/types.py` 新增 JobType。
- **holdings 儲存格式**：`holdings_json` 為 JSON 字串（Text 欄位），直接在 `SavedPortfolio` row 內，無獨立關聯表。新增持股欄位時須更新 `SavedHolding` schema 並考慮既存資料相容性。
- **400 錯誤前提**：`POST /api/portfolios/saved` 需要 `prices_daily` 表中有 `(symbol, base_date)` 收盤價。若 DB 無資料直接儲存會收到 400，需先跑 `daily_collect`。
