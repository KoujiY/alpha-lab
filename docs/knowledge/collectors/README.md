# collectors/ — 數據抓取模組

對應 `backend/src/alpha_lab/collectors/` 下各資料來源 adapter。每個資料來源一個 md，記錄：來源 URL、欄位說明、抓取頻率、錯誤處理、已知坑。

## 規劃條目

| 檔案 | 內容 | 規劃於 Phase |
|------|------|-------------|
| `twse.md` | 台灣證券交易所（股價、成交量、除權息） | Phase 1 |
| `mops.md` | 公開資訊觀測站（財報、法人持股、月營收） | Phase 1 |
| `news.md` | 新聞 / 事件抓取策略 | Phase 1+ |

Phase 0 只保留資料夾與本 README。
