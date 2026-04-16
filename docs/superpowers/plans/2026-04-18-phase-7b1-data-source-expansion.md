# Phase 7B.1：數據源擴充 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 TWSE 當 primary、Yahoo Finance 當 fallback 的價格數據管線接通；並把 Claude Code 真的會用到的「算好的技術指標 / 基本面比率」以 JSON 形式預先落檔到 `data/processed/`，讓分析流程不必每次重算。

**Architecture:**

- **Yahoo collector**：直接 `httpx` 打 Yahoo Finance Chart API（`https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>.TW`），不引入 `yfinance` 套件——`yfinance` 的確有 MIT licence 但整包相依 30+ 套件、維運風險高，我們只需要 OHLCV，直打 chart API 約 60 行解析。ToS 屬於「非商業個人用途」允許範圍內，備援角色合適。
- **Fallback 觸發條件**：**序列式**（TWSE → Yahoo），**非**並行。TWSE 明確失敗才 fallback，避免兩邊資料衝突/重複：
  - **Fallback**：`payload.stat` 為 `"查詢無資料"` / `"系統忙線中"` 等非 `OK` 且非「沒有符合條件」；HTTP 4xx/5xx、timeout、網路例外
  - **不 Fallback**：`TWSERateLimitError`（WAF 擋 IP，Yahoo 也擋不住要等）、`"沒有符合條件"`（假日/盤中，無意義再查）
  - **來源紀錄**：`prices_daily` 新增 `source` 欄位（`"twse"` / `"yahoo"` / 既有 row 為 `NULL`），未來爭議時可追溯
- **`data/processed/` 格式**：**JSON 非 parquet**。理由：(1) CLAUDE.md 明示 Claude Code 會直接讀 `data/processed/`，純文字最無障礙；(2) parquet 需額外引入 `pyarrow`（80MB wheel）不值得；(3) 每檔 symbol 單獨一檔，寫入是 atomic rename。命名規則：`data/processed/indicators/<symbol>.json`、`data/processed/ratios/<symbol>.json`。
- **更新時機**：新增 `PROCESSED_INDICATORS` / `PROCESSED_RATIOS` 兩個 JobType，手動觸發（可從前端「更新報價」按鈕延伸，也可 CLI）；**本 phase 不接排程**，排程屬於 7B.2 範圍。
- **新 JobTypes**：`YAHOO_PRICES`（明確指定抓 Yahoo，用於手動補資料 / 測試 / 或 TWSE 持續失敗時使用者手動切換）、`PROCESSED_INDICATORS`、`PROCESSED_RATIOS`。既有 `TWSE_PRICES` / `TWSE_PRICES_BATCH` 不變對外介面，在 dispatch 內部加 fallback 分支。
- **前端 impact**：**對既有頁面透明**。不新增 API、不新增頁，個股頁 / 追蹤頁照舊。未來若要讓使用者切換資料源或看到「這一天是 Yahoo 補的」提示，留待 Phase 8 UI 升級。本 phase 只在 backend 打地基。

**Tech Stack:** Python 3.11 + FastAPI、SQLAlchemy 2.x（SQLite）、Pydantic v2、httpx、pandas（已有，做 rolling 指標）、numpy、pytest + respx。

---

## File Structure

### 新增（backend）

- `backend/src/alpha_lab/collectors/yahoo.py` — Yahoo Chart API collector（`fetch_yahoo_daily_prices`）
- `backend/src/alpha_lab/collectors/_fallback.py` — TWSE → Yahoo fallback 決策工具（判斷例外類型是否該 fallback）
- `backend/src/alpha_lab/analysis/indicators.py` — 技術指標計算（MA5/20/60、RSI14、52 週高低比、年化波動率）
- `backend/src/alpha_lab/analysis/ratios.py` — 基本面比率計算（PE、PB placeholder、ROE、gross margin、debt ratio、FCF yield）
- `backend/src/alpha_lab/storage/processed_store.py` — `data/processed/*` 讀寫介面（`write_indicators_json` / `write_ratios_json`，atomic rename）
- `backend/tests/collectors/test_yahoo.py`
- `backend/tests/collectors/test_fallback.py`
- `backend/tests/analysis/test_indicators.py`
- `backend/tests/analysis/test_ratios.py`
- `backend/tests/storage/test_processed_store.py`
- `backend/tests/jobs/test_yahoo_prices_dispatch.py`
- `backend/tests/jobs/test_processed_jobs.py`
- `backend/scripts/smoke_yahoo.py`
- `docs/knowledge/collectors/yahoo.md`
- `docs/knowledge/architecture/processed-store.md`

### 修改（backend）

- `backend/src/alpha_lab/storage/models.py` — `PriceDaily` 新增 `source: str | None`
- `backend/src/alpha_lab/storage/init_db.py` — `add_column_if_missing(engine, "prices_daily", "source", "TEXT")`
- `backend/src/alpha_lab/schemas/price.py` — `DailyPrice` 新增 `source: str | None`
- `backend/src/alpha_lab/collectors/runner.py` — `upsert_daily_prices` 寫入 `source` 欄位；既有舊 row 若新 row `source=None` 時保留原值（don't overwrite to null）
- `backend/src/alpha_lab/jobs/types.py` — 新增 `YAHOO_PRICES` / `PROCESSED_INDICATORS` / `PROCESSED_RATIOS`
- `backend/src/alpha_lab/jobs/service.py` — 加三個新 dispatch 分支 + `TWSE_PRICES` / `TWSE_PRICES_BATCH` 內加 fallback 呼叫
- `backend/src/alpha_lab/config.py` — 新增 `yahoo_enabled: bool = True`、`processed_dir: Path = Path("data/processed")` 設定
- `backend/scripts/daily_collect.py` — 跑完 prices 後接一個 `PROCESSED_INDICATORS` job（若 `--symbols` 有指定；`--all` 不自動跑）
- `backend/tests/storage/test_init_db_migration.py` — 加 `prices_daily.source` migration 斷言
- `backend/tests/collectors/test_twse.py` — （若測過 `upsert_daily_prices`）補 `source="twse"` 斷言

### 文件更新

- `docs/knowledge/collectors/README.md` — 新增 `yahoo.md` 條目
- `docs/knowledge/collectors/twse.md` — 在「通用坑」下加「fallback 行為」說明
- `docs/knowledge/architecture/README.md` — 新增 `processed-store.md` 條目
- `docs/superpowers/specs/2026-04-14-alpha-lab-design.md` — 7B.1 狀態從「未開始」改「完成」，附摘要
- `docs/USER_GUIDE.md` — 新增「資料源 fallback」段落（1~2 段）+ 提到 `data/processed/` 供 Claude Code 讀取

---

## Task 1：`prices_daily.source` schema + migration

**Files:**
- Modify: `backend/src/alpha_lab/storage/models.py:38-51`
- Modify: `backend/src/alpha_lab/storage/init_db.py:11-24`
- Modify: `backend/src/alpha_lab/schemas/price.py`
- Test: `backend/tests/storage/test_init_db_migration.py`

- [ ] **Step 1：看現行 migration 測試長什麼樣**

Run: `ls backend/tests/storage/`
預期會看到 `test_init_db_migration.py` 與 `test_migrations.py`，Phase 7 已建立模式。

- [ ] **Step 2：寫 failing 測試 — migration 會補 `prices_daily.source` 欄位**

編輯 `backend/tests/storage/test_init_db_migration.py`，在檔尾附加：

```python
def test_init_db_adds_source_column_to_prices_daily(tmp_path, monkeypatch):
    """舊 DB（無 source 欄位）經 init_database 後補上 source TEXT。"""
    from sqlalchemy import Column, Date, Float, Integer, MetaData, String, Table, create_engine, inspect

    db_file = tmp_path / "legacy.db"
    engine_legacy = create_engine(f"sqlite:///{db_file}", future=True)
    meta = MetaData()
    Table(
        "prices_daily",
        meta,
        Column("symbol", String(10), primary_key=True),
        Column("trade_date", Date, primary_key=True),
        Column("open", Float, nullable=False),
        Column("high", Float, nullable=False),
        Column("low", Float, nullable=False),
        Column("close", Float, nullable=False),
        Column("volume", Integer, nullable=False),
    )
    # stocks 預先建起來滿足 FK（若其他測試共享 tmp_path 無 stocks 會整批失敗）
    Table(
        "stocks",
        meta,
        Column("symbol", String(10), primary_key=True),
        Column("name", String(64), nullable=False),
    )
    meta.create_all(engine_legacy)
    engine_legacy.dispose()

    monkeypatch.setenv("ALPHA_LAB_DB_URL", f"sqlite:///{db_file}")
    # 清快取：get_engine 用 lru_cache
    from alpha_lab.storage import engine as engine_mod
    engine_mod.get_engine.cache_clear()
    engine_mod.get_session_factory.cache_clear()

    from alpha_lab.storage.init_db import init_database
    init_database()

    engine_check = create_engine(f"sqlite:///{db_file}", future=True)
    cols = {c["name"] for c in inspect(engine_check).get_columns("prices_daily")}
    assert "source" in cols
```

