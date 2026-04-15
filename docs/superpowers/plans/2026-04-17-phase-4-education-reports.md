# Phase 4: 教學系統完整化 + 推薦理由 + 報告儲存與回顧 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 交付功能 E — 推薦理由（靜態模板，從因子分數產字串）、L2 詳解側邊面板（markdown 載體）、分析報告儲存 + 回顧模式（/reports 路由）。Phase 4 只做上層教學/報告功能，不動既有 collectors/scoring 核心。

**Architecture:**
- **推薦理由（reasons）**：純函式 `analysis/reasons.py`，輸入 `FactorBreakdown` + style，輸出 `list[str]`（2-4 條短句）。規則：每因子分數 ≥ 70 生「優勢」句；≤ 30 生「注意」句；style 特性句固定掛一條。不呼叫外部 API（Phase 7 才做 LLM）
- **Portfolio schema 擴充**：`Holding` 加 `reasons: list[str]`；`Portfolio` 可選加 `style_summary: str`
- **L2 詳解**：新目錄 `backend/src/alpha_lab/education/l2/<topic>.md`，每檔 frontmatter `id/title/related_terms` + markdown 內文；loader 讀目錄、快取；`GET /api/education/{topic_id}` 回 `{id, title, related_terms, body_markdown}`
- **L2 前端**：`<TermTooltip>` 右下加「看完整說明 →」按鈕；點擊開 `<L2Panel>`（右側 slide-in panel，非 modal，不擋主畫面）；用 react-markdown + remark-gfm render
- **Reports 儲存**：`backend/src/alpha_lab/reports/` 新模組（`storage.py` 讀寫檔案 + index.json；`service.py` 高階 API）；嚴格遵守 CLAUDE.md §「分析 SOP」檔名與 frontmatter 格式
- **Reports 自動寫**：`/api/portfolios/recommend` 成功後，若請求帶 `save_report=true` 則自動寫 `portfolio-<date>.md`；預設不自動寫（避免每次 refresh 都寫檔）。此外新增 `POST /api/reports` 支援手動儲存任意 payload
- **Reports API**：`GET /api/reports`（讀 index.json）、`GET /api/reports/{id}`（回 markdown + meta）、`POST /api/reports`（新增）
- **前端 /reports**：列表頁讀 `GET /api/reports`；單報告頁 `/reports/:id` 讀 `GET /api/reports/:id`，以 react-markdown render
- **知識庫同步**：新增 `features/education/l2-panel.md`、`features/education/reasons.md`、`features/reports/storage.md`、`features/reports/viewer.md`；更新 `features/education/tooltip.md`（L2 入口）、`features/portfolio/recommender.md`（reasons 欄位）、`architecture/data-flow.md`（報告流）

**Tech Stack:** 新增 frontend 套件 `react-markdown`、`remark-gfm`（pnpm add）。Backend 無新 Python 套件；沿用 PyYAML（frontmatter）+ stdlib json/pathlib。

---

## Phase 4 工作總覽

| Task | 主題 |
|------|------|
| 1 | 推薦理由 `analysis/reasons.py` + 單元測試 |
| 2 | 串接 `generate_portfolio` → Portfolio schema 擴欄 + API 回傳 + 前端顯示 |
| 3 | L2 教學內容 loader + 5 個核心 topic markdown |
| 4 | L2 API 端點 + 前端 `<L2Panel>` + `<TermTooltip>` 連結 |
| 5 | Reports 儲存後端（storage + index.json + `GET /api/reports`、`GET /api/reports/{id}`、`POST /api/reports`） |
| 6 | 組合推薦自動寫 portfolio 報告 + 前端「儲存報告」按鈕 |
| 7 | 前端 `/reports` 列表頁 + `/reports/:id` 單報告頁（react-markdown + remark-gfm） |
| 8 | E2E 整合測試 + 全套檢查 + spec §15 更新 |

**總計：8 tasks**

## 範圍與邊界

