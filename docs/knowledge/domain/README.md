# domain/ — 投資領域邏輯

這裡記錄 alpha-lab **系統內部**如何實作投資領域的規則，不是教學資料。重點在「Claude 修改系統時需要知道目前規則長怎樣」。

## 規劃條目

| 檔案 | 內容 | 規劃於 Phase |
|------|------|-------------|
| `factors.md` | Value / Growth / Dividend / Quality 四因子的實作細節、用到的指標、計算公式 | Phase 3 |
| `scoring.md` | 評分公式、權重、正規化方式、閾值 | Phase 3 |
| `industry-tagging.md` | 產業分類規則、標籤映射表 | Phase 2 |
| `reports.md` | 分析報告的產生規則、四種類型的用途與欄位 | Phase 4 |

Phase 0 只保留資料夾與本 README。