- [ ] **Step 3：跑測試確認 RED**

Run: `cd backend && pytest tests/storage/test_init_db_migration.py::test_init_db_adds_source_column_to_prices_daily -v`
Expected: FAIL（`assert "source" in cols` 失敗，或 `source` 欄位還不存在）。

- [ ] **Step 4：更新 model**

編輯 `backend/src/alpha_lab/storage/models.py`，把 `PriceDaily`（約第 38-51 行）改成：

```python
class PriceDaily(Base):
    __tablename__ = "prices_daily"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str | None] = mapped_column(String(16), nullable=True)

    stock: Mapped[Stock] = relationship(back_populates="prices")
```

- [ ] **Step 5：更新 migration**

編輯 `backend/src/alpha_lab/storage/init_db.py`，在既有兩行 `add_column_if_missing` 後追加：

```python
    add_column_if_missing(engine, "prices_daily", "source", "TEXT")
```

- [ ] **Step 6：更新 Pydantic schema**

覆寫 `backend/src/alpha_lab/schemas/price.py`：

```python
"""日股價 Pydantic 模型。"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


PriceSource = Literal["twse", "yahoo"]


class DailyPrice(BaseModel):
    """單一股票單日 OHLCV。source 為選填：None 表示既有舊 row 未紀錄來源。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    trade_date: date
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: int = Field(..., ge=0)
    source: PriceSource | None = None
```

- [ ] **Step 7：再跑測試確認 GREEN**

Run: `cd backend && pytest tests/storage/test_init_db_migration.py -v`
Expected: PASS。

- [ ] **Step 8：靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 error。

- [ ] **Step 9：Commit**

```bash
cd g:/codingdata/alpha-lab
rtk git add backend/src/alpha_lab/storage/models.py backend/src/alpha_lab/storage/init_db.py backend/src/alpha_lab/schemas/price.py backend/tests/storage/test_init_db_migration.py
rtk git commit -m "feat: add prices_daily.source column for data source tracking"
```

---

## Task 2：Yahoo Chart API collector

**Files:**
- Create: `backend/src/alpha_lab/collectors/yahoo.py`
- Create: `backend/tests/collectors/test_yahoo.py`

- [ ] **Step 1：寫 failing 測試**

建立 `backend/tests/collectors/test_yahoo.py`：

```python
"""Yahoo Finance Chart API collector 測試。"""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from alpha_lab.collectors.yahoo import YahooFetchError, fetch_yahoo_daily_prices


CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_daily_prices_parses_chart_payload():
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "2330.TW"},
                    "timestamp": [1711929600, 1712016000],  # 2024-04-01, 2024-04-02 UTC
                    "indicators": {
                        "quote": [
                            {
                                "open": [720.0, 725.0],
                                "high": [728.0, 730.0],
                                "low": [718.0, 723.0],
                                "close": [725.0, 728.0],
                                "volume": [30000000, 28000000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))

    rows = await fetch_yahoo_daily_prices(
        symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
    )
    assert len(rows) == 2
    assert rows[0].symbol == "2330"
    assert rows[0].source == "yahoo"
    assert rows[0].close == pytest.approx(725.0)
    assert rows[0].volume == 30000000


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_drops_rows_with_null_fields():
    """Yahoo 偶爾在某些交易日回 null（盤中斷訊）— 應過濾整列。"""
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "2330.TW"},
                    "timestamp": [1711929600, 1712016000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [720.0, None],
                                "high": [728.0, 730.0],
                                "low": [718.0, 723.0],
                                "close": [725.0, None],
                                "volume": [30000000, 28000000],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))

    rows = await fetch_yahoo_daily_prices(
        symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
    )
    assert len(rows) == 1
    assert rows[0].trade_date == date(2024, 4, 1)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_raises_on_error_envelope():
    payload = {
        "chart": {
            "result": None,
            "error": {"code": "Not Found", "description": "No data"},
        }
    }
    respx.get(CHART_URL).mock(return_value=httpx.Response(200, json=payload))
    with pytest.raises(YahooFetchError, match="Not Found"):
        await fetch_yahoo_daily_prices(
            symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
        )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_yahoo_raises_on_http_5xx():
    respx.get(CHART_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(YahooFetchError):
        await fetch_yahoo_daily_prices(
            symbol="2330", start=date(2024, 4, 1), end=date(2024, 4, 2)
        )
```

- [ ] **Step 2：跑測試確認 RED**

Run: `cd backend && pytest tests/collectors/test_yahoo.py -v`
Expected: FAIL（ModuleNotFoundError：`alpha_lab.collectors.yahoo`）。

- [ ] **Step 3：實作 Yahoo collector**

建立 `backend/src/alpha_lab/collectors/yahoo.py`：

```python
"""Yahoo Finance Chart API collector（台股備援）。

用途：TWSE 失敗或查無資料時退而求其次的價格來源。
端點：GET https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.TW
      ?period1={epoch}&period2={epoch}&interval=1d

注意：
- 台股 symbol 需附 `.TW` 後綴（上市）；上櫃 `.TWO`（Phase 8 再處理）
- 回傳 timestamps 為 UTC epoch；收盤日期取當地（台北 UTC+8）日期
- indicators.quote[0] 內任一欄位為 None 表示該日沒收盤（盤中/假日），整列捨棄
- 這是 **非官方 API**，隨時可能被拿掉；失敗時上拋 YahooFetchError
"""

from __future__ import annotations

import ssl
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx
import truststore

from alpha_lab.config import get_settings
from alpha_lab.schemas.price import DailyPrice

YAHOO_BASE_URL = "https://query1.finance.yahoo.com"
CHART_PATH_TEMPLATE = "/v8/finance/chart/{symbol}.TW"

# Yahoo 回傳是 UTC；台北 = UTC+8
TAIPEI_TZ = timezone(timedelta(hours=8))


class YahooFetchError(RuntimeError):
    """Yahoo Chart API 明確失敗（error envelope 或 HTTP 非 2xx）。"""


def _build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _epoch_from_taipei_date(d: date, end_of_day: bool = False) -> int:
    t = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    dt = datetime.combine(d, t, tzinfo=TAIPEI_TZ)
    return int(dt.timestamp())


async def fetch_yahoo_daily_prices(
    symbol: str, start: date, end: date
) -> list[DailyPrice]:
    """抓取 [start, end] 區間的每日 OHLCV。

    Raises:
        YahooFetchError: Yahoo 回錯誤 envelope 或 HTTP 5xx/4xx
    """
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent}
    params = {
        "period1": _epoch_from_taipei_date(start),
        "period2": _epoch_from_taipei_date(end, end_of_day=True),
        "interval": "1d",
    }
    path = CHART_PATH_TEMPLATE.format(symbol=symbol)

    async with httpx.AsyncClient(
        base_url=YAHOO_BASE_URL,
        timeout=settings.http_timeout_seconds,
        headers=headers,
        verify=_build_ssl_context(),
    ) as client:
        resp = await client.get(path, params=params)
        if resp.status_code >= 400:
            raise YahooFetchError(
                f"Yahoo chart HTTP {resp.status_code} for {symbol}: {resp.text[:200]}"
            )
        payload = resp.json()

    chart = payload.get("chart") or {}
    err = chart.get("error")
    if err:
        code = err.get("code") or "Unknown"
        desc = err.get("description") or ""
        raise YahooFetchError(f"Yahoo chart error for {symbol}: {code} {desc}")

    result_list = chart.get("result") or []
    if not result_list:
        return []
    result = result_list[0]

    timestamps: list[int] = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    rows: list[DailyPrice] = []
    for i, ts in enumerate(timestamps):
        o = _get(opens, i)
        h = _get(highs, i)
        lo = _get(lows, i)
        c = _get(closes, i)
        v = _get(volumes, i)
        if any(x is None for x in (o, h, lo, c, v)):
            continue
        trade_date = datetime.fromtimestamp(ts, tz=TAIPEI_TZ).date()
        rows.append(
            DailyPrice(
                symbol=symbol,
                trade_date=trade_date,
                open=float(o),
                high=float(h),
                low=float(lo),
                close=float(c),
                volume=int(v),
                source="yahoo",
            )
        )
    return rows


def _get(arr: list[Any], i: int) -> Any:
    return arr[i] if i < len(arr) else None
```

- [ ] **Step 4：跑測試確認 GREEN**

Run: `cd backend && pytest tests/collectors/test_yahoo.py -v`
Expected: PASS（3 個 test）。

- [ ] **Step 5：smoke script（選用但強烈建議）**

建立 `backend/scripts/smoke_yahoo.py`：

