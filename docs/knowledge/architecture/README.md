# architecture/ — 系統架構

跨功能的架構層知識。Claude 修改資料流、新增 API、調整資料模型時的首要參考。

## 規劃條目

| 檔案 | 內容 | 規劃於 Phase |
|------|------|-------------|
| `tech-stack.md` | 技術選型與理由（為什麼選 FastAPI、pnpm、SQLite 等） | Phase 0 末 |
| `data-models.md` | SQLAlchemy models 與 Pydantic schemas 總覽 | Phase 1 |
| `api-reference.md` | 所有 API endpoints 清單與用途（附 Swagger 連結） | Phase 2 起 |
| `data-flow.md` | TWSE/MOPS → collector → SQLite → API → UI 的完整路徑 | Phase 1 |
| `storage.md` | `data/` 下各子資料夾用途、`index.json` schema、備份策略 | Phase 4 |
| `ui-conventions.md` | 跨功能共用的前端 UI 模式（狀態面板、共用 dialog、hooks、localStorage vs DB） | Phase 6 |
| `processed-store.md` | `data/processed/` 計算後指標 JSON 存放 | Phase 7B.1 |
| `daily-briefing.md` | 每日市場簡報自動產出機制 | Phase 7B.2 |
| `report-cache.md` | 報告 IndexedDB 離線快取機制 | Phase 7B.3 |

Phase 0 只保留資料夾與本 README。
