---
domain: features/portfolio/weights
updated: 2026-04-15
related: [recommender.md, ../../domain/factors.md]
---

# 風格權重

## 目的

四因子在不同風格下的加權比例。

## 現行實作（Phase 3）

| Style | Value | Growth | Dividend | Quality |
|-------|-------|--------|----------|---------|
| conservative | 0.20 | 0.10 | 0.35 | 0.35 |
| balanced | 0.25 | 0.25 | 0.25 | 0.25 |
| aggressive | 0.15 | 0.50 | 0.05 | 0.30 |

## 關鍵檔案

- [backend/src/alpha_lab/analysis/weights.py](../../../../backend/src/alpha_lab/analysis/weights.py)

## 修改時注意事項

- 改權重必須保持總和 = 1；對應單元測試會檢查
- 新增 style → 加入 `STYLE_WEIGHTS`、`STYLE_LABELS`、`Style` Literal、前端 `STYLE_ORDER`