```python
"""真打一次 Yahoo Chart API，確認真實端點仍可用。"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from alpha_lab.collectors.yahoo import fetch_yahoo_daily_prices


async def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="2330")
    p.add_argument("--days", type=int, default=5)
    args = p.parse_args(argv)

    end = date.today()
    start = end - timedelta(days=args.days)
    rows = await fetch_yahoo_daily_prices(args.symbol, start=start, end=end)
    for r in rows:
        print(f"{r.trade_date} O={r.open} H={r.high} L={r.low} C={r.close} V={r.volume} src={r.source}")
    print(f"[total {len(rows)} rows]")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
```

- [ ] **Step 6：Commit**

```bash
rtk git add backend/src/alpha_lab/collectors/yahoo.py backend/tests/collectors/test_yahoo.py backend/scripts/smoke_yahoo.py
rtk git commit -m "feat: add Yahoo Finance Chart API collector"
```

---

## Task 3：`upsert_daily_prices` 寫入 source 欄位

**Files:**
- Modify: `backend/src/alpha_lab/collectors/runner.py:66-93`
- Test: `backend/tests/collectors/test_runner_source.py`（新增）

- [ ] **Step 1：寫 failing 測試**

建立 `backend/tests/collectors/test_runner_source.py`：

```python
"""upsert_daily_prices 對 source 欄位的行為。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.collectors.runner import upsert_daily_prices
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.storage.models import Base, PriceDaily


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)()


def test_upsert_writes_source(session: Session) -> None:
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 1),
                open=700.0,
                high=705.0,
                low=698.0,
                close=702.0,
                volume=1_000_000,
                source="twse",
            )
        ],
    )
    session.commit()
    row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 1)})
    assert row is not None
    assert row.source == "twse"


def test_upsert_yahoo_source(session: Session) -> None:
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 2),
                open=700.0,
                high=705.0,
                low=698.0,
                close=702.0,
                volume=1_000_000,
                source="yahoo",
            )
        ],
    )
    session.commit()
    row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 2)})
    assert row is not None
    assert row.source == "yahoo"


def test_upsert_none_source_does_not_overwrite_existing(session: Session) -> None:
    """既有 row 已有 source，新 row source=None 時不可覆寫為 null。"""
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 3),
                open=700.0, high=705.0, low=698.0, close=702.0,
                volume=1_000_000, source="twse",
            )
        ],
    )
    session.commit()
    upsert_daily_prices(
        session,
        [
            DailyPrice(
                symbol="2330",
                trade_date=date(2026, 4, 3),
                open=701.0, high=706.0, low=699.0, close=703.0,
                volume=1_100_000, source=None,
            )
        ],
    )
    session.commit()
    row = session.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 3)})
    assert row is not None
    assert row.close == 703.0  # OHLCV 有被更新
    assert row.source == "twse"  # source 未被 overwrite 為 null
```

- [ ] **Step 2：跑測試確認 RED**

Run: `cd backend && pytest tests/collectors/test_runner_source.py -v`
Expected: FAIL（`row.source` 為 None，因為現行 `upsert_daily_prices` 沒寫入 source）。

- [ ] **Step 3：更新 runner**

編輯 `backend/src/alpha_lab/collectors/runner.py`，把 `upsert_daily_prices` 改成：

```python
def upsert_daily_prices(session: Session, rows: list[DailyPrice]) -> int:
    """upsert 日股價。回傳寫入筆數（新增 + 更新）。

    `source` 欄位寫入規則：
    - 新 row 有 `source` → 寫入
    - 新 row `source=None` 且 DB 已有 row → 保留既有 source，不覆寫為 null
    - 新 row `source=None` 且 DB 無 row（新增） → source 寫 None
    """
    _ensure_stocks(session, (row.symbol for row in rows))
    count = 0
    for row in rows:
        existing = session.get(
            PriceDaily, {"symbol": row.symbol, "trade_date": row.trade_date}
        )
        if existing is None:
            session.add(
                PriceDaily(
                    symbol=row.symbol,
                    trade_date=row.trade_date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                    source=row.source,
                )
            )
        else:
            existing.open = row.open
            existing.high = row.high
            existing.low = row.low
            existing.close = row.close
            existing.volume = row.volume
            if row.source is not None:
                existing.source = row.source
        count += 1
    return count
```

- [ ] **Step 4：跑測試確認 GREEN**

Run: `cd backend && pytest tests/collectors/test_runner_source.py -v`
Expected: 3 PASS。

- [ ] **Step 5：更新既有 TWSE collector 回傳 `source="twse"`**

編輯 `backend/src/alpha_lab/collectors/twse.py`，在 `fetch_daily_prices` 的 `DailyPrice(...)` 建構處加 `source="twse"`：

```python
        results.append(
            DailyPrice(
                symbol=symbol,
                trade_date=_roc_date_to_iso(row[0]),
                open=_parse_float(row[3]),
                high=_parse_float(row[4]),
                low=_parse_float(row[5]),
                close=_parse_float(row[6]),
                volume=_parse_int(row[1]),
                source="twse",
            )
        )
```

- [ ] **Step 6：跑既有 TWSE collector 測試確保沒壞**

Run: `cd backend && pytest tests/collectors/test_twse.py -v`
Expected: PASS（既有測試不檢查 source，應無影響；若有失敗表示對 `DailyPrice` 驗證到 `source`，檢查是否要擴測試斷言 `source="twse"`）。

- [ ] **Step 7：Commit**

```bash
rtk git add backend/src/alpha_lab/collectors/runner.py backend/src/alpha_lab/collectors/twse.py backend/tests/collectors/test_runner_source.py
rtk git commit -m "feat: persist price data source in upsert_daily_prices"
```

---

## Task 4：Fallback 決策工具與 TWSE→Yahoo fallback 整合

**Files:**
- Create: `backend/src/alpha_lab/collectors/_fallback.py`
- Create: `backend/tests/collectors/test_fallback.py`
- Modify: `backend/src/alpha_lab/jobs/service.py`（`TWSE_PRICES` / `TWSE_PRICES_BATCH` 分支）
- Test: `backend/tests/jobs/test_yahoo_prices_dispatch.py`（涵蓋 dispatch）

- [ ] **Step 1：寫 fallback 決策 helper 測試**

建立 `backend/tests/collectors/test_fallback.py`：

```python
"""fallback 決策：什麼例外該 fallback 到 Yahoo。"""

from __future__ import annotations

import httpx
import pytest

from alpha_lab.collectors._fallback import should_fallback_to_yahoo
from alpha_lab.collectors._twse_common import TWSERateLimitError


def test_waf_error_does_not_fallback():
    assert should_fallback_to_yahoo(TWSERateLimitError("waf")) is False


def test_no_data_holiday_does_not_fallback():
    assert should_fallback_to_yahoo(ValueError("TWSE returned non-OK stat: 很抱歉，沒有符合條件的資料")) is False


def test_other_value_error_falls_back():
    assert should_fallback_to_yahoo(ValueError("TWSE returned non-OK stat: 系統忙線中")) is True


def test_http_error_falls_back():
    resp = httpx.Response(503, request=httpx.Request("GET", "https://x"))
    assert should_fallback_to_yahoo(httpx.HTTPStatusError("5xx", request=resp.request, response=resp)) is True


def test_timeout_falls_back():
    assert should_fallback_to_yahoo(httpx.TimeoutException("timeout")) is True


def test_unknown_exception_does_not_fallback():
    """未知例外保守處理：不 fallback，直接上拋。"""
    assert should_fallback_to_yahoo(RuntimeError("something else")) is False
```

- [ ] **Step 2：跑測試確認 RED**

Run: `cd backend && pytest tests/collectors/test_fallback.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3：實作 fallback helper**

建立 `backend/src/alpha_lab/collectors/_fallback.py`：

```python
"""TWSE → Yahoo fallback 決策。

設計原則：
- **WAF 錯誤不 fallback**：IP 被封，Yahoo 也治標不治本，該讓使用者等封鎖解除
- **「沒有符合條件」不 fallback**：那是假日/盤中，Yahoo 查也是空
- 其他 ValueError（TWSE 明確回錯誤 stat）、HTTP 4xx/5xx、timeout → fallback
- 未知例外 → 保守不 fallback，讓 caller decide
"""

from __future__ import annotations

import httpx

from alpha_lab.collectors._twse_common import TWSERateLimitError

_NO_DATA_MARKERS = ("沒有符合條件",)


def should_fallback_to_yahoo(exc: BaseException) -> bool:
    """判斷該例外類型是否該觸發 Yahoo fallback。"""
    if isinstance(exc, TWSERateLimitError):
        return False
    if isinstance(exc, ValueError):
        msg = str(exc)
        if any(m in msg for m in _NO_DATA_MARKERS):
            return False
        return True
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TimeoutException, httpx.TransportError)):
        return True
    return False
