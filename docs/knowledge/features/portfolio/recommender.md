---
domain: features/portfolio/recommender
updated: 2026-04-15
related: [weights.md, ../../domain/scoring.md]
---

# 組合推薦

## 目的

依風格產出持股配置與權重，供 `/portfolios` 頁呈現。

## 現行實作（Phase 3）

- **候選池**：讀 `scores` 最新 calc_date 所有 row，排除 total_score=None
- **Top 30**：按風格加權總分排序取前 30
- **產業分散**：同產業最多 5 檔
- **最終持股**：取前 10 檔
- **權重**：softmax(total / 20)，單檔 cap 30%，超出者平均分配到未 cap 檔
- **三組**：conservative / balanced / aggressive，balanced 標 `is_top_pick=true`
- **expected_yield**：目前 None（待股利資料接入）
- **risk_score**：`100 - 平均 quality_score`

## 關鍵檔案

- [backend/src/alpha_lab/analysis/portfolio.py](../../../../backend/src/alpha_lab/analysis/portfolio.py)
- [backend/src/alpha_lab/api/routes/portfolios.py](../../../../backend/src/alpha_lab/api/routes/portfolios.py)
- [frontend/src/pages/PortfoliosPage.tsx](../../../../frontend/src/pages/PortfoliosPage.tsx)
- [frontend/src/components/portfolio/PortfolioTabs.tsx](../../../../frontend/src/components/portfolio/PortfolioTabs.tsx)

## 修改時注意事項

- 改參數（TOP_N、MAX_PER_INDUSTRY、FINAL_HOLDINGS、MAX_WEIGHT）→ 檔頂常數
- `is_top_pick` 目前硬編碼為 `style == 'balanced'`；若要動態判定需改 `generate_portfolio` 並引入市場訊號
- 組合儲存、追蹤、回測留 Phase 6
