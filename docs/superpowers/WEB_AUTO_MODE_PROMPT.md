# Web Auto-Mode 開工 Prompt

> 當 Phase 實作要在 Claude Code Web session 以無人值守方式執行時，使用者直接把下方 prompt template 複製到 Web session 當作第一則訊息。把 `<N>` 與 `<name>` 替換成實際 Phase 編號與主題。

## 使用情境

- 使用者本機不方便長時間盯著實作（例如出門、休息）
- 希望整個 Phase 完成後收到 PR，自己本機 review + merge
- 本機協作規範（`.claude/CLAUDE.md` 的「手動驗收後才 commit」「字母群組停下等驗收」）在無人值守場景不適用，需要明確覆蓋

## Prompt Template

複製以下區塊貼到 Web session：

---

在 `feature/phase-<N>-<name>` 分支進行 Phase `<N>` 實作。本 session 為 Web 自動模式，不等人工驗收，完成後發 PR 交給我本機 review。

遵循 `docs/superpowers/PLAN_TEMPLATE.md`，先讀 `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` 撰寫 Phase `<N>` plan 到 `docs/superpowers/plans/<today>-phase-<N>-<name>.md`，commit 後才開始實作。

【每個 task 驗收規則】每個 task 結束前必須通過：
- backend: `ruff check .` + `mypy src` + 對應 `pytest` 全綠
- frontend: `tsc --noEmit` + `pnpm lint` + 對應 `vitest` 全綠

不通過不得 commit；通過了就 commit（不等人工），進下一個 task。

【覆蓋 `.claude/CLAUDE.md`】
- 本 session 不走「手動驗收後 commit」流程（無人值守）
- 每個 task commit 分開、按 type 拆（feat/fix/docs），訊息完整帶 why
- 中文亂碼掃描照做（`grep -r "��"` 排除 node_modules）
- 知識庫 `docs/knowledge/` 對應條目該更新就更新（同 commit）

【遇阻】不 hang、不 stop：
- 技術問題卡 30 分鐘仍無進展 → 在 PR draft 寫下 blocker 並跳過該 task 繼續後面能做的
- Spec 有歧義 → 選最保守解讀、PR 描述標註「待確認」
- 絕不擅自改 spec、不擅自 push 到 main、不 merge

【結束】
- 全部 task 完成或全部能做的都做完 → 開 PR 到 main
- PR 標題：`Phase <N>: <name>`
- PR 描述必須含：
  * 做了什麼（每個 task 一句）
  * 沒做或延後（blocker、待確認項）
  * 本機驗收 checklist（我本機要跑什麼指令才能確認 UI/E2E 沒炸，CMD 格式）
  * 風險點（單元測試覆蓋不到的地方）
- 不 merge，等我本機 pull 後驗收 + merge

---

## 與本機模式的差異

| 項目 | 本機互動模式（預設） | Web 自動模式 |
|------|---------------------|-------------|
| Commit 時機 | 使用者「驗證通過」後 | 靜態 + 單測通過即 commit |
| 群組驗收節點 | 🛑 停下等驗收 | 無視、連續執行 |
| 遇到 blocker | 詢問使用者 | 記錄到 PR、跳過繼續 |
| Phase 結束 | 打 tag、停下等下 Phase 指示 | 開 PR 到 main、等 review |
| 驗收指引 shell | CMD 格式給使用者 | 寫在 PR 描述裡（仍 CMD 格式） |

## 維護指引

- `.claude/CLAUDE.md` 或 `PLAN_TEMPLATE.md` 更新時，檢查此 prompt 的覆蓋清單是否仍完整
- 若新增本機獨有規範（例如新的 hook），要在「覆蓋」段落補上對應的關閉 / 替代指示
- Phase 名稱 `<name>` 建議用 spec 第 15 節 Phase 表的主題（如 `portfolio-recommender`、`tutorial-system`）