```

- [ ] **Step 4：跑測試確認 GREEN**

Run: `cd backend && pytest tests/collectors/test_fallback.py -v`
Expected: 6 PASS。

- [ ] **Step 5：寫 dispatch fallback 測試**

建立 `backend/tests/jobs/test_yahoo_prices_dispatch.py`：

```python
"""TWSE_PRICES dispatch 的 fallback 行為與 YAHOO_PRICES dispatch。"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.storage.models import Job, PriceDaily


@pytest.mark.asyncio
async def test_twse_prices_falls_back_to_yahoo_on_transient_error(session_factory):
    """TWSE 拋非 WAF ValueError → 自動 fallback Yahoo。最後 row.source == 'yahoo'。"""
    yahoo_rows = [
        DailyPrice(
            symbol="2330", trade_date=date(2026, 4, 10),
            open=700.0, high=705.0, low=698.0, close=702.0,
            volume=1_000_000, source="yahoo",
        )
    ]

    with session_factory() as s:
        job = create_job(s, job_type=JobType.TWSE_PRICES, params={"symbol": "2330", "year_month": "2026-04"})
        s.commit()
        job_id = job.id

    with patch("alpha_lab.jobs.service.fetch_daily_prices", new=AsyncMock(side_effect=ValueError("TWSE returned non-OK stat: 系統忙線中"))), \
         patch("alpha_lab.jobs.service.fetch_yahoo_daily_prices", new=AsyncMock(return_value=yahoo_rows)):
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "completed"
        assert done.result_summary is not None
        assert "yahoo" in done.result_summary
        row = s.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 10)})
        assert row is not None
        assert row.source == "yahoo"


@pytest.mark.asyncio
async def test_twse_prices_does_not_fallback_on_waf(session_factory):
    """WAF 錯誤直接 fail，不走 Yahoo。"""
    from alpha_lab.collectors._twse_common import TWSERateLimitError

    with session_factory() as s:
        job = create_job(s, job_type=JobType.TWSE_PRICES, params={"symbol": "2330", "year_month": "2026-04"})
        s.commit()
        job_id = job.id

    yahoo_mock = AsyncMock()
    with patch("alpha_lab.jobs.service.fetch_daily_prices", new=AsyncMock(side_effect=TWSERateLimitError("WAF"))), \
         patch("alpha_lab.jobs.service.fetch_yahoo_daily_prices", new=yahoo_mock):
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    yahoo_mock.assert_not_called()
    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "failed"


@pytest.mark.asyncio
async def test_yahoo_prices_direct_dispatch(session_factory):
    yahoo_rows = [
        DailyPrice(
            symbol="2330", trade_date=date(2026, 4, 11),
            open=700.0, high=705.0, low=698.0, close=702.0,
            volume=1_000_000, source="yahoo",
        )
    ]
    with session_factory() as s:
        job = create_job(
            s,
            job_type=JobType.YAHOO_PRICES,
            params={"symbol": "2330", "start": "2026-04-11", "end": "2026-04-11"},
        )
        s.commit()
        job_id = job.id

    with patch("alpha_lab.jobs.service.fetch_yahoo_daily_prices", new=AsyncMock(return_value=yahoo_rows)):
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "completed"
        row = s.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 11)})
        assert row is not None
        assert row.source == "yahoo"
```

並在 `backend/tests/jobs/conftest.py`（若不存在就建）加共用 fixture：

```python
"""Jobs 測試共用 fixture。"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.storage.models import Base


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)
```

（若 `backend/tests/jobs/__init__.py` 不存在，建立空檔。）

- [ ] **Step 6：跑測試確認 RED**

Run: `cd backend && pytest tests/jobs/test_yahoo_prices_dispatch.py -v`
Expected: FAIL（`JobType.YAHOO_PRICES` 未定義 / dispatch 未實作）。

- [ ] **Step 7：新增 JobType 值**

編輯 `backend/src/alpha_lab/jobs/types.py`：

```python
"""Job 類型列舉。新增 collector 時在此加一個 value 並在 service.run_job_sync 分派。"""

from enum import StrEnum


class JobType(StrEnum):
    TWSE_PRICES = "twse_prices"
    TWSE_PRICES_BATCH = "twse_prices_batch"
    TWSE_STOCK_INFO = "twse_stock_info"
    MOPS_REVENUE = "mops_revenue"
    TWSE_INSTITUTIONAL = "twse_institutional"
    TWSE_MARGIN = "twse_margin"
    MOPS_EVENTS = "mops_events"
    MOPS_FINANCIALS = "mops_financials"
    MOPS_CASHFLOW = "mops_cashflow"
    SCORE = "score"
    YAHOO_PRICES = "yahoo_prices"
    PROCESSED_INDICATORS = "processed_indicators"
    PROCESSED_RATIOS = "processed_ratios"
```

- [ ] **Step 8：更新 dispatch**

編輯 `backend/src/alpha_lab/jobs/service.py`：

1. 在檔頂 import 區塊加：

```python
from alpha_lab.collectors._fallback import should_fallback_to_yahoo
from alpha_lab.collectors.yahoo import YahooFetchError, fetch_yahoo_daily_prices
```

2. 把 `TWSE_PRICES` 分支（約第 108-118 行）換成：

```python
    if job_type is JobType.TWSE_PRICES:
        symbol = params["symbol"]
        year_month_str = params["year_month"]
        year, month = year_month_str.split("-")
        ym_date = date(int(year), int(month), 1)
        fallback_used = False
        try:
            price_rows = await fetch_daily_prices(symbol=symbol, year_month=ym_date)
        except Exception as exc:
            if not should_fallback_to_yahoo(exc):
                raise
            logger.info(
                "twse_prices %s %s → yahoo fallback triggered by %s",
                symbol, year_month_str, type(exc).__name__,
            )
            # Yahoo chart 以區間查：用該月 1 號到最後一日
            last_day = _last_day_of_month(ym_date)
            try:
                price_rows = await fetch_yahoo_daily_prices(
                    symbol=symbol, start=ym_date, end=last_day
                )
            except YahooFetchError as y_exc:
                raise RuntimeError(
                    f"both TWSE and Yahoo failed for {symbol} {year_month_str}: "
                    f"twse={type(exc).__name__}:{exc}; yahoo={y_exc}"
                ) from y_exc
            fallback_used = True
        with session_factory() as session:
            n = upsert_daily_prices(session, price_rows)
            session.commit()
        src = "yahoo" if fallback_used else "twse"
        return f"upserted {n} price rows for {symbol} {year_month_str} (source={src})"
```

3. 在 `TWSE_PRICES_BATCH` 內的單檔 fetch 段（try/except ValueError 那段，約第 137-165 行）加 fallback：

```python
            try:
                price_rows = await fetch_daily_prices(symbol=sym, year_month=ym_date)
            except TWSERateLimitError:
                raise
            except ValueError as exc:
                # 原本的 retry-once 邏輯保留；retry 仍失敗再 fallback Yahoo
                if "沒有符合條件" in str(exc):
                    logger.info("batch prices: %s no data, skip", sym)
                    continue
                logger.info("batch prices: %s transient stat, retry once: %s", sym, exc)
                await asyncio.sleep(1.0)
                try:
                    price_rows = await fetch_daily_prices(symbol=sym, year_month=ym_date)
                except Exception as retry_exc:
                    if not should_fallback_to_yahoo(retry_exc):
                        logger.warning("batch prices: %s failed after retry: %s", sym, retry_exc)
                        failed_symbols.append(sym)
                        continue
                    try:
                        last_day = _last_day_of_month(ym_date)
                        price_rows = await fetch_yahoo_daily_prices(symbol=sym, start=ym_date, end=last_day)
                        logger.info("batch prices: %s fallback to yahoo ok", sym)
                    except YahooFetchError as y_exc:
                        logger.warning("batch prices: %s fallback yahoo failed: %s", sym, y_exc)
                        failed_symbols.append(sym)
                        continue
            except httpx.HTTPError as exc:
                # 直接 fallback，不 retry
                try:
                    last_day = _last_day_of_month(ym_date)
                    price_rows = await fetch_yahoo_daily_prices(symbol=sym, start=ym_date, end=last_day)
                    logger.info("batch prices: %s http err → yahoo fallback: %s", sym, exc)
                except YahooFetchError as y_exc:
                    logger.warning("batch prices: %s both failed: twse=%s yahoo=%s", sym, exc, y_exc)
                    failed_symbols.append(sym)
                    continue
```

（上面 `httpx.HTTPError` 子句需要 `import httpx` — 在檔頂補上。）

4. 在檔尾加 helper：

```python
def _last_day_of_month(ym_date: date) -> date:
    """回傳該月最後一天。"""
    if ym_date.month == 12:
        return date(ym_date.year, 12, 31)
    next_month = date(ym_date.year, ym_date.month + 1, 1)
    from datetime import timedelta
    return next_month - timedelta(days=1)
