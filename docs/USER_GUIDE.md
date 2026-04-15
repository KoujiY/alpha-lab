# alpha-lab 使用者指南

## 快速開始

### 環境需求

- Node.js 20+
- Python 3.11+
- uv（Python 套件管理）或 pip
- pnpm 9+

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
# 啟動 venv（cmd）：  .venv\Scripts\activate
# 啟動 venv（PS）： .venv\Scripts\Activate.ps1
# 啟動 venv（bash）：source .venv/Scripts/activate
uvicorn alpha_lab.api.main:app --reload
# 或不啟動 venv，直接用：
#   .venv/Scripts/python.exe -m uvicorn alpha_lab.api.main:app --reload
# API 在 http://localhost:8000
# Swagger 文件在 http://localhost:8000/docs
# 退出 venv：deactivate

# Terminal 2 — Frontend
cd frontend
pnpm dev
# UI 在 http://localhost:5173
```

## 功能說明

### 個股頁

1. 確認後端已啟動（`uvicorn alpha_lab.api.main:app --reload`）、前端 dev server（`pnpm dev`）
2. 資料已抓取：`cd backend && .venv/Scripts/python.exe -m scripts.daily_collect --symbols 2330`（至少抓過目標 symbol 的股價與月營收；需用 backend venv。`--symbols` 指定要抓的股票；如需對 DB watchlist 全體抓 prices 請用 `--all`，否則 prices 會被 skip 以免誤觸 TWSE 限流）
3. 瀏覽器開 `http://localhost:5173/`，右上角搜尋框輸入股票代號（例：2330）按 Enter
4. 個股頁會顯示：基本資料、股價走勢、關鍵指標、月營收、季報摘要、三大法人、融資融券、重大訊息
5. 將游標停在下劃虛線的術語（例：本益比 (PE)、EPS）會跳出簡短定義

### 多因子評分（Phase 3）

個股頁右上會顯示四因子雷達圖（Value / Growth / Dividend / Quality）與總分。資料來自 `scores` 表；需先跑一次評分才會有值。

觸發評分（兩種等效）：

```cmd
REM CLI
cd backend
.venv\Scripts\python.exe -m scripts.compute_scores --date 2026-04-15

REM 或走 API（背景執行）
curl -X POST http://localhost:8000/api/jobs/collect ^
  -H "Content-Type: application/json" ^
  -d "{\"type\":\"score\",\"params\":{\"date\":\"2026-04-15\"}}"
```

評分前提：目標 symbol 已有每日股價、月營收、財報（income + balance）、現金流（`mops_cashflow`）四類資料；缺哪一類對應指標會是 None 並在加權時略過。

### 組合推薦（Phase 3）

Header 點「組合推薦」進 `/portfolios`，顯示三個 tab：

| Tab | 風格權重偏重 | 典型取向 |
|-----|-------------|----------|
| 保守組 | Dividend 0.35 / Quality 0.35 | 低波動、殖利率優先 |
| 平衡組（最推薦） | 四因子各 0.25 | 兼顧四面 |
| 積極組 | Growth 0.50 | 成長優先 |

每 tab 下顯示前 10 檔持股：代號、名稱、權重（softmax，單檔最高 30%）、總分。候選池為最新 `calc_date` 的 `scores` 全體，同產業最多 5 檔。

若頁面回傳 409，代表 `scores` 表無資料 — 先跑上面的評分任務。

### 術語庫

- 路徑：`backend/src/alpha_lab/glossary/terms.yaml`
- Phase 2 v1 共 15 條：PE、PB、EPS、ROE、毛利率、殖利率、月營收、YoY、MoM、三大法人、外資、投信、自營商、融資、融券
- 編輯後重啟 backend 才會生效（`load_terms` 有 lru_cache）
- 新增術語：只需編輯 yaml；`<TermTooltip term="新key">...</TermTooltip>` 即可套用

### 既有功能（Phase 0-1.5）

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

## Rebuild 本地資料庫

Phase 1.5 新增 4 個 table（`institutional_trades`、`margin_trades`、`events`、`financial_statements`）。
重啟 uvicorn 會自動 `create_all` 補上新表，舊表資料保留。

若要完全重建（例如測試乾淨起點）：

```bash
# 1. 停掉 uvicorn
# 2. 刪除 DB
rm data/alpha_lab.db

# 3. 重啟 uvicorn，startup 會自動重建全部 8 個 table
cd backend
.venv/Scripts/python.exe -m uvicorn alpha_lab.api.main:app --reload
```

確認 8 個 table 都在：

```bash
.venv/Scripts/python.exe -c "import sqlite3; c=sqlite3.connect('../data/alpha_lab.db'); print(sorted([r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')]))"
```

預期輸出：`['events', 'financial_statements', 'institutional_trades', 'jobs', 'margin_trades', 'prices_daily', 'revenues_monthly', 'stocks']`

## 常見問題

### Q：數據會更新嗎？

A：Phase 1 起，數據會透過 `POST /api/jobs/collect` 手動觸發抓取，或排程每日自動抓取。

### Q：報告會保存在哪？

A：Phase 4 起，分析報告會儲存在 `data/reports/analysis/`，可透過前端「回顧模式」瀏覽。

## 專有名詞對照

> 將於 Phase 2 起陸續補充。

---

_文件同步於 Phase 3。後續 Phase 會持續擴充。_
