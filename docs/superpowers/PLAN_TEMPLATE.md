# Phase 實作計畫通用模板

> 本模板從 Phase 2 / Phase 3 的實作計畫抽象而來。未來各 Phase（尤其在沒有 `superpowers:writing-plans` plugin 的環境，例如 Claude Code Web session）撰寫 `docs/superpowers/plans/<date>-phase-N-<name>.md` 時依此模板依樣畫葫蘆即可。

## Plan 文件整體骨架

每份 Phase plan 由以下段落組成，順序固定：

1. **Header**（三行）
2. **Phase 工作總覽**（表格：群組 × 任務數 × 主題）
3. **範圍與邊界**（本 Phase 包含 / 不包含）
4. **Commit 規範**（本專案 MANDATORY 項目）
5. **Task N: 任務名稱**（重複 N 個）
6. **群組驗收節點**（每個字母群組結尾）
7. **完成後**（指示使用者下一步）

---

## 1. Header 格式

````markdown
# Phase N: <主題> Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** <一句話敘述本 Phase 要交付什麼。包含主端點 / 主頁面 / 主資料流。>

**Architecture:**
- **<層級 1>**：<兩三句說明設計理念與關鍵抉擇>
- **<層級 2>**：...
- **知識庫同步**：本 Phase 建立 `...`，更新 `...`

**Tech Stack:** <逗號分隔的技術清單，對齊本專案技術棧>

---
````

## 2. Phase 工作總覽

表格化列出所有群組。群組用 A/B/C... 字母編號，便於「字母群組驗收節點」的溝通。

```markdown
## Phase N 工作總覽

| 群組 | 任務數 | 主題 |
|------|--------|------|
| A | 3 | <後端 schema / model 類> |
| B | 2 | <後端核心邏輯 1> |
| ...  |
| J | 2 | 知識庫 + USER_GUIDE + Phase 驗收 |

**總計：N tasks**
```

## 3. 範圍與邊界

強制雙列表，避免範圍蔓延與同步漏項。

```markdown
## 範圍與邊界

**本 Phase 包含**：
- <具體 endpoint / 頁面 / 元件 / 測試>
- ...

**本 Phase 不包含**（留後續 Phase）：
- <下一 Phase 才做的功能> → Phase M
- ...
```

## 4. Commit 規範段落

固定 8 條，直接複製此段（依專案規範微調）：

```markdown
## Commit 規範（本專案 MANDATORY）

1. **靜態分析必做**：`ruff check .` + `mypy src` + `pnpm type-check` + `pnpm lint` 必須 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit；給手動驗收指引、等使用者明確「驗證通過」
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` / `chore` 不混在同一 commit
4. **禁止 scope 括號**：`type: description`，不寫 `type(scope): description`
5. **同步檢查**：知識庫、spec、USER_GUIDE、E2E 是否需要連動更新
6. **中文亂碼掃描**：完成寫檔後 `grep -r "��" .`（不含 node_modules）
7. **驗收指引 shell**：給使用者的指令用 CMD 格式（反斜線路徑、REM 註解、```cmd code fence）
8. **群組驗收節點**：每個字母群組（A/B/...）完成後停下等使用者驗收（本機互動模式）
```

> Web 自動模式下，第 2 條與第 8 條由 WEB_AUTO_MODE_PROMPT.md 覆蓋（不等人工、task 完成即 commit）。

## 5. Task 結構

每個 task 採 **bite-sized step** 寫法，2-5 分鐘一步。

````markdown
## Task X·n: <任務名稱>

**Files:**
- Create: `exact/path/to/file.ext`
- Modify: `exact/path/to/existing.ext`
- Test: `tests/exact/path/to/test.ext`

- [ ] **Step 1: 寫失敗測試**

```<lang>
<完整可貼上的測試 code>
```

- [ ] **Step 2: 驗證測試失敗**

Run: `<完整 shell 指令>`
Expected: FAIL（<具體錯誤訊息>）

- [ ] **Step 3: 實作**

```<lang>
<完整可貼上的實作 code>
```

- [ ] **Step 4: 驗證測試通過**

Run: `<指令>`
Expected: PASS

- [ ] **Step 5: 靜態檢查**

Run: `<指令>`
Expected: 0 error

- [ ] **Step 6: 等使用者驗證後 commit**

```bash
git add <exact files>
git commit -m "<type>: <subject>"
```
````

### Task 設計要點

- **路徑要精確**：所有 `Create / Modify / Test` 列 exact 相對路徑
- **Code 要完整**：每個 step 有 code block 時必須是可直接貼上的完整內容，不能寫「類似 Task X」「填入 ...」
- **指令要具體**：`Run:` 後面必須是可直接貼上執行的完整指令（含 `cd` 若需要）
- **預期輸出要明確**：FAIL 要說失敗訊息，PASS 不用多話
- **Commit message 要 type 分開**：一個 task 只產生一個 type 的 commit；若涉及多 type（例如 feat + docs），拆成連續兩個 task

## 6. 群組驗收節點

每個字母群組結尾用醒目標記：

```markdown
---

**🛑 群組 X 驗收節點** — 停下等使用者驗證 <本群組交付物>。

<若需要使用者手動驗收，附 CMD 格式驗收指引>

```cmd
REM 驗收指令
cd backend
.venv\Scripts\python.exe ...
```

---
```

Web 自動模式下此節點忽略（連續執行到下一群組）。

## 7. 完成後段落

固定收尾：

```markdown
## 完成後

Phase N 全部 <n> tasks 結束。停下等使用者指示是否進入 Phase N+1。依 Phase 轉換 SOP，下一 Phase 計畫待使用者明確指示後才撰寫。
```

---

## No Placeholders 原則

寫 plan 時**禁止**以下句式（都屬於 plan failure）：

- 「TBD / TODO / 之後補 / 實作時再決定」
- 「適當處理錯誤 / 加上驗證 / 處理 edge case」（沒有具體 code）
- 「為上述寫測試」（沒有實際測試 code）
- 「類似 Task N」（工程師可能跳著讀，code 要重複）
- 只描述要做什麼、沒給 code 或指令
- 引用未在任何 task 定義過的型別 / 函式 / 欄位

## Self-Review Checklist

寫完 plan 後逐項檢查：

### 1. Spec coverage
- [ ] 逐一掃過 spec 相關段落，每個需求都能指到一個 task 實作
- [ ] 列出漏掉的需求，補 task
- [ ] 「不包含」清單有對應 Phase 編號，避免未來迷失

### 2. Placeholder scan
- [ ] 搜尋上面「No Placeholders」清單的句式
- [ ] 所有 code block 可直接貼上執行
- [ ] 所有 `Run:` 指令可直接貼上執行

### 3. Type consistency
- [ ] 後續 task 用到的型別 / 函式 / 欄位命名，與前面 task 定義一致
- [ ] API endpoint 路徑在 backend task 與 frontend task 一致
- [ ] Schema 欄位名稱在 DB model、Pydantic、TS types 間一致

### 4. Commit atomicity
- [ ] 每個 task 的 `git commit` 只有一個 type（feat/fix/docs 不混）
- [ ] `git add` 列出的檔案與該 task `Files:` 段落一致
- [ ] subject 沒有 scope 括號

### 5. 群組邊界
- [ ] 每個字母群組結尾都有 🛑 驗收節點
- [ ] 群組劃分合理（B 不依賴 G 尚未做的東西）

---

## 給 Web Session 的提醒

Claude Code Web session 無 `superpowers:writing-plans` skill 可用，請依本模板手動撰寫。寫完後執行 self-review，完成才 commit plan 本身，再進入實作。