```

5. 在既有 dispatch chain 尾端（`SCORE` 分支之前或之後都可）加 `YAHOO_PRICES` 分支：

```python
    if job_type is JobType.YAHOO_PRICES:
        symbol = str(params["symbol"])
        start = date.fromisoformat(str(params["start"]))
        end = date.fromisoformat(str(params["end"]))
        price_rows = await fetch_yahoo_daily_prices(symbol=symbol, start=start, end=end)
        with session_factory() as session:
            n = upsert_daily_prices(session, price_rows)
            session.commit()
        return f"upserted {n} price rows from yahoo for {symbol} {start}~{end}"
```

- [ ] **Step 9：跑測試確認 GREEN**

Run: `cd backend && pytest tests/jobs/test_yahoo_prices_dispatch.py tests/collectors/test_fallback.py -v`
Expected: 全 PASS（3 + 6 = 9 個 test）。

- [ ] **Step 10：靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 error。

- [ ] **Step 11：Commit**

```bash
rtk git add backend/src/alpha_lab/collectors/_fallback.py backend/src/alpha_lab/jobs/types.py backend/src/alpha_lab/jobs/service.py backend/tests/collectors/test_fallback.py backend/tests/jobs/test_yahoo_prices_dispatch.py backend/tests/jobs/conftest.py
rtk git commit -m "feat: add TWSE to Yahoo fallback for price collection"
```

---

## Task 5：技術指標計算模組

**Files:**
- Create: `backend/src/alpha_lab/analysis/indicators.py`
- Create: `backend/tests/analysis/test_indicators.py`

- [ ] **Step 1：寫 failing 測試**

建立 `backend/tests/analysis/test_indicators.py`：

```python
"""技術指標模組測試。純函式、不依賴 DB。"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from alpha_lab.analysis.indicators import IndicatorSeries, compute_indicators


def _price_series(count: int, start_close: float = 100.0, step: float = 1.0):
    """回傳 [(trade_date, close, high, low), ...]。"""
    base = date(2026, 1, 1)
    return [
        (base + timedelta(days=i), start_close + i * step, start_close + i * step + 2, start_close + i * step - 1)
        for i in range(count)
    ]


def test_compute_indicators_basic_ma():
    prices = _price_series(60)  # 60 交易日
    result = compute_indicators(prices)
    assert isinstance(result, IndicatorSeries)
    # 最新 MA5 = 平均最後 5 天
    last5 = [p[1] for p in prices[-5:]]
    assert result.latest.ma5 == pytest.approx(sum(last5) / 5)
    # MA60 = 平均所有 60 天
    all60 = [p[1] for p in prices]
    assert result.latest.ma60 == pytest.approx(sum(all60) / 60)


def test_compute_indicators_insufficient_data():
    """資料不足時對應 MA 為 None，不該炸。"""
    prices = _price_series(3)
    result = compute_indicators(prices)
    assert result.latest.ma5 is None
    assert result.latest.ma20 is None
    assert result.latest.ma60 is None


def test_compute_indicators_ratio_52w_high():
    prices = _price_series(260)  # 約 52 週
    result = compute_indicators(prices)
    latest_close = prices[-1][1]
    highs = [p[2] for p in prices]
    max_high = max(highs)
    assert result.latest.ratio_52w_high == pytest.approx(latest_close / max_high)


def test_compute_indicators_rsi14_monotonic_rising():
    """價格單邊上漲 → RSI14 應接近 100。"""
    prices = _price_series(30, step=1.0)
    result = compute_indicators(prices)
    assert result.latest.rsi14 is not None
    assert result.latest.rsi14 > 99.0


def test_compute_indicators_empty():
    assert compute_indicators([]).latest.ma5 is None
```

- [ ] **Step 2：跑測試確認 RED**

Run: `cd backend && pytest tests/analysis/test_indicators.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3：實作 indicators**

建立 `backend/src/alpha_lab/analysis/indicators.py`：

```python
"""技術指標計算（純函式，不觸 DB）。

輸入：時間序列 [(trade_date, close, high, low), ...]，須按日期升冪
輸出：IndicatorSnapshot（最新一日）+ 完整 series（Phase 7B.1 目前只用 latest）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class IndicatorSnapshot:
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    rsi14: float | None = None
    ratio_52w_high: float | None = None
    volatility_ann: float | None = None  # 年化波動率（std of daily return * sqrt(252)）


@dataclass
class IndicatorSeries:
    latest: IndicatorSnapshot = field(default_factory=IndicatorSnapshot)
    as_of: date | None = None


def compute_indicators(
    prices: list[tuple[date, float, float, float]]
) -> IndicatorSeries:
    """`prices` 須按 trade_date 升冪 `(date, close, high, low)`。"""
    if not prices:
        return IndicatorSeries()

    df = pd.DataFrame(prices, columns=["date", "close", "high", "low"]).sort_values("date").reset_index(drop=True)
    snap = IndicatorSnapshot()

    def _ma(window: int) -> float | None:
        if len(df) < window:
            return None
        return float(df["close"].tail(window).mean())

    snap.ma5 = _ma(5)
    snap.ma20 = _ma(20)
    snap.ma60 = _ma(60)

    if len(df) >= 15:
        delta = df["close"].diff().dropna()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)
        avg_gain = gains.tail(14).mean()
        avg_loss = losses.tail(14).mean()
        if avg_loss == 0:
            snap.rsi14 = 100.0
        else:
            rs = avg_gain / avg_loss
            snap.rsi14 = float(100 - (100 / (1 + rs)))

    if len(df) >= 20:
        lookback = df.tail(252) if len(df) >= 252 else df
        max_high = float(lookback["high"].max())
        latest_close = float(df["close"].iloc[-1])
        if max_high > 0:
            snap.ratio_52w_high = latest_close / max_high

    if len(df) >= 20:
        returns = df["close"].pct_change().dropna()
        if len(returns) > 0:
            # 252 交易日年化
            snap.volatility_ann = float(returns.std() * (252 ** 0.5))

    return IndicatorSeries(latest=snap, as_of=df["date"].iloc[-1])
```

- [ ] **Step 4：跑測試確認 GREEN**

Run: `cd backend && pytest tests/analysis/test_indicators.py -v`
Expected: 5 PASS。

- [ ] **Step 5：Commit**

```bash
rtk git add backend/src/alpha_lab/analysis/indicators.py backend/tests/analysis/test_indicators.py
rtk git commit -m "feat: add technical indicators computation module"
```

---

## Task 6：基本面比率計算模組

**Files:**
- Create: `backend/src/alpha_lab/analysis/ratios.py`
- Create: `backend/tests/analysis/test_ratios.py`

- [ ] **Step 1：寫 failing 測試**

建立 `backend/tests/analysis/test_ratios.py`：

```python
"""基本面比率模組測試。`compute_ratios` 從 DB session 拉資料算。"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alpha_lab.analysis.ratios import compute_ratios
from alpha_lab.storage.models import Base, FinancialStatement, PriceDaily, Stock


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)()


def _seed_financials(s: Session, symbol: str):
    s.add(Stock(symbol=symbol, name=symbol))
    # 兩年 income：近四季 + 前四季
    quarters = ["2026Q1", "2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2"]
    for q in quarters:
        s.add(FinancialStatement(
            symbol=symbol, period=q, statement_type="income",
            revenue=1_000_000, gross_profit=300_000, operating_income=200_000,
            net_income=150_000, eps=5.0,
        ))
    s.add(FinancialStatement(
        symbol=symbol, period="2026Q1", statement_type="balance",
        total_assets=10_000_000, total_liabilities=4_000_000, total_equity=6_000_000,
    ))
    s.add(PriceDaily(
        symbol=symbol, trade_date=date(2026, 4, 1),
        open=100.0, high=105.0, low=98.0, close=100.0, volume=1_000_000,
    ))
    s.commit()


def test_compute_ratios_pe_roe(session: Session):
    _seed_financials(session, "2330")
    r = compute_ratios(session, "2330", as_of=date(2026, 4, 1))
    # EPS TTM = 5 * 4 = 20；close=100 → PE=5
    assert r.pe == pytest.approx(5.0)
    # ROE = net_income TTM (150k*4=600k) / equity (6M) ≈ 0.1
    assert r.roe == pytest.approx(0.1)
    # gross margin TTM = 300k*4 / 1M*4 = 0.3
    assert r.gross_margin == pytest.approx(0.3)
    # debt_ratio = 4M / 10M = 0.4
    assert r.debt_ratio == pytest.approx(0.4)


def test_compute_ratios_no_financials_returns_nones(session: Session):
    session.add(Stock(symbol="XXXX", name="XXXX"))
    session.commit()
    r = compute_ratios(session, "XXXX", as_of=date(2026, 4, 1))
    assert r.pe is None
    assert r.roe is None
```

- [ ] **Step 2：跑測試確認 RED**

Run: `cd backend && pytest tests/analysis/test_ratios.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 3：實作 ratios**

建立 `backend/src/alpha_lab/analysis/ratios.py`：

```python
"""基本面比率計算：PE / ROE / gross margin / debt ratio / FCF TTM 等。

