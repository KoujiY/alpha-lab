---
domain: architecture
updated: 2026-04-17
related: [data-flow.md, ../collectors/twse.md, ../collectors/mops.md, ../collectors/mops-cashflow.md, ../collectors/events.md, ../domain/scoring.md]
---

# 資料模型

## 目的

記錄 SQLAlchemy models 與 Pydantic schemas 的總覽，供 Claude 修改資料結構時參考。

## 現行實作（Phase 1.5 完成）

### SQLAlchemy Models（`backend/src/alpha_lab/storage/models.py`）

| Table | 主鍵 | 來源 | Phase |
|-------|------|------|-------|
| `stocks` | symbol | collector 隱性建立 | 1 |
| `prices_daily` | (symbol, trade_date) | TWSE STOCK_DAY | 1 |
| `revenues_monthly` | (symbol, year, month) | MOPS t187ap05_L | 1 |
| `jobs` | id (autoincrement) | API 觸發 | 1 |
| `institutional_trades` | (symbol, trade_date) | TWSE T86 | 1.5 |
| `margin_trades` | (symbol, trade_date) | TWSE MI_MARGN | 1.5 |
| `events` | id (autoincrement) | TWSE OpenAPI t187ap04_L | 1.5 |
| `financial_statements` | (symbol, period, statement_type) | TWSE OpenAPI t187ap06/07_L_ci（income + balance）；cashflow 採 MOPS t164sb05 HTML scrape | 1.5 / 3 |
| `scores` | (symbol, calc_date) | `compute_scores` pipeline 產出 | 3 |
| `portfolios_saved` | id (autoincrement) | 使用者儲存的推薦組合，holdings 以 JSON Text 內嵌 | 6 |
| `portfolio_snapshots` | (portfolio_id, snapshot_date) | NAV 快照快取（`compute_performance` 自動 upsert 最新一筆） | 6 |

### Pydantic Schemas

| 檔案 | 用途 |
|------|------|
| `schemas/health.py` | `/api/health` 回傳 |
| `schemas/price.py` | `DailyPrice` |
| `schemas/revenue.py` | `MonthlyRevenue` |
| `schemas/institutional.py` | `InstitutionalTrade` |
| `schemas/margin.py` | `MarginTrade` |
| `schemas/event.py` | `Event` |
| `schemas/financial_statement.py` | `FinancialStatement` + `StatementType` enum |
| `schemas/job.py` | Job API request/response |
| `schemas/saved_portfolio.py` | Saved Portfolio API（`SavedPortfolioCreate`、`SavedPortfolioMeta`、`SavedPortfolioDetail`、`PerformanceResponse`） |

### 設計原則

- Collector 輸出 Pydantic 物件 → runner 負責 upsert 到 SQLAlchemy model
- Pydantic schemas 是「API / collector 邊界」的合約；SQLAlchemy models 是「持久層」的實體
- `financial_statements` 採「寬表 + raw_json_text」策略：常用欄位獨立存放，原始完整欄位以 JSON 字串保留供未來擴充
- `events` 主鍵為 autoincrement id（同公司同時刻可能多則），以 `(symbol, event_datetime, title)` 查重
- `Stock` 在 collector 隱性建立 placeholder（name=symbol）；正式公司資料同步在 Phase 2+

## 關鍵檔案

- [backend/src/alpha_lab/storage/models.py](../../../backend/src/alpha_lab/storage/models.py)
- [backend/src/alpha_lab/storage/engine.py](../../../backend/src/alpha_lab/storage/engine.py)
- [backend/src/alpha_lab/schemas/](../../../backend/src/alpha_lab/schemas/)

## 修改時注意事項

- 新增 table：加到 `models.py`、用 `create_all` 自動建表；**Phase 2 若 schema 再有破壞性變動，應引入 Alembic**
- 新增欄位：nullable 可直接加；既存 DB 會 no-op，需 drop 或手動 ALTER
- 主鍵選擇：時間序列用 composite；事件/任務類（`jobs`、`events`）用 autoincrement
- `financial_statements` 增加新表類型時：擴充 `StatementType` enum + 對應 nullable 欄位 + runner fields dict
- Phase 3 已加入 cashflow（FCF 評分需要）：來源 MOPS `t164sb05` HTML scrape，見 `collectors/mops-cashflow.md`
- `scores` 表只存當日快照；多次 upsert 同日會覆寫 row，歷史分數不保留
- Phase 6 `portfolios_saved` 的 `holdings_json` 欄位將持股明細（`list[{symbol, name, weight, base_price}]`）序列化為 JSON 字串存於 `Text` 欄位，無獨立 holdings 關聯表；修改持股資料結構時需同步更新 `SavedHolding` schema，並考量既存 DB row 的相容性
