# Alpha Lab 設計文件

- **專案名稱**：alpha-lab
- **設計日期**：2026-04-14
- **作者**：KoujiY（與 Claude 協作）
- **狀態**：Draft

## 1. 目的與願景

alpha-lab 是一個個人用的台股長線投資工具，目標是在自動化推薦的同時，讓使用者（投資知識薄弱的初學者）能夠逐步學習金融知識、理解每個決策的原理。

**核心使用者**：作者本人，用於投資實戰與學習。

**核心目標**：
1. 自動抓取台股數據，彙整成可讀報告
2. 以多因子策略產出長線配置推薦
3. 教學系統內嵌於使用流程，隨時解釋專有名詞與推理過程
4. 所有分析結果可永久保存、事後回顧

**未來擴張空間**：美股、交易策略（偏投機）模組。

## 2. 範圍

### 核心功能（MVP 全包）

| 代號 | 功能 | 描述 |
|------|------|------|
| A | 數據面板 | 個股資料、財報、走勢圖 |
| B | 選股篩選器 | 依多因子條件篩候選股 |
| C | 投資組合推薦 | 多套風格組合（保守/平衡/積極/最推薦） |
| D | 組合追蹤 | 模擬持有與績效計算 |
| E | 教學系統 | 術語 Tooltip、詳解、推薦理由 |

實作順序：Phase 0 基礎 → A → C → E → B → D。

### 不在範圍內

- 即時盯盤、當沖交易
- 多使用者、雲端部署
- 獨立的學習模式課程（教學只做嵌入式）
- 初期不實作 Claude API 整合（僅預留模組位置）

## 3. 使用者故事

- 作為投資初學者，我希望在儀表板看到今天的市場概況與我的組合狀態
- 作為投資初學者，我希望看到不懂的術語時可以即時看到解釋
- 作為投資初學者，我希望獲得自動化的投資組合推薦，並且能理解為什麼
- 作為投資初學者，我希望保存每次的分析報告，日後回頭檢視決策依據
- 作為投資初學者，我希望在熟悉之後，可以關掉教學提示，減少視覺干擾
- 作為開發者，我希望 Claude Code 能直接讀取本地數據協助深度分析
- 作為開發者，我希望工具架構有擴充空間，未來可以加入 Claude API 自動化分析

## 4. 整體架構

採用**混合架構（Hybrid）**：FastAPI 提供即時 API，同時把數據落檔供 Claude Code 分析。

```
                    ┌─→  data/*.json / SQLite ←──  Claude Code
                    │         ↑
backend/ (FastAPI)  ┤         │ 讀檔
                    │         │
                    └─API──→  frontend/ (React)
```

**設計理念**：前後端透過 API 溝通，但所有結構化數據同時落檔（SQLite + Markdown），讓 Claude Code 可以直接讀取進行深度分析，同時也保留未來實作 Claude API 自動化分析的擴充空間。

## 5. Repo 結構

```
alpha-lab/
├── CLAUDE.md                     # Claude Code 分析 SOP
├── README.md
├── frontend/                     # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/                # 路由頁面
│   │   ├── components/           # 共用元件
│   │   ├── api/                  # FastAPI 的 TS client
│   │   ├── contexts/             # TutorialModeContext 等
│   │   └── lib/
│   ├── tests/                    # vitest + Playwright
│   │   ├── unit/
│   │   ├── e2e/
│   │   └── fixtures/
│   ├── package.json
│   └── vite.config.ts
├── backend/                      # FastAPI + Python
│   ├── src/alpha_lab/
│   │   ├── api/                  # FastAPI routes
│   │   ├── collectors/           # TWSE、MOPS、新聞
│   │   ├── analysis/             # 多因子評分、組合生成
│   │   ├── storage/              # SQLAlchemy models、檔案 I/O
│   │   ├── schemas/              # Pydantic 模型
│   │   ├── glossary/             # 術語庫（靜態 YAML/JSON，由 /api/glossary 提供）
│   │   └── ai/                   # 預留 Claude API 整合
│   ├── scripts/                  # 手動/排程腳本
│   ├── tests/                    # pytest
│   └── pyproject.toml
├── data/                         # 共用數據層（不 commit，.gitignore）
│   ├── alpha_lab.db              # SQLite 結構化資料
│   ├── raw/                      # 原始抓取
│   ├── processed/                # 計算後指標
│   └── reports/
│       ├── index.json
│       ├── daily/
│       ├── analysis/
│       └── summaries/
└── docs/
    ├── USER_GUIDE.md
    └── superpowers/specs/
```

