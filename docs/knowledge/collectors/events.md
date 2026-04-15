---
domain: collectors/events
updated: 2026-04-15
related: [twse.md, mops.md, ../architecture/data-flow.md]
---

# 重大訊息 Collector

## 目的

抓取上市公司即時重大訊息，供個股頁、事件回顧與因子計算使用。

## 現行實作（Phase 1.5 完成）

### 端點

| 用途 | URL | 模組 |
|------|-----|------|
| 上市即時重大訊息 | `https://openapi.twse.com.tw/v1/opendata/t187ap04_L` | `collectors/mops_events.py` |

### 已實作函式

- `fetch_latest_events(symbols=None) -> list[Event]` — 最新一批即時重訊
  - `symbols=None`：回傳全體
  - `event_datetime` 由「發言日期」+「發言時間」合併

### 資料模型與查重

- `events` table：主鍵 autoincrement `id`（同公司同時刻可能多則重訊）
- 查重：以 `(symbol, event_datetime, title)` 三元組判斷是否已存在，已存則 skip（不 overwrite）
- 原則：「補漏不覆寫」— collector 同一 event 再次抓到不會重複寫入也不會蓋掉既有資料

### 真實 API 的欄位怪癖（實作時踩過的坑）

1. **Key 帶前後空白**：TWSE OpenAPI 偶有 key 名稱含前後空白（如 `"主旨 "`、`" 公司代號"`）。實作進入迴圈前先對每個 item 做一次 key 正規化：
   ```python
   norm = {str(k).strip(): v for k, v in item.items()}
   ```
   後續一律操作 `norm`。
2. **日期格式偵測**：「發言日期」欄位可能是 **ROC 7 碼**（`"1150410"`，民 115 年 4 月 10 日）或 **西元 8 碼**（`"20260410"`）。以字串長度 + `isdigit()` 區分：
   - len == 8 且全數字：視為西元
   - len >= 5：視為 ROC（前面數碼為年、最後 4 碼為月日）
3. **時間欄位長度不定**：「發言時間」可能 4/5/6 碼（如 `"93020"` 代表 09:30:20），一律 `zfill(6)` 再切片。
4. **欄位名稱可能分歧**：主旨 / 符合條款 / 說明的 key 偶爾會以不同名出現；實作以 `.get(primary_key) or .get(fallback_key) or ""` 處理，fallback 候選包含 `發言日期 / 發言日 / 資料日期`、`發言時間 / 時間`、`主旨 / 標題` 等。

### 端點侷限

- MOPS 原站「即時重訊」頁 `t05st01` 需 POST form + HTML 解析，**不推薦**；本實作改用 TWSE OpenAPI 彙總端點
- OpenAPI `t187ap04_L` 只回「最新一批」，不回全歷史；歷史事件需爬 mopsov 的對照表
- 上櫃（OTC / TPEx）公司的重訊未包含；Phase 2+ 再評估加入 TPEx 對應端點

### Phase 2+ 規劃

- 上櫃（TPEx）重訊
- 歷史事件回補
- 事件分類（財務、營運、股權、訴訟…）供因子使用

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops_events.py](../../../backend/src/alpha_lab/collectors/mops_events.py)
- [backend/src/alpha_lab/schemas/event.py](../../../backend/src/alpha_lab/schemas/event.py)
- [backend/tests/collectors/test_mops_events.py](../../../backend/tests/collectors/test_mops_events.py)
- [backend/scripts/smoke_mops_events.py](../../../backend/scripts/smoke_mops_events.py)

## 修改時注意事項

- 改欄位映射：同步更新 respx 測試的 sample payload，並保留 key 帶空白 / ROC 與西元日期兩種格式的測試案例（回歸保險）
- 擴充查重規則：`upsert_events` 以 `(symbol, event_datetime, title)` 判斷；若 title 會在事後補充，改以 `(symbol, event_datetime, event_type)`
- 加入 OTC 重訊：新模組 `collectors/tpex_events.py`，不要把兩源混入同一函式