**本 Phase 包含**：
- 靜態模板推薦理由（不接 LLM）
- L2 詳解 markdown 檔 + 載入器 + API + side panel UI
- `data/reports/` 讀寫模組、`index.json` 同步、`summaries/<date>.json` 一行摘要
- `/reports` 回顧路由（列表 + 單報告）
- portfolio 報告的「自動寫（需旗標）」與「手動寫」兩條路徑
- 對應 E2E / vitest / pytest 測試

**本 Phase 不包含**（留後續）：
- stock / events / research 類型的「自動生成」報告（本期只做 portfolio 自動寫、其他類型保留手動 POST）
- 接 Claude API 產生動態理由（Phase 7）
- 報告 PATCH / DELETE / 加星標（後續 Phase）
- 複雜搜尋（僅列表 + 類型/標籤過濾）

## Commit 規範（本專案 MANDATORY）

1. 靜態分析必做：`ruff check .` + `mypy src` + `pnpm type-check` + `pnpm lint` 必須 0 error
2. 每個 Task 完成即 commit（agentic 環境不等 review）
3. 按 type 拆分：`feat` / `docs` / `fix` / `refactor` / `test` 不混
4. **禁止 scope 括號**：`type: description`，不寫 `type(scope): description`
5. 同步檢查：知識庫、USER_GUIDE、E2E 連動更新
6. 中文亂碼掃描：完成後 `grep -r "��" .`

---

## Task 1：推薦理由生成器 analysis/reasons.py

**Files:**
- Create: `backend/src/alpha_lab/analysis/reasons.py`
- Create: `backend/tests/analysis/test_reasons.py`

**Steps:**

- [ ] Step 1：寫失敗測試，覆蓋
  - 高分因子（≥ 70）→ 出現正向描述（例：「Quality 分數 90，體質穩健」）
  - 低分因子（≤ 30）→ 出現警示描述（例：「Value 分數 25，估值偏貴需留意」）
  - 中段因子（30-70）→ 不生句
  - 每種 style 都有一條 style 特性句（conservative / balanced / aggressive）
  - None 分數不生句、不 crash
  - 輸出為 `list[str]`，長度至少 1、至多 6
- [ ] Step 2：實作 `build_reasons(breakdown: FactorBreakdown, style: Style) -> list[str]`
  - 內部常數：`HIGH_THRESHOLD=70`、`LOW_THRESHOLD=30`
  - 四因子對應的高/低文案模板（value/growth/dividend/quality × high/low = 8 模板）
  - style 特性句表（保守 → 注重殖利率與品質；平衡 → 四面兼顧；積極 → 追求成長）
  - 最終 `[style_line, *factor_lines]`
- [ ] Step 3：`ruff check . && mypy src && pytest tests/analysis/test_reasons.py -v` 全綠
- [ ] Step 4：`git add` + commit `feat: add multi-factor recommendation reason generator`

## Task 2：推薦理由串進 generate_portfolio 與前端顯示

**Files:**
- Modify: `backend/src/alpha_lab/schemas/portfolio.py`（Holding 加 `reasons: list[str]`）
- Modify: `backend/src/alpha_lab/analysis/portfolio.py`（呼叫 `build_reasons` 填入 Holding）
- Modify: `backend/tests/analysis/test_portfolio.py`（斷言 holdings[0].reasons 非空）
- Modify: `backend/tests/api/test_portfolios_recommend.py`（斷言 JSON 回傳含 reasons 陣列）
- Modify: `frontend/src/api/types.ts`（Holding 加 `reasons: string[]`）
- Modify: `frontend/src/components/portfolio/HoldingsTable.tsx`（可展開列顯示 reasons）
- Create: `frontend/tests/components/HoldingsTable.test.tsx`（若尚未存在，驗證 reasons 顯示）
- Modify: `frontend/tests/e2e/fixtures/portfolios-recommend.json`（每個 holding 加 reasons 範例）
- Modify: `frontend/tests/e2e/portfolios.spec.ts`（新增驗證理由文字出現的 case）

