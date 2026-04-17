---
domain: collectors/yahoo
updated: 2026-04-18
related: [twse.md, README.md, ../architecture/processed-store.md]
---

# Yahoo Finance Collector

## 目的

TWSE 抓不到或失敗時的價格備援來源（僅 OHLCV 日資料）。

## 現行實作（Phase 7B.1 完成）

### 端點

`GET https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>.TW?period1=&period2=&interval=1d`

- symbol 需加 `.TW` 後綴（上市）；上櫃 `.TWO` 未在 7B.1 支援
- 非官方 API、無 auth；ToS 只允許個人非商業使用——工具定位吻合
- **風險：Yahoo 隨時可能拔掉這個端點**，失敗時抬頭會是 4xx/5xx 或 `error.description = "Not Found"`

### Fallback 政策

在 `collectors/_fallback.py::should_fallback_to_yahoo`：

| 例外 | Fallback? | 理由 |
|------|-----------|------|
| `TWSERateLimitError` | ❌ | WAF 擋 IP，Yahoo 治標不治本 |
| `ValueError("沒有符合條件")` | ❌ | 假日/盤中，Yahoo 也沒資料 |
| 其他 `ValueError`（TWSE 非 OK stat） | ✅ | TWSE 端實際故障 |
| `httpx.HTTPStatusError / TimeoutException / TransportError` | ✅ | 網路層問題 |
| 未知例外 | ❌ | 保守上拋 |

### 記錄來源

`prices_daily.source` 欄位：`"twse"` / `"yahoo"` / `NULL`（Phase 7B.1 前的舊 row）。`upsert_daily_prices` 規則：新 row `source=None` 時**不覆寫**既有值。

## 關鍵檔案

- [backend/src/alpha_lab/collectors/yahoo.py](../../../backend/src/alpha_lab/collectors/yahoo.py)
- [backend/src/alpha_lab/collectors/_fallback.py](../../../backend/src/alpha_lab/collectors/_fallback.py)
- [backend/src/alpha_lab/jobs/service.py](../../../backend/src/alpha_lab/jobs/service.py)（TWSE_PRICES / TWSE_PRICES_BATCH / YAHOO_PRICES dispatch）
- [backend/tests/collectors/test_yahoo.py](../../../backend/tests/collectors/test_yahoo.py)
- [backend/tests/collectors/test_fallback.py](../../../backend/tests/collectors/test_fallback.py)

## 修改時注意事項

- Yahoo 回傳 timestamp 是 UTC epoch，必須以 `Asia/Taipei` (UTC+8) 轉日期，避免收盤日被算成前一天
- `indicators.quote[0]` 內任一欄位 `None` 需整列捨棄（盤中斷訊）
- 新增欄位：需同步更新 `DailyPrice` schema 與 `upsert_daily_prices`
- 若端點失效，優先檢查 User-Agent 是否被擋；其次考慮導回 `yfinance` 套件做備援的備援