## 6. 技術棧

### 前端

- **框架**：Vite + React + TypeScript
- **路由**：React Router
- **資料擷取**：TanStack Query
- **狀態**：Zustand（輕量全域狀態）
- **樣式**：Tailwind CSS（搭配 shadcn/ui）
- **圖表**：Recharts（基本）+ lightweight-charts（K 線）
- **Markdown 渲染**：react-markdown + remark-gfm
- **測試**：vitest + React Testing Library、Playwright

### 後端

- **框架**：FastAPI + uvicorn
- **ORM**：SQLAlchemy 2.x
- **資料庫**：SQLite
- **驗證**：Pydantic v2
- **數據處理**：pandas、numpy
- **HTTP Client**：httpx（async）
- **測試**：pytest + pytest-asyncio

## 7. 數據層設計

### 數據源（免費優先）

| 來源 | 用途 |
|------|------|
| TWSE OpenAPI | 每日股價、三大法人、融資融券 |
| 公開資訊觀測站 MOPS | 季報、月營收、重大訊息 |
| Yahoo Finance | 備援、歷史價格 |

### 更新頻率

| 資料類型 | 頻率 |
|---------|------|
| 股價、成交量、法人買賣 | 每日收盤後 |
| 月營收 | 每月 10 日後 |
| 季報 | 依公告期（5/15、8/14、11/14、3/31） |
| 重大訊息 | 每日掃描 |
| 新聞彙整 | 每週 |

### SQLite Schema（核心表）

- `stocks` — symbol, name, industry, listed_date
- `prices_daily` — symbol, date, OHLCV, institutional_net
- `financials` — symbol, period, revenue, gross_margin, net_income, eps, roe…
- `revenues_monthly` — symbol, month, revenue, yoy_growth, mom_growth
- `events` — symbol, date, type, title, content
- `scores` — symbol, calc_date, value/growth/dividend/quality scores, total
- `portfolios_saved` — id, style, holdings_json, created_at
- `portfolio_snapshots` — portfolio_id, date, nav, holdings_json（追蹤用）

### 檔案層（data/reports/）

```
data/reports/
├── index.json                    # 輕量索引（前端與 Claude Code 共用）
├── daily/                        # 每日自動簡報
│   └── 2026-04-14.md
├── analysis/                     # 深度分析報告（永久保存）
│   ├── stock-<symbol>-<date>.md
│   ├── portfolio-<date>.md
│   ├── events-<date>.md
│   └── research-<topic>-<date>.md
└── summaries/                    # 一行摘要（智能檢索）
    └── <date>.json
```

### 報告 Markdown Frontmatter 範本

```markdown
---
id: stock-2330-2026-04-14
type: stock | portfolio | events | research
title: 台積電深度分析
symbols: [2330]
tags: [半導體, buy]
date: 2026-04-14
data_sources:
  - prices: 2026-04-14
  - financials: 2026Q1
  - events: 2026-04-01 to 2026-04-14
related_reports: [portfolio-2026-04-14]
---
```

### index.json 結構

```json
{
  "updated_at": "2026-04-14T20:30:00",
  "reports": [
    {
      "id": "stock-2330-2026-04-14",
      "type": "stock",
      "title": "台積電深度分析",
      "symbols": ["2330"],
      "tags": ["半導體", "buy"],
      "date": "2026-04-14",
      "path": "analysis/stock-2330-2026-04-14.md",
      "summary_line": "Q1 財報亮眼，建議加碼",
      "starred": false
    }
  ]
}
```

## 8. 後端 API 設計

```
/api
├── /stocks
│   ├── GET /                       # 股票列表（支援篩選）
│   ├── GET /{symbol}
│   ├── GET /{symbol}/prices
│   ├── GET /{symbol}/financials
│   └── GET /{symbol}/events
├── /screener
│   ├── POST /filter                # 多因子篩選
│   └── GET /factors
├── /portfolios
│   ├── POST /recommend             # 產出推薦組合
│   ├── GET /saved
│   ├── POST /saved
│   └── GET /saved/{id}/performance
├── /reports
│   ├── GET /                       # 讀 index.json
│   ├── GET /{id}
│   ├── POST /                      # 新增（Claude Code 呼叫）
│   ├── PATCH /{id}
│   └── DELETE /{id}
├── /glossary
│   └── GET /{term}
└── /jobs
    ├── POST /collect
    └── GET /status
```