**Steps:**

- [ ] Step 1：擴 `Holding` schema 欄位 `reasons: list[str] = Field(default_factory=list)`
- [ ] Step 2：`generate_portfolio` 內部，對每個最終入選 holding 呼叫 `build_reasons(breakdown, style)`
- [ ] Step 3：補測試：unit 層 `test_portfolio.py` 與 API 層 `test_portfolios_recommend.py` 都要驗證 reasons
- [ ] Step 4：前端 `types.ts` 同步；`HoldingsTable` 在每列下加可展開理由區塊（預設摺疊，點「查看理由」展開）
- [ ] Step 5：更新 E2E fixture + 新增 E2E 斷言（點展開後能看到理由文字）
- [ ] Step 6：`ruff check . && mypy src && pytest` 全綠；`pnpm type-check && pnpm lint && pnpm test` 全綠
- [ ] Step 7：同步 `docs/knowledge/features/portfolio/recommender.md`（加「推薦理由」小節）+ 建立 `docs/knowledge/features/education/reasons.md`
- [ ] Step 8：commit `feat: include recommendation reasons in portfolio holdings`（可能拆兩個：backend feat + frontend feat）

## Task 3：L2 教學內容載入器 + 5 個核心 topic markdown

**Files:**
- Create: `backend/src/alpha_lab/education/__init__.py`
- Create: `backend/src/alpha_lab/education/loader.py`
- Create: `backend/src/alpha_lab/education/l2/PE.md`
- Create: `backend/src/alpha_lab/education/l2/ROE.md`
- Create: `backend/src/alpha_lab/education/l2/dividend-yield.md`
- Create: `backend/src/alpha_lab/education/l2/monthly-revenue.md`
- Create: `backend/src/alpha_lab/education/l2/multi-factor-scoring.md`
- Create: `backend/src/alpha_lab/schemas/education.py`
- Create: `backend/tests/education/__init__.py`
- Create: `backend/tests/education/test_loader.py`

**Steps:**

- [ ] Step 1：Pydantic schema `L2Topic { id: str, title: str, related_terms: list[str], body_markdown: str }`
- [ ] Step 2：Loader 實作
  - 掃 `education/l2/*.md`
  - 每檔以 `---` 分 frontmatter / body；PyYAML 解析 frontmatter
  - Cache：`@lru_cache` 單例快取；提供 `clear_cache()` 給測試
  - `load_l2_topics() -> dict[str, L2Topic]`、`get_l2_topic(topic_id) -> L2Topic | None`
- [ ] Step 3：5 份 markdown（每份 40-120 行，frontmatter 含 `id / title / related_terms`）
  - `PE.md`（本益比深度）
  - `ROE.md`（股東權益報酬率深度）
  - `dividend-yield.md`（殖利率與配息穩定度）
  - `monthly-revenue.md`（月營收與年增率）
  - `multi-factor-scoring.md`（四因子評分邏輯總覽，連結到本系統 scoring）
- [ ] Step 4：測試：loader 能讀出 5 條、frontmatter 解析正確、body 保留 markdown 段落
- [ ] Step 5：`ruff check . && mypy src && pytest tests/education/ -v`
- [ ] Step 6：建立 `docs/knowledge/features/education/l2-panel.md`（先寫 loader 段）
- [ ] Step 7：commit `feat: add L2 education content loader with 5 core topics`

## Task 4：L2 API 端點 + L2Panel + Tooltip 入口

**Files:**
- Create: `backend/src/alpha_lab/api/routes/education.py`
- Modify: `backend/src/alpha_lab/api/main.py`（include education router）
- Create: `backend/tests/api/test_education.py`
- Create: `frontend/src/api/education.ts`
- Create: `frontend/src/hooks/useL2Topic.ts`
- Create: `frontend/src/components/education/L2Panel.tsx`
- Modify: `frontend/src/components/TermTooltip.tsx`（加「看完整說明 →」按鈕、點擊打開 panel）
- Modify: `frontend/src/api/types.ts`（L2Topic 類型）
- Modify: `frontend/src/hooks/useGlossary.ts`（可能需補 glossary term → L2 topic id 對照）或於 TermTooltip 直接 prop 傳 `l2TopicId`
- Modify: `frontend/src/components/TermTooltip.tsx`（新 prop `l2TopicId?: string`）
- Create: `frontend/tests/components/L2Panel.test.tsx`

