---
domain: domain/factors
updated: 2026-04-15
related: [scoring.md, ../features/portfolio/recommender.md]
---

# 多因子指標

## 目的

定義四因子（Value / Growth / Dividend / Quality）各自的指標與計算公式。

## 現行實作（Phase 3）

| 因子 | 指標 | 來源 | 方向 |
|------|------|------|------|
| Value | PE | price.close / Σ(income.eps × 4Q) | 越低越佳 |
| Value | PB | 目前 None（缺 shares_outstanding） | — |
| Growth | 營收 YoY | 近 12M revenue / 前 12M revenue | 越高越佳 |
| Growth | EPS YoY | 近 4Q EPS 和 / 前 4Q EPS 和 | 越高越佳 |
| Dividend | 當期殖利率 | 目前 None（資料來源待補） | 越高越佳 |
| Quality | ROE | Σ(net_income 4Q) / total_equity | 越高越佳 |
| Quality | 毛利率 | Σ(gross_profit 4Q) / Σ(revenue 4Q) | 越高越佳 |
| Quality | 負債比 | total_liabilities / total_assets | 越低越佳 |
| Quality | FCF | Σ(operating_cf 4Q)（未扣 CapEx） | 越高越佳 |

## 關鍵檔案

- [backend/src/alpha_lab/analysis/factor_value.py](../../../backend/src/alpha_lab/analysis/factor_value.py)
- [backend/src/alpha_lab/analysis/factor_growth.py](../../../backend/src/alpha_lab/analysis/factor_growth.py)
- [backend/src/alpha_lab/analysis/factor_dividend.py](../../../backend/src/alpha_lab/analysis/factor_dividend.py)
- [backend/src/alpha_lab/analysis/factor_quality.py](../../../backend/src/alpha_lab/analysis/factor_quality.py)
- [backend/src/alpha_lab/analysis/normalize.py](../../../backend/src/alpha_lab/analysis/normalize.py)

## 修改時注意事項

- 新增指標 → 在對應 factor module 的 snapshot dict 加 key、在 `pipeline.build_snapshot` 填值
- 調整方向（高/低為佳） → 選用 `percentile_rank` 或 `percentile_rank_inverted`
- Dividend 與 PB 目前缺資料來源；Phase 4/5 補時同步更新此表
