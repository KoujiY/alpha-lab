---
domain: architecture
updated: 2026-04-17
related: [data-models.md, ../collectors/twse.md, ../collectors/twse-stock-info.md, ../collectors/mops.md, ../collectors/mops-cashflow.md, ../collectors/events.md, ../domain/scoring.md, ../features/portfolio/recommender.md, ../features/reports/storage.md, ../features/screener/overview.md, ../features/tracking/overview.md]
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
| `twse_stock_info` | `fetch_stock_info`（Pre-Phase 4 Step 0） | `stocks`（name / industry / listed_date） |
| `mops_revenue` | `fetch_latest_monthly_revenues` | `revenues_monthly` |
| `twse_institutional` | `fetch_institutional_trades` | `institutional_trades` |
| `twse_margin` | `fetch_margin_trades` | `margin_trades` |
| `mops_events` | `fetch_latest_events` | `events` |
| `mops_financials` | `fetch_income_statement` / `fetch_balance_sheet` | `financial_statements` |
| `mops_cashflow` | `fetch_cashflow`（Phase 3） | `financial_statements`（statement_type='cashflow'） |
| `score` | `score_all`（Phase 3） | `scores` |

### Session 管理原則

- 每個「邏輯工作單元」用一次 `session_scope()` context manager
- Job runner 把 read、write、執行 collector 分成獨立 session，避免長交易
- Collector 本身不碰 DB，純函式 → 方便測試

### 錯誤處理

- Collector 拋例外 → `run_job_sync` 捕捉、寫 `job.error_message`、`status=failed`、**不** re-raise
- HTTP 錯誤 → `resp.raise_for_status()` 自然拋 `httpx.HTTPStatusError`
- 資料驗證錯誤 → Pydantic `ValidationError`，當成 collector 異常處理

### 批次入口：`scripts/daily_collect.py`

- CLI 封裝「TWSE 上市公司基本資料 + TWSE 日成交 + 三大法人 + 融資融券 + 重大訊息」五類 daily job
- **上市公司基本資料放最前面**：後續 collector 若遇到新 symbol，`stocks` 表會已備好
  正式 name / industry / listed_date，而不是 placeholder（Pre-Phase 4 Step 0 起）
- 不走 HTTP API，直接呼叫 `create_job` + `run_job_sync`
- **Prices flag（2026-04-15 加入全市場保險）**：`--symbols` 與 `--all` 互斥
  - `--symbols 2330,2317` → 用傳入清單逐檔抓（最常見用法）
  - `--all` → 明示意圖跑 DB watchlist 全體（逐檔抓約 20-40 分鐘，有 TWSE IP 限流風險）
  - 皆未傳 → **skip prices** 並印引導訊息（避免誤觸 1000+ 檔全市場抓取）
  - `--all` 但 `stocks` 表為空 → skip prices 並提示
- 三大法人 / 融資融券 / 重大訊息則不吃 watchlist，保持 `symbols=None` 意即「全市場」——這三個端點本來就是「單次打、回全市場」，跟 prices 的「逐檔打」不同
- 未來若要排程，以 OS cron / Windows 排程器呼叫此腳本（Phase 1.5/2 階段不做排程本身）

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

## Phase 3 新增：評分與組合推薦

```
SQLite (prices_daily, revenues_monthly, financial_statements)
  → analysis/pipeline.py::build_snapshot（每 symbol 聚合出四因子原始指標）
    → analysis/normalize.py（橫截面百分位）
      → analysis/factor_*.py（0-100 分）
        → analysis/weights.py::weighted_total（balanced 權重 → total_score）
          → scores 表（upsert，每日 snapshot）

scores
  → api/routes/stocks.py::GET /api/stocks/{symbol}/score  → frontend ScoreRadar
  → api/routes/portfolios.py::POST /api/portfolios/recommend
      → analysis/portfolio.py::generate_portfolio（runtime 套風格權重、產業分散、softmax 權重）
        → frontend PortfoliosPage / PortfolioTabs
```

觸發：`POST /api/jobs/collect` with `job_type='score'` 或 CLI `scripts/compute_scores.py`。

詳見 [domain/scoring.md](../domain/scoring.md) 與 [features/portfolio/recommender.md](../features/portfolio/recommender.md)。