### 推薦組合回傳格式

```json
{
  "generated_at": "2026-04-14T...",
  "portfolios": [
    {
      "style": "conservative | balanced | aggressive",
      "label": "保守組 | 平衡組 | 積極組",
      "is_top_pick": false,
      "holdings": [
        {"symbol": "2330", "weight": 0.3, "score_breakdown": {...}}
      ],
      "expected_yield": 4.2,
      "risk_score": 2.1,
      "reasoning_ref": null
    }
  ]
}
```

- `is_top_pick: true` 標記最推薦那一組
- `reasoning_ref` 初期為 null；Claude Code 分析後會產生對應 `analysis/portfolio-*.md`，此欄位填入報告 id

### 術語查詢

```
GET /api/glossary/K線
→ {
  "term": "K線",
  "short": "呈現一段時間內股價變動的圖形",
  "detail": "...",
  "related": ["紅K", "黑K", "突破"]
}
```

術語庫存於 `backend/src/alpha_lab/glossary/` 的靜態 YAML/JSON。

## 9. 投資策略：多因子模型

四個維度，每個 0-100 分：

| 因子 | 代表指標 |
|------|---------|
| **Value 價值** | PE、PB、EV/EBITDA |
| **Growth 成長** | 營收 YoY、EPS YoY、產業地位 |
| **Dividend 股息** | 殖利率、連續配息年數、配息穩定度 |
| **Quality 品質** | ROE、毛利率、負債比、現金流 |

**總分**：加權平均，權重依組合風格調整：
- **保守組**：Dividend + Quality 權重高
- **平衡組**：四因子均衡
- **積極組**：Growth 權重高

**組合生成邏輯**：
1. 依風格權重計算總分
2. 取 Top N 候選（約 20-30 檔）
3. 加上產業分散、單檔上限等約束
4. 產出配置比例

**最推薦**：通常指平衡組，但會依近期市場狀況微調（初期以平衡組為預設）。

## 10. 前端設計

### 頁面路由

```
/                    儀表板
/stocks              股票瀏覽與搜尋
/stocks/:symbol      個股詳細頁（A）
/screener            選股篩選（B）
/portfolios          組合推薦（C）
/portfolios/:id      組合追蹤（D）
/history             回顧模式
/history/:reportId   單一報告
/settings            設定
```

### 關鍵元件

- `<TermTooltip term="...">` — 術語提示（教學核心）
- `<ReportCard>` — 報告列表卡片
- `<StockChart>` — K 線與走勢圖
- `<ScoreRadar>` — 多因子雷達
- `<MarkdownRender>` — 報告渲染

### 個股頁布局

```
┌─────────────────────────────────────────┐
│ 2330 台積電  [收藏] [加入組合]           │
├─────────────────────────────────────────┤
│ 股價走勢圖                              │
├──────────────┬──────────────────────────┤
│ 關鍵指標     │ 多因子評分雷達            │
├──────────────┴──────────────────────────┤
│ 財報摘要（季 / 月營收切換）              │
├─────────────────────────────────────────┤
│ 近期重大訊息                            │
├─────────────────────────────────────────┤
│ 相關分析報告                            │
└─────────────────────────────────────────┘
```

### 教學系統

**兩層呈現：**
- **L1**：hover 顯示 1-3 行簡短定義
- **L2**：點「了解更多」→ 側邊面板顯示完整解釋

**全域教學開關（三段密度）：**

| 模式 | L1 | L2 | 推薦理由 | 對象 |
|------|----|----|----|------|
| 完整（預設） | ✅ | ✅ | ✅ | 初學者 |
| 精簡 | ❌ | ✅（主動觸發） | ✅ | 略懂 |
| 關閉 | ❌ | ❌ | 僅結論 | 熟悉後 |

- 儲存於 `localStorage`
- 透過 `TutorialModeContext` 全域生效
- 右上角快捷切換（📖 圖示）

### 回顧模式

- 時間軸 / 列表 / 搜尋 三種瀏覽方式
- 依類型（個股/組合/事件/主題）篩選
- 依股票代號、關鍵字搜尋
- 報告可加星、改標籤、刪除
- 資料來源：`GET /api/reports`（讀 `index.json`）

