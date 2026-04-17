---
domain: features/tracking
updated: 2026-04-18
related: [../portfolio/recommender.md, ../../architecture/data-models.md, ../../architecture/data-flow.md, ../../architecture/ui-conventions.md]
---

# 組合追蹤

## 目的

讓使用者將推薦頁的組合「存下來」，之後可觀察 NAV 累積走勢與累積報酬。

## 現行實作（Phase 6）

### Phase 7A 追加：血緣欄位與連續 NAV

**資料表新增欄位：**

- `portfolios_saved.parent_id`：指向母組合（`portfolios_saved.id`，nullable，`ON DELETE SET NULL`）
- `portfolios_saved.parent_nav_at_fork`：fork 當下母組合的 `latest_nav`（nullable）

欄位以 idempotent `ALTER TABLE ADD COLUMN` migration 補上（見 `storage/migrations.py::add_column_if_missing` 與 `storage/init_db.py`）。

**`save_portfolio` 流程新增：**

- 若 `payload.parent_id` 非 None，先呼叫 `compute_performance(parent_id)` 取 `latest_nav`，存為 `parent_nav_at_fork`；parent 不存在 → `ValueError` → 400
- parent NAV 查詢發生於 `session_scope()` 之外，避免巢狀 session 衝突

**`compute_performance` 回傳新增：**

- `parent_points`：若 row 有 `parent_id`，遞迴取 parent 的 `points` 中 `date < child.base_date` 的部分；parent 已被刪除時退回 `None` 並在後端 log warning
- `parent_nav_at_fork`：直接讀 row 欄位
- `_visited` 參數防 parent 鏈 cycle（人為錯誤寫入）導致無窮遞迴

**SavedPortfolioCreate schema 驗證（Pydantic `model_validator(mode="after")`）：**

- `holdings` 內 `symbol` 不得重複 → `ValidationError` → 422
- `abs(sum(weights) - 1.0) > 1e-6` → `ValidationError` → 422（`buildMergedHoldings` 產生的浮點漂移落在容忍內；常數 `WEIGHT_SUM_TOLERANCE` 置於 schema 檔頂）

**前端連續曲線：**

- `PerformanceChart` 新增 `parentPoints` / `parentNavAtFork` / `childBaseDate` props；拿到時把 self 段 NAV `× parentNavAtFork` 勾連 parent 段末端成為連續曲線
- **`forkDate` 鎖定 `childBaseDate`**（不是 `points[0].date`）：若當天被交集踢掉（某持股當日缺價），垂直 `ReferenceLine` 仍固定在真正的 fork 日，不會飄到第一個有 NAV 的日期
- 在 `childBaseDate` 補一個 synthetic anchor row（`parent=scale, self=scale`），讓 parent 虛線與 self 實線視覺上在橘線上對齊。理論不變量：`child.nav(base_date) = 1.0 × scale = parent_nav_at_fork`
- `buildChartSeries` 函式單獨 export 供單測驗證（`frontend/tests/components/PerformanceChart.test.tsx`），含「base_date 被交集踢掉」與「points[0] 重複 base_date」兩個 edge case
- `PortfolioTrackingPage` 顯示「由 組合 #X 分裂」區塊（連結回父組合）與「自母組合起報酬」卡片（值為 `parent_nav_at_fork × latest_nav - 1`）
- `StockActions.persistMerged` 在 `POST /api/portfolios/saved` body 補 `parent_id: detail.id`

### 後端

**資料表（`backend/src/alpha_lab/storage/models.py`）：**

- **`portfolios_saved`**（主鍵：`id` autoincrement）：儲存一份已保存組合；`holdings_json` 以 JSON 字串存放 `list[{symbol, name, weight, base_price}]`，`base_date` 記錄儲存當天日期，`style` / `label` 來自推薦風格。
- **`portfolio_snapshots`**（複合主鍵：`portfolio_id + snapshot_date`）：每次呼叫 `GET .../performance` 時 upsert 最新一筆 NAV，目前為預留快取用途，前端不直接讀取。

