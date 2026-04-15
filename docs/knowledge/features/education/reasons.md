---
domain: features/education/reasons
updated: 2026-04-17
related: [tooltip.md, ../portfolio/recommender.md, ../../domain/scoring.md]
---

# 推薦理由（Phase 4）

## 目的

spec §10「三段密度教學」裡的推薦理由。Phase 4 走**靜態模板**：從因子分數 + 閾值 + style 條件組字串。Phase 7 再考慮接 Claude API 產生動態、個股化描述。

## 現行實作

- **進入點**：`analysis/reasons.py::build_reasons(breakdown, style) -> list[str]`
- **規則**：
  - 固定第一條為 style 特性句（conservative / balanced / aggressive 各一句）
  - 每個因子分數 ≥ 70 → 出現一條正向描述
  - 每個因子分數 ≤ 30 → 出現一條風險提示
  - 中段（>30、<70）→ 不生句
  - `None` 因子直接略過
- **呼叫處**：`analysis/portfolio.py::generate_portfolio` 每檔 holding 都會呼叫一次，結果塞入 `Holding.reasons`
- **Schema**：`schemas/portfolio.py::Holding.reasons: list[str]`（default `[]`）

## 閾值常數

- `HIGH_THRESHOLD = 70.0`
- `LOW_THRESHOLD = 30.0`
- 調整閾值 → 改 `analysis/reasons.py` 檔頂兩個常數 + 更新本檔數字

## 文案模板

共 10 條（4 因子 × 2 方向 + 3 個 style 句）。修改時在 `_FACTOR_HIGH_TEMPLATES`、`_FACTOR_LOW_TEMPLATES`、`_STYLE_LINES` 三張表更新並同步測試 assertions。

## 關鍵檔案

- [backend/src/alpha_lab/analysis/reasons.py](../../../../backend/src/alpha_lab/analysis/reasons.py)
- [backend/src/alpha_lab/analysis/portfolio.py](../../../../backend/src/alpha_lab/analysis/portfolio.py)
- [backend/src/alpha_lab/schemas/portfolio.py](../../../../backend/src/alpha_lab/schemas/portfolio.py)
- [frontend/src/components/portfolio/HoldingsTable.tsx](../../../../frontend/src/components/portfolio/HoldingsTable.tsx)

## 修改時注意事項

- 文案以中文為主、每句 20-40 字，避免太長
- 修改模板時**同步更新** `tests/analysis/test_reasons.py` 的關鍵字 assertions（如「體質穩健」、「估值偏貴」）
- 切勿把動態外部資訊（新聞、事件）塞進靜態模板，那屬於 Phase 7 LLM 範疇
- 若新增第五個因子，需更新 reasons.py 的 factor 迭代順序 + 模板表
