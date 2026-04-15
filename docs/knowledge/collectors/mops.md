---
domain: collectors/mops
updated: 2026-04-15
related: [twse.md, events.md, ../architecture/data-flow.md]
---

# MOPS Collector

## 目的

抓取公開資訊觀測站（MOPS）/ TWSE OpenAPI 的公司財務資料：月營收、季報（損益 + 資產負債）。重大訊息獨立於 [`events.md`](events.md)。

## 現行實作（Phase 1.5 完成）

### 端點總覽

| 用途 | URL | 模組 |
|------|-----|------|
| 最新月營收（全上市） | `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` | `collectors/mops.py` |
| 合併綜合損益表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci` | `collectors/mops_financials.py` |
| 合併資產負債表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci` | `collectors/mops_financials.py` |
| 重大訊息 | 見 [events.md](events.md) | `collectors/mops_events.py` |

### 已實作函式

- `fetch_latest_monthly_revenues(symbols=None)` — 最新月營收
- `fetch_income_statement(symbols=None)` — 最新季合併綜合損益
- `fetch_balance_sheet(symbols=None)` — 最新季合併資產負債

### 現金流量表：Phase 2 才做（重要）

**TWSE OpenAPI 實測只開放 income（`t187ap06_L_ci`）+ balance（`t187ap07_L_ci`）兩張表**。原本規劃的 `t187ap10_L_ci` 現金流量端點**實際不存在 / 回 404**，因此：

- Phase 1.5 **不**提供穩定的 cashflow 抓取；`fetch_cashflow_statement` 若存在也僅為 placeholder，**不建議在 production 呼叫**
- `financial_statements` table schema 已預留 `cashflow` 類型的欄位（`operating_cf` / `investing_cf` / `financing_cf`），但目前無 collector 填入
- **Phase 2 實作策略**：FCF 相關計分（free cash flow scoring）需要時，改爬 MOPS `t164sb05`（合併現金流量表 HTML 頁面），以 POST form + HTML parsing 實作，不走 OpenAPI

### 資料單位與欄位

- 月營收 `revenue`：千元（MOPS 原始單位）
- 季報數值（revenue / profit / 資產）：皆為**千元**
- `eps`：元（每股盈餘原始單位）
- yoy / mom growth：百分比（%），可能為 `null`

### 季報寬表策略

三表共用 `FinancialStatement` Pydantic + `financial_statements` table，以 `statement_type` 區分：
- `income`：填 `revenue / gross_profit / operating_income / net_income / eps`
- `balance`：填 `total_assets / total_liabilities / total_equity`
- `cashflow`：**Phase 2 才啟用**；欄位為 `operating_cf / investing_cf / financing_cf`

`raw_json_text` 欄位保留完整原始欄位（JSON 字串），供未來新 factor / 新指標使用。

### 已知坑

- `資料年月` 格式 `"11503"` = 民國 115 年 3 月；季報以 `年度` + `季別` 兩欄位合成 `period = "2026Q1"`
- 部分欄位可能為空字串或 `"-"`，以 `_parse_int_or_none` / `_parse_float_or_none` 處理
- **OpenAPI 欄位 key 偶有前後空白或全形括號**（`"營業毛利(毛損)"`）— 需逐字匹配，實作先對 key 做 `.strip()` 正規化
- OpenAPI 只回「最新一期」；歷史月份 / 歷史季度需改走 mopsov.twse.com.tw 的 POST form 介面，Phase 1.5 不做
- 現金流量端點不存在（見上節），Phase 2 改走 `t164sb05` HTML scrape

### Phase 2+ 規劃新增

- 現金流量表（MOPS `t164sb05` HTML）
- 歷史季度 / 歷史月份回補（爬 mopsov POST 介面或下載年度壓縮檔）
- 股利政策（配息 / 配股歷史）
- 董監事持股變動

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops.py](../../../backend/src/alpha_lab/collectors/mops.py)
- [backend/src/alpha_lab/collectors/mops_financials.py](../../../backend/src/alpha_lab/collectors/mops_financials.py)
- [backend/src/alpha_lab/schemas/revenue.py](../../../backend/src/alpha_lab/schemas/revenue.py)
- [backend/src/alpha_lab/schemas/financial_statement.py](../../../backend/src/alpha_lab/schemas/financial_statement.py)
- [backend/tests/collectors/test_mops.py](../../../backend/tests/collectors/test_mops.py)
- [backend/tests/collectors/test_mops_financials.py](../../../backend/tests/collectors/test_mops_financials.py)
- [backend/scripts/smoke_mops.py](../../../backend/scripts/smoke_mops.py)
- [backend/scripts/smoke_mops_financials.py](../../../backend/scripts/smoke_mops_financials.py)

## 修改時注意事項

- MOPS / OpenAPI 欄位名稱含特殊字元（全形括號、可能前後空白），必須逐字匹配並先 `.strip()` key；建議優先用 `.get(key)` 並提供 fallback key
- 新增表類型：擴充 `StatementType` enum + `FinancialStatement` schema nullable 欄位 + `mops_financials.py` 新 fetch 函式 + `runner.upsert_financial_statements` fields dict + `_dispatch` `MOPS_FINANCIALS` 分支 types 清單
- **Phase 2 加入 cashflow 時**：獨立模組（如 `mops_cashflow_html.py`），不要把 HTML 解析混入 OpenAPI 模組；需處理 MOPS session cookie、POST form、HTML table parse 等
- 歷史回補功能若要加：獨立新模組（`mops_history.py`），不要把 HTML 解析混入 OpenAPI 模組
