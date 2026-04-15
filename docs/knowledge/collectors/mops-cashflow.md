---
domain: collectors/mops-cashflow
updated: 2026-04-15
related: [../architecture/data-models.md]
---

# MOPS 現金流量表 Collector

## 目的

抓取 MOPS t164sb05 的季現金流，寫入 `financial_statements.statement_type='cashflow'`。

## 現行實作（Phase 3）

- **來源**：`POST https://mops.twse.com.tw/mops/web/ajax_t164sb05`
- **參數**：`TYPEK=sii`、`co_id=<symbol>`、`year=<民國年>`、`season=1-4`
- **反爬蟲**：需送 browser 級 headers（User-Agent / Referer / Origin），搭配 truststore SSLContext 避開 Windows Python 3.14 certifi SKID 問題
- **解析**：BS4 抓以「營業活動之淨現金流入」「投資活動之淨現金流入」「籌資活動之淨現金流入」為列標頭的 `<tr>`，取第一個純數字 cell
- **括號處理**：`(1,234)` → `-1234`
- **單位**：千元（TWSE 慣例，不做換算）

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops_cashflow.py](../../../backend/src/alpha_lab/collectors/mops_cashflow.py)
- [backend/tests/fixtures/mops_t164sb05_2330_2026Q1.html](../../../backend/tests/fixtures/)

## 觸發方式

- API：`POST /api/jobs/collect` with `job_type='mops_cashflow'`, `params={'symbol': '2330', 'period': '2026Q1'}`

## 修改時注意事項

- MOPS 表格結構變動 → 調整 `_LABELS` 與 `_find_row`
- 若要支援上櫃（otc）→ 加 `TYPEK=otc` 參數
- FCF 未扣 CapEx（Phase 3 簡化）；日後引入 CapEx 需另解析「購置不動產、廠房及設備」
