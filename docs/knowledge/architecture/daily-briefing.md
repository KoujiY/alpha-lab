---
domain: architecture/daily-briefing
updated: 2026-04-18
related: [processed-store.md, ../collectors/README.md]
---

# 每日市場簡報（Daily Briefing）

## 目的

每天收盤後自動產出一份 Markdown 簡報，涵蓋：市場概況、法人動向、重大訊息、組合追蹤。存至 `data/reports/daily/{date}.md`，同步更新 `data/reports/index.json`。

## 現行實作

- `briefing/sections.py`：四個 section builder（純函式，接收 dict list）
- `briefing/daily.py`：assembler，從 DB 查詢資料並組合各 section
- `reports/service.py` → `create_daily_report()`：寫檔 + 更新 index
- `reports/storage.py` → `write_daily_markdown()`：寫入 `daily/` 子目錄
- `JobType.DAILY_BRIEFING`：透過 job 系統觸發
- `daily_collect.py`：pipeline 尾端自動跑

## 關鍵檔案

- [backend/src/alpha_lab/briefing/daily.py](../../../backend/src/alpha_lab/briefing/daily.py)
- [backend/src/alpha_lab/briefing/sections.py](../../../backend/src/alpha_lab/briefing/sections.py)
- [backend/src/alpha_lab/reports/service.py](../../../backend/src/alpha_lab/reports/service.py)
- [backend/src/alpha_lab/reports/storage.py](../../../backend/src/alpha_lab/reports/storage.py)

## 修改時注意事項

- 新增 section：在 `sections.py` 加 builder，在 `daily.py` 的 `build_daily_briefing` 串入
- section builder 不可直接存取 DB（職責分離）；DB 查詢統一在 `daily.py`
- Daily 報告不寫 frontmatter（與 analysis/ 下的報告不同）——純 Markdown body
- `ReportType` 已擴充為 `"daily"`，前端 list reports 時需注意新類型
