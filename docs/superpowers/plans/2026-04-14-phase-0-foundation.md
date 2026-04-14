# Phase 0: 基礎建設 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 alpha-lab 專案骨架——前後端 hello world 可運行、互通，所有規範文件到位，為 Phase 1 起跑做好準備

**Architecture:** Monorepo（`frontend/` React + `backend/` FastAPI + `data/` 共用層）。Phase 0 不含業務邏輯，僅建立結構、工具鏈、規範文件、健康檢查端點

**Tech Stack:** Vite + React 19 + TypeScript 5、Tailwind CSS 4、TanStack Query、Zustand、vitest、Playwright；FastAPI + uvicorn、Pydantic v2、SQLAlchemy 2、pytest、ruff、mypy

---

## Phase 0 工作總覽

| 群組 | 任務 |
|------|------|
| A | Repo 基礎設定與規範文件 |
| B | Backend 骨架（FastAPI + 健康檢查） |
| C | Frontend 骨架（Vite + React + 首頁） |
| D | 前後端整合（CORS + /api/health 串接） |
| E | 靜態檢查與 E2E 骨架 |
| F | Phase 0 驗收與 commit |

## Commit 規範（本專案 MANDATORY）

本 Phase 起沿用 larp-nexus 規範：

1. **靜態分析必做**：`tsc --noEmit` 與 lint 必須 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit，給使用者手動驗收指引，等使用者明確說「驗證通過」「OK」才能 commit
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` 不混在同一 commit
4. **禁止 scope 括號**：`type: description`，不可寫 `type(scope): description`
5. **同步檢查**：文件、規劃、E2E 是否需要連動更新
6. **中文亂碼掃描**：完成寫檔後 Grep `��`

本計畫的每個「Commit」步驟在執行前，必須先完成該 Task 的所有程式碼步驟，並提供使用者**手動驗收指引**。

---

## Task A1: 建立 .gitignore 與 README

**Files:**
- Create: `g:/codingdata/alpha-lab/.gitignore`
- Create: `g:/codingdata/alpha-lab/README.md`

- [ ] **Step 1: 寫 `.gitignore`**

```gitignore
# Node / Frontend
node_modules/
dist/
.vite/
*.log
npm-debug.log*
.env.local
.env.development.local
.env.production.local