與 `analysis/pipeline.build_snapshot` 邏輯相近，但只算單一 symbol，回傳扁平
`RatioSnapshot`，供 `processed_store` 寫入 JSON。兩邊可在 Phase 8 統一抽出
`fundamentals.py`；此處先獨立避免大改 pipeline。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from alpha_lab.storage.models import FinancialStatement, PriceDaily


@dataclass
class RatioSnapshot:
    as_of: date
    symbol: str
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_ratio: float | None = None
    fcf_ttm: int | None = None


def _sum_n(vals: list[float | int | None]) -> float | None:
    filtered = [v for v in vals if v is not None]
    if len(filtered) < len(vals) or not filtered:
        return None
    return float(sum(filtered))


def compute_ratios(session: Session, symbol: str, as_of: date) -> RatioSnapshot:
    snap = RatioSnapshot(as_of=as_of, symbol=symbol)

    price_row = session.execute(
        select(PriceDaily.close)
        .where(PriceDaily.symbol == symbol, PriceDaily.trade_date <= as_of)
        .order_by(PriceDaily.trade_date.desc())
        .limit(1)
    ).first()
    close = float(price_row[0]) if price_row else None

    income_rows = (
        session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == symbol,
                FinancialStatement.statement_type == "income",
            )
            .order_by(FinancialStatement.period.desc())
            .limit(8)
        )
        .scalars()
        .all()
    )

    balance_row = session.execute(
        select(FinancialStatement)
        .where(
            FinancialStatement.symbol == symbol,
            FinancialStatement.statement_type == "balance",
        )
        .order_by(FinancialStatement.period.desc())
        .limit(1)
    ).scalar_one_or_none()

    cashflow_rows = (
        session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == symbol,
                FinancialStatement.statement_type == "cashflow",
            )
            .order_by(FinancialStatement.period.desc())
            .limit(4)
        )
        .scalars()
        .all()
    )

    eps_ttm = _sum_n([r.eps for r in income_rows[:4]])
    rev_ttm = _sum_n([r.revenue for r in income_rows[:4]])
    gross_ttm = _sum_n([r.gross_profit for r in income_rows[:4]])
    ni_ttm = _sum_n([r.net_income for r in income_rows[:4]])

    if close and eps_ttm and eps_ttm > 0:
        snap.pe = close / eps_ttm

    if (
        ni_ttm is not None
        and balance_row is not None
        and balance_row.total_equity
    ):
        snap.roe = ni_ttm / balance_row.total_equity

    if gross_ttm is not None and rev_ttm:
        snap.gross_margin = gross_ttm / rev_ttm

    if (
        balance_row is not None
        and balance_row.total_liabilities is not None
        and balance_row.total_assets
    ):
        snap.debt_ratio = balance_row.total_liabilities / balance_row.total_assets

    if len(cashflow_rows) == 4 and all(r.operating_cf is not None for r in cashflow_rows):
        snap.fcf_ttm = int(sum(r.operating_cf for r in cashflow_rows if r.operating_cf is not None))

    return snap
```

- [ ] **Step 4：跑測試確認 GREEN**

Run: `cd backend && pytest tests/analysis/test_ratios.py -v`
Expected: 2 PASS。

- [ ] **Step 5：Commit**

```bash
rtk git add backend/src/alpha_lab/analysis/ratios.py backend/tests/analysis/test_ratios.py
rtk git commit -m "feat: add fundamental ratios computation module"
```

---

## Task 7：`data/processed/` JSON 讀寫層

**Files:**
- Create: `backend/src/alpha_lab/storage/processed_store.py`
- Create: `backend/tests/storage/test_processed_store.py`
- Modify: `backend/src/alpha_lab/config.py`（加 `processed_dir` 設定）

- [ ] **Step 1：先讀現行 config**

Run: `cat backend/src/alpha_lab/config.py` — 確認有 `get_settings()` 且用 `pydantic_settings`。

- [ ] **Step 2：寫 failing 測試**

建立 `backend/tests/storage/test_processed_store.py`：

```python
"""processed_store: atomic JSON read/write under data/processed/."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from alpha_lab.analysis.indicators import IndicatorSeries, IndicatorSnapshot
from alpha_lab.analysis.ratios import RatioSnapshot
from alpha_lab.storage.processed_store import (
    read_indicators_json,
    write_indicators_json,
    write_ratios_json,
)


def test_write_indicators_creates_file(tmp_path: Path):
    series = IndicatorSeries(
        latest=IndicatorSnapshot(ma5=100.0, ma20=99.0, ma60=95.0, rsi14=55.0, ratio_52w_high=0.9, volatility_ann=0.25),
        as_of=date(2026, 4, 1),
    )
    write_indicators_json(base_dir=tmp_path, symbol="2330", series=series)
    path = tmp_path / "indicators" / "2330.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["symbol"] == "2330"
    assert payload["as_of"] == "2026-04-01"
    assert payload["latest"]["ma5"] == 100.0
    assert "updated_at" in payload


def test_write_ratios_creates_file(tmp_path: Path):
    snap = RatioSnapshot(
        as_of=date(2026, 4, 1),
        symbol="2330",
        pe=20.5, pb=None, roe=0.25, gross_margin=0.5, debt_ratio=0.3, fcf_ttm=500_000,
    )
    write_ratios_json(base_dir=tmp_path, snap=snap)
    path = tmp_path / "ratios" / "2330.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["symbol"] == "2330"
    assert payload["pe"] == 20.5
    assert payload["pb"] is None


def test_read_indicators_round_trip(tmp_path: Path):
    series = IndicatorSeries(
        latest=IndicatorSnapshot(ma5=100.0),
        as_of=date(2026, 4, 1),
    )
    write_indicators_json(base_dir=tmp_path, symbol="2330", series=series)
    loaded = read_indicators_json(base_dir=tmp_path, symbol="2330")
    assert loaded is not None
    assert loaded["latest"]["ma5"] == 100.0


def test_read_indicators_returns_none_when_missing(tmp_path: Path):
    assert read_indicators_json(base_dir=tmp_path, symbol="9999") is None


def test_write_indicators_atomic_no_partial_file(tmp_path: Path, monkeypatch):
    """寫入過程若崩壞，原檔不該留下損壞內容（ atomic rename ）。"""
    series = IndicatorSeries(latest=IndicatorSnapshot(ma5=1.0), as_of=date(2026, 4, 1))
    write_indicators_json(base_dir=tmp_path, symbol="2330", series=series)
    existing = (tmp_path / "indicators" / "2330.json").read_text(encoding="utf-8")

    # 第二次寫入，強制 json.dumps 炸：replace 前的 .tmp 可能存在，但主檔不能壞
    import alpha_lab.storage.processed_store as mod
    def _boom(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(mod.json, "dumps", _boom)
    with pytest.raises(RuntimeError):
        write_indicators_json(base_dir=tmp_path, symbol="2330", series=series)
    # 主檔應維持原版本
    still = (tmp_path / "indicators" / "2330.json").read_text(encoding="utf-8")
    assert still == existing
```

- [ ] **Step 3：跑測試確認 RED**

Run: `cd backend && pytest tests/storage/test_processed_store.py -v`
Expected: FAIL（ModuleNotFoundError）。

- [ ] **Step 4：實作 processed_store**

建立 `backend/src/alpha_lab/storage/processed_store.py`：

```python
"""`data/processed/` 下 per-symbol JSON 讀寫層。

檔案配置：
- `{base_dir}/indicators/{symbol}.json`
- `{base_dir}/ratios/{symbol}.json`

寫入策略：先寫到 `*.json.tmp`，json.dumps 成功後 os.replace（atomic rename）。
讀取是 plain `json.loads`，沒有 schema 驗證（呼叫端若需結構可自行擴）。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alpha_lab.analysis.indicators import IndicatorSeries
from alpha_lab.analysis.ratios import RatioSnapshot


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=_default_serializer)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _default_serializer(o: Any) -> Any:
    if hasattr(o, "isoformat"):
        return o.isoformat()
    raise TypeError(f"not serializable: {type(o)}")


def write_indicators_json(base_dir: Path, symbol: str, series: IndicatorSeries) -> Path:
    path = base_dir / "indicators" / f"{symbol}.json"
    payload: dict[str, Any] = {
        "symbol": symbol,
        "as_of": series.as_of.isoformat() if series.as_of else None,
        "updated_at": datetime.now(UTC).isoformat(),
        "latest": asdict(series.latest),
    }
    _atomic_write_json(path, payload)
    return path


