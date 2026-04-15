---
domain: collectors/mops
updated: 2026-04-15
related: [twse.md, ../architecture/data-flow.md]
---

# MOPS Collector

## 目的

抓取公開資訊觀測站（MOPS）資料。

## 現行實作（Phase 1）

### 端點

| 用途 | URL | 備註 |
|------|-----|------|
| 最新月營收（全上市） | `https://openapi.twse.com.tw/v1/opendata/t187ap05_L` | 只回傳「最新一期」；要抓歷史需走 HTML |

### 已實作函式

- `fetch_latest_monthly_revenues(symbols=None) -> list[MonthlyRevenue]`
  - `symbols=None` 代表回傳全上市；傳 list 則過濾
  - 資料年月（民國）自動轉西元

### 資料單位與欄位

- `revenue`：千元（MOPS 原始單位）
- `yoy_growth` / `mom_growth`：百分比（%），可能為 `null`（MOPS 欄位空字串）

### 已知坑

- `資料年月` 格式 `"11503"` = 民國 115 年 3 月
- 部分欄位可能為空字串或 `"-"`，以 `_parse_optional_float` 處理
- Open API 不含歷史月份；Phase 1.5 要補歷史月需改爬 HTML 或用 `t21sc03` 檔下載

### Phase 1.5 規劃新增

- 季報（合併損益 `t164sb03`、資產負債、現金流 `t164sb05`）
- 重大訊息（`t146sb05`）
- 月營收歷史月份

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops.py](../../../backend/src/alpha_lab/collectors/mops.py)
- [backend/src/alpha_lab/schemas/revenue.py](../../../backend/src/alpha_lab/schemas/revenue.py)
- [backend/tests/collectors/test_mops.py](../../../backend/tests/collectors/test_mops.py)
- [backend/scripts/smoke_mops.py](../../../backend/scripts/smoke_mops.py)

## 修改時注意事項

- MOPS 欄位名稱含中文且有特殊字元（如 `"營業收入-當月營收"`），要逐字匹配
- 新增欄位：擴充 `MonthlyRevenue` + `RevenueMonthly` + upsert
- Open API 有時會回傳空陣列（每月 10 日前新月份尚未公告），需 handle
