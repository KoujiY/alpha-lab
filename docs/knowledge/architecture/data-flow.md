---
domain: architecture
updated: 2026-04-15
related: [data-models.md, ../collectors/twse.md, ../collectors/mops.md, ../collectors/events.md]
---

# 資料流

## 目的

描述「外部資料源 → collector → SQLite → API → UI」完整路徑。

## 現行實作（Phase 1.5 完成）

### 端到端流程

```
使用者 / CLI (scripts/daily_collect.py) / 排程
   │  POST /api/jobs/collect  或  create_job + run_job_sync
   ▼
Job runner (jobs/service.py)
   │  status=running → dispatch by JobType ↓
   ▼
Collector (collectors/*.py)
   │  httpx + truststore SSL → TWSE / MOPS / OpenAPI
   │  回傳 list[Pydantic schema]
   ▼
Upsert runner (collectors/runner.py)
   │  SQLAlchemy session → SQLite (data/alpha_lab.db)
   ▼
Job runner
   │  status=completed, result_summary 寫回 jobs 表
   ▼
API 輪詢 / CLI 印出結果
```

### JobType 與 collector 對應

| JobType | collector 函式 | 落庫 table |
|---------|---------------|-----------|
| `twse_prices` | `fetch_daily_prices` | `prices_daily` |
| `mops_revenue` | `fetch_latest_monthly_revenues` | `revenues_monthly` |
| `twse_institutional` | `fetch_institutional_trades` | `institutional_trades` |
| `twse_margin` | `fetch_margin_trades` | `margin_trades` |
| `mops_events` | `fetch_latest_events` | `events` |
| `mops_financials` | `fetch_income_statement` / `fetch_balance_sheet`（cashflow 延至 Phase 3） | `financial_statements` |

### Session 管理原則

- 每個「邏輯工作單元」用一次 `session_scope()` context manager
- Job runner 把 read、write、執行 collector 分成獨立 session，避免長交易
- Collector 本身不碰 DB，純函式 → 方便測試

### 錯誤處理

- Collector 拋例外 → `run_job_sync` 捕捉、寫 `job.error_message`、`status=failed`、**不** re-raise
- HTTP 錯誤 → `resp.raise_for_status()` 自然拋 `httpx.HTTPStatusError`
- 資料驗證錯誤 → Pydantic `ValidationError`，當成 collector 異常處理

### 批次入口：`scripts/daily_collect.py`

- CLI 封裝「TWSE 日成交 + 三大法人 + 融資融券 + 重大訊息」四類 daily job
- 不走 HTTP API，直接呼叫 `create_job` + `run_job_sync`
- **`--symbols` 省略時**：從 DB `stocks` 表讀 watchlist 當 TWSE 日成交的 symbols 清單（逐檔抓）；若 DB 為空才真正 skip（2026-04-15 加入）
- 三大法人 / 融資融券 / 重大訊息則不吃 watchlist，保持 `symbols=None` 意即「全市場」
- 未來若要排程，以 OS cron / Windows 排程器呼叫此腳本（Phase 1.5/2 階段不做排程本身）
- **實務注意**：全 watchlist（上千檔）逐檔抓耗時 20-40 分鐘且有 TWSE 限流風險，平時建議傳 `--symbols` 顯式指定

## 關鍵檔案

- [backend/src/alpha_lab/jobs/service.py](../../../backend/src/alpha_lab/jobs/service.py)
- [backend/src/alpha_lab/jobs/types.py](../../../backend/src/alpha_lab/jobs/types.py)
- [backend/src/alpha_lab/collectors/runner.py](../../../backend/src/alpha_lab/collectors/runner.py)
- [backend/src/alpha_lab/api/routes/jobs.py](../../../backend/src/alpha_lab/api/routes/jobs.py)
- [backend/scripts/daily_collect.py](../../../backend/scripts/daily_collect.py)

## 修改時注意事項

- 新增 collector：
  1. 在 `collectors/` 新增模組（fetch 函式輸出 Pydantic list）
  2. 在 `schemas/` 建立對應 Pydantic model
  3. 在 `storage/models.py` 建立對應 SQLAlchemy model + 更新 `__init__.py`
  4. 在 `collectors/runner.py` 加對應 upsert 函式
  5. 在 `jobs/types.py::JobType` 加一個 value
  6. 在 `jobs/service.py::_dispatch` 加分支
  7. （可選）在 `scripts/daily_collect.py` 追加一個 `_run_one` 呼叫
  8. 更新對應 `collectors/<source>.md` 知識庫 + 本檔 JobType 對應表
- 改 job 執行模型（例如要併發）：
  - 現在是 FastAPI BackgroundTasks（單程序），改 Celery/RQ 需同步改 `service.run_job_sync` 入口與 session factory 傳遞
- 排程：目前無 APScheduler / cron 整合；Phase 2+ 再評估

## Phase 2 新增：讀取面

Phase 2 導入**讀取面 API 層**：

```
SQLite (prices_daily, revenues_monthly, financial_statements, institutional_trades, margin_trades, events, stocks)
  → api/routes/stocks.py::_load_* helpers
    → api/routes/stocks.py::get_stock_overview（聚合）/ get_stock_{section}（細端點）
      → frontend hooks/useStockOverview.ts
        → pages/StockPage.tsx → components/stock/*
```

Glossary 走獨立管線（YAML → loader → API → useGlossary → TermTooltip），無 SQLite 參與。

詳見 [features/data-panel/overview.md](../features/data-panel/overview.md) 與 [features/education/tooltip.md](../features/education/tooltip.md)。
