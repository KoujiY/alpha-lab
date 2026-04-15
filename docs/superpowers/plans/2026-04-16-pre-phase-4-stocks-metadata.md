# Pre-Phase 4 Step 0: stocks 表公司基本資料同步

Phase 1/1.5 殘留：`stocks` 表目前只有 collector 隱性建立的 placeholder（`name=symbol`、`industry=null`、`listed_date=null`）。組合推薦的產業分散限制與前端顯示的公司名稱都受影響。此 step 獨立於 Phase 4 主題之外，作為 Phase 4 暖身 task；完成後再進 Phase 4 正題。

## 範圍

- 新 collector：TWSE OpenAPI `v1/opendata/t187ap03_L`（上市公司基本資料）
- 新 JobType：`twse_stock_info`
- Upsert 更新既有 `stocks` row 的 `name` / `industry` / `listed_date`（不覆寫其他欄位、不 delete placeholder）
- 接入 `scripts/daily_collect.py`
- 知識庫 + `data-flow.md` JobType 表

**不包含**：上櫃（otc）、興櫃、已下市公司；歷史公司名變更保留。

## Tasks

### Task 0.1：Collector + Schema + 測試

**Files:**
- Create: `backend/src/alpha_lab/collectors/twse_stock_info.py`
- Create: `backend/src/alpha_lab/schemas/stock_info.py`
- Create: `backend/tests/collectors/test_twse_stock_info.py`
- Create: `backend/tests/fixtures/twse_t187ap03_L_sample.json`

**Steps:**

- [ ] Fixture：sample 3-5 檔（2330、2317、2454 等）JSON，欄位含公司代號、簡稱、產業別、上市日期
- [ ] Pydantic schema `StockInfo`（symbol, name, industry, listed_date）
- [ ] 失敗測試 → `fetch_stock_info` 回傳 list[StockInfo]（解析欄位名多候選）
- [ ] 實作 collector（`httpx` + truststore，跟既有 pattern 一致）
- [ ] 測試：3 個 case（正常、欄位缺失、空 payload）
- [ ] `ruff check . && mypy src && pytest tests/collectors/test_twse_stock_info.py`
- [ ] 使用者驗收指引 + 「0.1 OK」後 commit

### Task 0.2：Upsert + Job 接線

**Files:**
- Modify: `backend/src/alpha_lab/collectors/runner.py`（新 `upsert_stock_info`）
- Modify: `backend/src/alpha_lab/jobs/types.py`（加 `TWSE_STOCK_INFO`）
- Modify: `backend/src/alpha_lab/jobs/service.py`（加 dispatch 分支）
- Create: `backend/tests/collectors/test_stock_info_upsert.py`

**Steps:**

- [ ] `upsert_stock_info(session, rows)` — 對既有 row 做 UPDATE（name / industry / listed_date），不存在才 INSERT
- [ ] Test：既有 placeholder 被更新、新 symbol 被插入、無效 row 略過
- [ ] `_dispatch` 加 `TWSE_STOCK_INFO` 分支
- [ ] 全靜態 + pytest
- [ ] 移除 `runner.py` docstring 的 TODO 註解（公司基本資料同步已完成）
- [ ] 使用者驗收指引 + 「0.2 OK」後 commit

### Task 0.3：daily_collect 整合 + 知識庫

**Files:**
- Modify: `backend/scripts/daily_collect.py`
- Modify: `docs/knowledge/architecture/data-flow.md`（JobType 表加一行）
- Create: `docs/knowledge/collectors/twse-stock-info.md`

**Steps:**

- [ ] `daily_collect.py` 加 `_run_stock_info()` 呼叫，放在最前面（其他 collector 可依賴 `stocks` 有 name/industry）
- [ ] 知識庫文件
- [ ] 本機 smoke：跑 `python -m scripts.daily_collect --symbols 2330,2454` 驗證 stocks 表 name/industry/listed_date 被填入
- [ ] 「0.3 OK」後 commit

## 🛑 Step 0 驗收節點

使用者回報「Step 0 驗證通過」後才進 Phase 4 主題規劃。

## Web 執行備註

- Task 0.1 / 0.2 全程可在 web 做（sandbox bash 跑 pytest 即可）
- Task 0.3 最後一步「本機 smoke」需切回本機環境執行
- Push 節奏：每個 task 完成 + 使用者 OK 後 commit，但不主動 push，等 Step 0 全部完成再一起 push
