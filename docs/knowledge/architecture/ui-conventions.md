---
domain: architecture
updated: 2026-04-17
related: [../features/tracking/overview.md, ../features/reports/viewer.md]
---

# UI 慣例

跨功能共用的前端 UI 模式與理由。Claude 新增 / 修改 UI 前應參考，避免重做已定型的共用元件。

## 目的

集中記錄 alpha-lab 前端的「約定俗成做法」：哪些模式已經選定、為什麼選這樣、什麼時候該沿用而非重新設計。這些決策多半來自使用者反饋或實作上踩到的坑，不讀文件很難從 codebase 反推出來。

## 現行慣例（Phase 6）

### 狀態回饋：顯式 popover 優於原生 `title=` tooltip

**決策**：按鈕的「動作進行中 / 完成 / 失敗」狀態，用**顯式 popover 面板**呈現，不用 `title=` HTML 屬性。

**理由**：

- 原生 `title=` tooltip 在 macOS 與部分瀏覽器不顯示 / hover 延遲過長，跨平台不可靠
- 使用者反饋：「按鈕本身沒有 tooltip，你確定有做這個功能嗎？」—— 證實 `title=` 在實務上形同沒做
- 顯式 popover 可以同時顯示較長的資訊（例：batch job 摘要、缺價 symbol 清單）而不被字元數限制

**典範**：[`NavUpdatePricesButton.tsx`](../../../frontend/src/components/NavUpdatePricesButton.tsx) — 按鈕下方 absolute-positioned 面板，有 ✕ 讓使用者手動關閉。

**什麼時候適用**：任何「按完按鈕需要使用者看見結果」的流程。即席資訊（例：純靜態說明）仍可用 `title=`。

### 「今日報價不齊」類確認 dialog：共用 `BaseDateConfirmDialog`

**決策**：涉及「prices_daily 今日可能不齊、需使用者確認是否以歷史日為基準」的流程，一律用共用元件 [`BaseDateConfirmDialog.tsx`](../../../frontend/src/components/portfolio/BaseDateConfirmDialog.tsx)。

**理由**：

- 這個檢查 + 確認模式有兩個以上觸發點（儲存推薦組合、加入組合），邏輯一致
- 統一訊息文字與互動語意，避免「這頁 dialog 跟那頁 dialog 講的不是同件事」
- 測試 ID `save-confirm-dialog` / `save-confirm-cancel` / `save-confirm-proceed` 跨頁一致，E2E 寫一次可重用

**什麼時候適用**：任何需要使用 `probeBaseDate` 的流程。新增觸發點時直接用 `<BaseDateConfirmDialog>`，不要另外做。

### 價格更新 job：共用 `useUpdatePricesJob` hook

**決策**：任何觸發 `twse_prices_batch` job 的 UI 一律用 [`useUpdatePricesJob`](../../../frontend/src/hooks/useUpdatePricesJob.ts) hook，不要在元件內直接呼叫 API + 輪詢。

**理由**：

- Polling 邏輯（2s interval、completed / failed 狀態轉換、invalidate queries）在多個觸發點一致，沒理由各自實作
- Hook 提供 `{state, run, reset}` 三元組介面，UI 元件只負責 button label / 狀態面板，不碰 job API
- 未來若要加指數退避、取消、併發控制，只改 hook 內部

**什麼時候適用**：任何觸發「多檔股票批次更新」的按鈕。單一檔的場景（例：stock page 強制補抓今天）目前沒有，但若要加也應該放進這個 hook。

### 收藏與偏好：localStorage 為主、不進 DB

**決策**：個人工具性質的 UI 偏好（收藏清單、教學密度模式）用 localStorage，不寫進後端。

**理由**：

- 單機個人工具，跨裝置同步需求為零
- 免去一整層 API + schema + migration 的開銷
- 清理 / reset 只要使用者 clear site data 即可

**典範**：`frontend/src/lib/favorites.ts`（收藏）、`frontend/src/contexts/TutorialModeContext.tsx`（教學密度）。

**什麼時候不適用**：需要跨裝置同步、需要後端做彙總統計、或需要權限控管的狀態。這些應該進 DB（例如 `portfolios_saved`）。

### Icon button 升級延後到 Phase 8

**決策**：列表 / 卡片 / 詳情頁的動作按鈕（收藏 ☆★、刪除、編輯等）目前用文字 button + emoji，不做 icon button。統一延到 Phase 8 UI 升級做。

**理由**：

- 現在用 Tailwind + 純 button，Phase 8 才會引入 shadcn/ui；提前做 icon button 是無謂的重工
- 功能正確性 > UI 拋光，Phase 6 的重點在把組合追蹤 / 教學開關 / 報告管理 的流程打通

**什麼時候適用**：任何新增動作按鈕（例如 Phase 6 收藏切換、刪除報告）都用文字 + emoji 即可，先保留 `data-testid` 名稱讓 Phase 8 升級能直接換 icon、E2E 不需要改。

## 關鍵檔案

- [frontend/src/components/NavUpdatePricesButton.tsx](../../../frontend/src/components/NavUpdatePricesButton.tsx)
- [frontend/src/components/portfolio/BaseDateConfirmDialog.tsx](../../../frontend/src/components/portfolio/BaseDateConfirmDialog.tsx)
- [frontend/src/hooks/useUpdatePricesJob.ts](../../../frontend/src/hooks/useUpdatePricesJob.ts)
- [frontend/src/contexts/TutorialModeContext.tsx](../../../frontend/src/contexts/TutorialModeContext.tsx)
- [frontend/src/lib/favorites.ts](../../../frontend/src/lib/favorites.ts)

## 修改時注意事項

- **新增「按下去會有異步狀態」的按鈕**：參考 `NavUpdatePricesButton` 做顯式 popover，不要只放 `title=`
- **新增涉及 base_date 檢查的儲存流程**：先 `probeBaseDate`、再視情況彈 `BaseDateConfirmDialog`，不要繞過這層直接 POST
- **新增批次 job 觸發 UI**：用 `useUpdatePricesJob`（或比照它做類似 hook），不要在元件內 inline polling
- **新增個人偏好選項**：優先考慮 localStorage；若最後決定進 DB，在 PR 描述或 commit message 寫清楚為什麼不用 localStorage
- **Phase 8 要動這些共用元件時**：icon button 化 + shadcn/ui 遷移應同時做，避免新舊元件並存
