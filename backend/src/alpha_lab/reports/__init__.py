"""Reports 儲存模組（Phase 4）。

嚴格依 CLAUDE.md §「Claude Code 分析 SOP」：

- 檔案根目錄：`data/reports/`（可由環境變數 `ALPHA_LAB_REPORTS_ROOT` 覆寫，測試用）
- 子目錄：`analysis/`（報告主體）、`daily/`（每日簡報）、`summaries/<date>.json`（一行摘要）
- Index：`index.json` 彙整所有 meta，供前端 / Claude Code 智能檢索
"""

from alpha_lab.reports.service import create_report, get_report, list_reports
from alpha_lab.reports.storage import get_reports_root

__all__ = [
    "create_report",
    "get_report",
    "get_reports_root",
    "list_reports",
]
