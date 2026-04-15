# alpha-lab 專案協作指南

## 專案概述

台股長線投資個人工具，目標是「自動推薦 + 嵌入式教學」。

完整設計見 [docs/superpowers/specs/2026-04-14-alpha-lab-design.md](docs/superpowers/specs/2026-04-14-alpha-lab-design.md)。

## 技術棧

- **Frontend**：Vite + React 19 + TypeScript、Tailwind CSS、TanStack Query、Zustand、vitest、Playwright
- **Backend**：FastAPI + Python 3.11+、SQLAlchemy 2.x、SQLite、Pydantic v2、pytest
- **數據層**：本地檔案 + SQLite（`data/` 不 commit）
- **Package Manager**：frontend 用 pnpm；backend 用 uv 或 pip

## 常用指令

```bash
# Backend
cd backend && uvicorn alpha_lab.api.main:app --reload
cd backend && pytest
cd backend && ruff check . && mypy src

# Frontend
cd frontend && pnpm dev
cd frontend && pnpm build
cd frontend && pnpm type-check
cd frontend && pnpm lint
cd frontend && pnpm test
cd frontend && pnpm e2e
```

## 使用者驗收指引 Shell 格式（MANDATORY）

使用者跑驗收指令的環境是 **Windows CMD**（不是 bash、不是 PowerShell）。產出驗收指引時：

- **路徑分隔**：用反斜線 `\`（如 `.venv\Scripts\python.exe`），不要用正斜線
- **註解**：用 `REM`，不用 `#`
- **變數**：用 `%VAR%`，不用 `$VAR`
- **code fence 語言**：寫 ```cmd 不寫 ```bash
- **多指令串接**：用 `&&`（cmd 也支援），但避免 `;`（cmd 不支援）
- `rm` / `ls` / `cat` 等 Unix 指令不可用；需要刪檔用 `del`、列目錄用 `dir`

開發者自己（Claude）用的 Bash tool 仍用 Unix 語法（harness 提供 bash shell），只有給使用者的驗收指引要切 CMD 格式。

## 開發流程

1. 讀設計 spec 確認範圍
2. 依當前 Phase 的實作計畫（`docs/superpowers/plans/`）進行
3. 每個 Task 完成後：
   - 跑靜態檢查（`tsc`、`ruff`、`mypy`）
   - 跑對應測試
   - **給使用者手動驗收指引**
   - 等使用者明確確認「驗證通過」
   - 才 commit
4. **每個 Phase 結束**：等使用者指示再開始下一個 Phase

## 分階段規劃原則（MANDATORY）

**實作計畫採「Just-in-Time」撰寫**：

- 專案有整體設計 spec（`docs/superpowers/specs/`），定義所有 Phase 的整體方向
- 但**實作計畫每次只擴寫當前要做的 Phase**（`docs/superpowers/plans/<date>-phase-N-<name>.md`）
- **下一個 Phase 的實作計畫不預先撰寫**，要等當前 Phase 驗收完成、使用者明確指示後才撰寫

**Phase 轉換 SOP**：

1. 當前 Phase 全部 Task 完成且靜態檢查通過
2. 使用者手動驗收並回報「Phase N 驗證通過」
3. 執行該 Phase 最終 commit
4. **停下來等使用者指示**（可能當下開始下一 Phase，也可能隔天或換 session 才繼續）
5. 收到「開始 Phase N+1」指示後，使用 `superpowers:writing-plans` skill 撰寫下一 Phase 計畫
6. 使用者審視計畫後才進入實作

**理由**：越後面的 Phase 不確定性越高，實作計畫有「保鮮期」；此外使用者可能換 session，明確的接續點能避免誤解。

## Commit 前檢查（MANDATORY）