## Phase 4 新增：報告寫入 / 讀取

```
POST /api/reports (ReportCreate)  |  Claude Code 分析 SOP
  → reports/service.py::create_report
      │  _build_report_id(type, date, subject)
      ▼
  reports/storage.py
      ├─ write_report_markdown → data/reports/analysis/<id>.md（YAML frontmatter + body）
      ├─ upsert_in_index        → data/reports/index.json（meta 去重 + date 排序）
      └─ append_summary         → data/reports/summaries/<date>.json（list of {summary}）

GET /api/reports(?type=&tag=)
  → reports/service.py::list_reports → load_index → filter by type / tag

GET /api/reports/{id}
  → reports/service.py::get_report → load_index + read_report_markdown → ReportDetail
```

- **根目錄**：預設 `data/reports/`，環境變數 `ALPHA_LAB_REPORTS_ROOT` 可覆寫（測試 / 自訂存放點）。
- **檔案三件組**：一份報告寫 markdown + 更新 index.json + append summary，三者一致性由 `create_report` 一次搞定。
- **id 規則**：見 [features/reports/storage.md](../features/reports/storage.md)；破壞此規則要同步 CLAUDE.md SOP。
- **讀取面**：前端 `/reports` 列表直接吃 `index.json` 排好的順序；細節頁才讀 markdown 檔。

詳見 [features/reports/storage.md](../features/reports/storage.md)。

## Phase 5 新增：選股篩選器

```
GET /api/screener/factors → 靜態 FACTOR_DEFINITIONS → FactorsResponse

POST /api/screener/filter (FilterRequest)
  → screener.py::filter_stocks
    → latest_calc_date(session)
    → SELECT scores + stocks WHERE calc_date = latest
    → _passes_filters（逐 row 過濾）
    → weighted_total（balanced 權重算 total）
    → 排序 + limit → FilterResponse
```

前端：`/screener` → fetchFactors + filterStocks → ScreenerPage（滑桿 + 結果表格）

詳見 [features/screener/overview.md](../features/screener/overview.md)。

## Phase 6 新增：組合追蹤

```
POST /api/portfolios/saved (SavedPortfolioCreate)
  → portfolios/service.py::save_portfolio
    → base_date = date.today()（由 route 傳入）
    → 遍歷 holdings：若 base_price <= 0
        → SELECT prices_daily.close WHERE symbol = h.symbol AND trade_date = base_date
        → 找不到 → raise ValueError → route 回 HTTP 400
    → INSERT portfolios_saved row（holdings 序列化為 JSON Text 內嵌）

GET /api/portfolios/saved → list_saved()
  → SELECT portfolios_saved ORDER BY created_at DESC → list[SavedPortfolioMeta]

GET /api/portfolios/saved/{id} → get_saved()
  → session.get(SavedPortfolio, id) → SavedPortfolioDetail（含 holdings 明細）

DELETE /api/portfolios/saved/{id} → delete_saved()
  → session.delete(row) → 204；不存在 → 404

GET /api/portfolios/saved/{id}/performance
  → portfolios/service.py::compute_performance
    → load SavedPortfolio row + _holdings_from_json
    → SELECT prices_daily WHERE symbol IN holdings AND trade_date >= base_date
    → 計算各 symbol 有報價日期的交集（共同交易日）
    → for each trade_date（升序）：
        nav(t) = Σ( weight_i × price_i(t) / base_price_i )
        daily_return = nav(t) / nav(t-1) - 1（第一筆為 None）
    → upsert portfolio_snapshots（最新一筆，供排程擴充用）
    → PerformanceResponse { portfolio, points, latest_nav, total_return }
```

前端消費：
- `PortfolioTrackingPage.tsx` 呼叫 `fetchPerformance(id)` → `PerformanceChart.tsx`（recharts `LineChart`）渲染 NAV 走勢；`total_return` 以百分比格式顯示於頁面上方。
- `SavedPortfolioList.tsx` 於 `/portfolios` 推薦頁底渲染已儲存清單，每項可跳轉 `/portfolios/:id`。

詳見 [features/tracking/overview.md](../features/tracking/overview.md)。