# Python / Backend
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
build/
dist/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Data (本地持久層，不 commit)
data/*.db
data/*.db-journal
data/raw/
data/processed/
data/reports/
data/logs/
data/cache/
# 保留資料夾結構
!data/.gitkeep
!data/reports/.gitkeep

# Env
.env
.env.*
!.env.example

# Test artifacts
test-results/
playwright-report/
coverage/
```

- [ ] **Step 2: 寫 `README.md`**

```markdown
# alpha-lab

台股長線投資個人工具，整合數據面板、選股篩選、多因子組合推薦與嵌入式教學系統。

## 結構

- `frontend/` — React + Vite + TypeScript UI
- `backend/` — FastAPI + Python 資料抓取與分析
- `data/` — 本地數據層（SQLite + 分析報告，不 commit）
- `docs/` — 設計文件、使用者指南

## 設計文件

- [Design Spec](docs/superpowers/specs/2026-04-14-alpha-lab-design.md)
- [User Guide](docs/USER_GUIDE.md)

## 開發

```bash
# Backend
cd backend
uv sync
uvicorn alpha_lab.api.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

## 授權

個人專案，暫無授權條款。
```

- [ ] **Step 3: STOP — 請使用者確認檔案內容後再 commit**

提示使用者檢視 `.gitignore` 與 `README.md`。

**Commit（待使用者驗證後執行）：**

```bash
git add .gitignore README.md
git commit -m "chore: add .gitignore and README"
```

---

## Task A2: CLAUDE.md（專案協作規範）

**Files:**
- Create: `g:/codingdata/alpha-lab/.claude/CLAUDE.md`

- [ ] **Step 1: 寫 CLAUDE.md**

```markdown
# alpha-lab 專案協作指南

## 專案概述

台股長線投資個人工具，目標是「自動推薦 + 嵌入式教學」。

完整設計見 [docs/superpowers/specs/2026-04-14-alpha-lab-design.md](docs/superpowers/specs/2026-04-14-alpha-lab-design.md)。

## 技術棧

- **Frontend**：Vite + React 19 + TypeScript、Tailwind CSS、TanStack Query、Zustand、vitest、Playwright
- **Backend**：FastAPI + Python 3.11+、SQLAlchemy 2.x、SQLite、Pydantic v2、pytest
- **數據層**：本地檔案 + SQLite（`data/` 不 commit）

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
3. 執行該 Phase 最終 commit（可選 `git tag -a phase-N-complete`）
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
   - 設計 spec 是否需要更新
   - `USER_GUIDE.md` 是否需要補充
   - 相關 E2E 是否需要新增/更新
6. **中文亂碼掃描**：`grep -r "��" .` 確認無編碼錯誤

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
    └── superpowers/
        ├── specs/
        └── plans/
```
```

- [ ] **Step 2: STOP — 請使用者確認 CLAUDE.md 內容**

**Commit（待使用者驗證後執行）：**

```bash
git add .claude/CLAUDE.md
git commit -m "docs: add project CLAUDE.md with collaboration rules"
```

---

## Task A3: USER_GUIDE.md v0

**Files:**
- Create: `g:/codingdata/alpha-lab/docs/USER_GUIDE.md`

- [ ] **Step 1: 寫 USER_GUIDE.md 初版**

```markdown
# alpha-lab 使用者指南

## 快速開始

### 環境需求

- Node.js 20+
- Python 3.11+
- uv（Python 套件管理）或 pip

### 首次設置

```bash
# Backend
cd backend
uv sync         # 或 pip install -e .

# Frontend
cd frontend
pnpm install
```

### 日常啟動

開兩個終端機：

```bash
# Terminal 1 — Backend
cd backend
uvicorn alpha_lab.api.main:app --reload
# API 在 http://localhost:8000
# Swagger 文件在 http://localhost:8000/docs

# Terminal 2 — Frontend
cd frontend
pnpm dev
# UI 在 http://localhost:5173
```

## 功能說明

> Phase 0 僅提供骨架，功能將於後續 Phase 逐步加入。

### 目前版本（Phase 0）

- 首頁顯示後端連線狀態
- Swagger API 文件可瀏覽

### 規劃中

| Phase | 功能 |
|-------|------|
| 1 | 數據抓取（TWSE、MOPS） |
| 2 | 個股數據面板（A） |
| 3 | 多因子組合推薦（C） |
| 4 | 教學系統完整化 + 分析報告儲存（E） |
| 5 | 選股篩選器（B） |
| 6 | 組合追蹤（D） |
| 7 | Claude API 整合（預留） |

## 常見問題

### Q：數據會更新嗎？

A：Phase 1 起，數據會透過 `POST /api/jobs/collect` 手動觸發抓取，或排程每日自動抓取。

### Q：報告會保存在哪？

A：Phase 4 起，分析報告會儲存在 `data/reports/analysis/`，可透過前端「回顧模式」瀏覽。

## 專有名詞對照

> 將於 Phase 2 起陸續補充。

---

_文件同步於 Phase 0。後續 Phase 會持續擴充。_
```

- [ ] **Step 2: STOP — 請使用者確認 USER_GUIDE.md**

**Commit（待使用者驗證後執行）：**

```bash
git add docs/USER_GUIDE.md
git commit -m "docs: add initial user guide"
```

---

## Task B1: Backend 專案初始化

**Files:**
- Create: `g:/codingdata/alpha-lab/backend/pyproject.toml`
- Create: `g:/codingdata/alpha-lab/backend/.python-version`
- Create: `g:/codingdata/alpha-lab/backend/README.md`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/api/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/collectors/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/analysis/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/storage/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/schemas/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/glossary/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/ai/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/ai/README.md`
- Create: `g:/codingdata/alpha-lab/backend/tests/__init__.py`

- [ ] **Step 1: 寫 `backend/pyproject.toml`**

```toml
[project]
name = "alpha-lab"
version = "0.1.0"
description = "Taiwan stock long-term investment tool — backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "sqlalchemy>=2.0",
    "httpx>=0.27",
    "pandas>=2.2",
    "numpy>=2.0",
    "python-dateutil>=2.9",
    "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "httpx>=0.27",
    "ruff>=0.7",
    "mypy>=1.13",
    "types-PyYAML>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/alpha_lab"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "B", "UP", "RUF"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
mypy_path = "src"
packages = ["alpha_lab"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]
```

- [ ] **Step 2: 寫 `backend/.python-version`**

```
3.11
```

- [ ] **Step 3: 寫 `backend/README.md`**

```markdown
# alpha-lab backend

FastAPI 後端：數據抓取、分析、API 提供。

## 開發

```bash
uv sync --all-extras        # 或 pip install -e ".[dev]"
uvicorn alpha_lab.api.main:app --reload
```

## 結構

- `src/alpha_lab/api/` — FastAPI 路由
- `src/alpha_lab/collectors/` — 數據抓取（TWSE、MOPS 等）
- `src/alpha_lab/analysis/` — 多因子評分、組合生成
- `src/alpha_lab/storage/` — SQLAlchemy models、檔案 I/O
- `src/alpha_lab/schemas/` — Pydantic DTO
- `src/alpha_lab/glossary/` — 術語庫（靜態資料）
- `src/alpha_lab/ai/` — 預留 Claude API 整合

## 測試

```bash
pytest                     # 執行測試
ruff check .              # lint
mypy src                   # 型別檢查
```
```

- [ ] **Step 4: 寫所有 `__init__.py`（每個都是空檔）**

每個檔案內容皆為：

```python
```

（空檔即可，讓 Python 辨識為 package）

- [ ] **Step 5: 寫 `backend/src/alpha_lab/ai/README.md`（預留模組說明）**

```markdown
# AI 整合模組（預留）

此模組於 Phase 0 暫未實作，預留給未來 Phase 7：Claude API 自動化分析整合。

## 規劃內容

- `client.py` — Anthropic SDK wrapper（含 prompt caching）
- `prompts/` — 系統提示範本
  - `stock_analyzer.md` — 個股分析角色
  - `portfolio_recommender.md` — 組合推薦角色
  - `events_summarizer.md` — 事件摘要角色
- `analyzers/` — 對應四種報告類型的自動化生成邏輯

## 初期替代方案

Phase 0-6 期間，上述分析工作由 Claude Code（對話式）處理。Claude Code 讀取 `data/reports/index.json` 與 `data/alpha_lab.db`，產出 Markdown 報告到 `data/reports/analysis/`。
```

- [ ] **Step 6: 安裝依賴**

Run:
```bash
cd backend && uv sync --all-extras
```

若沒 uv：`pip install -e ".[dev]"`

Expected: 無錯誤，依賴安裝完成。

- [ ] **Step 7: 驗證 lint / mypy 能跑**

Run:
```bash
cd backend && ruff check . && mypy src
```

Expected: `ruff check` 顯示 `All checks passed!`；`mypy` 顯示 `Success: no issues found`（目前只有空檔，應該通過）。

- [ ] **Step 8: STOP — 請使用者手動確認**

提示使用者：
1. 查看 `backend/` 結構是否如預期
2. 確認 `uv sync` 或 `pip install` 成功
3. 確認 `ruff` 與 `mypy` 無錯誤

**Commit（待使用者驗證後執行）：**

```bash
git add backend/
git commit -m "feat: scaffold backend python project with fastapi and tooling"
```

---

## Task B2: FastAPI 健康檢查端點（TDD）

**Files:**
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/api/main.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/api/routes/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/api/routes/health.py`
- Create: `g:/codingdata/alpha-lab/backend/src/alpha_lab/schemas/health.py`
- Create: `g:/codingdata/alpha-lab/backend/tests/api/__init__.py`
- Create: `g:/codingdata/alpha-lab/backend/tests/api/test_health.py`

- [ ] **Step 1: 寫失敗的測試**

`backend/tests/api/test_health.py`：

```python
from fastapi.testclient import TestClient

from alpha_lab.api.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd backend && pytest tests/api/test_health.py -v
```

Expected: FAIL（因為 `alpha_lab.api.main` 還不存在或沒 `app`）

- [ ] **Step 3: 寫 schema**

`backend/src/alpha_lab/schemas/health.py`：

```python
from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
```

- [ ] **Step 4: 寫 health route**

`backend/src/alpha_lab/api/routes/health.py`：

```python
from datetime import datetime, timezone

from fastapi import APIRouter

from alpha_lab.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )
```

- [ ] **Step 5: 寫 routes package init**

`backend/src/alpha_lab/api/routes/__init__.py`：

```python
```

（空檔）

- [ ] **Step 6: 寫 FastAPI app**

`backend/src/alpha_lab/api/main.py`：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpha_lab.api.routes import health

app = FastAPI(
    title="alpha-lab",
    description="台股長線投資個人工具 API",
    version="0.1.0",
)

# CORS: 允許前端 dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
```

- [ ] **Step 7: Run test to verify it passes**

Run:
```bash
cd backend && pytest tests/api/test_health.py -v
```

Expected: PASS。

- [ ] **Step 8: 靜態檢查**

Run:
```bash
cd backend && ruff check . && mypy src
```

Expected: 兩者皆 0 error。

- [ ] **Step 9: 手動啟動 dev server 驗證**

Run:
```bash
cd backend && uvicorn alpha_lab.api.main:app --reload
```

瀏覽：
- http://localhost:8000/api/health → 應回傳 JSON `{status: "ok", version: "0.1.0", timestamp: "..."}`
- http://localhost:8000/docs → 應看到 Swagger UI，`GET /api/health` 可展開測試

- [ ] **Step 10: STOP — 請使用者手動驗收**

提示使用者：
1. 啟動 dev server（指令如上）
2. 用瀏覽器訪問 `/api/health`、`/docs`
3. 確認內容正確
4. 回報「驗證通過」才能 commit

**Commit（待使用者驗證後執行）：**

```bash
git add backend/
git commit -m "feat: add health check endpoint"
```

---

## Task C1: Frontend 專案初始化

**Files:**
- Create: `g:/codingdata/alpha-lab/frontend/package.json`
- Create: `g:/codingdata/alpha-lab/frontend/tsconfig.json`
- Create: `g:/codingdata/alpha-lab/frontend/tsconfig.node.json`
- Create: `g:/codingdata/alpha-lab/frontend/vite.config.ts`
- Create: `g:/codingdata/alpha-lab/frontend/index.html`
- Create: `g:/codingdata/alpha-lab/frontend/src/main.tsx`
- Create: `g:/codingdata/alpha-lab/frontend/src/App.tsx`
- Create: `g:/codingdata/alpha-lab/frontend/src/index.css`
- Create: `g:/codingdata/alpha-lab/frontend/src/vite-env.d.ts`
- Create: `g:/codingdata/alpha-lab/frontend/postcss.config.js`
- Create: `g:/codingdata/alpha-lab/frontend/tailwind.config.ts`
- Create: `g:/codingdata/alpha-lab/frontend/eslint.config.js`
- Create: `g:/codingdata/alpha-lab/frontend/README.md`

- [ ] **Step 1: 寫 `package.json`**

```json
{
  "name": "alpha-lab-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "packageManager": "pnpm@9.14.0",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "type-check": "tsc --noEmit",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test",
    "e2e:install": "playwright install"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.60.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^9.15.0",
    "@eslint/js": "^9.15.0",
    "typescript-eslint": "^8.15.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "vitest": "^2.1.0",
    "@vitest/ui": "^2.1.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^25.0.0",
    "@playwright/test": "^1.48.0"
  }
}
```

- [ ] **Step 2: 寫 `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,
    "noEmit": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "tests"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: 寫 `tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true
  },
  "include": ["vite.config.ts", "vitest.config.ts", "playwright.config.ts"]
}
```

- [ ] **Step 4: 寫 `vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
});
```

- [ ] **Step 5: 寫 `index.html`**

```html
<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>alpha-lab</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: 寫 `src/main.tsx`**

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 7: 寫 `src/App.tsx`**

```typescript
function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">alpha-lab</h1>
        <p className="mt-2 text-slate-400">Phase 0 骨架運作中</p>
      </div>
    </main>
  );
}

export default App;
```

- [ ] **Step 8: 寫 `src/index.css`**

```css
@import "tailwindcss";

html,
body,
#root {
  height: 100%;
}

body {
  margin: 0;
  font-family:
    system-ui,
    -apple-system,
    "Segoe UI",
    Roboto,
    sans-serif;
}
```

- [ ] **Step 9: 寫 `src/vite-env.d.ts`**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 10: 寫 `postcss.config.js`**

```javascript
export default {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 11: 寫 `tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 12: 寫 `eslint.config.js`**

```javascript
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist", "playwright-report", "test-results"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
);
```

- [ ] **Step 13: 寫 `frontend/README.md`**

```markdown
# alpha-lab frontend

Vite + React + TypeScript UI。

## 開發

```bash
pnpm install
pnpm dev           # http://localhost:5173
```

## 指令

- `pnpm build` — 生產打包
- `pnpm type-check` — TypeScript 檢查
- `pnpm lint` — ESLint
- `pnpm test` — Vitest
- `pnpm e2e` — Playwright E2E
```

- [ ] **Step 14: 補依賴 globals**

修改 `package.json`，在 devDependencies 加入 `"globals": "^15.12.0"`（ESLint config 需要）。

- [ ] **Step 15: 安裝依賴**

Run:
```bash
cd frontend && pnpm install
```

Expected: 無錯誤，安裝完成。

- [ ] **Step 16: 靜態檢查**

Run:
```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 兩者皆 0 error。

- [ ] **Step 17: 啟動 dev server 驗證**

Run:
```bash
cd frontend && pnpm dev
```

瀏覽 http://localhost:5173 應看到「alpha-lab / Phase 0 骨架運作中」，深色背景。

- [ ] **Step 18: STOP — 請使用者手動驗收**

提示使用者：
1. 瀏覽器打開 http://localhost:5173
2. 確認看到預期畫面（深色背景、標題置中）
3. 確認 `type-check` 與 `lint` 無錯

**Commit（待使用者驗證後執行）：**

```bash
git add frontend/
git commit -m "feat: scaffold frontend vite react project with tailwind"
```

---

## Task D1: 前後端整合（健康檢查串接）

**Files:**
- Create: `g:/codingdata/alpha-lab/frontend/src/api/client.ts`
- Create: `g:/codingdata/alpha-lab/frontend/src/api/health.ts`
- Create: `g:/codingdata/alpha-lab/frontend/src/components/HealthStatus.tsx`
- Modify: `g:/codingdata/alpha-lab/frontend/src/App.tsx`
- Create: `g:/codingdata/alpha-lab/frontend/.env.development`

- [ ] **Step 1: 寫 `.env.development`**

`frontend/.env.development`：

```
VITE_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 2: 寫 API client**

`frontend/src/api/client.ts`：

```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}
```

- [ ] **Step 3: 寫 health API hook**

`frontend/src/api/health.ts`：

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";

export type HealthResponse = {
  status: string;
  version: string;
  timestamp: string;
};

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/api/health"),
    refetchInterval: 30_000,
  });
}
```

- [ ] **Step 4: 寫 HealthStatus 元件**

`frontend/src/components/HealthStatus.tsx`：

```typescript
import { useHealth } from "@/api/health";

export function HealthStatus() {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return (
      <div className="text-slate-400" role="status">
        檢查後端中...
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="text-red-400" role="alert">
        ⚠ 後端連線失敗（請確認 backend dev server 是否運行於 :8000）
      </div>
    );
  }

  return (
    <div className="text-emerald-400" role="status">
      ✓ 後端連線正常 · v{data.version}
    </div>
  );
}
```

- [ ] **Step 5: 更新 `App.tsx`**

```typescript
import { HealthStatus } from "@/components/HealthStatus";

function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">alpha-lab</h1>
        <p className="text-slate-400">Phase 0 骨架運作中</p>
        <HealthStatus />
      </div>
    </main>
  );
}

export default App;
```

- [ ] **Step 6: 靜態檢查**

Run:
```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 error。

- [ ] **Step 7: 手動整合測試**

兩個終端機：
- Terminal 1：`cd backend && uvicorn alpha_lab.api.main:app --reload`
- Terminal 2：`cd frontend && pnpm dev`

開 http://localhost:5173：
- 應顯示綠色 ✓「後端連線正常 · v0.1.0」

關掉 backend 試試：
- 應轉為紅色 ⚠「後端連線失敗」訊息

- [ ] **Step 8: STOP — 請使用者手動驗收**

提示使用者：
1. 兩個 dev server 都啟動
2. 瀏覽 http://localhost:5173，確認顯示綠色「後端連線正常」
3. 關掉 backend，確認切換為紅色錯誤訊息
4. 重啟 backend，確認自動恢復（30 秒內）

**Commit（待使用者驗證後執行）：**

```bash
git add frontend/
git commit -m "feat: integrate frontend with backend health check"
```

---

## Task E1: Vitest 骨架與第一個元件測試

**Files:**
- Create: `g:/codingdata/alpha-lab/frontend/vitest.config.ts`
- Create: `g:/codingdata/alpha-lab/frontend/tests/setup.ts`
- Create: `g:/codingdata/alpha-lab/frontend/tests/components/HealthStatus.test.tsx`

- [ ] **Step 1: 寫 `vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    include: ["tests/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**"],
  },
});
```

- [ ] **Step 2: 寫 `tests/setup.ts`**

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: 寫失敗的元件測試**

`frontend/tests/components/HealthStatus.test.tsx`：

```typescript
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { HealthStatus } from "@/components/HealthStatus";

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("HealthStatus", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows success when backend responds ok", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          status: "ok",
          version: "0.1.0",
          timestamp: new Date().toISOString(),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderWithClient(<HealthStatus />);
    expect(await screen.findByText(/後端連線正常/)).toBeInTheDocument();
  });

  it("shows error when backend fails", async () => {
    (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("network error"),
    );

    renderWithClient(<HealthStatus />);
    expect(await screen.findByText(/後端連線失敗/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: 跑測試**

Run:
```bash
cd frontend && pnpm test
```

Expected: 2 個測試都 PASS（元件已實作，測試也正確）。

- [ ] **Step 5: 靜態檢查**

Run:
```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 error。

- [ ] **Step 6: STOP — 請使用者手動驗收**

提示使用者：
1. `pnpm test` 應看到 2 tests passed
2. 確認測試跑完會正常結束

**Commit（待使用者驗證後執行）：**

```bash
git add frontend/
git commit -m "test: add vitest setup and health status unit test"
```

---

## Task E2: Playwright E2E 骨架

**Files:**
- Create: `g:/codingdata/alpha-lab/frontend/playwright.config.ts`
- Create: `g:/codingdata/alpha-lab/frontend/tests/e2e/homepage.spec.ts`
- Create: `g:/codingdata/alpha-lab/frontend/tests/e2e/fixtures/.gitkeep`

- [ ] **Step 1: 寫 `playwright.config.ts`**

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
```

- [ ] **Step 2: 寫第一個 E2E 測試（P0：首頁載入）**

`frontend/tests/e2e/homepage.spec.ts`：

```typescript
import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("載入首頁並顯示標題", async ({ page }) => {
    // Mock health API so this E2E doesn't need backend running
    await page.route("**/api/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          version: "0.1.0",
          timestamp: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "alpha-lab" })).toBeVisible();
    await expect(page.getByText("Phase 0 骨架運作中")).toBeVisible();
  });

  test("後端連線成功時顯示綠色狀態", async ({ page }) => {
    await page.route("**/api/health", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          version: "0.1.0",
          timestamp: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/");
    await expect(page.getByText(/後端連線正常/)).toBeVisible();
  });

  test("後端失敗時顯示錯誤訊息", async ({ page }) => {
    await page.route("**/api/health", async (route) => {
      await route.abort("failed");
    });

    await page.goto("/");
    await expect(page.getByText(/後端連線失敗/)).toBeVisible();
  });
});
```

- [ ] **Step 3: 建 fixtures 資料夾佔位檔**

`frontend/tests/e2e/fixtures/.gitkeep`：

```
```

（空檔，用來讓 git 保留空資料夾）

- [ ] **Step 4: 安裝 Playwright browsers**

Run:
```bash
cd frontend && pnpm e2e:install
```

Expected: Chromium 下載安裝完成。

- [ ] **Step 5: 跑 E2E**

Run:
```bash
cd frontend && pnpm e2e
```

Expected: 3 個測試 PASS。

- [ ] **Step 6: 靜態檢查**

Run:
```bash
cd frontend && pnpm type-check && pnpm lint
```

Expected: 0 error。

- [ ] **Step 7: STOP — 請使用者手動驗收**

提示使用者：
1. `pnpm e2e` 應 3 tests passed
2. 可選：`pnpm e2e -- --ui` 用 UI 模式看看執行過程

**Commit（待使用者驗證後執行）：**

```bash
git add frontend/
git commit -m "test: add playwright e2e skeleton with homepage tests"
```

---

## Task F1: Data 資料夾佔位結構

**Files:**
- Create: `g:/codingdata/alpha-lab/data/.gitkeep`
- Create: `g:/codingdata/alpha-lab/data/reports/.gitkeep`
- Create: `g:/codingdata/alpha-lab/data/reports/README.md`

- [ ] **Step 1: 建立資料夾佔位檔**

`data/.gitkeep`（空檔）

`data/reports/.gitkeep`（空檔）

- [ ] **Step 2: 寫 `data/reports/README.md`**

```markdown
# data/reports — 分析報告永久儲存區

