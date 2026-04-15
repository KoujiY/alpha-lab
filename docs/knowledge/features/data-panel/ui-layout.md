---
domain: features/data-panel
updated: 2026-04-15
related: [overview.md]
---

# 個股頁 UI 布局

## 版面順序（由上而下）

1. **StockHeader**：symbol + name + industry + listed_date
2. **PriceChart**（Recharts LineChart）：近 60 日收盤走勢
3. **KeyMetrics**：最新收盤 / 最新 EPS / PE（算出） / 最新期別
4. **RevenueSection**（Recharts BarChart）：近 12 個月營收
5. **FinancialsSection**（表格）：近 4 季財報（營收、毛利、營業利益、淨利、EPS、股東權益）
6. **InstitutionalSection**（多系列 BarChart）：近 20 日外資/投信/自營商買賣超
7. **MarginSection**：最新一日融資融券 6 欄卡片
8. **EventsSection**：近 20 筆重大訊息列表

## 元件原則

- 每個 section 元件接受自己需要的資料 props，**不自行發 API**（由 StockPage 傳 overview.XXX）
- 空資料 → 顯示 `尚無XXX資料` 占位（由各 section 元件自行處理）
- 所有 section 用 `<section aria-label="XX">` 包裹，E2E 以 `getByRole('region', { name: 'XX' })` 取得

## 關鍵檔案

- [frontend/src/pages/StockPage.tsx](../../../frontend/src/pages/StockPage.tsx)
- [frontend/src/components/stock/](../../../frontend/src/components/stock/)

## 修改時注意事項

- 新增 section 時記得加 `aria-label` 並更新 E2E `stock-page.spec.ts`
- Chart 統一用 Recharts。K 線延到後續 Phase 視需求改用 lightweight-charts
- 金額單位：表格用「百萬」，股數類用「張」，都在 header 上標示避免混淆