**Steps:**

- [ ] Step 1：後端 router：
  - `GET /api/education/l2` → 回所有 topic meta（不含 body，供前端 discovery）
  - `GET /api/education/l2/{topic_id}` → 回完整 L2Topic；找不到 404
- [ ] Step 2：後端測試（已設 5 topic，至少驗證 list 有 5 筆、單一取值、404）
- [ ] Step 3：frontend pnpm 安裝 `react-markdown` + `remark-gfm`（`cd frontend && pnpm add react-markdown remark-gfm`）
- [ ] Step 4：`L2Panel`：右側 slide-in（Tailwind `fixed right-0 top-0 h-full w-96`），有關閉按鈕；內容用 `<ReactMarkdown remarkPlugins={[remarkGfm]}>`
- [ ] Step 5：`<TermTooltip>`：加 prop `l2TopicId?: string`。若有，tooltip 內容右下加「看完整說明 →」按鈕；點擊 setState 開啟 L2Panel
  - 狀態可用 local state（Tooltip 自管）或 context（多處 Tooltip 共用一個 panel）→ 本 Phase 用 context（`L2PanelContext`）更乾淨
- [ ] Step 6：`L2PanelProvider` 掛在 `AppLayout` 最外層，全域一個 panel
- [ ] Step 7：測試：`L2Panel.test.tsx`（渲染 markdown、關閉按鈕）；`TermTooltip` 測試補「含 l2TopicId 時顯示連結」
- [ ] Step 8：全套檢查；`docs/knowledge/features/education/l2-panel.md` 更新至完整；更新 `features/education/tooltip.md`（L1 → L2 入口）
- [ ] Step 9：commit `feat: add L2 education side panel and term tooltip integration`

## Task 5：Reports 儲存後端 + GET/POST API

**Files:**
- Create: `backend/src/alpha_lab/reports/__init__.py`
- Create: `backend/src/alpha_lab/reports/storage.py`
- Create: `backend/src/alpha_lab/reports/service.py`
- Create: `backend/src/alpha_lab/schemas/report.py`
- Create: `backend/src/alpha_lab/api/routes/reports.py`
- Modify: `backend/src/alpha_lab/api/main.py`（掛載 reports router）
- Create: `backend/tests/reports/__init__.py`
- Create: `backend/tests/reports/test_storage.py`
- Create: `backend/tests/api/test_reports.py`

**Steps:**

- [ ] Step 1：schemas `ReportMeta { id, type, title, symbols, tags, date, path, summary_line, starred }` 與 `ReportDetail(ReportMeta + body_markdown)`；`ReportCreate { type, title, ... , body_markdown, summary_line }`
- [ ] Step 2：`storage.py` 低階層
  - `REPORTS_ROOT = data/reports`（可由 env 覆寫，便於測試；用 `get_reports_root()` 讀 `ALPHA_LAB_REPORTS_ROOT` 環境變數，否則預設專案 `data/reports`）
  - `load_index() -> list[ReportMeta]`、`save_index(items)`、`append_to_index(meta)`
  - `write_report_markdown(report_id, body, frontmatter)` 寫 `analysis/<id>.md`
  - `write_summary(date, summary_line)` 寫 `summaries/<date>.json`（append 一行）
- [ ] Step 3：`service.py` 高階層
  - `create_report(payload: ReportCreate) -> ReportMeta`：組 id（依 type 套 CLAUDE.md SOP 檔名）、寫 md、append index、寫 summary
  - `list_reports(type?, tag?) -> list[ReportMeta]`
  - `get_report(id) -> ReportDetail | None`