**API 端點（`/api/portfolios/saved`）：**

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/portfolios/saved` | 儲存組合；`base_date` 由後端取 `date.today()`，可帶 `?allow_fallback=true` 走 probe 回退路徑 |
| GET | `/api/portfolios/saved/probe` | 前置探測：給一組 symbols，回 `{target_date, resolved_date, today_available, missing_today_symbols, symbol_statuses}` |
| GET | `/api/portfolios/saved` | 列出全部已儲存組合（metadata，不含 holdings 明細） |
| GET | `/api/portfolios/saved/{id}` | 取單筆詳細（含 holdings 明細） |
| DELETE | `/api/portfolios/saved/{id}` | 刪除組合；成功 204，不存在 404 |
| GET | `/api/portfolios/saved/{id}/performance` | 計算並回傳 NAV 走勢 |

**base_date probe 流程：**

- 前端呼叫 `POST /portfolios/saved/probe`（body：`{symbols: [...]}`），後端檢查 `prices_daily`：
  - `target_date`：`date.today()`
  - `today_available`：所有 symbol 今日都有收盤價時為 `true`
  - `resolved_date`：若 `today_available=false`，倒退找「所有 symbol 都有報價」的最近歷史日；若歷史上從未全齊則為 `null`
  - `missing_today_symbols`：今日缺價的 symbol 清單
- 前端依 probe 結果決定：
  - `today_available=true` → 直接 `POST /portfolios/saved`（`allow_fallback=false`）
  - `today_available=false` 且 `resolved_date` 有值 → 彈 `BaseDateConfirmDialog`，使用者選「以 `resolved_date` 為基準繼續」則帶 `allow_fallback=true` 再 POST
  - `resolved_date=null` → dialog 內「繼續」按鈕 disabled，只能取消去點 nav 更新報價補抓

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
- 點擊先呼叫 `probeBaseDate(symbols)`：
  - `today_available=true` → 直接存
  - `today_available=false` → 彈 `BaseDateConfirmDialog`，使用者確認後才以 `allow_fallback=true` 呼叫 `POST /api/portfolios/saved`
- 成功後重新載入頁底「已儲存組合」清單
- 「已儲存組合」清單由 `SavedPortfolioList.tsx` 渲染，每項顯示 label / style / base_date / 持股數；點擊跳轉 `/portfolios/:id`
- **頁內原有的「更新今日報價」按鈕已移除**（統一搬到 nav，見下）

**`/portfolios/:id` 追蹤詳細頁（`PortfolioTrackingPage.tsx`）：**

- 上方顯示：累積報酬（`total_return` 百分比格式，正負以顏色區分）、base_date、style
- NAV 走勢圖（`PerformanceChart.tsx`）：recharts `LineChart`，X 軸為日期，Y 軸為 NAV 值
- 持股明細表：symbol / name / 權重 / base_price
- 右上「刪除追蹤組合」按鈕 → 視窗確認 → `DELETE /api/portfolios/saved/{id}` → 跳回 `/portfolios`

**Nav 全域「更新報價」按鈕（`NavUpdatePricesButton.tsx`）：**

- 位於右上 header，跨頁常駐
- 點擊後收集 union(saved portfolios 持股 ∪ localStorage 收藏 ∪ 當前 `/stocks/:symbol` URL 的 symbol)，派出 `twse_prices_batch` job
- 狀態回饋改用**顯式 popover 狀態面板**：按鈕下方浮出（running 琥珀 / done 綠 / error 紅），有 ✕ 按鈕讓使用者手動解除
  - 為什麼不用 `title=` 原生 tooltip：macOS / 部分瀏覽器不顯示或 hover 延遲過長
- 底層是共用 hook `useUpdatePricesJob`，同一套 state machine 被「加入組合」等其他觸發點重用（目前僅 nav 使用，但 hook 保留擴充空間）

**「部分持股報價不齊」共用 Dialog（`BaseDateConfirmDialog.tsx`）：**

- 同時被 `PortfoliosPage`（儲存推薦組合）與 `StockActions`（加入組合）使用
- Phase 7B.3 新增 `symbol_statuses` 分類引導：後端 `probe_base_date` 回傳每個缺價 symbol 的原因分類（`no_data` / `stale` / `today_missing`），dialog 依分類分組顯示不同引導訊息與顏色（紅 / 橘 / 琥珀）
  - `no_data`：完全無報價紀錄 → 紅色，提示先執行資料蒐集
  - `stale`：最近報價 > 7 天 → 橘色，提示可能停牌或下市
  - `today_missing`：有近期報價但今日無 → 琥珀色，提示 TWSE 14:00 後公告
- `resolved_date=null` 時「繼續」按鈕 disabled，並提示使用者先補抓報價

**API client：**`frontend/src/api/savedPortfolios.ts`，包含 `listSavedPortfolios`、`getSavedPortfolio`、`saveRecommendedPortfolio`（支援 `{allowFallback}`）、`deleteSavedPortfolio`、`fetchPerformance`、`probeBaseDate`。

## 關鍵檔案

- [backend/src/alpha_lab/portfolios/service.py](../../../../backend/src/alpha_lab/portfolios/service.py)
- [backend/src/alpha_lab/storage/migrations.py](../../../../backend/src/alpha_lab/storage/migrations.py)
- [frontend/tests/components/PerformanceChart.test.tsx](../../../../frontend/tests/components/PerformanceChart.test.tsx)
- [backend/src/alpha_lab/schemas/saved_portfolio.py](../../../../backend/src/alpha_lab/schemas/saved_portfolio.py)
- [backend/src/alpha_lab/api/routes/portfolios.py](../../../../backend/src/alpha_lab/api/routes/portfolios.py)
- [backend/src/alpha_lab/storage/models.py](../../../../backend/src/alpha_lab/storage/models.py)（`SavedPortfolio`、`PortfolioSnapshot` 類別）
- [backend/src/alpha_lab/jobs/service.py](../../../../backend/src/alpha_lab/jobs/service.py)（`TWSE_PRICES_BATCH` 分派：0.3s throttle + 1s retry-once 吃掉 TWSE WAF 偶發 stat 錯誤）
- [frontend/src/api/savedPortfolios.ts](../../../../frontend/src/api/savedPortfolios.ts)
- [frontend/src/pages/PortfolioTrackingPage.tsx](../../../../frontend/src/pages/PortfolioTrackingPage.tsx)
- [frontend/src/components/portfolio/PerformanceChart.tsx](../../../../frontend/src/components/portfolio/PerformanceChart.tsx)
- [frontend/src/components/portfolio/SavedPortfolioList.tsx](../../../../frontend/src/components/portfolio/SavedPortfolioList.tsx)
- [frontend/src/components/portfolio/BaseDateConfirmDialog.tsx](../../../../frontend/src/components/portfolio/BaseDateConfirmDialog.tsx)（跨頁共用 dialog）
- [frontend/src/components/NavUpdatePricesButton.tsx](../../../../frontend/src/components/NavUpdatePricesButton.tsx)
- [frontend/src/hooks/useUpdatePricesJob.ts](../../../../frontend/src/hooks/useUpdatePricesJob.ts)
- [frontend/tests/e2e/portfolio-tracking.spec.ts](../../../../frontend/tests/e2e/portfolio-tracking.spec.ts)
- [frontend/tests/e2e/stock-actions.spec.ts](../../../../frontend/tests/e2e/stock-actions.spec.ts)（含 probe / dialog 案例）

## 修改時注意事項

- **新增 NAV 對基準的呈現**（例如與大盤比較）：須在 `compute_performance` 額外查詢基準指數，並擴充 `PerformanceResponse` schema 與前端 `PerformanceChart` 的資料系列。
- **改 `base_date` 邏輯**：目前固定取 `date.today()`（由 route 傳入），若改成讓使用者自選 base_date，需同步更新 `SavedPortfolioCreate` schema 和 route 參數。
- **`portfolio_snapshots` 擴充**：目前 `compute_performance` 僅 upsert 最新一筆作快取；若未來要用它做批次 NAV 更新（排程），需修改 upsert 邏輯為逐日寫入，並在 `jobs/types.py` 新增 JobType。
- **holdings 儲存格式**：`holdings_json` 為 JSON 字串（Text 欄位），直接在 `SavedPortfolio` row 內，無獨立關聯表。新增持股欄位時須更新 `SavedHolding` schema 並考慮既存資料相容性。
- **400 錯誤前提**：`POST /api/portfolios/saved` 需要 `prices_daily` 表中有 `(symbol, base_date)` 收盤價。若 DB 無資料直接儲存會收到 400，需先跑 nav 更新報價或 `daily_collect`。前端已改為**先 probe 後 POST** 避開這條 error path，但保留作為兜底。
- **新增觸發點要重用共用元件**：任何新的「儲存 / 加入組合」流程都要走 `probeBaseDate` + `BaseDateConfirmDialog`，不要自己重做 dialog；任何需要觸發價格更新的 UI 都用 `useUpdatePricesJob` hook，不要重新實作 polling。
- **TWSE_PRICES_BATCH 偶發失敗**：已加 0.3s 間隔 + 1s 退避重試吃掉 WAF 偶發 stat 錯誤；`TWSERateLimitError`（明確 403/封鎖）不重試、直接 fail 整個 job。若出現大量 `failed:` suffix 在 summary，先排查是不是撞到 WAF 而非單檔資料問題。
- **Phase 7 血緣欄位為 nullable**：既有儲存組合的 `parent_id` / `parent_nav_at_fork` 皆為 NULL，所有前端 UI 必須把「沒 parent」當正常狀態顯示（`PortfolioTrackingPage` 以 `hasLineage` 判斷，`PerformanceChart` 接受 `parentPoints?: null`）。
- **fork 不會 rebuild 父組合歷史**：`parent_points` 是在 `compute_performance(child)` 時臨時遞迴出來的，parent 本身資料改動會即時反映；若 parent 被刪除，child 的 `parent_id` 會因 `ON DELETE SET NULL` 變 NULL、`parent_nav_at_fork` 仍保留在 row 上（歷史快照）。改動刪除語意前（例如改成 CASCADE 或阻擋）要同步評估這個快照是否還有意義。
- **修改 schema validator tolerance**：`WEIGHT_SUM_TOLERANCE = 1e-6` 對應 `buildMergedHoldings` 的典型浮點漂移；若改大會放過真正錯誤的輸入（例如 UI 沒做 normalize 的新流程），改小則可能讓前端自動 normalize 出的權重被拒絕。要調整時先看 [frontend/src/lib/portfolioMerge.ts](../../../../frontend/src/lib/portfolioMerge.ts) 的合成邏輯。
