---
domain: collectors/twse
updated: 2026-04-15
related: [mops.md, ../architecture/data-flow.md, ../architecture/data-models.md]
---

# TWSE Collector

## 目的

抓取台灣證券交易所（TWSE）公開資料。

## 現行實作（Phase 1）

### 端點

| 用途 | URL | 備註 |
|------|-----|------|
| 個股日成交資訊 | `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=YYYYMMDD&stockNo=SYMBOL&response=json` | 以月為單位回傳該月所有交易日 |

### 已實作函式

- `fetch_daily_prices(symbol, year_month) -> list[DailyPrice]`
  - 回傳當月所有交易日的 OHLCV
  - 民國日期自動轉西元
  - `stat != "OK"` 會拋 `ValueError`

### 已知坑

- TWSE 對短時間多次請求會擋 IP；smoke 測試需手動節流
- 成交股數含逗號，需去逗號後 int
- 漲跌價差欄位有 `+`/`-` 符號，Phase 1 未解析（未入庫）
- ROC 年份轉換：`115 + 1911 = 2026`

### Phase 1.5 規劃新增

- 三大法人買賣超（T86 報表）
- 融資融券（MI_MARGN）
- 除權息（TWTB4U / dividend table）

## 關鍵檔案

- [backend/src/alpha_lab/collectors/twse.py](../../../backend/src/alpha_lab/collectors/twse.py)
- [backend/src/alpha_lab/schemas/price.py](../../../backend/src/alpha_lab/schemas/price.py)
- [backend/tests/collectors/test_twse.py](../../../backend/tests/collectors/test_twse.py)
- [backend/scripts/smoke_twse.py](../../../backend/scripts/smoke_twse.py)

## 修改時注意事項

- 改 URL 或參數：同步更新測試的 `respx.mock` 路徑
- 新增欄位：擴充 `DailyPrice` schema + `PriceDaily` model + `upsert_daily_prices`
- TWSE 若改回傳格式（欄位順序變動），`data` index 存取邏輯要改
