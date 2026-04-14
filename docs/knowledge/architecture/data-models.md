---
domain: architecture
updated: 2026-04-15
related: [data-flow.md, ../collectors/twse.md, ../collectors/mops.md]
---

# 資料模型

## 目的

記錄 SQLAlchemy models 與 Pydantic schemas 的總覽，供 Claude 修改資料結構時參考。

## 現行實作（Phase 1）

### SQLAlchemy Models（`backend/src/alpha_lab/storage/models.py`）

| Table | 主鍵 | 來源 | Phase |
|-------|------|------|-------|
| `stocks` | symbol | 手動/collector 隱性建立 | 1 |
| `prices_daily` | (symbol, trade_date) | TWSE STOCK_DAY | 1 |
| `revenues_monthly` | (symbol, year, month) | MOPS t187ap05_L | 1 |
| `jobs` | id (autoincrement) | API 觸發 | 1 |

**Phase 1.5 規劃新增**：`financial_statements`、`institutional_trades`、`margin_trades`、`events`。

### Pydantic Schemas

| 檔案 | 用途 |
|------|------|
| `schemas/health.py` | `/api/health` 回傳 |
| `schemas/price.py` | `DailyPrice`（collector 輸出） |
| `schemas/revenue.py` | `MonthlyRevenue`（collector 輸出） |
| `schemas/job.py` | Job API request/response |

### 設計原則

- Collector 輸出 Pydantic 物件 → runner 負責 upsert 到 SQLAlchemy model
- Pydantic schemas 是「API / collector 邊界」的合約；SQLAlchemy models 是「持久層」的實體
- `Stock` 在 collector 隱性建立 placeholder（name=symbol）；正式公司資料同步在 Phase 1.5 或 2

## 關鍵檔案

- [backend/src/alpha_lab/storage/models.py](../../../backend/src/alpha_lab/storage/models.py)
- [backend/src/alpha_lab/storage/engine.py](../../../backend/src/alpha_lab/storage/engine.py)
- [backend/src/alpha_lab/schemas/](../../../backend/src/alpha_lab/schemas/)

## 修改時注意事項

- 新增 table：加到 `models.py`、用 `create_all` 自動建表；Phase 1.5 若要變更現有欄位，考慮引入 Alembic
- 新增欄位：若是 nullable 可直接加，`create_all` 對既存表是 no-op，需 drop DB 或手動 ALTER
- 主鍵選擇：時間序列（`prices_daily`、`revenues_monthly`）用 composite；事件/任務類（`jobs`）用 autoincrement
