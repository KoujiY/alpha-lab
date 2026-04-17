# collectors/ — 數據抓取模組

對應 `backend/src/alpha_lab/collectors/` 下各資料來源 adapter。每個資料來源一個 md，記錄：來源 URL、欄位說明、抓取頻率、錯誤處理、已知坑。

## 現行條目

| 檔案 | 內容 | 建立於 Phase |
|------|------|-------------|
| `twse.md` | TWSE 日股價（STOCK_DAY）、三大法人（T86）、融資融券（MI_MARGN） | Phase 1 / 1.5 擴充 |
| `twse-stock-info.md` | TWSE 上市公司基本資料（t187ap03_L）：name / industry / listed_date | Pre-Phase 4 Step 0 |
| `mops.md` | MOPS 月營收（t187ap05_L）、季報 income（t187ap06_L_ci）+ balance（t187ap07_L_ci）；cashflow 延至 Phase 3（走 t164sb05 HTML） | Phase 1 / 1.5 擴充 |
| `mops-cashflow.md` | MOPS t164sb05 HTML 爬現金流量表（FCF 評分） | Phase 3 |
| `events.md` | 上市即時重大訊息（OpenAPI t187ap04_L） | Phase 1.5 || `yahoo.md` | Yahoo Finance Chart API（TWSE 備援） | Phase 7B.1 |

## 規劃中（尚未建立）

| 檔案 | 內容 | 規劃於 Phase |
|------|------|-------------|
| `tpex_events.md`（暫名） | 上櫃（OTC）重大訊息 | Phase 2+ |
| `news.md` | 新聞彙整策略（Phase 7B.2 以 DB events 為主，外部新聞源留待後續） | Phase 7B.2+ |
