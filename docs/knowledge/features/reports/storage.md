---
domain: features/reports/storage
updated: 2026-04-17
related: [../../architecture/data-flow.md, ../portfolio/recommender.md]
---

# Reports 儲存層（Phase 4）

## 目的

實作 CLAUDE.md §「Claude Code 分析 SOP」中定義的「分析後寫 Markdown 報告 + 更新 index.json + 寫一行摘要」流程。讓 Claude Code / 前端 / 後端 auto-save 都走同一組 API。

## 現行實作

- **根目錄**：`data/reports/`（預設）；測試或自訂可透過環境變數 `ALPHA_LAB_REPORTS_ROOT` 覆寫
- **目錄結構**：
  - `analysis/<id>.md` — 報告主體（YAML frontmatter + Markdown body）
  - `summaries/<YYYY-MM-DD>.json` — 當日每份報告一行摘要；append list
  - `index.json` — 全站 meta 索引，前端 / Claude 智能檢索用
- **報告類型與 id 規則**（對齊 CLAUDE.md SOP）：
  - `stock` → `stock-<symbol>-<YYYY-MM-DD>`（需 `subject`）
  - `research` → `research-<slugified-topic>-<YYYY-MM-DD>`（需 `subject`，內含空白 / `/` 轉為 `-`）
  - `portfolio` → `portfolio-<YYYY-MM-DD>`
  - `events` → `events-<YYYY-MM-DD>`
  - 同一 id 再寫會覆寫 markdown、**index 去重**（保留最新一筆）
- **排序**：`index.json` 內 `reports` 以 `(date, id)` 降冪排列，便於前端直接渲染列表

## 關鍵檔案

- [backend/src/alpha_lab/schemas/report.py](../../../backend/src/alpha_lab/schemas/report.py) — `ReportType` / `ReportMeta` / `ReportDetail` / `ReportCreate`
- [backend/src/alpha_lab/reports/storage.py](../../../backend/src/alpha_lab/reports/storage.py) — 低階 I/O：`get_reports_root`、`load_index`、`save_index`、`upsert_in_index`、`write_report_markdown`、`read_report_markdown`、`append_summary`
- [backend/src/alpha_lab/reports/service.py](../../../backend/src/alpha_lab/reports/service.py) — 高階 API：`create_report` / `list_reports` / `get_report`，`_build_report_id` 封裝 id 組裝規則
- [backend/src/alpha_lab/api/routes/reports.py](../../../backend/src/alpha_lab/api/routes/reports.py) — `GET /api/reports`、`GET /api/reports/{id}`、`POST /api/reports`
- [backend/tests/reports/test_storage.py](../../../backend/tests/reports/test_storage.py) — storage/service 單測
- [backend/tests/api/test_reports.py](../../../backend/tests/api/test_reports.py) — API 路由整合測試

## 修改時注意事項

- **id 規則改動要同步兩處**：`service._build_report_id` + CLAUDE.md SOP 表格。若破壞舊 id 格式，得給 migration / rename 腳本。
- **`date` 欄位**：schema 用 `from datetime import date as date_type`，避免「field 名 `date` 遮蔽 class 名 `date`」這個 Python annotation 坑（否則會噴 `NoneType | NoneType`）。新增 date 欄位沿用同樣 alias。
- **檔案側效**：`create_report` 會同時寫 3 個地方（markdown / index / summary）；改流程要一起測 roundtrip。
- **寫入不 atomic**：若日後有併發寫入需求，要改走 write-temp-then-rename 或加鎖；目前單人工具足矣。
- **frontmatter 要穩**：若前端或 Claude 以 regex 讀 frontmatter，欄位順序由 `service.create_report` 的 dict 決定（`sort_keys=False`），改 dict 時要考慮對下游的影響。