1. **靜態分析必做**：
   - Frontend：`tsc --noEmit`、`pnpm lint` 兩者 0 error
   - Backend：`ruff check .`、`mypy src` 兩者 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit。給使用者手動驗收指引，等使用者明確說「驗證通過」或「OK」才能 commit。靜態檢查/單元測試通過**不算**驗證
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` / `chore` 不混在同一 commit
4. **禁止 scope 括號**：commit subject 必須是 `type: description`，不可寫 `type(scope): description`
5. **同步檢查**：
   - **知識庫**：`docs/knowledge/` 下的對應條目是否需要更新（新增/修改/刪除功能時必做）
   - 設計 spec 是否需要更新
   - `USER_GUIDE.md` 是否需要補充
   - 相關 E2E 是否需要新增/更新
6. **中文亂碼掃描**：`grep -r "��" .` 確認無編碼錯誤

## 知識庫（MANDATORY）

知識庫位於 `docs/knowledge/`，服務於**修改 alpha-lab 的 Claude**（不是幫使用者做投資分析的 Claude）。詳細結構與原則見 [`docs/knowledge/index.md`](../docs/knowledge/index.md)。

### 何時讀

**修改既有功能前必讀對應條目**：依功能定位找到對應資料夾（`features/` / `domain/` / `architecture/` / `collectors/` / `ai-integration/`），讀完該條目再動手。若條目尚未撰寫（該功能 Phase 未到），至少讀該資料夾 `README.md` 了解範圍。

### 何時寫 / 更新

**每次開發完、commit 前必評估**：

1. **新增功能** → 在對應 domain 建立或更新 md
2. **修改現有邏輯**（資料結構、流程、規則、關鍵檔案路徑） → 更新對應 md
3. **重構後介面改變** → 更新「關鍵檔案」清單
4. **刪除功能** → 移除或標記過時條目

違反此規範會讓知識庫與 codebase 脫節，失去存在意義。

### 檔案格式

每個知識庫 md 使用固定 frontmatter：

```markdown
---
domain: features/portfolio
updated: 2026-04-14
related: [factors.md, scoring.md]
---

# 概念名稱

## 目的
## 現行實作
## 關鍵檔案
- [src/alpha_lab/...](...)
## 修改時注意事項
```

## Claude Code 分析 SOP

當使用者請你分析數據時：

1. **讀取 `data/reports/index.json`** 判斷是否有相關歷史報告
2. **若有相關報告**：讀取該報告 markdown 內容作為脈絡
3. **讀取 `data/alpha_lab.db` 或 `data/processed/` 結構化數據**進行分析
4. **產出分析結論**
5. **強制詢問使用者**：「此分析是否要儲存成報告？」
6. **若使用者同意儲存**：
   - 寫 Markdown 到 `data/reports/analysis/<type>-<key>-<date>.md`
   - 更新 `data/reports/index.json`（加入新項目）
   - 寫一行摘要到 `data/reports/summaries/<date>.json`

### 報告類型

| 類型 | 檔名格式 |
|------|---------|
| stock | `stock-<symbol>-YYYY-MM-DD.md` |
| portfolio | `portfolio-YYYY-MM-DD.md` |
| events | `events-YYYY-MM-DD.md` |
| research | `research-<topic>-YYYY-MM-DD.md` |

### 報告 Frontmatter 範本

```markdown
---
id: stock-2330-2026-04-14
type: stock
title: 台積電深度分析
symbols: [2330]
tags: [半導體, buy]
date: 2026-04-14
data_sources:
  - prices: 2026-04-14
  - financials: 2026Q1
related_reports: []
summary_line: "Q1 財報亮眼，建議加碼"
---

## 執行摘要
...
```

## 資料夾結構

```
alpha-lab/
├── .claude/
│   └── CLAUDE.md    # 本協作指南
├── README.md
├── frontend/
├── backend/
├── data/            # 本地持久層（不 commit）
└── docs/
    ├── USER_GUIDE.md
    ├── knowledge/   # 開發者知識庫（服務於修改 alpha-lab 的 Claude）
    └── superpowers/
        ├── specs/
        └── plans/
```
