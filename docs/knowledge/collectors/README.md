# collectors/ — 數據抓取模組

對應 `backend/src/alpha_lab/collectors/` 下各資料來源 adapter。每個資料來源一個 md，記錄：來源 URL、欄位說明、抓取頻率、錯誤處理、已知坑。

## 規劃條目

| 檔案 | 內容 | 規劃於 Phase |
|------|------|-------------|
| `twse.md` | TWSE 日股價（OHLCV）；Phase 1.5 加入三大法人、融資融券 | Phase 1 |
| `mops.md` | MOPS 月營收；Phase 1.5 加入季報（合併損益/資產負債/現金流）、重大訊息 | Phase 1 |
| `news.md` | 新聞抓取策略（暫緩，待 Phase 2+ 再評估是否需要） | Phase 2+ |

Phase 0 只保留資料夾與本 README。Phase 1 建立 `twse.md` 與 `mops.md` 的初版（僅涵蓋該 Phase 實作的 collector），Phase 1.5 擴充。
