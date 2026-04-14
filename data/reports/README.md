# data/reports — 分析報告永久儲存區

這個資料夾用來儲存 Claude Code 分析產出的 Markdown 報告。Git 不追蹤內容檔案（由 `.gitignore` 排除），只保留資料夾結構說明與這份 README。

## 結構

```
data/reports/
├── index.json              # 所有報告的輕量索引
├── daily/                  # 每日自動簡報
├── analysis/               # 深度分析（永久保存）
└── summaries/              # 一行摘要（智能檢索用）
```

## 報告類型

| 類型 | 檔名格式 |
|------|---------|
| stock | `stock-<symbol>-YYYY-MM-DD.md` |
| portfolio | `portfolio-YYYY-MM-DD.md` |
| events | `events-YYYY-MM-DD.md` |
| research | `research-<topic>-YYYY-MM-DD.md` |

## 備份

此資料夾不納入 git。若需備份，建議同步到雲端硬碟或定期 zip 存檔。
