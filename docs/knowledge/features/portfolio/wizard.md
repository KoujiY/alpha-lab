---
domain: features/portfolio/wizard
updated: 2026-04-18
related: [recommender.md, weights.md, ../../architecture/report-cache.md]
---

# 加入組合兩步 Wizard（Phase 9）

## 目的

把「加入組合」的權重決策從 inline popover 黑箱（「新持股 10%、其餘等比稀釋」直接 POST）改成顯性化兩步流程：讓使用者先挑基底組合、再預覽權重表並可逐檔微調、最後才確認建立。

## 現行實作

### UI 結構

- **入口**：`StockActions` 的「加入組合」按鈕 open `AddToPortfolioWizard`（shadcn `Dialog`）
- **Step 1（`wizard-step-1`）**：列出 `listSavedPortfolios()` 回傳的已儲存組合；空列表顯示「先到 /portfolios 儲存」
- **Step 2（`wizard-step-2`）**：
  - 呼叫 `getSavedPortfolio(baseId)` 拿 detail
  - 以 `buildMergedHoldings({ existing, symbol, name, delta: 0.1 })` 產出預設合併（新股 10%、其他等比稀釋）
  - 顯示權重表（代號 / 名稱 / 權重 % 手動 input）
  - 每列 `<input type="number">` `onChange` 呼叫 `rebalanceAfterEdit(preview, symbol, pct/100)`：其他檔等比縮放到剩餘空間
  - `SoftLimitWarningList` 即時顯示 `checkSoftLimits(previewHoldings)` 結果
  - `wizard-confirm` disabled 條件：`!isWeightSumValid(previewHoldings)` 或 mutation pending
- **確認流程**：呼叫 `probeBaseDate(symbols)`，若 `today_available=false` 彈 `BaseDateConfirmDialog`（與 Phase 7B.3 共用）；否則直接 `saveRecommendedPortfolio` 並帶 `parent_id = baseDetail.id`

### Soft limit warning

- 規則定義在 `lib/softLimits.ts`（`SOFT_LIMITS.MAX_HOLDINGS=20` / `MAX_SINGLE_WEIGHT=0.4` / `MIN_SINGLE_WEIGHT=0.005`）
- Warning code：`too_many_holdings` / `single_weight_too_high` / `weight_too_small`
- **非阻擋**：只顯示琥珀色警告條，使用者仍可按確認儲存
- 同時在 `PortfoliosPage.handleSaveClick` 前 pre-check：有警告 → 彈 `soft-limit-dialog` 讓使用者「仍要儲存」或「取消」

### 權重 re-normalize（`rebalanceAfterEdit`）

```
editedWeight 夾到 [0, 1]
若 holdings.length === 1：強制 weight = 1
其他 holdings 權重總和 = otherSum
  - otherSum > 0：每檔新 weight = 原 weight / otherSum * (1 - editedWeight)
  - otherSum = 0：remainder 平均分給其他 holdings
```

保證 `Σ weight - 1 < 1e-6`（`isWeightSumValid` 容忍閾值）。

## 關鍵檔案

- [frontend/src/components/portfolio/AddToPortfolioWizard.tsx](../../../../frontend/src/components/portfolio/AddToPortfolioWizard.tsx)
- [frontend/src/components/portfolio/SoftLimitWarningList.tsx](../../../../frontend/src/components/portfolio/SoftLimitWarningList.tsx)
- [frontend/src/lib/weightAdjust.ts](../../../../frontend/src/lib/weightAdjust.ts)
- [frontend/src/lib/softLimits.ts](../../../../frontend/src/lib/softLimits.ts)
- [frontend/src/lib/portfolioMerge.ts](../../../../frontend/src/lib/portfolioMerge.ts) — `buildMergedHoldings` 提供 wizard step 2 的初始合併
- [frontend/src/components/stock/StockActions.tsx](../../../../frontend/src/components/stock/StockActions.tsx) — wizard 入口
- [frontend/src/pages/PortfoliosPage.tsx](../../../../frontend/src/pages/PortfoliosPage.tsx) — soft limit pre-check
- [frontend/tests/lib/weightAdjust.test.ts](../../../../frontend/tests/lib/weightAdjust.test.ts)
- [frontend/tests/lib/softLimits.test.ts](../../../../frontend/tests/lib/softLimits.test.ts)
- [frontend/tests/e2e/portfolio-wizard.spec.ts](../../../../frontend/tests/e2e/portfolio-wizard.spec.ts) — 兩步流程 / soft limit / back button
- [frontend/tests/e2e/stock-actions.spec.ts](../../../../frontend/tests/e2e/stock-actions.spec.ts) — wizard + BaseDateConfirmDialog 整合

## 修改時注意事項

- **testid 命名**：wizard 內部 `wizard-step-1` / `wizard-step-2` / `wizard-back` / `wizard-cancel` / `wizard-confirm` / `wizard-row-<symbol>` / `wizard-weight-input-<symbol>` / `wizard-sum` / `wizard-warning-<code>` / `wizard-input-invalid` / `wizard-sum-invalid` / `wizard-auto-normalize` 都是 E2E 的錨；改前要同步搬 E2E
- **保留的對外 testid**：`add-to-portfolio`（StockActions 按鈕）、`pick-portfolio-${id}`（step 1 每一列）、`save-confirm-dialog` / `save-confirm-cancel` / `save-confirm-proceed`（BaseDateConfirmDialog）不得改
- **Soft limit 閾值調整**：改 `SOFT_LIMITS` 常數會影響 wizard 與 PortfoliosPage 兩處；同時要看 `tests/lib/softLimits.test.ts` 的邊界測資是否需要更新
- **wizard 不負責建立全新組合**：目前 `AddToPortfolioWizard` 只支援「以既有組合為基底」；想支援「建立全新組合」要擴 step 1 並新增一條空 holdings 初始化路徑
- **wizard 關閉時清 state**：`useEffect(() => { if (!open) reset }, [open])` 一定要保留，否則連續開兩次會帶上次 state
- **手動覆寫 input 的 re-normalize 有一瞬間不穩定**：使用者連續快速敲打鍵盤時，每個 onChange 都做一次全表縮放；暫不 debounce（1 行 /次 很快），未來如果效能痛點出現可用 `useDeferredValue`
- **編輯狀態單一化**：Phase 9 補丁後 wizard 不再維護 `weightInputs` map，只記目前正在編輯的那格（`editing = { symbol, raw }`）；其他行一律從 `previewHoldings` 格式化顯示。這避免「字串態」與「數值態」漂移；代價是「失焦後自動把 raw 存入 previewHoldings」這件事改由 `handleWeightBlur` 清掉 editing 來觸發重新格式化
- **自動補正按鈕（`wizard-auto-normalize`）**：當使用者連續編輯導致 `isWeightSumValid` 回 false（目前 1e-6 容忍足夠，理論上不會觸發；但若加 hard limit clamp 之後可能），按鈕會呼叫 `normalizeToOne` 等比縮放。sum 為 0（所有權重打成 0）時 disabled，避免除以零
- **非數字輸入**：`"" / "." / NaN` 類輸入會顯示 `wizard-input-invalid` 琥珀提示條但不觸發 re-normalize，其他列權重保持不動（避免閃爍）
- **PortfoliosPage 的 soft limit pre-check 不阻擋**：Soft limit 只是顧問角色，Phase 9 spec 明確要求不得 hard block；若未來要加 hard limit，要另外分一個 validation 層，不要混入 `checkSoftLimits`
