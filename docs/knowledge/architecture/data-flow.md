---
domain: architecture
updated: 2026-04-15
related: [data-models.md, ../collectors/twse.md, ../collectors/mops.md]
---

# 資料流

## 目的

描述「外部資料源 → collector → SQLite → API → UI」完整路徑。

## 現行實作（Phase 1）

### 端到端流程

```
使用者/排程
   │  POST /api/jobs/collect
   ▼
FastAPI route (api/routes/jobs.py)
   │  create_job (jobs 表 status=pending)
   │  background_tasks.add_task(run_job_sync)
   ▼
Job runner (jobs/service.py)
   │  status=running
   │  dispatch by JobType →
   ▼
Collector (collectors/twse.py or mops.py)
   │  httpx.AsyncClient → TWSE/MOPS API
   │  回傳 list[DailyPrice] or list[MonthlyRevenue]
   ▼
Upsert runner (collectors/runner.py)
   │  SQLAlchemy session → SQLite (data/alpha_lab.db)
   ▼
Job runner
   │  status=completed, result_summary 寫回 jobs 表
   ▼
使用者 GET /api/jobs/status/{id} 輪詢
```

### Session 管理原則

- 每個「邏輯工作單元」用一次 `session_scope()` context manager
- Job runner 把 read（取參數）、write（更新 status）、執行 collector 分成獨立 session，避免長交易
- Collector 本身不碰 DB，純函式 → 方便測試

### 錯誤處理

- Collector 拋例外 → `run_job_sync` 捕捉、寫 `job.error_message`、`status=failed`、**不** re-raise（背景任務不中斷 app）
- HTTP 錯誤 → `resp.raise_for_status()` 自然拋 `httpx.HTTPStatusError`
- 資料驗證錯誤 → Pydantic `ValidationError`，當成 collector 異常處理

## 關鍵檔案

- [backend/src/alpha_lab/jobs/service.py](../../../backend/src/alpha_lab/jobs/service.py)
- [backend/src/alpha_lab/collectors/runner.py](../../../backend/src/alpha_lab/collectors/runner.py)
- [backend/src/alpha_lab/api/routes/jobs.py](../../../backend/src/alpha_lab/api/routes/jobs.py)

## 修改時注意事項

- 新增 collector：
  1. 在 `collectors/` 新增模組
  2. 在 `jobs/types.py` 的 `JobType` 加一個值
  3. 在 `jobs/service.py::_dispatch` 加分支
  4. 在 `collectors/runner.py` 加對應 upsert
  5. 更新 `collectors/<source>.md` 知識庫
- 改 job 執行模型（例如要併發）：
  - 現在是 FastAPI BackgroundTasks（單程序），改 Celery/RQ 需同步改 `service.run_job_sync` 入口與 session factory 傳遞
- Phase 1.5 若要加排程：建議獨立 `backend/scripts/daily_collect.py`，由 OS cron 觸發，不走 API
