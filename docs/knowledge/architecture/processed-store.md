---
domain: architecture/processed-store
updated: 2026-04-18
related: [../collectors/yahoo.md, data-models.md]
---

# `data/processed/` 計算後指標層

## 目的

讓 Claude Code 分析時不必重算技術指標與基本面比率：job 跑完就把「最新一日」結果存成 JSON，Claude 直接讀 `data/processed/indicators/2330.json`、`data/processed/ratios/2330.json`。

## 格式選擇

**JSON 非 parquet**：

- Claude Code 直接讀 `data/processed/`，純文字無門檻
- parquet 需 `pyarrow` 80MB wheel，單機工具不值得
- 每 symbol 單檔、atomic rename 寫入（`.tmp` → `os.replace`）

## 檔案配置

```
data/processed/
├── indicators/
│   └── <symbol>.json    # MA5/MA20/MA60/RSI14/ratio_52w_high/volatility_ann
└── ratios/
    └── <symbol>.json    # PE/PB/ROE/gross_margin/debt_ratio/fcf_ttm
```

## 更新時機（Phase 7B.1）

- `PROCESSED_INDICATORS` job（手動觸發或 `daily_collect.py` 尾端自動）
- `PROCESSED_RATIOS` job（同上）
- 排程自動化屬於 Phase 7B.2

## 關鍵檔案

- [backend/src/alpha_lab/storage/processed_store.py](../../../backend/src/alpha_lab/storage/processed_store.py)
- [backend/src/alpha_lab/analysis/indicators.py](../../../backend/src/alpha_lab/analysis/indicators.py)
- [backend/src/alpha_lab/analysis/ratios.py](../../../backend/src/alpha_lab/analysis/ratios.py)
- [backend/tests/storage/test_processed_store.py](../../../backend/tests/storage/test_processed_store.py)

## 修改時注意事項

- 新增指標：同步更新 `IndicatorSnapshot` / `RatioSnapshot` dataclass；`write_*_json` 自動序列化 asdict
- 不要改成「每日歷史序列都落檔」——檔案大小會爆；要分析歷史序列直接讀 SQLite
- 刪掉這層前先確認 Claude Code SOP 沒依賴 `data/processed/`
