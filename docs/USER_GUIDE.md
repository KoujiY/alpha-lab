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
6. 頁面上方有「收藏 ☆ / 已收藏 ★」切換（存 localStorage）、「加入組合」按鈕（展開清單挑一個已儲存組合、把這檔 symbol 混入）、「相關分析報告」區塊（列出 `GET /api/reports?symbol={symbol}` 的結果）
   - 加入組合同樣走 probe 檢查：若今日報價不齊會彈「今日報價不齊」dialog，流程與儲存推薦組合一致

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

### 推薦理由與 L2 詳解（Phase 4）

- **推薦理由**：`/portfolios` 每檔持股下方有「查看理由」可展開 1-5 條中文短句，說明為何它出現在這個風格裡（style 特性 + 分數高/低的因子名）。理由是靜態模板生成，規則見 `docs/knowledge/features/education/reasons.md`。
- **L2 詳解面板**：個股頁、Portfolios、Reports 上的術語 Tooltip 若該術語有 L2 條目，Tooltip 內會多出「看完整說明 →」按鈕；點開右側滑出詳解面板（含 Markdown 內文、互動範例說明）。目前共 5 個 topic：
  - PE（本益比）、ROE、殖利率、月營收 YoY、多因子評分
- 關閉面板：點遮罩、按 ESC、或點其他 topic 切換。

### 分析報告儲存與回顧（Phase 4）

**存報告**：

```cmd
REM 方法 1：/portfolios 頁面右上按「儲存此次推薦為報告」→ 自動寫入 portfolio-<calc_date>.md
REM 方法 2：直接打 API
curl -X POST "http://localhost:8000/api/portfolios/recommend?save_report=true"

REM 方法 3：Claude Code 分析 SOP（手動 / 半自動）
REM   POST /api/reports 帶 type=stock/research/portfolio/events + body_markdown
```

**回顧**：

- Header 點「回顧」→ `/reports`，列表以 type 過濾（全部 / 個股 / 組合 / 事件 / 研究）
- 頁面上方有搜尋欄，可依「標題 / 摘要 / 標籤 / 代號」即時篩選；搜尋與 type 過濾可組合
- 點卡片進細節頁，Markdown 以 react-markdown + remark-gfm 渲染（支援表格、程式區塊、清單）
- **管理動作**（Phase 6）：
  - ☆ / ★ 收藏切換（列表卡片與詳情頁皆可）
  - 刪除（會跳出 `window.confirm` 確認；詳情頁刪除後自動返回列表）
  - 未來 Phase 8 UI 升級會把這些按鈕改為 icon button，操作語意不變
- 檔案實體路徑：
  - `data/reports/analysis/<id>.md` — frontmatter + body
  - `data/reports/index.json` — meta 索引（前端列表直接吃這個）
  - `data/reports/summaries/<date>.json` — 當日每份報告一行摘要

### 教學密度切換（Phase 6）✅

右上角 header 有一顆 toggle 按鈕，依序循環三段：

| 模式 | 顯示 | 行為 |
|------|------|------|
| 📖 完整教學 | 預設 | 術語 hover 出 tooltip、點擊進 L2 詳解；推薦組合顯示「查看理由」欄 |
| 📗 精簡 | 中階 | 術語不出 tooltip，但仍可點擊進 L2；「查看理由」欄保留 |
| 📕 關閉 | 熟手 | 術語完全不標示、不可互動；「查看理由」欄隱藏 |

偏好存在 `localStorage['alpha-lab:tutorial-mode']`，換頁 / 重整保留。未來 Phase 8 UI 升級會把這顆文字 toggle 改成 icon button。

### 選股篩選器（Phase 5）✅

Header 點「選股篩選」進 `/screener`，可依四因子分數篩選候選股：

1. 四個滑桿分別設定 Value / Growth / Dividend / Quality 的「最低分數」門檻（0-100，步進 5）
2. 按「篩選」→ 下方表格顯示符合條件的股票（代號、名稱、產業、四因子分數、總分）
3. 點擊表頭可切換排序（升降序）
4. 股票代號可點擊跳轉個股頁

前提：`scores` 表需有資料（同組合推薦）。若 scores 為空，按篩選會顯示「尚無評分資料」引導提示。

篩選器的資料量取決於跑過 data collection + scoring 的股票數。目前需手動觸發（Phase 7 才有自動排程）。

### 組合追蹤（Phase 6）✅

**儲存組合：**

1. 進入 `/portfolios` 推薦頁，切換到任一 tab（保守組 / 平衡組 / 積極組）
2. 點擊持股列表下方「儲存此組合」按鈕
3. 前端先呼叫 `POST /api/portfolios/saved/probe` 檢查今日所有持股都有收盤價：
   - **今日都有** → 直接以今日為 `base_date` 寫入 `portfolios_saved`
   - **任一檔缺今日價** → 彈「今日報價不齊」dialog，列出缺價 symbol 與可用的 `resolved_date`（最近「全檔都有報價」的歷史日）；使用者可選「取消」或「以 {resolved_date} 為基準繼續」
4. 儲存成功後，頁面底部「已儲存組合」清單會即時新增一筆

**補抓今日報價**：右上 nav 有全域「更新報價」按鈕，點擊後會 union(已儲存組合持股 ∪ 收藏清單 ∪ 目前瀏覽的 `/stocks/:symbol`) 批次送 TWSE 抓當月股價。按鈕下方會浮出狀態面板（琥珀進行中 / 綠色完成 / 紅色失敗），按 ✕ 可關閉。

