---
domain: collectors/twse
updated: 2026-04-15
related: [mops.md, events.md, ../architecture/data-flow.md, ../architecture/data-models.md]
---

# TWSE Collector

## 目的

抓取台灣證券交易所（TWSE）公開資料。

## 現行實作（Phase 1.5 完成）

### 端點總覽

| 用途 | URL | 模組 |
|------|-----|------|
| 個股日成交資訊 | `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=YYYYMMDD&stockNo=SYMBOL&response=json` | `collectors/twse.py` |
| 三大法人買賣超（T86） | `https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json` | `collectors/twse_institutional.py` |
| 融資融券餘額（MI_MARGN） | `https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=YYYYMMDD&selectType=ALL&response=json` | `collectors/twse_margin.py` |

### 已實作函式

- `fetch_daily_prices(symbol, year_month) -> list[DailyPrice]` — 個股當月 OHLCV
- `fetch_institutional_trades(trade_date, symbols=None) -> list[InstitutionalTrade]` — 某交易日全體或指定代號
- `fetch_margin_trades(trade_date, symbols=None) -> list[MarginTrade]` — 某交易日全體或指定代號

### STOCK_DAY（日成交）

- 民國日期自動轉西元：`115 + 1911 = 2026`
- 成交股數含千分位逗號，需 `_parse_int` 處理
- `stat != "OK"` 會拋 `ValueError`
- 漲跌價差欄位含 `+`/`-` 符號，Phase 1 未解析入庫

### T86（三大法人）

- **欄位順序會隨年份變動**：2018 年後多出「外資自營商」獨立欄位；實作以 `_find_idx(fields, name)` 從欄位名稱查 index，避開硬編位置
- TWSE **實際回傳的 field 名稱與文件不一致**（B1 修復期間發現）：`外陸資買進股數(不含外資自營商)`、`外資自營商買賣超股數` 等名稱含全形括號；逐字匹配且需提供多個候選 key fallback
- 買賣超單位為「股」；應用層需自行換算張數（÷1000）

### MI_MARGN（融資融券）

payload 結構為多層 tables：
- `tables[*]` 每個 table 具有 `title`（含「信用交易彙總」）、`groups`（欄位群組標題，如 `融資`/`融券`）、`fields`（欄位名稱，融資與融券**子欄位名稱相同**，只能靠 groups 區分）、`data`（逐列資料）
- `groups` 項目形如 `{"span": 6, "title": "融資"}`，`start` 不一定提供，需按 span 累加推導；前面通常有 `{"title":"股票","span":2}` 之類的前置識別群組
- `_find_credit_table` 兼容 `tables` 與 `creditList` 兩種包裹格式（C1 修復期間發現舊版 payload）
- `_resolve_group_indices(groups, fields, group_title)` 把某個 group（融資 / 融券）的欄位索引投射到原始 `fields` index，才能正確取值
- 融資融券單位為「張」

### 通用坑

- TWSE 對短時間多次請求會擋 IP；smoke 測試需手動節流（1 分鐘以上）
- ROC 年份轉換：`115 + 1911 = 2026`
- 實作以名稱查欄位優於靠 index 位置（格式變動容忍度較高）

### Phase 2+ 規劃新增

- 除權息（TWTB4U / dividend history）
- 逐筆日交易歷史（盤中輪廓）
- 個股公司基本資料正式同步

## 關鍵檔案

- [backend/src/alpha_lab/collectors/twse.py](../../../backend/src/alpha_lab/collectors/twse.py)
- [backend/src/alpha_lab/collectors/twse_institutional.py](../../../backend/src/alpha_lab/collectors/twse_institutional.py)
- [backend/src/alpha_lab/collectors/twse_margin.py](../../../backend/src/alpha_lab/collectors/twse_margin.py)
- [backend/src/alpha_lab/schemas/price.py](../../../backend/src/alpha_lab/schemas/price.py)
- [backend/src/alpha_lab/schemas/institutional.py](../../../backend/src/alpha_lab/schemas/institutional.py)
- [backend/src/alpha_lab/schemas/margin.py](../../../backend/src/alpha_lab/schemas/margin.py)
- [backend/tests/collectors/test_twse.py](../../../backend/tests/collectors/test_twse.py)
- [backend/tests/collectors/test_twse_institutional.py](../../../backend/tests/collectors/test_twse_institutional.py)
- [backend/tests/collectors/test_twse_margin.py](../../../backend/tests/collectors/test_twse_margin.py)
- [backend/scripts/smoke_twse.py](../../../backend/scripts/smoke_twse.py)
- [backend/scripts/smoke_twse_institutional.py](../../../backend/scripts/smoke_twse_institutional.py)
- [backend/scripts/smoke_twse_margin.py](../../../backend/scripts/smoke_twse_margin.py)

## 修改時注意事項

- 改 URL 或參數：同步更新對應 respx.mock 路徑
- 新增欄位：擴充 schema + model + upsert runner 三處
- TWSE 若改回傳格式：優先用 `_find_idx` / `_find_credit_table` / `_resolve_group_indices` 等名稱查詢式存取，而非 index 位置
- MI_MARGN 若新增子欄位：同步更新 `groups` title 對照（`MARGIN_GROUP` / `SHORT_GROUP`）與 `fields` 查找表