- [ ] Step 4：router
  - `GET /api/reports?type=&tag=` → list
  - `GET /api/reports/{report_id}` → detail；404 when 缺
  - `POST /api/reports` → body 為 `ReportCreate`，回 `ReportMeta`
- [ ] Step 5：測試
  - `test_storage.py`：tmp dir 注入 env → 寫 / 讀 / index 同步行為
  - `test_reports.py`：FastAPI TestClient 端到端驗證
  - 檔名格式：`portfolio-YYYY-MM-DD.md`、`stock-<symbol>-YYYY-MM-DD.md`、`research-<topic>-YYYY-MM-DD.md`、`events-YYYY-MM-DD.md`
  - 重複 id 處理：同一天重複建立 → 以既有為準還是覆寫？本 Phase 策略「覆寫 + index 更新 updated_at」
- [ ] Step 6：全套檢查
- [ ] Step 7：建立 `docs/knowledge/features/reports/storage.md`；更新 `architecture/data-flow.md` 加報告流
- [ ] Step 8：commit `feat: add report storage backend with index json sync`

## Task 6：組合推薦自動寫 portfolio 報告 + 手動儲存按鈕

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/portfolios.py`（接受 `save_report` query flag）
- Modify: `backend/src/alpha_lab/reports/service.py`（補 `build_portfolio_report_markdown(response)` helper）
- Modify: `backend/tests/api/test_portfolios_recommend.py`（補 `save_report=true` 測試）
- Modify: `frontend/src/api/portfolios.ts`（`recommendPortfolios({ style?, saveReport? })` 介面）
- Modify: `frontend/src/pages/PortfoliosPage.tsx`（加「儲存此次推薦為報告」按鈕 → 呼叫 `saveReport=true` 版推薦或直接 `POST /api/reports`）
- Create: `frontend/src/api/reports.ts`（list / get / create）
- Modify: `frontend/src/api/types.ts`（report 類型）
- Create: `frontend/tests/components/PortfoliosPage.saveReport.test.tsx`（或整合到現有 page test）

**Steps:**

- [ ] Step 1：`build_portfolio_report_markdown(resp: RecommendResponse) -> tuple[str, dict]` 回 markdown body 與 frontmatter
  - body：四組 tab 各列持股表 + reasons 區塊 + 計算日期
  - frontmatter：`id=portfolio-<calc_date>`、`type=portfolio`、`title=組合推薦 YYYY-MM-DD`、`symbols=<union of holdings>`、`tags=[portfolio]`、`date=<calc_date>`、`summary_line="{num_holdings} 檔；平衡組最高分 {top_score}"`
- [ ] Step 2：portfolios router 支援 `save_report: bool = False` query；為 true 時呼叫 `create_report` 並把 `reasoning_ref` 設到該 report_id
- [ ] Step 3：`POST /api/reports` 已於 Task 5 完成，前端以該端點支援「手動從 UI 填寫並儲存」路徑；本 Phase 先做「一鍵自動內容 + 儲存」
- [ ] Step 4：前端按鈕：`PortfoliosPage` 右上加「儲存此次推薦」；點擊 mutation 呼叫 `recommendPortfolios({ saveReport: true })` 並 toast/alert 顯示已儲存 + 連結到 `/reports/{id}`
- [ ] Step 5：測試：pytest 驗證 `save_report=true` 後 `data/reports/index.json` 新增一筆、`analysis/*.md` 存在；frontend vitest 驗證按鈕存在 + 呼叫 API 時帶 flag
- [ ] Step 6：全套檢查
- [ ] Step 7：更新 `docs/knowledge/features/portfolio/recommender.md`（自動儲存行為）+ `features/reports/storage.md`（portfolio 自動寫路徑）
- [ ] Step 8：commit `feat: auto write portfolio recommendation report when flagged`

## Task 7：前端 /reports 列表頁 + 單報告頁

**Files:**
- Create: `frontend/src/pages/ReportsPage.tsx`（列表）
- Create: `frontend/src/pages/ReportDetailPage.tsx`（單報告）
- Create: `frontend/src/hooks/useReports.ts`
- Create: `frontend/src/hooks/useReport.ts`
- Create: `frontend/src/components/reports/ReportCard.tsx`
- Create: `frontend/src/components/MarkdownRender.tsx`（包 react-markdown + remark-gfm，供報告頁與 L2 共用）
- Modify: `frontend/src/App.tsx`（加 `/reports` 與 `/reports/:id` 路由）
- Modify: `frontend/src/layouts/AppLayout.tsx`（header 加「回顧」連結）
- Create: `frontend/tests/components/ReportCard.test.tsx`
- Create: `frontend/tests/components/MarkdownRender.test.tsx`

**Steps:**

- [ ] Step 1：`MarkdownRender` 元件抽共用，prop `source: string`；全部 render 用這個（Task 4 的 L2Panel 也改 import 此元件以免重複）
- [ ] Step 2：`useReports` / `useReport` TanStack Query hooks
- [ ] Step 3：`ReportsPage` — 列表（type 篩選 dropdown + 卡片 grid），item 點擊導 `/reports/:id`
- [ ] Step 4：`ReportDetailPage` — header（title/date/tags/symbols） + 本文 markdown + 「返回列表」連結
- [ ] Step 5：route 掛上；AppLayout header 加「回顧」
- [ ] Step 6：vitest：ReportCard 顯示 meta；MarkdownRender 能 render basic markdown（含 table 測試 gfm）
- [ ] Step 7：全套前端檢查
- [ ] Step 8：更新 `docs/knowledge/features/reports/viewer.md` + `USER_GUIDE.md`（回顧模式操作）
- [ ] Step 9：commit `feat: add reports list and detail pages with markdown renderer`

## Task 8：E2E 整合測試 + 全套檢查 + spec §15 更新

**Files:**
- Create: `frontend/tests/e2e/reports.spec.ts`
- Create: `frontend/tests/e2e/fixtures/reports-index.json`
- Create: `frontend/tests/e2e/fixtures/report-detail-portfolio.json`
- Modify: `frontend/tests/e2e/portfolios.spec.ts`（補儲存按鈕 → reports flow）
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（§15 表把 Phase 4 改成 ✅）
- Modify: `docs/USER_GUIDE.md`（新功能章節彙整）

**Steps:**

- [ ] Step 1：E2E reports：mock `GET /api/reports` 列出 2 筆、點卡片進單報告頁、驗證 markdown 標題與段落
- [ ] Step 2：E2E portfolios：mock `POST /api/portfolios/recommend?save_report=true` 回帶 `reasoning_ref` 的 response；驗證點擊「儲存」後 toast 出現與前端可跳 `/reports/{id}`
- [ ] Step 3：backend 全套：`ruff check . && python -m mypy src && pytest`
- [ ] Step 4：frontend 全套：`pnpm type-check && pnpm lint && pnpm test && pnpm build`
- [ ] Step 5：E2E：`pnpm e2e`；若沙盒無瀏覽器則跳過並於 PR body 註記
- [ ] Step 6：`grep -r "��" .`（跳過 node_modules）確認 0 亂碼
- [ ] Step 7：spec §15 把 Phase 4 狀態改 ✅ 完成（`2026-04-17`）
- [ ] Step 8：`docs/USER_GUIDE.md` 加教學系統完整版、回顧模式章節；CMD 格式使用指引
- [ ] Step 9：commit：
  - `test: add e2e coverage for reports flow and portfolio save`
  - `docs: mark phase 4 complete and document education and reports`
- [ ] Step 10：`git push -u origin claude/phase-4-feature-e-m1R1N`（失敗退指數回退 2s/4s/8s/16s）
- [ ] Step 11：以 `mcp__github__create_pull_request` 開 PR；title 小寫 + 無 scope 括號
- [ ] Step 12：輸出 PR URL + commits + 跳過項目 + CMD 格式手動 smoke 指令
