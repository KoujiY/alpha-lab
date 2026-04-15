---
domain: collectors/mops
updated: 2026-04-16
related: [twse.md, events.md, ../architecture/data-flow.md]
---

# MOPS Collector

## 目的

抓取公開資訊觀測站（MOPS）/ TWSE OpenAPI 的公司財務資料：月營收、季報（損益 + 資產負債）。重大訊息獨立於 [`events.md`](events.md)。

## 現行實作（Phase 1.5 完成，Phase 3 增補現金流）

### 端點總覽

| 用途 | URL | 模組 |
|------|-----|------|
| 最新月營收（全上市） | `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` | `collectors/mops.py` |
| 合併綜合損益表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci` | `collectors/mops_financials.py` |
| 合併資產負債表（季） | `https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci` | `collectors/mops_financials.py` |
| 合併現金流量表（季，單檔） | `https://mops.twse.com.tw/mops/web/ajax_t164sb05`（POST HTML） | `collectors/mops_cashflow.py` |
| 重大訊息 | 見 [events.md](events.md) | `collectors/mops_events.py` |

### 已實作函式

- `fetch_latest_monthly_revenues(symbols=None)` — 最新月營收
- `fetch_income_statement(symbols=None)` — 最新季合併綜合損益
- `fetch_balance_sheet(symbols=None)` — 最新季合併資產負債
- `fetch_cashflow(symbol, roc_year, season)` — 單檔單季現金流（t164sb05 HTML parse）
- `upsert_cashflow(session, symbol, period, cf)` — 委派 runner.upsert_financial_statements

### 現金流量表（Phase 3 已落地）

**TWSE OpenAPI 的 `t187ap10_L_ci` 實測不存在 / 回 404**；`fetch_cashflow_statement`（mops_financials.py）保留為 placeholder，對應端點會 302 重導並回空 list，**不可**在 production 使用。

Phase 3 改走 **MOPS `t164sb05` 的 HTML 介面**（`collectors/mops_cashflow.py`）：

- POST form：`TYPEK=sii&co_id=<symbol>&year=<roc_year>&season=<1-4>`
- 以 BeautifulSoup 解析表格，用「營業活動之淨現金流入」「投資活動之淨現金流入」「籌資活動之淨現金流入」為列標頭 key
- 金額支援括號負數（`(1,234)` → -1234）與逗號千位分隔
- **MOPS WAF 敏感**：必須使用瀏覽器級 User-Agent + Referer + Origin（見 `_browser_headers`）。純 curl / 預設 httpx UA 會被擋回 `THE PAGE CANNOT BE ACCESSED`，此時 `fetch_cashflow` 會 raise `TWSERateLimitError`
- Job dispatch：`JobType.MOPS_CASHFLOW`（per-symbol/period），與既有 bulk `MOPS_FINANCIALS` 並存；不合併是因為 t164sb05 只能單檔單季抓
- **FCF 代理**：Phase 3 以 OCF（近四季加總）作為 FCF 近似，不扣 CapEx。CapEx 擷取留待未來 Phase（需 t164sb05 更細欄位或其他來源）

### 資料單位與欄位

- 月營收 `revenue`：千元（MOPS 原始單位）
- 季報數值（revenue / profit / 資產）：皆為**千元**
- `eps`：元（每股盈餘原始單位）
- yoy / mom growth：百分比（%），可能為 `null`

### 季報寬表策略

三表共用 `FinancialStatement` Pydantic + `financial_statements` table，以 `statement_type` 區分：
- `income`：填 `revenue / gross_profit / operating_income / net_income / eps`
- `balance`：填 `total_assets / total_liabilities / total_equity`
- `cashflow`：Phase 3 啟用（FCF 評分）；欄位為 `operating_cf / investing_cf / financing_cf`，由 `mops_cashflow.upsert_cashflow` 寫入

`raw_json_text` 欄位保留完整原始欄位（JSON 字串），供未來新 factor / 新指標使用。

### 已知坑

- `資料年月` 格式 `"11503"` = 民國 115 年 3 月；季報以 `年度` + `季別` 兩欄位合成 `period = "2026Q1"`
- 部分欄位可能為空字串或 `"-"`，以 `_parse_int_or_none` / `_parse_float_or_none` 處理
- **OpenAPI 欄位 key 偶有前後空白或全形括號**（`"營業毛利(毛損)"`）— 需逐字匹配，實作先對 key 做 `.strip()` 正規化
- OpenAPI 只回「最新一期」；歷史月份 / 歷史季度需改走 mopsov.twse.com.tw 的 POST form 介面，Phase 1.5 不做
- 現金流量端點（OpenAPI）不存在；Phase 3 改走 `t164sb05` HTML scrape（per-symbol/period，MOPS WAF 對 UA 敏感）

### Phase 3+ 規劃新增

- 歷史季度 / 歷史月份回補（爬 mopsov POST 介面或下載年度壓縮檔）
- 股利政策（配息 / 配股歷史）
- 董監事持股變動
- CapEx 擷取以支援完整 FCF = OCF - CapEx（目前 Phase 3 以 OCF 為代理）

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops.py](../../../backend/src/alpha_lab/collectors/mops.py)
- [backend/src/alpha_lab/collectors/mops_financials.py](../../../backend/src/alpha_lab/collectors/mops_financials.py)
- [backend/src/alpha_lab/collectors/mops_cashflow.py](../../../backend/src/alpha_lab/collectors/mops_cashflow.py)
- [backend/src/alpha_lab/schemas/revenue.py](../../../backend/src/alpha_lab/schemas/revenue.py)
- [backend/src/alpha_lab/schemas/financial_statement.py](../../../backend/src/alpha_lab/schemas/financial_statement.py)
- [backend/tests/collectors/test_mops.py](../../../backend/tests/collectors/test_mops.py)
- [backend/tests/collectors/test_mops_financials.py](../../../backend/tests/collectors/test_mops_financials.py)
- [backend/tests/collectors/test_mops_cashflow.py](../../../backend/tests/collectors/test_mops_cashflow.py)
- [backend/tests/collectors/test_mops_cashflow_upsert.py](../../../backend/tests/collectors/test_mops_cashflow_upsert.py)
- [backend/scripts/smoke_mops.py](../../../backend/scripts/smoke_mops.py)
- [backend/scripts/smoke_mops_financials.py](../../../backend/scripts/smoke_mops_financials.py)

## 修改時注意事項

- MOPS / OpenAPI 欄位名稱含特殊字元（全形括號、可能前後空白），必須逐字匹配並先 `.strip()` key；建議優先用 `.get(key)` 並提供 fallback key
- 新增表類型：擴充 `StatementType` enum + `FinancialStatement` schema nullable 欄位 + `mops_financials.py` 新 fetch 函式 + `runner.upsert_financial_statements` fields dict + `_dispatch` `MOPS_FINANCIALS` 分支 types 清單
- **Phase 3 加入 cashflow 時（FCF 評分需要）**：獨立模組（如 `mops_cashflow_html.py`），不要把 HTML 解析混入 OpenAPI 模組；需處理 MOPS session cookie、POST form、HTML table parse 等
- 歷史回補功能若要加：獨立新模組（`mops_history.py`），不要把 HTML 解析混入 OpenAPI 模組
