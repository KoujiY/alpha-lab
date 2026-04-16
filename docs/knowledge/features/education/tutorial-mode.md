---
domain: features/education
updated: 2026-04-16
related: [tooltip.md, l2-panel.md, reasons.md]
---

# 教學密度切換 TutorialMode（Phase 6）

## 目的

讓使用者依熟悉度切換教學密度，避免「新手需要提示、老手覺得吵」兩極體驗。實作 spec §15 Phase 6 交付物之一。

## 現行實作

- **三段模式**（依序循環 `full → compact → off → full`）：
  - `full`：完整教學。`TermTooltip` hover 顯示 L1、點擊開 L2；`HoldingsTable` 顯示「理由」欄。
  - `compact`：隱藏 L1 hover 提示；但若 `l2TopicId` 存在，`<abbr>` 仍可點擊開 L2（保留深入學習入口）。
  - `off`：`TermTooltip` 直接 render `children`，不加底線、不可互動；`HoldingsTable` 完全隱藏「理由」欄（標題 + 儲存格 + 展開列）。
- **Context**：`frontend/src/contexts/TutorialModeContext.ts` 定義 `TutorialMode` type、`TutorialModeContext`、`useTutorialMode` hook；provider 在 `TutorialModeProvider.tsx`。
- **持久化**：`localStorage['alpha-lab:tutorial-mode']` 儲存 `"full" | "compact" | "off"`，初始化時 `readInitialMode()` 讀回；每次 mode 變動 `useEffect` 寫回。
- **預設 full**：初次載入、localStorage 被清、值不合法都回到 `full`。
- **無 Provider 時 NOOP**：`useTutorialMode()` 在沒有 Provider 時返回 `{ mode: "full", setMode: noop, cycle: noop }`，對齊 `useL2Panel` 的慣例 → 單元測試可以不包 Provider 直接測。
- **Toggle UI**：`TutorialModeToggle` 是 header 右上的 pill 按鈕，`data-mode=<mode>`、`data-testid=tutorial-mode-toggle`；標籤依 mode 變為「完整教學 / 精簡 / 關閉」，aria-label 同步反映當前密度。
- **AppLayout 巢套順序**：`TutorialModeProvider > L2PanelProvider > app tree`。TutorialMode 在外是因為 TermTooltip 需要同時讀兩個 Context。

## 關鍵檔案

- [frontend/src/contexts/TutorialModeContext.ts](../../../../frontend/src/contexts/TutorialModeContext.ts) — type、context、hook、NOOP 預設
- [frontend/src/contexts/TutorialModeProvider.tsx](../../../../frontend/src/contexts/TutorialModeProvider.tsx) — state + localStorage sync
- [frontend/src/components/TutorialModeToggle.tsx](../../../../frontend/src/components/TutorialModeToggle.tsx) — header pill 按鈕
- [frontend/src/components/TermTooltip.tsx](../../../../frontend/src/components/TermTooltip.tsx) — 依 mode 分支 render
- [frontend/src/components/portfolio/HoldingsTable.tsx](../../../../frontend/src/components/portfolio/HoldingsTable.tsx) — `showReasons` 條件渲染
- [frontend/src/layouts/AppLayout.tsx](../../../../frontend/src/layouts/AppLayout.tsx) — Provider 巢套 + Toggle 掛載
- [frontend/tests/components/TutorialModeContext.test.tsx](../../../../frontend/tests/components/TutorialModeContext.test.tsx) — 5 個單元測
- [frontend/tests/e2e/tutorial-mode.spec.ts](../../../../frontend/tests/e2e/tutorial-mode.spec.ts) — 循環 + 持久化 + 標籤 E2E

## 修改時注意事項

- **新加教學元件**要尊重 mode：在元件頂部 `const { mode } = useTutorialMode();`，並按照「full / compact / off」三段決定 render。預設在 off 模式就「完全隱藏或退化成純文字」。
- **Toggle 按鈕 Phase 8 會換 icon button**（見 spec §15），但 `data-testid="tutorial-mode-toggle"` 與 `data-mode` 屬性要保留以維持 E2E。
- **不可在 provider 外面掛依賴 mode 的元件**：Provider 目前在 `AppLayout` 最外層，所有 route 都拿得到。若日後要把某頁移出 AppLayout（例如純 modal），要自己包 `TutorialModeProvider` 或預期 NOOP 預設。
- **localStorage key 改動**：改 `STORAGE_KEY` 會讓舊使用者的偏好重置；若要遷移要寫 migration 讀舊 key → 寫新 key → 刪舊 key。
- **E2E 避免用 `addInitScript` 清 localStorage**：`addInitScript` 在每次 page init（含 reload）都會跑，會打壞持久化測試。Playwright 每個 test 本來就是獨立 context，localStorage 預設為空。
- **mode 套到其他教學元件的順序**：之後要擴充到 `ReasonsList` / L2 主動彈出 / 推薦理由預設展開等行為時，先更新本檔「現行實作」的三段定義表，再動 code。
