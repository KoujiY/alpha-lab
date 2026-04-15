---
domain: domain/scoring
updated: 2026-04-15
related: [factors.md, ../features/portfolio/weights.md]
---

# 評分流程

## 目的

將四因子 0-100 分數組合為單一總分，儲存至 `scores` 表供組合推薦使用。

## 現行實作（Phase 3）

- **橫截面歸一化**：單一 `calc_date` 所有 symbol 一起排名、轉百分位
- **Ties**：同值共享平均 rank
- **None**：不參與排名、結果保留 None
- **風格權重加權**：`scores.total_score` 儲存 balanced 權重總分；recommend 時 runtime 以 conservative/aggressive 權重重算
- **None 因子處理**：`weighted_total` 略過 None，剩餘權重再正規化

## 關鍵檔案

- [backend/src/alpha_lab/analysis/pipeline.py](../../../backend/src/alpha_lab/analysis/pipeline.py)
- [backend/src/alpha_lab/analysis/weights.py](../../../backend/src/alpha_lab/analysis/weights.py)
- [backend/scripts/compute_scores.py](../../../backend/scripts/compute_scores.py)

## 觸發方式

- CLI：`python scripts/compute_scores.py --date YYYY-MM-DD`
- API：`POST /api/jobs/collect` with `job_type='score'`

## 修改時注意事項

- 加新因子 → `Score` model 加欄位、`pipeline` 填、`weighted_total` 加參數、`STYLE_WEIGHTS` 調整
- 改歸一化策略 → 改 `normalize.py`（目前為百分位；若改 z-score 要注意 score 範圍不再是 0-100）
- `scores` 表只存當日快照；歷史分數多次 upsert 會覆寫同日 row
