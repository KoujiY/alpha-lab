---
domain: domain/industry-tagging
updated: 2026-04-15
related: [../architecture/data-models.md]
---

# 產業分類

## 目的

替 `stocks.industry` 提供最小可行的映射，讓個股頁 header 與未來的篩選器（Phase 5）能用產業別分類。

## 現行實作（Phase 2：最小）

- **映射來源**：`backend/src/alpha_lab/storage/industry_map.yaml` 手動維護 `{symbol: 產業}` 字典
- **Backfill**：`backend/scripts/backfill_industry.py` 讀 YAML，對 DB 已存在的 symbol 更新 `industry`；映射表沒有的 symbol 不動
- **不做**：自動從 TWSE 產業別檔案同步（未來擴充）

## 關鍵檔案

- [backend/src/alpha_lab/storage/industry_map.yaml](../../backend/src/alpha_lab/storage/industry_map.yaml)
- [backend/scripts/backfill_industry.py](../../backend/scripts/backfill_industry.py)

## 修改時注意事項

- 加新股票時：先 collector 抓到 `stocks` 表，再手動加映射、跑 backfill
- Phase 5（選股篩選器）會用到 `stocks.industry` 當過濾條件；若映射缺口大要先補
- 未來自動同步可參考 TWSE 產業類別 OpenAPI 或 MOPS 產業分類檔，屆時把此檔改成 fallback 來源
