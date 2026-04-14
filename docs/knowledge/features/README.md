# features/ — 五大功能模組知識

每個子資料夾對應 alpha-lab 設計 spec 裡的一個功能（A~E）：

| 子資料夾 | 對應 | 規劃於 Phase |
|---------|------|-------------|
| `data-panel/` | A：個股數據面板 | Phase 2 |
| `screener/` | B：選股篩選器 | Phase 5 |
| `portfolio/` | C：多因子組合推薦 | Phase 3 |
| `tracking/` | D：組合追蹤 | Phase 6 |
| `education/` | E：嵌入式教學 | Phase 4 |

## 每個 feature 資料夾建議包含

- `overview.md` — 功能定義、負責的 UI 路徑與 API endpoints
- `data-sources.md` — 用到哪些 collector、資料從哪來
- `ui-layout.md` — 前端元件、頁面結構
- （視情況）`edge-cases.md`、`business-rules.md`

Phase 0 只保留資料夾與本 README，實際內容在對應 Phase 開始實作時撰寫。