TWSE 收盤價通常在交易日 14:00 後公告；非交易日或盤中時段本來就不會有「今日價」，此時直接用 dialog 選 `resolved_date` 即可。

**查看 NAV 走勢：**

點擊「已儲存組合」清單中的任一項目 → 跳轉 `/portfolios/:id` 追蹤詳細頁：

- **累積報酬**：`total_return` 以百分比格式顯示於頁面上方，正報酬綠色、負報酬紅色
- **NAV 累積走勢圖**：recharts 折線圖，X 軸為日期，Y 軸為 NAV（初始值 1.0）
- **持股明細表**：代號、名稱、softmax 權重、base_price（基準收盤價）

**NAV 計算原理：**

```
nav(t) = Σ( weight_i × today_close_i / base_close_i )
```

- `base_close_i`：儲存組合當日各持股收盤價
- 缺價的日子（任一持股當日無收盤價）會自動跳過，不納入走勢圖

**刪除組合：**

追蹤詳細頁右上「刪除追蹤組合」按鈕 → 視窗二次確認 → 從 `portfolios_saved` 移除，自動跳回 `/portfolios`。

### 組合血緣（Phase 7A）✅

當你在個股頁點「加入組合」建立的新組合，會自動記錄來自哪個母組合。進到新組合的追蹤頁時：

- 標題下方會顯示「由 組合 #X 分裂」連結，一鍵回到母組合
- 報酬卡片會多一張琥珀色「自母組合起報酬」，呈現從母組合 `base_date` 起算的連續報酬（= `parent_nav_at_fork × latest_nav - 1`）
- NAV 走勢圖把母組合歷史走勢（灰色虛線）接在新組合之前，fork 當日畫一條橘色垂直線標示切換點

沒有母組合（直接在 `/portfolios` 儲存推薦）的組合則維持原樣，不顯示上述資訊。

此外，Phase 7A 在後端 schema 層加了兩道防線：同一組合不能有重複 symbol、持股權重總和需在 `|sum - 1.0| ≤ 1e-6` 內，違反會回 422；這避免前端 `buildMergedHoldings` 合成時意外把同檔股票重複加入或累積浮點誤差。

### 資料來源備援

- 預設每日價格來自 TWSE（台灣證券交易所）
- 若 TWSE 暫時故障，系統會自動 fallback 到 Yahoo Finance；資料庫 `prices_daily.source` 會標記來源
- Yahoo 是非官方 API、準確度偶有偏差，僅作為備援；若頻繁使用 Yahoo 資料請自行交叉比對

### 每日市場簡報（Phase 7B.2）✅

每次執行 `daily_collect.py` 後，pipeline 尾端會自動產出一份 Markdown 簡報，包含：

- **市場概況**：當日所有已抓取股票的收盤價、漲跌幅、成交量
- **法人動向**：三大法人買賣超（外資 / 投信 / 自營商）
- **重大訊息**：當日重大訊息列表
- **組合追蹤**：已儲存組合一覽

**檔案位置**：`data/reports/daily/YYYY-MM-DD.md`

**手動觸發**：

```cmd
cd backend
.venv\Scripts\python.exe scripts\daily_collect.py --symbols 2330 --date 2026-04-17
REM daily briefing 會在 pipeline 尾端自動產出
type ..\data\reports\daily\2026-04-17.md
```

簡報同時會寫入 `data/reports/index.json`（type = `"daily"`），可在前端 `/reports` 回顧頁查看。

### 計算後指標（供 Claude Code 使用）

- `data/processed/indicators/<symbol>.json`：MA / RSI / 52 週高低比
- `data/processed/ratios/<symbol>.json`：PE / ROE / 毛利率 / 負債比 / FCF
- 由 daily_collect 或手動觸發 `PROCESSED_INDICATORS` / `PROCESSED_RATIOS` 更新

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
| 5 | 選股篩選器（B）✅ |
| 6 | 組合追蹤 + 報告管理 + 教學開關（D）✅ |
| 7A | 組合追蹤強化（血緣 + schema 驗證）✅ |
| 7B.1 | 數據源擴充（Yahoo 備援、processed 指標 JSON、daily_collect 串接）✅ |
| 7B.2 | 內容自動化（每日市場簡報）✅ |
| 7B.3 | UX 與快取（報告離線快取、加入組合強化） |
| 8 | UI 升級 |
| 9 | 頁面擴充 |

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

預期輸出：`['events', 'financial_statements', 'institutional_trades', 'jobs', 'margin_trades', 'prices_daily', 'revenues_monthly', 'scores', 'stocks']`

## 常見問題

### Q：數據會更新嗎？

A：Phase 1 起，數據會透過 `POST /api/jobs/collect` 手動觸發抓取，或排程每日自動抓取。

### Q：報告會保存在哪？

A：Phase 4 起，分析報告會儲存在 `data/reports/analysis/<id>.md`，同時更新 `data/reports/index.json` 與當日 `data/reports/summaries/<date>.json`；前端 `/reports` 頁面可瀏覽列表與細節。自訂儲存目錄可設 `ALPHA_LAB_REPORTS_ROOT` 環境變數。

## 專有名詞對照

> 將於 Phase 2 起陸續補充。

---

_文件同步於 Phase 7B.2。後續 Phase 會持續擴充。_
