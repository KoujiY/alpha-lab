---
domain: collectors/twse-stock-info
updated: 2026-04-16
related: [twse.md, mops.md, ../architecture/data-flow.md, ../architecture/data-models.md]
---

# TWSE 上市公司基本資料 Collector

## 目的

補 `stocks` 表的 `name` / `industry` / `listed_date` 三欄。Phase 1/1.5 的 collector
只建 placeholder（`name=symbol`、其餘 NULL），組合推薦的「產業分散限制」與前端顯示
的公司名稱都會受影響；Pre-Phase 4 Step 0 以獨立 collector 同步基本資料。

## 現行實作（Pre-Phase 4 Step 0 完成）

### 端點

| 用途 | URL | 模組 |
|------|-----|------|
| 上市公司基本資料 | `https://openapi.twse.com.tw/v1/opendata/t187ap03_L` | `collectors/twse_stock_info.py` |

### 已實作函式

- `fetch_stock_info(symbols=None) -> list[StockInfo]` — 全上市或指定代號子集
- `runner.upsert_stock_info(session, rows) -> int` — 對既有 row 做 UPDATE
  （name / industry / listed_date 全覆寫），不存在則 INSERT 完整資料

### 欄位名候選

TWSE OpenAPI 命名偶有調整，collector 採多候選逐個嘗試：

| 目標欄位 | 候選 keys |
|---------|-----------|
| symbol | `公司代號`、`證券代號` |
| name | `公司簡稱`、`公司名稱`、`證券名稱` |
| industry | `產業別`、`產業類別`、`產業` |
| listed_date | `上市日期`、`上市日`、`公司上市日期` |

實作位於 `twse_stock_info._SYMBOL_KEYS` 等模組級 tuple，需要擴充時加在末尾即可。

### 民國日期解析

`_parse_roc_date` 支援三種格式：

- 7 碼 `YYYMMDD`（含前導 0，如 `0800206` = 民國 80 年 02 月 06 日 = 1991-02-06）
- 6 碼 `YYMMDD`（民國 100 以下的舊格式，部分舊資料源出現）
- `YYY/MM/DD` 或 `YYY-MM-DD` 分隔形式

無法解析（空字串、`-`、格式不符、日期不合法）一律回 `None`，不拋例外。

### Upsert 行為

- 既有 `Stock` row（含 Phase 1 留下的 placeholder，`name=symbol`）→ UPDATE
  `name` / `industry` / `listed_date`；不碰其他欄位（例如後續 Phase 若在 stocks
  表加欄位，此函式不會覆寫）
- 新 symbol → INSERT 完整資料（不走 `_ensure_stock` placeholder 路徑）
- `symbol` 或 `name` 為空字串 → 略過（collector 已先過濾，upsert 層作防禦）
- 相同資料重複呼叫為 idempotent：不會重複插入、欄位結果相同

## Job 整合

- `JobType.TWSE_STOCK_INFO`（value: `"twse_stock_info"`）
- `_dispatch` 分支：`params = {"symbols": list[str] | None}`；結果 summary
  `"upserted N stock info rows"`
- `scripts/daily_collect.py` 把 `_run_one("TWSE stock info", TWSE_STOCK_INFO, ...)`
  放在最前面執行，後續 collector 若遇新 symbol 會看到正式 name / industry

## 資料範圍限制

- **僅上市（sii）**：端點 `t187ap03_L` 不含上櫃（otc）、興櫃、已下市公司
- 歷史公司名變更保留：TWSE OpenAPI 僅回最新狀態，歷史沿革不在此抓
- 上櫃公司基本資料若未來要加，端點可能是 `t187ap03_R`（OTC）或走 TPEx OpenAPI，
  需另一支 collector（欄位名可能不同）

## 關鍵檔案

- [backend/src/alpha_lab/collectors/twse_stock_info.py](../../../backend/src/alpha_lab/collectors/twse_stock_info.py)
- [backend/src/alpha_lab/schemas/stock_info.py](../../../backend/src/alpha_lab/schemas/stock_info.py)
- [backend/src/alpha_lab/collectors/runner.py](../../../backend/src/alpha_lab/collectors/runner.py)（`upsert_stock_info`）
- [backend/tests/collectors/test_twse_stock_info.py](../../../backend/tests/collectors/test_twse_stock_info.py)
- [backend/tests/collectors/test_stock_info_upsert.py](../../../backend/tests/collectors/test_stock_info_upsert.py)
- [backend/tests/fixtures/twse_t187ap03_L_sample.json](../../../backend/tests/fixtures/twse_t187ap03_L_sample.json)
- [backend/scripts/daily_collect.py](../../../backend/scripts/daily_collect.py)

## 修改時注意事項

- 新增 / 擴充欄位候選：直接在模組級 `_*_KEYS` tuple 末尾加，collector 會逐個嘗試
- 若 TWSE 改欄位命名造成 fixture 不再對齊實際 payload，請用 curl / smoke 腳本確認
  並更新 fixture + `_*_KEYS` 候選；knowledge base 需同步
- `backfill_industry.py`（Phase 1 暫行方案，依靜態 YAML 更新）可視為 fallback；
  若 OpenAPI 端點異動或被 WAF 擋，仍可跑該腳本補 industry
- 歷史公司名 / 產業別變更：OpenAPI 只回最新狀態；若未來要追歷史，需另存
  `stock_history` 表或類似結構（非本 Step 範圍）
