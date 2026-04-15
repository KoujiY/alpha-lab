---
domain: features/data-panel
updated: 2026-04-15
related: [overview.md, ../../collectors/twse.md, ../../collectors/mops.md]
---

# 個股頁資料來源對應

| 頁面 section | SQLite 表 | Collector | 更新頻率 |
|-------------|----------|----------|---------|
| Header（meta） | `stocks` | 手動 + `backfill_industry.py` | 少動 |
| PriceChart | `prices_daily` | `twse.py`（STOCK_DAY） | 每日收盤後 |
| RevenueSection | `revenues_monthly` | `mops.py`（t05st10） | 每月 10 日後 |
| FinancialsSection | `financial_statements` (income + balance) | `mops_financials.py`（t164sb03/04） | 每季公告期 |
| InstitutionalSection | `institutional_trades` | `twse_institutional.py`（T86） | 每日 |
| MarginSection | `margin_trades` | `twse_margin.py`（MI_MARGN） | 每日 |
| EventsSection | `events` | `mops_events.py`（t146sb05） | 每日掃描 |

## 現金流（Phase 3）

`financial_statements` 已預留 `statement_type='cashflow'` 欄位，但 Phase 2 不讀也不顯示。Phase 3 做 FCF 評分時一併補 MOPS t164sb05 collector + `_load_financials` 合併邏輯。