## 11. Claude Code 協作機制

### CLAUDE.md 角色

放在專案根目錄，定義 Claude Code 的分析 SOP：

1. **分析前**：讀 `data/reports/index.json` 判斷是否有相關歷史報告
2. **分析中**：讀 SQLite 或 `data/processed/` 內的結構化數據
3. **分析後**：**強制詢問使用者「是否儲存此報告？」**
4. **儲存時**：
   - 寫 Markdown 到 `data/reports/analysis/`
   - 更新 `index.json`
   - 寫一行摘要到 `summaries/`

### 智能檢索流程

1. Claude Code 分析前先讀 `index.json`（輕量）
2. 依當前問題判斷哪些歷史報告相關
3. 只讀相關那幾份完整 Markdown
4. 避免每次都讀所有報告造成 context 膨脹

### 四種報告類型

| 類型 | 檔名 | 用途 |
|------|------|------|
| stock | `stock-<symbol>-YYYY-MM-DD.md` | 單檔深度分析 |
| portfolio | `portfolio-YYYY-MM-DD.md` | 組合推薦理由 |
| events | `events-YYYY-MM-DD.md` | 重大訊息/新聞摘要 |
| research | `research-<topic>-YYYY-MM-DD.md` | 主題研究 |

### 預留 AI API 模組

`backend/src/alpha_lab/ai/` 初期只放 README 說明未來規劃。真正實作時放：

- `client.py` — Anthropic SDK wrapper（含 prompt caching）
- `prompts/` — 系統提示範本（投資分析角色、分析框架）
- `analyzers/` — 對應四種報告類型的自動化生成邏輯

## 12. 測試策略

| 層級 | 工具 | 覆蓋 |
|------|------|------|
| 後端單元 | pytest | collectors、analysis、storage |
| 後端整合 | pytest + TestClient | FastAPI routes |
| 前端單元 | vitest + RTL | 關鍵元件 |
| E2E | Playwright | 關鍵使用者流程 |

### E2E 測試範圍

| 優先度 | 情境 |
|-------|------|
| P0 | 首頁載入、導覽 |
| P0 | 個股頁顯示數據 |
| P0 | 生成組合推薦流程 |
| P1 | 儲存與讀取分析報告 |
| P1 | 教學 Tooltip 全域開關 |
| P1 | 選股篩選器 |
| P2 | 組合追蹤績效計算 |

- 用 MSW 或 Playwright route interception mock 後端 API
- Fixture 存於 `frontend/tests/fixtures/`
- 每個 Phase 同步增加對應 E2E

## 13. 錯誤處理與資料驗證

- **數據抓取**：所有 collector 輸出經 Pydantic schema 驗證；異常資料寫 log 而非靜默失敗
- **API**：FastAPI 自動處理輸入驗證，統一錯誤格式（含 error code + message）
- **前端**：TanStack Query 的 error boundary；網路錯誤顯示重試按鈕
- **資料來源失效**：單一 collector 失敗不影響其他；失敗記錄寫入 `data/logs/`

## 14. 安全性

- 本地工具，無多使用者驗證需求
- `data/` 資料夾加入 `.gitignore`
- 若未來啟用 Claude API，API key 存 `.env`（不 commit）
- 無外部網路服務暴露風險（僅 localhost）

## 15. 開發階段