這個資料夾用來儲存 Claude Code 分析產出的 Markdown 報告。Git 不追蹤內容檔案（由 `.gitignore` 排除），只保留資料夾結構說明。

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
```

- [ ] **Step 3: 確認 `.gitignore` 行為**

Run:
```bash
cd g:/codingdata/alpha-lab && git status
```

Expected: 只看到 `data/.gitkeep`、`data/reports/.gitkeep`、`data/reports/README.md` 被追蹤。

- [ ] **Step 4: STOP — 請使用者確認**

**Commit（待使用者驗證後執行）：**

```bash
git add data/
git commit -m "chore: add data folder structure placeholder"
```

---

## Task F1.5: 開發者知識庫骨架

**定位**：`docs/knowledge/` 服務於**修改 alpha-lab 的 Claude**（開發者立場），比照 larp-nexus 模式。Phase 0 只建骨架與維護規範，實際條目隨 Phase 逐步補。

**Files:**
- Create: `docs/knowledge/index.md`
- Create: `docs/knowledge/features/README.md`
- Create: `docs/knowledge/features/{data-panel,screener,portfolio,tracking,education}/.gitkeep`
- Create: `docs/knowledge/domain/README.md`
- Create: `docs/knowledge/architecture/README.md`
- Create: `docs/knowledge/collectors/README.md`
- Create: `docs/knowledge/ai-integration/README.md`
- Modify: `.claude/CLAUDE.md`（加「知識庫 MANDATORY」段落、同步檢查加「知識庫」項、資料夾結構加 `knowledge/`）
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（第 15 節加「開發者知識庫」小節）

- [ ] **Step 1: 建立骨架**：index.md + 5 個資料夾 README + features 下 5 個子資料夾的 `.gitkeep`

- [ ] **Step 2: `.claude/CLAUDE.md` 加維護規範**

加入「知識庫（MANDATORY）」段落，內容包含：
- 定位（給開發者 Claude 讀）
- 何時讀（修改既有功能前）
- 何時寫/更新（新增/修改/重構/刪除功能時）
- 檔案格式（frontmatter 範本）
- 同步檢查清單新增「知識庫」一項
- 資料夾結構加 `docs/knowledge/`

- [ ] **Step 3: 設計 spec 第 15 節加「開發者知識庫」小節**

說明定位、結構、原則。同步檢查清單加「`docs/knowledge/` 對應條目更新」。

- [ ] **Step 4: STOP — 請使用者確認**

提示使用者：
1. 瀏覽 `docs/knowledge/index.md` 確認總覽
2. 瀏覽各 `README.md` 確認分類範圍
3. 確認 `.claude/CLAUDE.md` 與 spec 的新增內容

**Commit（待使用者驗證後執行）：**

```bash
git add docs/knowledge/ .claude/CLAUDE.md docs/superpowers/specs/2026-04-14-alpha-lab-design.md docs/superpowers/plans/2026-04-14-phase-0-foundation.md
git commit -m "docs: add knowledge base skeleton and maintenance rules"
```

---

## Task F2: Phase 0 完成驗收

- [ ] **Step 1: 執行全套靜態檢查與測試**

Run:
```bash
# Backend
cd backend && ruff check . && mypy src && pytest -v