def write_ratios_json(base_dir: Path, snap: RatioSnapshot) -> Path:
    path = base_dir / "ratios" / f"{snap.symbol}.json"
    payload: dict[str, Any] = {
        "symbol": snap.symbol,
        "as_of": snap.as_of.isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "pe": snap.pe,
        "pb": snap.pb,
        "roe": snap.roe,
        "gross_margin": snap.gross_margin,
        "debt_ratio": snap.debt_ratio,
        "fcf_ttm": snap.fcf_ttm,
    }
    _atomic_write_json(path, payload)
    return path


def read_indicators_json(base_dir: Path, symbol: str) -> dict[str, Any] | None:
    path = base_dir / "indicators" / f"{symbol}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 5：擴 config.py**

編輯 `backend/src/alpha_lab/config.py`。先讀檔對照現行欄位（避免覆蓋既有設定），在 `Settings` class body 內加：

```python
    processed_dir: Path = Path("data/processed")
    yahoo_enabled: bool = True
```

（若檔頂尚未 `from pathlib import Path`，需補上。）

- [ ] **Step 6：跑測試確認 GREEN**

Run: `cd backend && pytest tests/storage/test_processed_store.py -v`
Expected: 5 PASS。

- [ ] **Step 7：Commit**

```bash
rtk git add backend/src/alpha_lab/storage/processed_store.py backend/src/alpha_lab/config.py backend/tests/storage/test_processed_store.py
rtk git commit -m "feat: add processed/ JSON atomic read-write layer"
```

---

## Task 8：`PROCESSED_INDICATORS` / `PROCESSED_RATIOS` job dispatch

**Files:**
- Modify: `backend/src/alpha_lab/jobs/service.py`（dispatch 分支）
- Create: `backend/tests/jobs/test_processed_jobs.py`

- [ ] **Step 1：寫 failing 測試**

建立 `backend/tests/jobs/test_processed_jobs.py`：

```python
"""PROCESSED_INDICATORS / PROCESSED_RATIOS job 測試。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Base, FinancialStatement, Job, PriceDaily, Stock


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine)


@pytest.mark.asyncio
async def test_processed_indicators_writes_json(session_factory, tmp_path: Path, monkeypatch):
    with session_factory() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        # 30 天 close 資料就夠 ma5 / ma20
        for i in range(30):
            s.add(PriceDaily(
                symbol="2330",
                trade_date=date(2026, 1, 1).replace(day=min(i + 1, 28)),
                open=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.0 + i, volume=1000,
            ))
        s.commit()

    monkeypatch.setattr("alpha_lab.jobs.service.get_settings_for_processed", lambda: type("X", (), {"processed_dir": tmp_path}))
    with session_factory() as s:
        job = create_job(s, job_type=JobType.PROCESSED_INDICATORS, params={"symbols": ["2330"]})
        s.commit()
        job_id = job.id

    await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "completed"

    out = tmp_path / "indicators" / "2330.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["symbol"] == "2330"
    assert payload["latest"]["ma5"] is not None


@pytest.mark.asyncio
async def test_processed_ratios_writes_json(session_factory, tmp_path: Path, monkeypatch):
    with session_factory() as s:
        s.add(Stock(symbol="2330", name="台積電"))
        for q in ["2026Q1", "2025Q4", "2025Q3", "2025Q2"]:
            s.add(FinancialStatement(
                symbol="2330", period=q, statement_type="income",
                revenue=1_000, gross_profit=300, operating_income=200,
                net_income=150, eps=5.0,
            ))
        s.add(FinancialStatement(
            symbol="2330", period="2026Q1", statement_type="balance",
            total_assets=10_000, total_liabilities=4_000, total_equity=6_000,
        ))
        s.add(PriceDaily(symbol="2330", trade_date=date(2026, 4, 1),
                        open=100.0, high=105.0, low=98.0, close=100.0, volume=1000))
        s.commit()

    monkeypatch.setattr("alpha_lab.jobs.service.get_settings_for_processed", lambda: type("X", (), {"processed_dir": tmp_path}))
    with session_factory() as s:
        job = create_job(s, job_type=JobType.PROCESSED_RATIOS, params={"symbols": ["2330"], "as_of": "2026-04-01"})
        s.commit()
        job_id = job.id

    await run_job_sync(job_id=job_id, session_factory=session_factory)

    out = tmp_path / "ratios" / "2330.json"
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["pe"] == pytest.approx(5.0)  # close/(eps*4) = 100/20
```

- [ ] **Step 2：跑測試確認 RED**

Run: `cd backend && pytest tests/jobs/test_processed_jobs.py -v`
Expected: FAIL（JobType 未定義對應分支 / `get_settings_for_processed` 未定義）。

- [ ] **Step 3：實作 dispatch**

編輯 `backend/src/alpha_lab/jobs/service.py`：

1. 檔頂 imports 補：

```python
from alpha_lab.analysis.indicators import compute_indicators
from alpha_lab.analysis.ratios import compute_ratios
from alpha_lab.storage.processed_store import write_indicators_json, write_ratios_json
from alpha_lab.config import get_settings
```

2. 檔尾加 helper（測試會用 monkeypatch 覆寫）：

```python
def get_settings_for_processed():
    """獨立取出供測試 monkeypatch（直接 patch get_settings 會影響其他模組）。"""
    return get_settings()
```

3. 在 dispatch chain 中加兩個分支（任意位置，建議放在 SCORE 之前）：

```python
    if job_type is JobType.PROCESSED_INDICATORS:
        symbols = params.get("symbols") or []
        settings = get_settings_for_processed()
        processed_dir = Path(settings.processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)
        total = 0
        with session_factory() as session:
            for sym in symbols:
                rows = session.execute(
                    select(
                        PriceDaily.trade_date, PriceDaily.close,
                        PriceDaily.high, PriceDaily.low,
                    )
                    .where(PriceDaily.symbol == sym)
                    .order_by(PriceDaily.trade_date.asc())
                ).all()
                series = compute_indicators([(r[0], float(r[1]), float(r[2]), float(r[3])) for r in rows])
                if series.as_of is None:
                    continue
                write_indicators_json(base_dir=processed_dir, symbol=sym, series=series)
                total += 1
        return f"wrote {total} indicators json files"

    if job_type is JobType.PROCESSED_RATIOS:
        symbols = params.get("symbols") or []
        as_of_str = params.get("as_of")
        as_of = (
            date.fromisoformat(str(as_of_str))
            if as_of_str
            else datetime.now(UTC).date()
        )
        settings = get_settings_for_processed()
        processed_dir = Path(settings.processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)
        total = 0
        with session_factory() as session:
            for sym in symbols:
                snap = compute_ratios(session, sym, as_of)
                write_ratios_json(base_dir=processed_dir, snap=snap)
                total += 1
        return f"wrote {total} ratios json files for {as_of}"
```

4. 檔頂補上 imports（若缺）：

```python
from pathlib import Path
from sqlalchemy import select
from alpha_lab.storage.models import PriceDaily
```

- [ ] **Step 4：跑測試確認 GREEN**

Run: `cd backend && pytest tests/jobs/test_processed_jobs.py -v`
Expected: 2 PASS。

- [ ] **Step 5：跑所有新增 / 修改過的測試**

Run: `cd backend && pytest tests/jobs/ tests/analysis/ tests/collectors/ tests/storage/ -v`
Expected: 全部 PASS。

- [ ] **Step 6：靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 error。

- [ ] **Step 7：Commit**

```bash
rtk git add backend/src/alpha_lab/jobs/service.py backend/tests/jobs/test_processed_jobs.py
rtk git commit -m "feat: add processed indicators and ratios job dispatch"
```

---

## Task 9：`daily_collect.py` 串接 processed 更新

**Files:**
- Modify: `backend/scripts/daily_collect.py`

- [ ] **Step 1：看現行 daily_collect 結尾流程（只加不改既有流程）**

Run: `head -n 180 backend/scripts/daily_collect.py` — 確認 daily_jobs 列表所在位置。

- [ ] **Step 2：在 daily_jobs 後、print summary 前，加 processed 收尾**

編輯 `backend/scripts/daily_collect.py`，在 `for label, job_type, params in daily_jobs:` 迴圈結束後、`print("\n=== summary ===")` 前，加：

```python
    # Phase 7B.1：若有明確 symbols，跑一次 processed 指標落檔（--all 不自動跑，避免 60 分鐘）
    if price_symbols:
        _label = "processed indicators"
        status, summary = await _run_one(
            _label,
            JobType.PROCESSED_INDICATORS,
            {"symbols": price_symbols},
            session_factory,
        )
        results.append((_label, status, summary))

        _label = "processed ratios"
        status, summary = await _run_one(
            _label,
            JobType.PROCESSED_RATIOS,
            {"symbols": price_symbols, "as_of": trade_date_str},
            session_factory,
        )
        results.append((_label, status, summary))
```

- [ ] **Step 3：手動 sanity 檢查（不寫自動測試，因為 daily_collect 是 e2e 腳本、自動測試成本高）**