| Phase | 狀態 | 目標 | 交付物 |
|-------|------|------|--------|
| 0 | ✅ 完成（2026-04-15） | 基礎建設 | Repo 結構、FastAPI/React hello world、健康檢查串接、CLAUDE.md、USER_GUIDE.md v0、知識庫骨架 |
| 1 | ✅ 完成（2026-04-15） | 數據抓取（最小管線） | SQLAlchemy + SQLite 基礎建設、TWSE 日股價 collector、MOPS 月營收 collector、`POST /api/jobs/collect`、`GET /api/jobs/status/{id}` |
| 1.5 | ✅ 完成（2026-04-15） | 數據抓取擴充 | 三大法人、融資融券、季報（合併損益/資產負債）、重大訊息 collectors[^phase15-cashflow] |
| 2 | ✅ 完成（2026-04-15） | 功能 A | 個股頁、術語 Tooltip 基礎、術語庫 v1 |
| 3 | ✅ 完成（2026-04-16） | 功能 C | 多因子評分引擎（Value/Growth/Dividend/Quality）、MOPS 現金流 collector（FCF）、組合推薦 API、`/portfolios` 頁面與個股頁雷達圖 |
| 4 | ✅ 完成（2026-04-17） | 功能 E | 推薦理由靜態模板、L2 詳解側邊面板（5 個初始 topic）、報告儲存後端（`data/reports/`、`index.json`、summaries）、`/reports` 回顧列表與細節頁、「儲存此次推薦為報告」按鈕；TWSE 產業代碼→中文名稱映射表留待 Phase 5/6 再補 |
| 5 | ✅ 完成（2026-04-17） | 功能 B：選股篩選器 | `POST /api/screener/filter`、`GET /api/screener/factors`、`/screener` 頁面（因子滑桿 + 可排序結果表格 + 409 引導提示）；`apiPost` 擴充 JSON body 支援 |
| 6 | ✅ 完成（2026-04-17） | 功能 D + 報告管理 + 教學開關 | 組合追蹤（`portfolios_saved`、`portfolio_snapshots` 表、`GET/POST /portfolios/saved`、`GET /saved/{id}/performance`、`/portfolios/:id` 追蹤頁）、績效計算、報告管理（`PATCH /reports/{id}` 加星/改標籤、`DELETE /reports/{id}`）、報告全文搜尋、教學三段密度開關（`TutorialModeContext` + 右上角快捷切換）、個股頁「收藏」「加入組合」按鈕 + 「相關分析報告」區塊；D-UX：`POST /portfolios/saved/probe` + 共用 `BaseDateConfirmDialog` 導入兩個儲存流程、`useUpdatePricesJob` hook + nav 全域「更新報價」按鈕（顯式 popover 狀態面板）、TWSE batch job 加 throttle + retry-once 吃掉 WAF 偶發 stat 錯誤；報告離線快取留到 Phase 7 |
| 7A | ✅ 完成（2026-04-17） | 組合追蹤強化 | `portfolios_saved.parent_id` + `parent_nav_at_fork` 血緣欄位（`ON DELETE SET NULL`，透過 idempotent `ALTER TABLE ADD COLUMN` migration 補上）；`SavedPortfolioCreate` Pydantic `model_validator`（symbol 唯一 / `\|sum(weights)-1\| < 1e-6`）；`GET /saved/{id}/performance` 回傳 `parent_points` + `parent_nav_at_fork`（遞迴取 parent、`_visited` cycle guard）；`PerformanceChart` 連續 NAV 曲線（parent 虛線 + self 實線 + fork 垂直線，`buildChartSeries` 獨立 export 供單測）；`PortfolioTrackingPage` 「由 組合 #X 分裂」連結與「自母組合起報酬」卡片；`StockActions.persistMerged` 自動帶 `parent_id` |
| 7B | 拆成 3 個 sub-phase（見下） | 數據源與自動化 | 原本一個 phase 包 6 塊功能過重，拆成 7B.1 / 7B.2 / 7B.3 依序進行 |
| 7B.1 | ✅ 完成（2026-04-18） | 數據源擴充 | Yahoo Finance fallback collector、prices_daily.source、data/processed/ 指標與比率 JSON（atomic write）、YAHOO_PRICES / PROCESSED_INDICATORS / PROCESSED_RATIOS JobType；daily_collect 尾端自動跑 processed |
| 7B.2 | ✅ 完成（2026-04-18） | 內容自動化 | Daily Briefing（market overview / institutional / events / portfolio tracking 四段式 Markdown）、`DAILY_BRIEFING` JobType、`daily_collect.py` 尾端自動觸發、`data/reports/daily/` 儲存 + index 同步；新聞彙整暫以 DB events 彙整為主，外部新聞源留待後續 |
| 7B.3 | 未開始 | UX 與快取 | 報告離線快取（前端 IndexedDB 或後端快取策略）、「加入組合」新 symbol 在 base_date 停牌的強化 UX（目前走 `probe_base_date` + dialog，視使用情境強化） |
| 8 | 未開始 | UI 升級 | shadcn/ui 元件庫遷移、K 線圖改用 lightweight-charts、列表 / 卡片 / 詳情頁的動作按鈕（收藏 ☆★、刪除、編輯等）一律改用 icon button（搭 `aria-label` + hover tooltip；`data-testid` 保留不變以維持 E2E）；**「加入組合」兩步 wizard UI**（選基底組合 → 預覽 delta-weight 套用後的新權重表 + 可手動微調每檔 → 確認後建立新組合，把權重決策從黑箱改為顯性化）；**Soft limit warnings**（持股數 > 20、單檔權重 > 40%、極小權重 < 0.5% 跳警告，不 hard block） |
| 9 | 未開始 | 頁面擴充 | `/stocks` 股票瀏覽列表頁、`/settings` 設定頁（localStorage 偏好管理）、回顧時間軸瀏覽模式 |