# Frontend
cd frontend && pnpm type-check && pnpm lint && pnpm test && pnpm e2e
```

Expected: 全部通過。

- [ ] **Step 2: 中文亂碼掃描**

Run:
```bash
cd g:/codingdata/alpha-lab && grep -r "��" --include="*.md" --include="*.ts" --include="*.tsx" --include="*.py" --include="*.json" --include="*.toml" --include="*.yaml" .
```

Expected: 無輸出（表示無亂碼）。

- [ ] **Step 3: 端到端手動煙霧測試**

兩個 terminal：
1. `cd backend && uvicorn alpha_lab.api.main:app --reload`
2. `cd frontend && pnpm dev`

瀏覽：
- http://localhost:5173 → 標題 + 綠色狀態
- http://localhost:8000/docs → Swagger UI 可用

關掉 backend，觀察前端 30 秒內自動切換為紅色。

- [ ] **Step 4: STOP — 請使用者最終驗收 Phase 0**

提示使用者：
1. 完成上述 Step 1-3 全部檢查
2. 確認整個 Phase 0 骨架可運作
3. 告知「Phase 0 驗證通過」

- [ ] **Step 5: 最終 commit（標記 Phase 0 完成）**

Run:
```bash
cd g:/codingdata/alpha-lab && git log --oneline
```

確認 Phase 0 所有 commit 都在：
- `chore: add .gitignore and README`
- `docs: add project CLAUDE.md with collaboration rules`
- `docs: add initial user guide`
- `feat: scaffold backend python project with fastapi and tooling`
- `feat: add health check endpoint`
- `feat: scaffold frontend vite react project with tailwind`
- `feat: integrate frontend with backend health check`
- `test: add vitest setup and health status unit test`
- `test: add playwright e2e skeleton with homepage tests`
- `chore: add data folder structure placeholder`

**可選：** 打 tag 標記階段：

```bash
git tag -a phase-0-complete -m "Phase 0: 基礎建設完成"
```

- [ ] **Step 6: STOP — 等使用者指示再開始 Phase 1**

告知使用者 Phase 0 完成，等使用者給予指示後才進行 Phase 1 實作計畫撰寫。

---

## Self-Review Notes

**Spec coverage:**
- ✅ Repo 結構（Task B1、C1、F1）
- ✅ pyproject.toml / package.json（Task B1、C1）
- ✅ FastAPI hello world（Task B2）
- ✅ React hello world（Task C1）
- ✅ 前後端互通（Task D1）
- ✅ CLAUDE.md（Task A2）
- ✅ USER_GUIDE.md 初版（Task A3）
- ✅ 基本靜態檢查（每個 Task 都有）
- ✅ 單元測試骨架（Task E1）
- ✅ E2E 骨架（Task E2）
- ✅ AI 預留模組（Task B1 中的 `ai/README.md`）
- ⏸ SQLite schema 建表 — **延後到 Phase 1**（Phase 0 不需要 schema，等 Phase 1 抓資料時一起建）

**關於 SQLite 延後：** spec Phase 0 描述中有提到「SQLite schema 建表」，但實際上 Phase 0 沒有任何欄位需要建表（所有 model 都在 Phase 1 才定義）。把 SQLite 連線初始化與 schema 建立放 Phase 1 開頭會更自然，也避免 Phase 0 產生「建了空表但無用」的狀態。

**Placeholder scan:** 無 TBD / TODO / 模糊描述。

**Type consistency:** 
- `HealthResponse`（後端 Pydantic）與 `HealthResponse`（前端 TS type）欄位一致：`status`、`version`、`timestamp`
- API 路徑 `/api/health` 在 backend、frontend、E2E 三處一致