Run: `cd backend && ruff check scripts/daily_collect.py && mypy scripts/daily_collect.py`
Expected: 0 error。

- [ ] **Step 4：Commit**

```bash
rtk git add backend/scripts/daily_collect.py
rtk git commit -m "feat: hook processed indicators and ratios into daily_collect"
```

---

## Task 10：知識庫 + 文件同步

**Files:**
- Create: `docs/knowledge/collectors/yahoo.md`
- Create: `docs/knowledge/architecture/processed-store.md`
- Modify: `docs/knowledge/collectors/README.md`
- Modify: `docs/knowledge/collectors/twse.md`
- Modify: `docs/knowledge/architecture/README.md`
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`
- Modify: `docs/USER_GUIDE.md`

- [ ] **Step 1：建立 `docs/knowledge/collectors/yahoo.md`**

```markdown
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
```

- [ ] **Step 2：建立 `docs/knowledge/architecture/processed-store.md`**

```markdown
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
```

- [ ] **Step 3：更新 `collectors/README.md` 與 `architecture/README.md`**

編輯 `docs/knowledge/collectors/README.md`，在 `## 現行條目` 表格最後加：

```markdown
| `yahoo.md` | Yahoo Finance Chart API（TWSE 備援） | Phase 7B.1 |
```

編輯 `docs/knowledge/architecture/README.md`（若不存在先讀看看），加：

```markdown
| `processed-store.md` | `data/processed/` 計算後指標 JSON 存放 | Phase 7B.1 |
```

- [ ] **Step 4：更新 `collectors/twse.md`**

在「通用坑」章節或 Phase 2+ 規劃之前，插入一段：

```markdown
### Fallback 到 Yahoo（Phase 7B.1）

`jobs/service.py::TWSE_PRICES` 捕捉非 WAF 例外後會透過 `_fallback.should_fallback_to_yahoo` 決定是否轉 `collectors/yahoo.fetch_yahoo_daily_prices`。WAF 錯誤與「沒有符合條件」不 fallback。寫入 `prices_daily` 時帶 `source="twse"` / `"yahoo"`，既有無 source 的舊 row 會被保留（新 row source=None 不覆寫）。
```

- [ ] **Step 5：更新設計 spec**

編輯 `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`，把 `| 7B.1 | 未開始 | ...` 那列改成 `| 7B.1 | ✅ 完成（2026-04-18） | 數據源擴充 | Yahoo Finance fallback collector、prices_daily.source、data/processed/ 指標與比率 JSON（atomic write）、YAHOO_PRICES / PROCESSED_INDICATORS / PROCESSED_RATIOS JobType；daily_collect 尾端自動跑 processed |`。

- [ ] **Step 6：更新 USER_GUIDE.md**

在「資料源」相關段落或檔案中後段，加一段：

```markdown
### 資料來源備援

- 預設每日價格來自 TWSE（台灣證券交易所）
- 若 TWSE 暫時故障，系統會自動 fallback 到 Yahoo Finance；資料庫 `prices_daily.source` 會標記來源
- Yahoo 是非官方 API、準確度偶有偏差，僅作為備援；若頻繁使用 Yahoo 資料請自行交叉比對

### 計算後指標（供 Claude Code 使用）

- `data/processed/indicators/<symbol>.json`：MA / RSI / 52 週高低比
- `data/processed/ratios/<symbol>.json`：PE / ROE / 毛利率 / 負債比 / FCF
- 由 daily_collect 或手動觸發 `PROCESSED_INDICATORS` / `PROCESSED_RATIOS` 更新
```

- [ ] **Step 7：中文亂碼掃描**

Run: `cd g:/codingdata/alpha-lab && grep -r "��" docs/knowledge/collectors/yahoo.md docs/knowledge/architecture/processed-store.md docs/USER_GUIDE.md || echo "clean"`
Expected: `clean`。

- [ ] **Step 8：給使用者驗收指引**

```cmd
REM === Phase 7B.1 驗收指引（Windows CMD） ===
cd /d g:\codingdata\alpha-lab

REM 1) 跑所有新增 / 修改的後端測試
cd backend && .venv\Scripts\python.exe -m pytest tests\collectors\test_yahoo.py tests\collectors\test_fallback.py tests\collectors\test_runner_source.py tests\analysis\test_indicators.py tests\analysis\test_ratios.py tests\storage\test_processed_store.py tests\storage\test_init_db_migration.py tests\jobs\test_yahoo_prices_dispatch.py tests\jobs\test_processed_jobs.py -v

REM 2) 靜態檢查
.venv\Scripts\python.exe -m ruff check . && .venv\Scripts\python.exe -m mypy src

REM 3) smoke test：真打 Yahoo（需網路）
.venv\Scripts\python.exe scripts\smoke_yahoo.py --symbol 2330 --days 5

REM 4) 啟動 API、手動觸發 YAHOO_PRICES
REM 另開 cmd：.venv\Scripts\python.exe -m uvicorn alpha_lab.api.main:app --reload
REM 然後：curl -X POST http://127.0.0.1:8000/api/jobs/collect -H "Content-Type: application/json" -d "{\"type\":\"yahoo_prices\",\"params\":{\"symbol\":\"2330\",\"start\":\"2026-04-01\",\"end\":\"2026-04-15\"}}"

REM 5) 觸發 PROCESSED_INDICATORS 並檢查檔案
REM curl -X POST http://127.0.0.1:8000/api/jobs/collect -H "Content-Type: application/json" -d "{\"type\":\"processed_indicators\",\"params\":{\"symbols\":[\"2330\"]}}"
dir data\processed\indicators\2330.json
type data\processed\indicators\2330.json
```

請手動驗收上述步驟，確認：
- 測試全綠
- smoke_yahoo 能印出最近 5 天 OHLCV
- `yahoo_prices` job 跑完 DB `prices_daily` 有 `source="yahoo"` 的 row
- `data/processed/indicators/2330.json` 真的被建立且內容合理

- [ ] **Step 9：等使用者明確「驗證通過」後 commit**

```bash
rtk git add docs/
rtk git commit -m "docs: sync knowledge base for Phase 7B.1 data source expansion"
```

---

## Self-Review Notes

- **Spec coverage**：
  - ✅ Yahoo Finance 備援數據源 → Task 2 + Task 4
  - ✅ `data/processed/` 計算後指標（技術指標 + 基本面比率） → Task 5 + 6 + 7
  - ✅ 新 JobType 分派 → Task 4 + Task 8（`YAHOO_PRICES` / `PROCESSED_INDICATORS` / `PROCESSED_RATIOS`）
  - ✅ Fallback 決策（TWSE → Yahoo 序列） → Task 4 的 `_fallback.should_fallback_to_yahoo`
  - ✅ `prices_daily.source` 欄位 → Task 1 + Task 3

- **Placeholder scan**：所有 step 都有具體 code 或 shell 指令；無 TODO / TBD。

- **Type consistency**：
  - `DailyPrice.source` 在 Task 1 定為 `Literal["twse", "yahoo"] | None`；Task 2 Yahoo collector 填 `"yahoo"`、Task 3 TWSE collector 填 `"twse"` — 對齊
  - `IndicatorSeries` / `IndicatorSnapshot` dataclass 在 Task 5 定義，Task 7 處理序列化，Task 8 用 `compute_indicators(...)` 回傳型別 — 對齊
  - `RatioSnapshot` 在 Task 6 定義，Task 7 / Task 8 使用 — 對齊
  - JobType 值在 Task 4 Step 7 新增，後續 Task 8 dispatch 使用同名 — 對齊

- **不涵蓋的項目（留給 7B.2 / 7B.3）**：
  - 新聞彙整、每日簡報、排程機制 → 7B.2
  - 報告離線快取、「加入組合」UX 強化 → 7B.3
  - 前端資料來源 badge 顯示 → 留到 Phase 8 UI 升級

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-18-phase-7b1-data-source-expansion.md`.**

審核重點請確認：

1. **Yahoo API 選擇**（直打 chart API，不引入 `yfinance`）是否接受？
2. **Fallback 策略**（WAF/「沒有符合條件」不 fallback，其餘失敗 fallback）是否接受？
3. **processed/ JSON 格式**（非 parquet）是否接受？
4. **daily_collect 自動跑 processed** 的條件（只在有 `--symbols` 或 `--all` 時跑）是否合理？
5. **前端完全不動**這點是否接受？（Yahoo 來源對使用者透明；若想看到 badge，會拉到 Phase 8 處理）

審核通過後，兩種執行路徑：

**1. Subagent-Driven（recommended）** — 每個 Task 派一個新的 subagent 實作 + 主 agent review，10 個 Task 約可控

**2. Inline Execution** — 此 session 直接按 Task 順序實作，每 Task 完成後停下等你確認

請回覆「Plan OK，採 1」或「Plan OK，採 2」，或告訴我要改的地方。