**Phase 1 vs 1.5 切分理由**：Phase 1 先打通「抓取 → 落庫 → API 觸發」的核心管線，驗證 job 系統與資料流設計正確；季報、事件等複雜度高的 collector 放 Phase 1.5。schema 一次定義完整（Phase 1 建表涵蓋 1.5 的欄位），避免之後重構。

**Phase 2 依賴**：Phase 1 + 1.5 都完成後才啟動，確保個股頁可以一次完整呈現（股價、月營收、季報、事件）。

[^phase15-cashflow]: **現金流現有兩條路徑**：Phase 1.5 實作走 TWSE OpenAPI `t187ap10_L_ci`（全市場最新一期，併入 `MOPS_FINANCIALS` job）；Phase 3 為了 FCF 因子需要多季歷史，再補 MOPS `t164sb05` HTML scrape（per-symbol/period，獨立 `MOPS_CASHFLOW` job）。兩者都寫 `financial_statements.statement_type='cashflow'`，不衝突；歷史回填用後者，日常最新季可用前者。

### 分階段規劃原則（MANDATORY）

**實作計畫採「Just-in-Time」撰寫：**

- **僅當前 Phase 有詳細實作計畫**（`docs/superpowers/plans/<date>-phase-N-<name>.md`）
- **下一個 Phase 的實作計畫，僅在當前 Phase 驗收完成後才撰寫**
- 理由：
  1. 越後面的 Phase 不確定性越高，提前規劃會因前一階段學到的知識而需大改
  2. 避免一次輸出過多內容，保持計畫精準度
  3. 使用者可能換 session，需要明確的「接續點」

**Phase 轉換流程：**
1. 當前 Phase 所有 Task 完成
2. 使用者手動驗收通過並明確確認「Phase N 驗證通過」
3. Commit Phase 最終狀態
4. 等使用者明確指示「開始 Phase N+1」
5. 呼叫 `writing-plans` skill 撰寫下一 Phase 的實作計畫
6. 使用者審視計畫並確認後，進入實作

### 每個 Phase 的驗收標準

- 功能可用、流程完整
- `tsc --noEmit` 與 Python 型別檢查通過
- 核心邏輯單元測試
- 對應 E2E 新增
- `USER_GUIDE.md` 同步更新
- **`docs/knowledge/` 對應條目同步更新**（見下節）
- 使用者手動驗證

### 開發者知識庫

位於 `docs/knowledge/`，服務於**修改 alpha-lab 的 Claude**（開發者立場，非投資分析立場）。比照 larp-nexus `docs/knowledge/` 模式原子化拆分：

```
docs/knowledge/
├── index.md              # 總覽 + 維護規範
├── features/             # A~E 五大功能模組
├── domain/               # 投資領域內部邏輯（factors、scoring、reports）
├── architecture/         # 系統架構（data models、API、資料流）
├── collectors/           # 數據抓取模組
└── ai-integration/       # Claude Code SOP、Claude API 預留
```

**原則**：
- **讀者**：開發者 Claude，不是使用者
- **原子化**：每 md 單一概念，50~200 行
- **隨 Phase 補**：Phase 0 只建骨架，實際內容於各 Phase 撰寫
- **強制同步**：修改功能前讀對應條目、commit 前評估是否需更新

## 16. 未解決議題

- **術語庫撰寫**：初版 20-30 個核心詞的清單需要在 Phase 2 確認
- **多因子權重校準**：預設權重需要實際跑過資料後調整
- **最推薦組合邏輯**：目前是「平衡組 = 最推薦」，未來是否要更複雜的邏輯（例如依市場多空）待觀察
- **Claude API 整合時機**：由使用體驗決定何時啟動 Phase 7

---

**設計完成日期**：2026-04-14
