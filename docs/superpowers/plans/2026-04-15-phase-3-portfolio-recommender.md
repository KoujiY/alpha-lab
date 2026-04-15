# Phase 3: 多因子評分引擎 + 組合推薦頁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付功能 C — 多因子評分引擎（Value / Growth / Dividend / Quality）與四套風格組合推薦頁（保守 / 平衡 / 積極，平衡組標記為最推薦），後端 `/api/portfolios/recommend` + `/api/stocks/{symbol}/score`，前端 `/portfolios` 頁 + 個股頁 ScoreRadar。Phase 中段補 MOPS 現金流 collector 並將 FCF 接入 Quality 因子。

**Architecture:**
- **Factor engine**：純函式，輸入 symbol + 資料快照 → 輸出 0-100 分。每個因子有自己的 `compute_<factor>()`，內部指標各自歸一化後再平均。歸一化採「橫截面百分位法」(cross-sectional percentile)：同一 `calc_date` 所有 symbol 一起排名→百分位。
- **Scoring pipeline**：`score_all(calc_date)` 先拉快照、批次算分、upsert 到 `scores` 表。透過 `POST /api/jobs/collect` 以 `job_type='score'` 觸發，或 `scripts/compute_scores.py` CLI。
- **Portfolio generator**：讀 `scores` 最新一筆，依風格權重加權總分，取 Top 30 → 產業分散約束（同產業最多 5 檔）→ 單檔上限 30% → 權重按總分 softmax 配置。四組共用同一份候選池、只在權重設定與配置比例上差異。
- **Cashflow collector**：MOPS t164sb05 HTML scrape，解析「營業活動現金流」「投資」「融資」三大類淨額→ upsert `financial_statements.statement_type='cashflow'`。FCF 在 Phase 3 中段接入 Quality 因子；若 scrape 卡住，Quality 可先用 3 指標出線。
- **Frontend**：新增 `/portfolios` 頁面用 4 個 tab 呈現 conservative/balanced/aggressive（+ top pick 徽章），個股頁加 ScoreRadar 區塊（五角雷達圖：四因子 + 總分）。
- **知識庫同步**：建立 `domain/factors.md`、`domain/scoring.md`、`features/portfolio/recommender.md`、`features/portfolio/weights.md`、`collectors/mops-cashflow.md`；更新 `architecture/data-flow.md`、`architecture/data-models.md`。

**Tech Stack:** FastAPI、SQLAlchemy 2.x、Pydantic v2、numpy（百分位與 softmax）、pandas（橫截面 join）、BeautifulSoup4（MOPS HTML scrape）、React 19、TanStack Query v5、Recharts（RadarChart）、Tailwind 4、vitest、Playwright、pytest。

---

## Phase 3 工作總覽

| 群組 | 任務數 | 主題 |
|------|--------|------|
| A | 3 | Storage — `scores` 表、Pydantic schemas、engine scaffold |
| B | 2 | Factor engine — Value + Growth |
| C | 2 | Factor engine — Dividend（殖利率） + Quality（ROE/毛利率/負債比） |
| D | 2 | Total score + 風格權重 + scoring pipeline + CLI |
| E | 3 | Portfolio generator + `/api/portfolios/recommend` + 個股 score 端點 |
| F | 3 | MOPS cashflow collector + FCF 接入 Quality |
| G | 2 | Frontend — ScoreRadar 元件、個股頁整合 |
| H | 3 | Frontend — portfolios 頁面、API client、tab 切換 |
| I | 2 | 測試（vitest + Playwright E2E） |
| J | 2 | 知識庫 + USER_GUIDE + Phase 驗收 |

**總計：24 tasks**

## 範圍與邊界

**本 Phase 包含**：
- `scores` 表（symbol, calc_date, value/growth/dividend/quality/total），upsert by (symbol, calc_date)
- 四因子計算：Value（PE、PB）、Growth（營收 YoY、EPS YoY）、Dividend（當期殖利率）、Quality（ROE、毛利率、負債比 + 中段補 FCF）
- 橫截面百分位歸一化（單一 calc_date 內所有 symbol 一起排名）
- 風格權重表（conservative / balanced / aggressive）
- `/api/stocks/{symbol}/score`（單檔最新分）
- `/api/portfolios/recommend?style=<...>`（單一 style）與 `/api/portfolios/recommend`（全部四組）
- `POST /api/jobs/collect` 支援 `job_type='score'`（算分並寫 `scores`）
- `scripts/compute_scores.py` CLI（手動觸發）
- MOPS t164sb05 現金流 collector + `POST /api/jobs/collect` 支援 `job_type='cashflow'`
- 前端 `/portfolios` 頁（4 tab：保守/平衡/積極 + 最推薦徽章），顯示持股、權重、expected_yield、risk_score、因子分佈
- 個股頁 `ScoreRadar` 元件（四因子雷達 + 總分徽章）
- 單元 + 整合測試；1 條 E2E（portfolios 頁載入 + tab 切換 + holdings 顯示）
- 知識庫：`domain/factors.md`、`domain/scoring.md`、`features/portfolio/recommender.md`、`features/portfolio/weights.md`、`collectors/mops-cashflow.md`

**本 Phase 不包含**（留後續 Phase）：
- 連續配息年數、配息穩定度（Dividend 因子的延伸指標）→ Phase 4 / 5
- 產業地位（Growth 因子的質化部分）→ Phase 5
- L2 推薦理由側邊面板（Phase 4 教學系統）
- 報告儲存、回顧模式（Phase 4）
- 組合儲存與追蹤、`/portfolios/:id`、績效計算（Phase 6）
- 選股篩選器 `/screener`（Phase 5）
- PE/PB 即時計算快取（每次都是 on-the-fly 從 price * shares 推）

## Commit 規範（本專案 MANDATORY）

1. **靜態分析必做**：`ruff check .` + `mypy src` + `pnpm type-check` + `pnpm lint` 必須 0 error
2. **使用者驗證優先**：完成功能後**不可**自動 commit；給手動驗收指引、等使用者明確「驗證通過」
3. **按 type 拆分**：`feat` / `docs` / `fix` / `refactor` / `chore` 不混在同一 commit
4. **禁止 scope 括號**：`type: description`，不寫 `type(scope): description`
5. **同步檢查**：知識庫、spec、USER_GUIDE、E2E 是否需要連動更新
6. **中文亂碼掃描**：完成寫檔後 `grep -r "��" .`（不含 node_modules）
7. **驗收指引 shell**：給使用者的指令用 CMD 格式（反斜線路徑、REM 註解、```cmd code fence）
8. **群組驗收節點**：每個字母群組（A/B/...）完成後停下等使用者驗收（避免觸發 auto-compact）

---

## Task A1: `scores` 表 SQLAlchemy model

**Files:**
- Modify: `backend/src/alpha_lab/storage/models.py`（加入 `Score` class）
- Test: `backend/tests/storage/test_models_score.py`

- [ ] **Step 1: 寫失敗測試**

```python
# backend/tests/storage/test_models_score.py
"""驗證 Score model 可建立、欄位型別正確、可 upsert。"""

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alpha_lab.storage.models import Base, Score, Stock


def test_score_model_persist_and_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.add(
            Score(
                symbol="2330",
                calc_date=date(2026, 4, 15),
                value_score=72.5,
                growth_score=85.0,
                dividend_score=60.0,
                quality_score=90.0,
                total_score=77.6,
            )
        )
        session.commit()

        row = session.get(Score, ("2330", date(2026, 4, 15)))
        assert row is not None
        assert row.total_score == 77.6
        assert row.value_score == 72.5
```

- [ ] **Step 2: 驗證測試失敗**

Run: `cd backend && pytest tests/storage/test_models_score.py -v`
Expected: FAIL（`ImportError: cannot import name 'Score'`）

- [ ] **Step 3: 在 `models.py` 末尾加入 `Score`**

```python
class Score(Base):
    """多因子評分（Phase 3）。

    每個因子 0-100 分，total_score 為加權平均（權重隨風格調整時在 runtime 算）。
    本表儲存四個因子的「中性」分數；組合推薦時讀取並按風格權重加權。
    """

    __tablename__ = "scores"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    calc_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    growth_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
```

- [ ] **Step 4: 驗證測試通過**

Run: `cd backend && pytest tests/storage/test_models_score.py -v`
Expected: PASS

- [ ] **Step 5: 靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 error

- [ ] **Step 6: 等使用者驗證後 commit**

```bash
git add backend/src/alpha_lab/storage/models.py backend/tests/storage/test_models_score.py
git commit -m "feat: add Score SQLAlchemy model for multi-factor scoring"
```

---

## Task A2: Score / Portfolio Pydantic schemas

**Files:**
- Create: `backend/src/alpha_lab/schemas/score.py`
- Create: `backend/src/alpha_lab/schemas/portfolio.py`
- Test: `backend/tests/schemas/test_score.py`
- Test: `backend/tests/schemas/test_portfolio.py`

- [ ] **Step 1: 寫 `schemas/score.py`**

```python
"""多因子評分 Pydantic schemas。"""

from datetime import date

from pydantic import BaseModel, Field


class FactorBreakdown(BaseModel):
    """單檔的四因子分數與總分。"""

    symbol: str = Field(..., min_length=1, max_length=10)
    calc_date: date
    value_score: float | None = None
    growth_score: float | None = None
    dividend_score: float | None = None
    quality_score: float | None = None
    total_score: float | None = None


class ScoreResponse(BaseModel):
    """`GET /api/stocks/{symbol}/score` 回應。"""

    symbol: str
    latest: FactorBreakdown | None = None
```

- [ ] **Step 2: 寫 `schemas/portfolio.py`**

```python
"""組合推薦 Pydantic schemas。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from alpha_lab.schemas.score import FactorBreakdown

Style = Literal["conservative", "balanced", "aggressive"]


class Holding(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str
    weight: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: FactorBreakdown


class Portfolio(BaseModel):
    style: Style
    label: str  # 「保守組」等中文
    is_top_pick: bool = False
    holdings: list[Holding]
    expected_yield: float | None = None  # %
    risk_score: float | None = None  # 0-100，越高越高風險
    reasoning_ref: str | None = None  # Phase 4 填入報告 id


class RecommendResponse(BaseModel):
    generated_at: datetime
    calc_date: str  # "2026-04-15"
    portfolios: list[Portfolio]
```

- [ ] **Step 3: 寫對應測試**

```python
# backend/tests/schemas/test_score.py
from datetime import date

from alpha_lab.schemas.score import FactorBreakdown, ScoreResponse


def test_factor_breakdown_optional_fields() -> None:
    fb = FactorBreakdown(symbol="2330", calc_date=date(2026, 4, 15))
    assert fb.total_score is None


def test_score_response_with_latest() -> None:
    resp = ScoreResponse(
        symbol="2330",
        latest=FactorBreakdown(
            symbol="2330",
            calc_date=date(2026, 4, 15),
            value_score=70,
            total_score=70,
        ),
    )
    assert resp.latest is not None
    assert resp.latest.value_score == 70
```

```python
# backend/tests/schemas/test_portfolio.py
from datetime import date, datetime

from alpha_lab.schemas.portfolio import Holding, Portfolio, RecommendResponse
from alpha_lab.schemas.score import FactorBreakdown


def test_portfolio_with_holdings() -> None:
    fb = FactorBreakdown(symbol="2330", calc_date=date(2026, 4, 15), total_score=80)
    h = Holding(symbol="2330", name="台積電", weight=0.3, score_breakdown=fb)
    p = Portfolio(
        style="balanced",
        label="平衡組",
        is_top_pick=True,
        holdings=[h],
        expected_yield=4.2,
        risk_score=45.0,
    )
    assert p.is_top_pick
    assert p.holdings[0].weight == 0.3


def test_recommend_response() -> None:
    resp = RecommendResponse(
        generated_at=datetime(2026, 4, 15, 20, 0, 0),
        calc_date="2026-04-15",
        portfolios=[],
    )
    assert resp.calc_date == "2026-04-15"
```

- [ ] **Step 4: 執行並驗證**

Run: `cd backend && pytest tests/schemas/test_score.py tests/schemas/test_portfolio.py -v`
Expected: PASS

- [ ] **Step 5: 靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 error

- [ ] **Step 6: commit**

```bash
git add backend/src/alpha_lab/schemas/score.py backend/src/alpha_lab/schemas/portfolio.py backend/tests/schemas/test_score.py backend/tests/schemas/test_portfolio.py
git commit -m "feat: add Score and Portfolio Pydantic schemas"
```

---

## Task A3: Factor engine scaffold + 百分位歸一化工具

**Files:**
- Create: `backend/src/alpha_lab/analysis/__init__.py`（確認存在，若已有則略）
- Create: `backend/src/alpha_lab/analysis/normalize.py`
- Test: `backend/tests/analysis/test_normalize.py`

- [ ] **Step 1: 寫測試**

```python
# backend/tests/analysis/test_normalize.py
"""驗證百分位歸一化：最小→0、最大→100、線性內插。"""

import math

from alpha_lab.analysis.normalize import percentile_rank, percentile_rank_inverted


def test_percentile_rank_extremes() -> None:
    values = {"A": 10.0, "B": 20.0, "C": 30.0}
    out = percentile_rank(values)
    assert out["A"] == 0.0
    assert out["C"] == 100.0
    assert 0 < out["B"] < 100


def test_percentile_rank_handles_ties() -> None:
    values = {"A": 10.0, "B": 10.0, "C": 30.0}
    out = percentile_rank(values)
    assert out["A"] == out["B"]
    assert out["C"] == 100.0


def test_percentile_rank_skips_none() -> None:
    values = {"A": 10.0, "B": None, "C": 30.0}
    out = percentile_rank(values)
    assert out["B"] is None
    assert out["A"] == 0.0
    assert out["C"] == 100.0


def test_percentile_rank_inverted_lower_is_better() -> None:
    # PE 越低越好：10 應拿到 100、30 應拿到 0
    values = {"A": 10.0, "B": 20.0, "C": 30.0}
    out = percentile_rank_inverted(values)
    assert out["A"] == 100.0
    assert out["C"] == 0.0


def test_percentile_rank_single_value() -> None:
    out = percentile_rank({"A": 10.0})
    assert out["A"] == 50.0  # 單一值給中位數
```

- [ ] **Step 2: 執行測試（應失敗）**

Run: `cd backend && pytest tests/analysis/test_normalize.py -v`
Expected: FAIL

- [ ] **Step 3: 實作 `normalize.py`**

```python
"""橫截面百分位歸一化工具。

同一 calc_date 所有 symbol 一起排名，轉成 0-100 分。
- percentile_rank: 值越大分數越高（適用 ROE、營收 YoY）
- percentile_rank_inverted: 值越小分數越高（適用 PE、PB、負債比）

None 會被保留為 None（不參與排名）。
"""

from __future__ import annotations


def _rank_core(values: dict[str, float | None]) -> dict[str, float | None]:
    items = [(k, v) for k, v in values.items() if v is not None]
    if not items:
        return dict.fromkeys(values)
    if len(items) == 1:
        out: dict[str, float | None] = dict.fromkeys(values)
        out[items[0][0]] = 50.0
        return out

    sorted_items = sorted(items, key=lambda kv: kv[1])
    n = len(sorted_items)
    # 先算每個 index 對應的分數；遇到同值（ties）取平均 rank
    scores: dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_items[j + 1][1] == sorted_items[i][1]:
            j += 1
        # ranks i..j 共享一個分數
        avg_rank = (i + j) / 2
        pct = (avg_rank / (n - 1)) * 100.0 if n > 1 else 50.0
        for k in range(i, j + 1):
            scores[sorted_items[k][0]] = pct
        i = j + 1

    result: dict[str, float | None] = dict.fromkeys(values)
    for k, v in scores.items():
        result[k] = v
    return result


def percentile_rank(values: dict[str, float | None]) -> dict[str, float | None]:
    """值越大分數越高。"""
    return _rank_core(values)


def percentile_rank_inverted(
    values: dict[str, float | None],
) -> dict[str, float | None]:
    """值越小分數越高（用於 PE、PB、負債比等）。"""
    ranked = _rank_core(values)
    return {k: (100.0 - v if v is not None else None) for k, v in ranked.items()}
```

- [ ] **Step 4: 驗證通過**

Run: `cd backend && pytest tests/analysis/test_normalize.py -v`
Expected: PASS

- [ ] **Step 5: 靜態檢查**

Run: `cd backend && ruff check . && mypy src`
Expected: 0 error

- [ ] **Step 6: commit**

```bash
git add backend/src/alpha_lab/analysis/normalize.py backend/tests/analysis/
git commit -m "feat: add cross-sectional percentile normalization for factor scoring"
```

---

**🛑 群組 A 驗收節點** — 停下等使用者驗證 `Score` model、Pydantic schemas、`normalize` 工具皆可用。使用者回報「A 驗證通過」後才進入群組 B。

---

## Task B1: Value 因子（PE、PB）

**Files:**
- Create: `backend/src/alpha_lab/analysis/factor_value.py`
- Test: `backend/tests/analysis/test_factor_value.py`

**背景**：
- **PE** = price / eps_ttm；eps_ttm 為近四季 EPS 加總（從 `financial_statements.statement_type='income'` 讀）
- **PB** = price / book_per_share；book_per_share = (total_equity / shares_outstanding)。shares_outstanding 未存於 DB → **簡化**：先用 `total_equity / revenue_per_share_proxy` 的近似，或採 price-to-book 無法算時設 `None`。為避免引入新欄位，Phase 3 先以「PB unavailable → Value 只用 PE」做退化（PB 分數 = None 會在 factor_value 內被忽略）。實測時若 PB 全為 None，value_score = pe_score。

- [ ] **Step 1: 寫測試**

```python
# backend/tests/analysis/test_factor_value.py
"""Value 因子：PE 越低分越高，PB 同理；None 值被忽略。"""

from datetime import date

from alpha_lab.analysis.factor_value import compute_value_scores


def test_compute_value_scores_pe_only() -> None:
    snapshot = {
        "2330": {"pe": 15.0, "pb": None},
        "2454": {"pe": 20.0, "pb": None},
        "1301": {"pe": 25.0, "pb": None},
    }
    out = compute_value_scores(snapshot)
    # PE 最低 = 2330 → 100；PE 最高 = 1301 → 0
    assert out["2330"] == 100.0
    assert out["1301"] == 0.0


def test_compute_value_scores_none_passthrough() -> None:
    snapshot = {
        "2330": {"pe": None, "pb": None},
        "2454": {"pe": 20.0, "pb": None},
    }
    out = compute_value_scores(snapshot)
    assert out["2330"] is None
    assert out["2454"] == 50.0


def test_compute_value_scores_pe_and_pb_averaged() -> None:
    snapshot = {
        "2330": {"pe": 15.0, "pb": 5.0},
        "2454": {"pe": 25.0, "pb": 2.0},
    }
    out = compute_value_scores(snapshot)
    # 2330: pe=100, pb=0 → avg 50
    # 2454: pe=0, pb=100 → avg 50
    assert out["2330"] == 50.0
    assert out["2454"] == 50.0
```

- [ ] **Step 2: 執行（應失敗）**

Run: `cd backend && pytest tests/analysis/test_factor_value.py -v`
Expected: FAIL

- [ ] **Step 3: 實作**

```python
"""Value 因子：PE + PB，低者為佳。

Snapshot 格式：
    {symbol: {"pe": float | None, "pb": float | None}}

回傳：
    {symbol: value_score (0-100) | None}

規則：PE 與 PB 各自做 percentile_rank_inverted（低者得高分），
      取可用因子的平均；若兩者皆 None → None。
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank_inverted


def compute_value_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    pe_values = {s: v.get("pe") for s, v in snapshot.items()}
    pb_values = {s: v.get("pb") for s, v in snapshot.items()}

    pe_scores = percentile_rank_inverted(pe_values)
    pb_scores = percentile_rank_inverted(pb_values)

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [s for s in (pe_scores[sym], pb_scores[sym]) if s is not None]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
```

- [ ] **Step 4: 驗證**

Run: `cd backend && pytest tests/analysis/test_factor_value.py -v`
Expected: PASS

- [ ] **Step 5: 靜態檢查**

Run: `cd backend && ruff check . && mypy src`

- [ ] **Step 6: commit**

```bash
git add backend/src/alpha_lab/analysis/factor_value.py backend/tests/analysis/test_factor_value.py
git commit -m "feat: add Value factor scoring (PE, PB with inverted percentile)"
```

---

## Task B2: Growth 因子（營收 YoY、EPS YoY）

**Files:**
- Create: `backend/src/alpha_lab/analysis/factor_growth.py`
- Test: `backend/tests/analysis/test_factor_growth.py`

- [ ] **Step 1: 測試**

```python
# backend/tests/analysis/test_factor_growth.py
from alpha_lab.analysis.factor_growth import compute_growth_scores


def test_higher_yoy_higher_score() -> None:
    snapshot = {
        "A": {"revenue_yoy": 0.30, "eps_yoy": 0.50},
        "B": {"revenue_yoy": 0.10, "eps_yoy": 0.10},
        "C": {"revenue_yoy": -0.10, "eps_yoy": -0.20},
    }
    out = compute_growth_scores(snapshot)
    assert out["A"] == 100.0
    assert out["C"] == 0.0


def test_none_ignored() -> None:
    snapshot = {
        "A": {"revenue_yoy": 0.3, "eps_yoy": None},
        "B": {"revenue_yoy": 0.1, "eps_yoy": 0.1},
    }
    out = compute_growth_scores(snapshot)
    # A 只有 revenue_yoy 分數可用
    assert out["A"] is not None
    assert out["B"] is not None
```

- [ ] **Step 2: 實作**

```python
"""Growth 因子：營收 YoY + EPS YoY，高者為佳。

Snapshot 格式：
    {symbol: {"revenue_yoy": float | None, "eps_yoy": float | None}}
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank


def compute_growth_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    rev = {s: v.get("revenue_yoy") for s, v in snapshot.items()}
    eps = {s: v.get("eps_yoy") for s, v in snapshot.items()}

    rev_scores = percentile_rank(rev)
    eps_scores = percentile_rank(eps)

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [s for s in (rev_scores[sym], eps_scores[sym]) if s is not None]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
```

- [ ] **Step 3: 驗證 + 靜態檢查**

Run: `cd backend && pytest tests/analysis/test_factor_growth.py -v && ruff check . && mypy src`

- [ ] **Step 4: commit**

```bash
git add backend/src/alpha_lab/analysis/factor_growth.py backend/tests/analysis/test_factor_growth.py
git commit -m "feat: add Growth factor scoring (revenue YoY, EPS YoY)"
```

---

**🛑 群組 B 驗收節點** — 停下等使用者驗證 Value / Growth 因子函式。

---

## Task C1: Dividend 因子（當期殖利率）

**Files:**
- Create: `backend/src/alpha_lab/analysis/factor_dividend.py`
- Test: `backend/tests/analysis/test_factor_dividend.py`

**備註**：連續配息年數、穩定度留 Phase 4/5；本 Phase 只算當期殖利率。殖利率 = last_dividend_per_share / current_price。last_dividend_per_share 若 DB 無現成欄位，先從 `financial_statements` raw_json_text 或新增 `dividend_per_share` 欄位；為避免 schema migration，**初版直接從 `RevenueMonthly` 等現有資料無法取得 → Dividend 因子 snapshot 由 caller 提供 `{symbol: dividend_yield}`**，caller（pipeline）暫以 `None` 填滿；後續 Phase 補資料來源時再接。

- [ ] **Step 1: 測試**

```python
# backend/tests/analysis/test_factor_dividend.py
from alpha_lab.analysis.factor_dividend import compute_dividend_scores


def test_higher_yield_higher_score() -> None:
    snapshot = {"A": 0.05, "B": 0.03, "C": 0.01}
    out = compute_dividend_scores(snapshot)
    assert out["A"] == 100.0
    assert out["C"] == 0.0


def test_none_passthrough() -> None:
    out = compute_dividend_scores({"A": None, "B": 0.03})
    assert out["A"] is None
    assert out["B"] == 50.0
```

- [ ] **Step 2: 實作**

```python
"""Dividend 因子：當期殖利率，高者為佳。

Snapshot 格式：{symbol: yield | None}
yield 以小數表示（0.05 = 5%）。
連續配息年數、穩定度留後續 Phase。
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank


def compute_dividend_scores(
    snapshot: dict[str, float | None],
) -> dict[str, float | None]:
    return percentile_rank(snapshot)
```

- [ ] **Step 3: 驗證 + 靜態**

Run: `cd backend && pytest tests/analysis/test_factor_dividend.py -v && ruff check . && mypy src`

- [ ] **Step 4: commit**

```bash
git add backend/src/alpha_lab/analysis/factor_dividend.py backend/tests/analysis/test_factor_dividend.py
git commit -m "feat: add Dividend factor scoring (current yield)"
```

---

## Task C2: Quality 因子（ROE、毛利率、負債比）

**Files:**
- Create: `backend/src/alpha_lab/analysis/factor_quality.py`
- Test: `backend/tests/analysis/test_factor_quality.py`

**備註**：FCF 留 Task F3 補；本 task 先做 3 指標。

- [ ] **Step 1: 測試**

```python
# backend/tests/analysis/test_factor_quality.py
from alpha_lab.analysis.factor_quality import compute_quality_scores


def test_quality_higher_roe_better() -> None:
    snapshot = {
        "A": {"roe": 0.25, "gross_margin": 0.5, "debt_ratio": 0.3},
        "B": {"roe": 0.10, "gross_margin": 0.3, "debt_ratio": 0.6},
    }
    out = compute_quality_scores(snapshot)
    # A ROE 高、毛利高、負債低 → 總分高
    assert out["A"] == 100.0
    assert out["B"] == 0.0


def test_quality_none_ignored() -> None:
    snapshot = {
        "A": {"roe": 0.25, "gross_margin": None, "debt_ratio": None},
        "B": {"roe": 0.10, "gross_margin": None, "debt_ratio": None},
    }
    out = compute_quality_scores(snapshot)
    assert out["A"] == 100.0
    assert out["B"] == 0.0
```

- [ ] **Step 2: 實作**

```python
"""Quality 因子：ROE + 毛利率（高者佳）+ 負債比（低者佳）。

FCF 於 Task F3 加入。
Snapshot 格式：
    {symbol: {"roe": f | None, "gross_margin": f | None, "debt_ratio": f | None}}
"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank, percentile_rank_inverted


def compute_quality_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    roe = percentile_rank({s: v.get("roe") for s, v in snapshot.items()})
    gm = percentile_rank({s: v.get("gross_margin") for s, v in snapshot.items()})
    dr = percentile_rank_inverted(
        {s: v.get("debt_ratio") for s, v in snapshot.items()}
    )

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [s for s in (roe[sym], gm[sym], dr[sym]) if s is not None]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
```

- [ ] **Step 3: 驗證 + 靜態**

Run: `cd backend && pytest tests/analysis/test_factor_quality.py -v && ruff check . && mypy src`

- [ ] **Step 4: commit**

```bash
git add backend/src/alpha_lab/analysis/factor_quality.py backend/tests/analysis/test_factor_quality.py
git commit -m "feat: add Quality factor scoring (ROE, gross margin, debt ratio)"
```

---

**🛑 群組 C 驗收節點** — 停下等使用者驗證 Dividend / Quality 因子。

---

## Task D1: 風格權重 + 總分計算 + scoring pipeline

**Files:**
- Create: `backend/src/alpha_lab/analysis/weights.py`
- Create: `backend/src/alpha_lab/analysis/pipeline.py`
- Test: `backend/tests/analysis/test_weights.py`
- Test: `backend/tests/analysis/test_pipeline.py`

- [ ] **Step 1: 寫 `weights.py`**

```python
"""四因子風格權重。總和為 1。

權重設計（初版）：
- conservative：Dividend + Quality 重
- balanced：四因子均衡
- aggressive：Growth 重
"""

from __future__ import annotations

from typing import Literal, TypedDict

Style = Literal["conservative", "balanced", "aggressive"]


class FactorWeights(TypedDict):
    value: float
    growth: float
    dividend: float
    quality: float


STYLE_WEIGHTS: dict[Style, FactorWeights] = {
    "conservative": {"value": 0.20, "growth": 0.10, "dividend": 0.35, "quality": 0.35},
    "balanced": {"value": 0.25, "growth": 0.25, "dividend": 0.25, "quality": 0.25},
    "aggressive": {"value": 0.15, "growth": 0.50, "dividend": 0.05, "quality": 0.30},
}


def weighted_total(
    value: float | None,
    growth: float | None,
    dividend: float | None,
    quality: float | None,
    weights: FactorWeights,
) -> float | None:
    """以指定權重計算總分；None 因子會被略過，剩餘權重再正規化。"""

    pairs = [
        (value, weights["value"]),
        (growth, weights["growth"]),
        (dividend, weights["dividend"]),
        (quality, weights["quality"]),
    ]
    usable = [(s, w) for s, w in pairs if s is not None]
    if not usable:
        return None
    total_w = sum(w for _, w in usable)
    if total_w == 0:
        return None
    return sum(s * w for s, w in usable) / total_w
```

- [ ] **Step 2: `weights.py` 測試**

```python
# backend/tests/analysis/test_weights.py
from alpha_lab.analysis.weights import STYLE_WEIGHTS, weighted_total


def test_style_weights_sum_to_one() -> None:
    for _, w in STYLE_WEIGHTS.items():
        assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weighted_total_all_equal() -> None:
    out = weighted_total(80, 80, 80, 80, STYLE_WEIGHTS["balanced"])
    assert out == 80.0


def test_weighted_total_none_skipped() -> None:
    out = weighted_total(100, None, None, None, STYLE_WEIGHTS["balanced"])
    assert out == 100.0  # 只剩 value


def test_weighted_total_all_none() -> None:
    out = weighted_total(None, None, None, None, STYLE_WEIGHTS["balanced"])
    assert out is None
```

- [ ] **Step 3: 寫 `pipeline.py`（scoring pipeline：讀 DB 快照 → 算四因子 → 算 balanced total → upsert `scores`）**

```python
"""Scoring pipeline：從 DB 拉快照、算四因子 + balanced 總分、upsert `scores` 表。

Balanced total 儲存進 `scores.total_score`；其他風格在 recommend 時
runtime 以 `weighted_total` 重新算（避免三倍儲存）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from alpha_lab.analysis.factor_dividend import compute_dividend_scores
from alpha_lab.analysis.factor_growth import compute_growth_scores
from alpha_lab.analysis.factor_quality import compute_quality_scores
from alpha_lab.analysis.factor_value import compute_value_scores
from alpha_lab.analysis.weights import STYLE_WEIGHTS, weighted_total
from alpha_lab.storage.models import (
    FinancialStatement,
    PriceDaily,
    RevenueMonthly,
    Score,
    Stock,
)


@dataclass
class Snapshot:
    """單一 calc_date 的快照，供四因子使用。"""

    value: dict[str, dict[str, float | None]]
    growth: dict[str, dict[str, float | None]]
    dividend: dict[str, float | None]
    quality: dict[str, dict[str, float | None]]


def build_snapshot(session: Session, calc_date: date) -> Snapshot:
    """從 DB 組合當日快照。

    - PE = close / eps_ttm（近四季 EPS 加總）
    - PB 目前 None（缺 shares_outstanding，Phase 4+ 補）
    - revenue_yoy：近 12 月營收 vs 前 12 月
    - eps_yoy：近四季 EPS 總和 vs 前四季
    - dividend_yield：目前 None（資料來源待 Phase 4/5 補）
    - ROE = net_income_ttm / total_equity
    - gross_margin = gross_profit_ttm / revenue_ttm
    - debt_ratio = total_liabilities / total_assets
    """

    symbols = [row[0] for row in session.execute(select(Stock.symbol)).all()]
    value: dict[str, dict[str, float | None]] = {}
    growth: dict[str, dict[str, float | None]] = {}
    dividend: dict[str, float | None] = {}
    quality: dict[str, dict[str, float | None]] = {}

    for sym in symbols:
        price_row = session.execute(
            select(PriceDaily.close)
            .where(PriceDaily.symbol == sym, PriceDaily.trade_date <= calc_date)
            .order_by(PriceDaily.trade_date.desc())
            .limit(1)
        ).first()
        close = float(price_row[0]) if price_row else None

        income_rows = session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == sym,
                FinancialStatement.statement_type == "income",
            )
            .order_by(FinancialStatement.period.desc())
            .limit(8)
        ).scalars().all()

        balance_row = session.execute(
            select(FinancialStatement)
            .where(
                FinancialStatement.symbol == sym,
                FinancialStatement.statement_type == "balance",
            )
            .order_by(FinancialStatement.period.desc())
            .limit(1)
        ).scalar_one_or_none()

        eps_ttm = _sum_n([r.eps for r in income_rows[:4]])
        prev_eps_ttm = _sum_n([r.eps for r in income_rows[4:8]])
        rev_ttm = _sum_n([r.revenue for r in income_rows[:4]])
        prev_rev_ttm = _sum_n([r.revenue for r in income_rows[4:8]])
        gross_ttm = _sum_n([r.gross_profit for r in income_rows[:4]])
        ni_ttm = _sum_n([r.net_income for r in income_rows[:4]])

        pe = (close / eps_ttm) if close and eps_ttm and eps_ttm > 0 else None

        eps_yoy = (
            (eps_ttm - prev_eps_ttm) / abs(prev_eps_ttm)
            if eps_ttm is not None and prev_eps_ttm not in (None, 0)
            else None
        )

        rev_12m = _sum_revenue_12m(session, sym, calc_date, offset=0)
        rev_prev = _sum_revenue_12m(session, sym, calc_date, offset=12)
        revenue_yoy = (
            (rev_12m - rev_prev) / rev_prev
            if rev_12m is not None and rev_prev not in (None, 0)
            else None
        )

        roe = (
            ni_ttm / balance_row.total_equity
            if ni_ttm is not None
            and balance_row is not None
            and balance_row.total_equity
            else None
        )
        gross_margin = (
            gross_ttm / rev_ttm if gross_ttm is not None and rev_ttm else None
        )
        debt_ratio = (
            balance_row.total_liabilities / balance_row.total_assets
            if balance_row is not None
            and balance_row.total_liabilities is not None
            and balance_row.total_assets
            else None
        )

        value[sym] = {"pe": pe, "pb": None}
        growth[sym] = {"revenue_yoy": revenue_yoy, "eps_yoy": eps_yoy}
        dividend[sym] = None
        quality[sym] = {
            "roe": roe,
            "gross_margin": gross_margin,
            "debt_ratio": debt_ratio,
        }

    return Snapshot(value=value, growth=growth, dividend=dividend, quality=quality)


def _sum_n(items: list[float | int | None]) -> float | None:
    vals = [x for x in items if x is not None]
    if len(vals) < len(items) or not vals:
        return None
    return float(sum(vals))


def _sum_revenue_12m(
    session: Session, symbol: str, calc_date: date, offset: int
) -> float | None:
    rows = session.execute(
        select(RevenueMonthly.revenue)
        .where(RevenueMonthly.symbol == symbol)
        .order_by(RevenueMonthly.year.desc(), RevenueMonthly.month.desc())
        .offset(offset)
        .limit(12)
    ).all()
    if len(rows) < 12:
        return None
    return float(sum(r[0] for r in rows))


def score_all(session: Session, calc_date: date) -> int:
    """算分並 upsert 到 scores 表。回傳寫入筆數。"""

    snap = build_snapshot(session, calc_date)
    value_scores = compute_value_scores(snap.value)
    growth_scores = compute_growth_scores(snap.growth)
    dividend_scores = compute_dividend_scores(snap.dividend)
    quality_scores = compute_quality_scores(snap.quality)

    rows: list[dict[str, object]] = []
    for sym in snap.value:
        total = weighted_total(
            value_scores[sym],
            growth_scores[sym],
            dividend_scores[sym],
            quality_scores[sym],
            STYLE_WEIGHTS["balanced"],
        )
        rows.append(
            {
                "symbol": sym,
                "calc_date": calc_date,
                "value_score": value_scores[sym],
                "growth_score": growth_scores[sym],
                "dividend_score": dividend_scores[sym],
                "quality_score": quality_scores[sym],
                "total_score": total,
            }
        )

    if not rows:
        return 0

    stmt = sqlite_insert(Score).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "calc_date"],
        set_={
            "value_score": stmt.excluded.value_score,
            "growth_score": stmt.excluded.growth_score,
            "dividend_score": stmt.excluded.dividend_score,
            "quality_score": stmt.excluded.quality_score,
            "total_score": stmt.excluded.total_score,
        },
    )
    session.execute(stmt)
    session.commit()
    return len(rows)
```

- [ ] **Step 4: pipeline 測試（用 in-memory DB + fixture）**

```python
# backend/tests/analysis/test_pipeline.py
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alpha_lab.analysis.pipeline import score_all
from alpha_lab.storage.models import (
    Base,
    FinancialStatement,
    PriceDaily,
    RevenueMonthly,
    Score,
    Stock,
)


def _seed(session: Session) -> None:
    for sym, name in [("2330", "台積電"), ("2454", "聯發科"), ("1301", "台塑")]:
        session.add(Stock(symbol=sym, name=name))
        session.add(
            PriceDaily(
                symbol=sym,
                trade_date=date(2026, 4, 15),
                open=100,
                high=110,
                low=95,
                close=105,
                volume=1000,
            )
        )
        for q_idx, period in enumerate(
            ["2026Q1", "2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2"]
        ):
            session.add(
                FinancialStatement(
                    symbol=sym,
                    period=period,
                    statement_type="income",
                    revenue=100 + q_idx,
                    gross_profit=30,
                    net_income=20,
                    eps=2.0 if sym == "2330" else 1.0,
                )
            )
        session.add(
            FinancialStatement(
                symbol=sym,
                period="2026Q1",
                statement_type="balance",
                total_assets=1000,
                total_liabilities=400,
                total_equity=600,
            )
        )
        for year in (2025, 2026):
            for month in range(1, 13):
                session.add(
                    RevenueMonthly(
                        symbol=sym, year=year, month=month, revenue=10 + month
                    )
                )
    session.commit()


def test_score_all_writes_scores() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed(session)
        written = score_all(session, date(2026, 4, 15))
        assert written == 3

        rows = session.execute(select(Score)).scalars().all()
        assert len(rows) == 3
        # 2330 EPS 最高 → value_score 最高（PE 最低）
        row_2330 = next(r for r in rows if r.symbol == "2330")
        assert row_2330.value_score == 100.0
```

- [ ] **Step 5: 驗證 + 靜態**

Run: `cd backend && pytest tests/analysis/test_weights.py tests/analysis/test_pipeline.py -v && ruff check . && mypy src`

- [ ] **Step 6: commit**

```bash
git add backend/src/alpha_lab/analysis/weights.py backend/src/alpha_lab/analysis/pipeline.py backend/tests/analysis/test_weights.py backend/tests/analysis/test_pipeline.py
git commit -m "feat: add factor weights and scoring pipeline (build_snapshot + score_all)"
```

---

## Task D2: `scripts/compute_scores.py` CLI + `POST /api/jobs/collect` 支援 `job_type='score'`

**Files:**
- Create: `backend/scripts/compute_scores.py`
- Modify: `backend/src/alpha_lab/jobs/service.py`（加入 `score` job handler）
- Test: `backend/tests/scripts/test_compute_scores.py`
- Test: `backend/tests/jobs/test_service_score.py`

- [ ] **Step 1: 寫 CLI**

```python
# backend/scripts/compute_scores.py
"""手動觸發評分 pipeline。

用法：
    python scripts/compute_scores.py [--date YYYY-MM-DD]

不帶 --date → 今天。
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

from alpha_lab.analysis.pipeline import score_all
from alpha_lab.storage.engine import get_session


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute factor scores")
    parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD")
    args = parser.parse_args()

    calc_date = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(UTC).date()
    )
    with get_session() as session:
        n = score_all(session, calc_date)
    print(f"Scored {n} symbols for {calc_date.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 在 `jobs/service.py` 加入 `score` handler（讀現有檔案再加 branch）**

先讀 `backend/src/alpha_lab/jobs/service.py` 確認現有 dispatch 結構，在 `JOB_HANDLERS` 字典或 dispatcher switch 內加入：

```python
# jobs/service.py 內新增 import
from datetime import date as _date

from alpha_lab.analysis.pipeline import score_all

# 在 handler dispatcher 加入：
def _handle_score(params: dict[str, object], session: Session) -> str:
    date_str = params.get("date")
    calc_date = (
        _date.fromisoformat(str(date_str))
        if isinstance(date_str, str)
        else _date.today()
    )
    n = score_all(session, calc_date)
    return f"scored {n} symbols"

# 註冊到 JOB_HANDLERS（或 if/elif 分支）
# "score": _handle_score
```

（如 `service.py` 實際結構與假設不同，以現有 dispatch 模式為準，加入 `score` 分支，簽名與其他 handler 對齊。）

- [ ] **Step 3: CLI 測試**

```python
# backend/tests/scripts/test_compute_scores.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_runs(tmp_path: Path, monkeypatch) -> None:
    # 這只是煙霧測試：-h 應成功
    repo_backend = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/compute_scores.py", "-h"],
        cwd=repo_backend,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Compute factor scores" in result.stdout
```

- [ ] **Step 4: jobs service 測試**

```python
# backend/tests/jobs/test_service_score.py
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alpha_lab.jobs.service import run_job  # 依實際命名，可能是 execute_job
from alpha_lab.storage.models import Base, Score, Stock


def test_run_score_job(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()
        summary = run_job(
            session,
            job_type="score",
            params={"date": "2026-04-15"},
        )
        assert "scored" in summary
        rows = session.execute(select(Score)).scalars().all()
        # 無 price/財報 → value_score/total 可能都 None，但 row 仍寫入
        assert len(rows) == 1
```

（若 `jobs.service` 實際 API 不同，把 test 改成呼叫實際 API；重點是驗 `job_type='score'` 可被處理。）

- [ ] **Step 5: 驗證 + 靜態**

Run: `cd backend && pytest tests/scripts/test_compute_scores.py tests/jobs/test_service_score.py -v && ruff check . && mypy src`

- [ ] **Step 6: commit**

```bash
git add backend/scripts/compute_scores.py backend/src/alpha_lab/jobs/service.py backend/tests/scripts/test_compute_scores.py backend/tests/jobs/test_service_score.py
git commit -m "feat: add compute_scores CLI and score job handler"
```

---

**🛑 群組 D 驗收節點** — 停下等使用者跑 CLI 驗證 `scores` 表有資料。

使用者驗收指引（CMD 格式）：

```cmd
REM 確認已有個股 + 財報 + 月營收資料（Phase 1/1.5 跑過）
cd backend
.venv\Scripts\python.exe scripts\compute_scores.py --date 2026-04-15

REM 查 scores 表
.venv\Scripts\python.exe -c "from alpha_lab.storage.engine import get_session; from alpha_lab.storage.models import Score; from sqlalchemy import select; s=get_session().__enter__(); print(s.execute(select(Score)).scalars().all()[:3])"
```

---

## Task E1: `GET /api/stocks/{symbol}/score`

**Files:**
- Modify: `backend/src/alpha_lab/api/routes/stocks.py`
- Test: `backend/tests/api/test_stocks_score.py`

- [ ] **Step 1: 測試**

```python
# backend/tests/api/test_stocks_score.py
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alpha_lab.api.main import app
from alpha_lab.storage.models import Score, Stock


def test_get_stock_score(test_session: Session, client: TestClient) -> None:
    test_session.add(Stock(symbol="2330", name="台積電"))
    test_session.add(
        Score(
            symbol="2330",
            calc_date=date(2026, 4, 15),
            value_score=70,
            growth_score=80,
            dividend_score=50,
            quality_score=90,
            total_score=72.5,
        )
    )
    test_session.commit()

    r = client.get("/api/stocks/2330/score")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "2330"
    assert data["latest"]["total_score"] == 72.5


def test_get_stock_score_none_if_absent(
    test_session: Session, client: TestClient
) -> None:
    test_session.add(Stock(symbol="9999", name="無評分"))
    test_session.commit()
    r = client.get("/api/stocks/9999/score")
    assert r.status_code == 200
    assert r.json()["latest"] is None
```

（假設 `test_session` / `client` fixture 已在 Phase 2 測試建起；若否，在 `conftest.py` 建。）

- [ ] **Step 2: 在 `routes/stocks.py` 加入 endpoint**

```python
# 在現有 router 加入：
from sqlalchemy import select

from alpha_lab.schemas.score import FactorBreakdown, ScoreResponse
from alpha_lab.storage.models import Score


@router.get("/{symbol}/score", response_model=ScoreResponse)
def get_stock_score(
    symbol: str, session: Session = Depends(get_db_session)
) -> ScoreResponse:
    row = session.execute(
        select(Score)
        .where(Score.symbol == symbol)
        .order_by(Score.calc_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return ScoreResponse(symbol=symbol, latest=None)
    return ScoreResponse(
        symbol=symbol,
        latest=FactorBreakdown(
            symbol=row.symbol,
            calc_date=row.calc_date,
            value_score=row.value_score,
            growth_score=row.growth_score,
            dividend_score=row.dividend_score,
            quality_score=row.quality_score,
            total_score=row.total_score,
        ),
    )
```

（依現有 `stocks.py` router 與 DI 寫法對齊。）

- [ ] **Step 3: 驗證 + 靜態**

Run: `cd backend && pytest tests/api/test_stocks_score.py -v && ruff check . && mypy src`

- [ ] **Step 4: commit**

```bash
git add backend/src/alpha_lab/api/routes/stocks.py backend/tests/api/test_stocks_score.py
git commit -m "feat: add GET /api/stocks/{symbol}/score endpoint"
```

---

## Task E2: Portfolio generator + `POST /api/portfolios/recommend`

**Files:**
- Create: `backend/src/alpha_lab/analysis/portfolio.py`
- Create: `backend/src/alpha_lab/api/routes/portfolios.py`
- Modify: `backend/src/alpha_lab/api/main.py`（註冊 router）
- Test: `backend/tests/analysis/test_portfolio.py`
- Test: `backend/tests/api/test_portfolios_recommend.py`

- [ ] **Step 1: 實作 `analysis/portfolio.py`**

```python
"""組合生成：讀最新 scores、依風格權重排序 + 產業分散 + 配置比例。

演算法：
1. 拉該 calc_date 所有 scores（排除 total_score=None 者）
2. 對每個風格：runtime 用 style 權重重算 total
3. 排序 Top 30
4. 產業分散：同產業最多 5 檔（掃描時捨棄超出者）
5. 取前 10 檔為最終持股
6. 權重 = softmax(total_score / 20)，並 cap 單檔 30%
"""

from __future__ import annotations

import math
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from alpha_lab.analysis.weights import STYLE_WEIGHTS, Style, weighted_total
from alpha_lab.schemas.portfolio import Holding, Portfolio
from alpha_lab.schemas.score import FactorBreakdown
from alpha_lab.storage.models import Score, Stock

STYLE_LABELS: dict[Style, str] = {
    "conservative": "保守組",
    "balanced": "平衡組",
    "aggressive": "積極組",
}
TOP_N_CANDIDATES = 30
MAX_PER_INDUSTRY = 5
FINAL_HOLDINGS = 10
MAX_WEIGHT = 0.30


def latest_calc_date(session: Session) -> date | None:
    row = session.execute(
        select(Score.calc_date).order_by(Score.calc_date.desc()).limit(1)
    ).first()
    return row[0] if row else None


def generate_portfolio(session: Session, style: Style, calc_date: date) -> Portfolio:
    weights = STYLE_WEIGHTS[style]

    rows = session.execute(
        select(Score, Stock)
        .join(Stock, Stock.symbol == Score.symbol)
        .where(Score.calc_date == calc_date)
    ).all()

    scored: list[tuple[Score, Stock, float]] = []
    for s, stk in rows:
        total = weighted_total(
            s.value_score,
            s.growth_score,
            s.dividend_score,
            s.quality_score,
            weights,
        )
        if total is None:
            continue
        scored.append((s, stk, total))

    scored.sort(key=lambda t: t[2], reverse=True)
    top_candidates = scored[:TOP_N_CANDIDATES]

    # 產業分散
    per_industry: dict[str, int] = {}
    filtered: list[tuple[Score, Stock, float]] = []
    for s, stk, total in top_candidates:
        ind = stk.industry or "未分類"
        if per_industry.get(ind, 0) >= MAX_PER_INDUSTRY:
            continue
        filtered.append((s, stk, total))
        per_industry[ind] = per_industry.get(ind, 0) + 1
        if len(filtered) >= FINAL_HOLDINGS:
            break

    # Softmax 權重（以 total_score/20 為 temperature-scaled logits）
    if not filtered:
        return Portfolio(
            style=style,
            label=STYLE_LABELS[style],
            is_top_pick=(style == "balanced"),
            holdings=[],
        )

    logits = [t / 20.0 for _, _, t in filtered]
    max_l = max(logits)
    exps = [math.exp(lg - max_l) for lg in logits]
    z = sum(exps)
    raw_weights = [e / z for e in exps]

    # Cap 單檔 30%；超出的部分分配到其他檔（簡化：均分到未被 cap 的）
    capped = _cap_weights(raw_weights, MAX_WEIGHT)

    holdings: list[Holding] = []
    for (s, stk, total), w in zip(filtered, capped, strict=True):
        holdings.append(
            Holding(
                symbol=stk.symbol,
                name=stk.name,
                weight=round(w, 4),
                score_breakdown=FactorBreakdown(
                    symbol=s.symbol,
                    calc_date=s.calc_date,
                    value_score=s.value_score,
                    growth_score=s.growth_score,
                    dividend_score=s.dividend_score,
                    quality_score=s.quality_score,
                    total_score=total,
                ),
            )
        )

    return Portfolio(
        style=style,
        label=STYLE_LABELS[style],
        is_top_pick=(style == "balanced"),
        holdings=holdings,
        expected_yield=None,  # Phase 4 接股利資料後計算
        risk_score=_risk_score(filtered),
        reasoning_ref=None,
    )


def _cap_weights(weights: list[float], cap: float) -> list[float]:
    # 簡化：迭代至多 5 次，把超過 cap 的部分平均給未 cap 的
    w = list(weights)
    for _ in range(5):
        over = [i for i, x in enumerate(w) if x > cap]
        if not over:
            break
        excess = sum(w[i] - cap for i in over)
        under = [i for i, x in enumerate(w) if x < cap]
        if not under:
            break
        for i in over:
            w[i] = cap
        add = excess / len(under)
        for i in under:
            w[i] += add
    s = sum(w)
    return [x / s for x in w]


def _risk_score(items: list[tuple[Score, Stock, float]]) -> float | None:
    # 粗估：100 - 平均 quality_score（品質越高風險越低）；無 quality 則 None
    qs = [s.quality_score for s, _, _ in items if s.quality_score is not None]
    if not qs:
        return None
    return round(100.0 - sum(qs) / len(qs), 1)
```

- [ ] **Step 2: 實作 `routes/portfolios.py`**

```python
"""/api/portfolios 路由。"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from alpha_lab.analysis.portfolio import generate_portfolio, latest_calc_date
from alpha_lab.analysis.weights import STYLE_WEIGHTS, Style
from alpha_lab.api.deps import get_db_session  # 依實際 DI 命名
from alpha_lab.schemas.portfolio import Portfolio, RecommendResponse

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    style: Style | None = None,
    session: Session = Depends(get_db_session),
) -> RecommendResponse:
    calc_date = latest_calc_date(session)
    if calc_date is None:
        raise HTTPException(
            status_code=409,
            detail="no scores available; run POST /api/jobs/collect with job_type='score' first",
        )

    styles: list[Style]
    if style is None:
        styles = list(STYLE_WEIGHTS.keys())
    else:
        styles = [style]

    portfolios: list[Portfolio] = [
        generate_portfolio(session, s, calc_date) for s in styles
    ]
    return RecommendResponse(
        generated_at=datetime.now(UTC),
        calc_date=calc_date.isoformat(),
        portfolios=portfolios,
    )
```

- [ ] **Step 3: 在 `api/main.py` 註冊 router**

依現有 main.py 結構，在其他 `include_router(...)` 下加一行：

```python
from alpha_lab.api.routes import portfolios as portfolios_routes

app.include_router(portfolios_routes.router)
```

- [ ] **Step 4: 寫測試**

```python
# backend/tests/analysis/test_portfolio.py
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alpha_lab.analysis.portfolio import generate_portfolio, latest_calc_date
from alpha_lab.storage.models import Base, Score, Stock


def _seed_scores(session: Session, n: int = 12) -> None:
    for i in range(n):
        sym = f"A{i:03d}"
        session.add(Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 3}"))
        session.add(
            Score(
                symbol=sym,
                calc_date=date(2026, 4, 15),
                value_score=50 + i,
                growth_score=50 + i,
                dividend_score=50 + i,
                quality_score=50 + i,
                total_score=50 + i,
            )
        )
    session.commit()


def test_latest_calc_date() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        _seed_scores(s, 3)
        assert latest_calc_date(s) == date(2026, 4, 15)


def test_generate_portfolio_balanced_is_top_pick() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        _seed_scores(s, 12)
        p = generate_portfolio(s, "balanced", date(2026, 4, 15))
        assert p.is_top_pick is True
        assert p.style == "balanced"
        assert len(p.holdings) <= 10
        assert abs(sum(h.weight for h in p.holdings) - 1.0) < 1e-6
        assert all(h.weight <= 0.30 + 1e-6 for h in p.holdings)


def test_industry_diversification() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        # 全 30 檔同產業 → 最多只留 5 檔
        for i in range(30):
            sym = f"B{i:03d}"
            s.add(Stock(symbol=sym, name=f"同業{i}", industry="半導體"))
            s.add(
                Score(
                    symbol=sym,
                    calc_date=date(2026, 4, 15),
                    value_score=50 + i,
                    growth_score=50 + i,
                    dividend_score=50 + i,
                    quality_score=50 + i,
                    total_score=50 + i,
                )
            )
        s.commit()
        p = generate_portfolio(s, "balanced", date(2026, 4, 15))
        assert len(p.holdings) == 5
```

```python
# backend/tests/api/test_portfolios_recommend.py
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alpha_lab.storage.models import Score, Stock


def test_recommend_all_styles(
    test_session: Session, client: TestClient
) -> None:
    for i in range(12):
        sym = f"C{i:03d}"
        test_session.add(Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 3}"))
        test_session.add(
            Score(
                symbol=sym,
                calc_date=date(2026, 4, 15),
                value_score=50 + i,
                growth_score=50 + i,
                dividend_score=50 + i,
                quality_score=50 + i,
                total_score=50 + i,
            )
        )
    test_session.commit()

    r = client.post("/api/portfolios/recommend")
    assert r.status_code == 200
    data = r.json()
    assert len(data["portfolios"]) == 3
    styles = [p["style"] for p in data["portfolios"]]
    assert set(styles) == {"conservative", "balanced", "aggressive"}
    balanced = next(p for p in data["portfolios"] if p["style"] == "balanced")
    assert balanced["is_top_pick"] is True


def test_recommend_single_style(test_session: Session, client: TestClient) -> None:
    test_session.add(Stock(symbol="2330", name="台積電", industry="半導體"))
    test_session.add(
        Score(
            symbol="2330",
            calc_date=date(2026, 4, 15),
            value_score=80,
            growth_score=80,
            dividend_score=80,
            quality_score=80,
            total_score=80,
        )
    )
    test_session.commit()

    r = client.post("/api/portfolios/recommend?style=aggressive")
    assert r.status_code == 200
    data = r.json()
    assert len(data["portfolios"]) == 1
    assert data["portfolios"][0]["style"] == "aggressive"


def test_recommend_409_when_no_scores(
    test_session: Session, client: TestClient
) -> None:
    r = client.post("/api/portfolios/recommend")
    assert r.status_code == 409
```

- [ ] **Step 5: 驗證 + 靜態**

Run: `cd backend && pytest tests/analysis/test_portfolio.py tests/api/test_portfolios_recommend.py -v && ruff check . && mypy src`

- [ ] **Step 6: commit**

```bash
git add backend/src/alpha_lab/analysis/portfolio.py backend/src/alpha_lab/api/routes/portfolios.py backend/src/alpha_lab/api/main.py backend/tests/analysis/test_portfolio.py backend/tests/api/test_portfolios_recommend.py
git commit -m "feat: add portfolio generator and POST /api/portfolios/recommend"
```

---

## Task E3: 手動驗收 smoke test

- [ ] **Step 1: 使用者驗收指引**

```cmd
REM 啟動後端
cd backend
.venv\Scripts\uvicorn.exe alpha_lab.api.main:app --reload

REM 另開 cmd
curl -X POST http://localhost:8000/api/jobs/collect -H "Content-Type: application/json" -d "{\"job_type\":\"score\",\"params\":{\"date\":\"2026-04-15\"}}"
curl -X POST http://localhost:8000/api/portfolios/recommend
curl http://localhost:8000/api/stocks/2330/score
```

- [ ] **Step 2: 使用者回報三支 API 都回合理 JSON → commit 本群組最終說明文件（若有）**

**🛑 群組 E 驗收節點** — 停下等使用者驗證 API 可用。

---

## Task F1: MOPS 現金流 collector

**Files:**
- Create: `backend/src/alpha_lab/collectors/mops_cashflow.py`
- Test: `backend/tests/collectors/test_mops_cashflow.py`
- Test fixture: `backend/tests/fixtures/mops_t164sb05_2330_2026Q1.html`

**來源**：`https://mops.twse.com.tw/mops/web/ajax_t164sb05`（POST，form-encoded）。參數：`TYPEK=sii&co_id=<symbol>&year=<roc_year>&season=<1-4>`。回應為 HTML，需以 BS4 解析表格。關鍵列：
- 「營業活動之淨現金流入（流出）」
- 「投資活動之淨現金流入（流出）」
- 「籌資活動之淨現金流入（流出）」

- [ ] **Step 1: 儲存一份真實 fixture HTML（本地已跑過 curl 的結果；若無則先手動抓）**

```cmd
REM 取得 fixture
curl -X POST "https://mops.twse.com.tw/mops/web/ajax_t164sb05" ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "encodeURIComponent=1&step=1&firstin=1&TYPEK=sii&co_id=2330&year=115&season=1" ^
  > backend\tests\fixtures\mops_t164sb05_2330_2026Q1.html
```

（115 = 民國 115 年 = 2026）

- [ ] **Step 2: 寫 parser 測試**

```python
# backend/tests/collectors/test_mops_cashflow.py
from pathlib import Path

from alpha_lab.collectors.mops_cashflow import parse_cashflow_html


def test_parse_cashflow_basic() -> None:
    html = (
        Path(__file__).parent.parent / "fixtures" / "mops_t164sb05_2330_2026Q1.html"
    ).read_text(encoding="utf-8")
    result = parse_cashflow_html(html)
    assert "operating_cf" in result
    assert "investing_cf" in result
    assert "financing_cf" in result
    assert isinstance(result["operating_cf"], int)
```

- [ ] **Step 3: 實作 collector**

```python
"""MOPS 現金流量表 collector（t164sb05）。

來源 HTML 結構：表格內以「營業活動之淨現金流入（流出）」等字串為列標頭，
下一個數字 cell 是金額（單位：千元，TWSE 慣例）。

本 collector 只回傳 Phase 3 需要的三項（OCF/ICF/FCF）— 完整項目
存至 FinancialStatement.raw_json_text 由呼叫端處理。
"""

from __future__ import annotations

import asyncio
import re
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

MOPS_URL = "https://mops.twse.com.tw/mops/web/ajax_t164sb05"

_LABELS = {
    "operating_cf": "營業活動之淨現金流入",
    "investing_cf": "投資活動之淨現金流入",
    "financing_cf": "籌資活動之淨現金流入",
}


class Cashflow(TypedDict):
    operating_cf: int | None
    investing_cf: int | None
    financing_cf: int | None


def parse_cashflow_html(html: str) -> Cashflow:
    soup = BeautifulSoup(html, "html.parser")
    out: Cashflow = {
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
    }
    for key, label in _LABELS.items():
        row = soup.find("tr", string=None)  # placeholder; real search below
        row = _find_row(soup, label)
        if row is None:
            continue
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        val = _first_number(cells)
        out[key] = val  # type: ignore[literal-required]
    return out


def _find_row(soup: BeautifulSoup, label: str):
    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)
        if label in text:
            return tr
    return None


def _first_number(cells: list[str]) -> int | None:
    for c in cells:
        stripped = c.replace(",", "").replace("(", "-").replace(")", "").strip()
        if re.fullmatch(r"-?\d+", stripped):
            return int(stripped)
    return None


async def fetch_cashflow(
    symbol: str, roc_year: int, season: int, client: httpx.AsyncClient | None = None
) -> Cashflow:
    """抓取單檔單季現金流。roc_year = 民國年（2026 → 115）。"""

    owns_client = client is None
    c = client or httpx.AsyncClient(timeout=30.0)
    try:
        resp = await c.post(
            MOPS_URL,
            data={
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "1",
                "TYPEK": "sii",
                "co_id": symbol,
                "year": str(roc_year),
                "season": str(season),
            },
        )
        resp.raise_for_status()
        html = resp.text
    finally:
        if owns_client:
            await c.aclose()
    return parse_cashflow_html(html)


def fetch_cashflow_sync(symbol: str, roc_year: int, season: int) -> Cashflow:
    return asyncio.run(fetch_cashflow(symbol, roc_year, season))
```

- [ ] **Step 4: 驗證**

Run: `cd backend && pytest tests/collectors/test_mops_cashflow.py -v && ruff check . && mypy src`

- [ ] **Step 5: commit**

```bash
git add backend/src/alpha_lab/collectors/mops_cashflow.py backend/tests/collectors/test_mops_cashflow.py backend/tests/fixtures/mops_t164sb05_2330_2026Q1.html
git commit -m "feat: add MOPS cashflow collector (t164sb05 HTML parser)"
```

---

## Task F2: Cashflow upsert + job handler

**Files:**
- Modify: `backend/src/alpha_lab/jobs/service.py`（加入 `cashflow` handler）
- Modify: `backend/src/alpha_lab/collectors/mops_cashflow.py`（加入 `upsert_cashflow`）
- Test: `backend/tests/collectors/test_mops_cashflow_upsert.py`

- [ ] **Step 1: 在 `mops_cashflow.py` 加入 upsert**

```python
from datetime import date

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from alpha_lab.storage.models import FinancialStatement


def upsert_cashflow(
    session: Session, symbol: str, period: str, cf: Cashflow
) -> None:
    """寫入 financial_statements 表，statement_type='cashflow'。"""

    stmt = sqlite_insert(FinancialStatement).values(
        symbol=symbol,
        period=period,
        statement_type="cashflow",
        operating_cf=cf["operating_cf"],
        investing_cf=cf["investing_cf"],
        financing_cf=cf["financing_cf"],
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "period", "statement_type"],
        set_={
            "operating_cf": stmt.excluded.operating_cf,
            "investing_cf": stmt.excluded.investing_cf,
            "financing_cf": stmt.excluded.financing_cf,
        },
    )
    session.execute(stmt)
    session.commit()
```

- [ ] **Step 2: 測試**

```python
# backend/tests/collectors/test_mops_cashflow_upsert.py
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alpha_lab.collectors.mops_cashflow import upsert_cashflow
from alpha_lab.storage.models import Base, FinancialStatement, Stock


def test_upsert_cashflow() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Stock(symbol="2330", name="台積電"))
        session.commit()
        upsert_cashflow(
            session,
            "2330",
            "2026Q1",
            {"operating_cf": 1000, "investing_cf": -500, "financing_cf": -200},
        )
        row = session.execute(
            select(FinancialStatement).where(
                FinancialStatement.symbol == "2330",
                FinancialStatement.period == "2026Q1",
                FinancialStatement.statement_type == "cashflow",
            )
        ).scalar_one()
        assert row.operating_cf == 1000
        assert row.investing_cf == -500
```

- [ ] **Step 3: 在 `jobs/service.py` 加入 `cashflow` handler（依現有 dispatch 模式）**

```python
# 新增 handler
from alpha_lab.collectors.mops_cashflow import fetch_cashflow_sync, upsert_cashflow


def _handle_cashflow(params: dict[str, object], session: Session) -> str:
    symbol = str(params["symbol"])
    period = str(params["period"])  # "2026Q1"
    year_int, q = int(period[:4]), int(period[-1])
    roc_year = year_int - 1911
    cf = fetch_cashflow_sync(symbol, roc_year, q)
    upsert_cashflow(session, symbol, period, cf)
    return f"cashflow {symbol} {period} written"
```

- [ ] **Step 4: 驗證 + 靜態**

Run: `cd backend && pytest tests/collectors/test_mops_cashflow_upsert.py -v && ruff check . && mypy src`

- [ ] **Step 5: commit**

```bash
git add backend/src/alpha_lab/collectors/mops_cashflow.py backend/src/alpha_lab/jobs/service.py backend/tests/collectors/test_mops_cashflow_upsert.py
git commit -m "feat: add cashflow upsert and job handler"
```

---

## Task F3: FCF 接入 Quality 因子

**Files:**
- Modify: `backend/src/alpha_lab/analysis/factor_quality.py`（多接 `fcf` 指標）
- Modify: `backend/src/alpha_lab/analysis/pipeline.py`（snapshot 加 FCF）
- Modify: `backend/tests/analysis/test_factor_quality.py`（加 FCF 測試）
- Modify: `backend/tests/analysis/test_pipeline.py`（seed 加 cashflow）

- [ ] **Step 1: 更新 `factor_quality.py` — 加入 FCF（FCF = OCF；本 Phase 不扣 CapEx）**

```python
"""Quality 因子：ROE + 毛利率 + 負債比 + FCF。"""

from __future__ import annotations

from alpha_lab.analysis.normalize import percentile_rank, percentile_rank_inverted


def compute_quality_scores(
    snapshot: dict[str, dict[str, float | None]],
) -> dict[str, float | None]:
    roe = percentile_rank({s: v.get("roe") for s, v in snapshot.items()})
    gm = percentile_rank({s: v.get("gross_margin") for s, v in snapshot.items()})
    dr = percentile_rank_inverted(
        {s: v.get("debt_ratio") for s, v in snapshot.items()}
    )
    fcf = percentile_rank({s: v.get("fcf") for s, v in snapshot.items()})

    result: dict[str, float | None] = {}
    for sym in snapshot:
        parts = [
            s for s in (roe[sym], gm[sym], dr[sym], fcf[sym]) if s is not None
        ]
        result[sym] = sum(parts) / len(parts) if parts else None
    return result
```

- [ ] **Step 2: `pipeline.py` 的 `build_snapshot` 加 FCF**

在建構 `quality[sym]` 之前加：

```python
cashflow_row = session.execute(
    select(FinancialStatement)
    .where(
        FinancialStatement.symbol == sym,
        FinancialStatement.statement_type == "cashflow",
    )
    .order_by(FinancialStatement.period.desc())
    .limit(4)
).scalars().all()

fcf_ttm: float | None = None
if len(cashflow_row) == 4 and all(r.operating_cf is not None for r in cashflow_row):
    fcf_ttm = float(sum(r.operating_cf for r in cashflow_row if r.operating_cf is not None))

# 更新 quality snapshot
quality[sym] = {
    "roe": roe,
    "gross_margin": gross_margin,
    "debt_ratio": debt_ratio,
    "fcf": fcf_ttm,
}
```

- [ ] **Step 3: 更新測試**

在 `test_factor_quality.py` 加：

```python
def test_quality_with_fcf() -> None:
    snapshot = {
        "A": {"roe": 0.25, "gross_margin": 0.5, "debt_ratio": 0.3, "fcf": 1000.0},
        "B": {"roe": 0.10, "gross_margin": 0.3, "debt_ratio": 0.6, "fcf": 100.0},
    }
    out = compute_quality_scores(snapshot)
    assert out["A"] == 100.0
    assert out["B"] == 0.0
```

`test_pipeline.py._seed` 加入 cashflow 資料（每家 4 季）：

```python
for period in ["2026Q1", "2025Q4", "2025Q3", "2025Q2"]:
    session.add(
        FinancialStatement(
            symbol=sym,
            period=period,
            statement_type="cashflow",
            operating_cf=1000,
            investing_cf=-300,
            financing_cf=-200,
        )
    )
```

- [ ] **Step 4: 驗證 + 靜態**

Run: `cd backend && pytest tests/analysis/ -v && ruff check . && mypy src`

- [ ] **Step 5: commit**

```bash
git add backend/src/alpha_lab/analysis/factor_quality.py backend/src/alpha_lab/analysis/pipeline.py backend/tests/analysis/test_factor_quality.py backend/tests/analysis/test_pipeline.py
git commit -m "feat: add FCF to Quality factor scoring"
```

---

**🛑 群組 F 驗收節點** — 停下等使用者實際抓一檔現金流 + 跑評分驗證 FCF 已納入。

驗收指引：

```cmd
cd backend
curl -X POST http://localhost:8000/api/jobs/collect -H "Content-Type: application/json" -d "{\"job_type\":\"cashflow\",\"params\":{\"symbol\":\"2330\",\"period\":\"2026Q1\"}}"

REM 重算評分
.venv\Scripts\python.exe scripts\compute_scores.py --date 2026-04-15

REM 確認 2330 quality_score 已變
curl http://localhost:8000/api/stocks/2330/score
```

---

## Task G1: 前端 `ScoreRadar` 元件

**Files:**
- Create: `frontend/src/components/stock/ScoreRadar.tsx`
- Create: `frontend/src/api/scores.ts`
- Modify: `frontend/src/api/types.ts`（加 `FactorBreakdown`）
- Test: `frontend/tests/unit/ScoreRadar.test.tsx`

- [ ] **Step 1: 在 `types.ts` 加型別**

```typescript
// frontend/src/api/types.ts — 末尾加入
export interface FactorBreakdown {
  symbol: string
  calc_date: string // ISO date
  value_score: number | null
  growth_score: number | null
  dividend_score: number | null
  quality_score: number | null
  total_score: number | null
}

export interface ScoreResponse {
  symbol: string
  latest: FactorBreakdown | null
}
```

- [ ] **Step 2: `api/scores.ts`**

```typescript
import { apiClient } from './client'
import type { ScoreResponse } from './types'

export async function fetchStockScore(symbol: string): Promise<ScoreResponse> {
  const { data } = await apiClient.get<ScoreResponse>(`/stocks/${symbol}/score`)
  return data
}
```

- [ ] **Step 3: `ScoreRadar.tsx`**

```tsx
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import type { FactorBreakdown } from '@/api/types'

interface ScoreRadarProps {
  breakdown: FactorBreakdown
}

export function ScoreRadar({ breakdown }: ScoreRadarProps) {
  const data = [
    { factor: '價值', score: breakdown.value_score ?? 0 },
    { factor: '成長', score: breakdown.growth_score ?? 0 },
    { factor: '股息', score: breakdown.dividend_score ?? 0 },
    { factor: '品質', score: breakdown.quality_score ?? 0 },
  ]

  return (
    <div className="rounded-lg border p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold">多因子評分</h3>
        <span className="text-sm text-gray-600">
          總分 {breakdown.total_score?.toFixed(1) ?? '—'}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="factor" />
          <PolarRadiusAxis domain={[0, 100]} tick={false} />
          <Radar dataKey="score" stroke="#2563eb" fill="#3b82f6" fillOpacity={0.3} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 4: 測試**

```typescript
// frontend/tests/unit/ScoreRadar.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ScoreRadar } from '@/components/stock/ScoreRadar'

describe('ScoreRadar', () => {
  it('renders total score and factor labels', () => {
    render(
      <ScoreRadar
        breakdown={{
          symbol: '2330',
          calc_date: '2026-04-15',
          value_score: 70,
          growth_score: 80,
          dividend_score: 50,
          quality_score: 90,
          total_score: 72.5,
        }}
      />,
    )
    expect(screen.getByText(/多因子評分/)).toBeInTheDocument()
    expect(screen.getByText(/72.5/)).toBeInTheDocument()
  })

  it('shows dash when total is null', () => {
    render(
      <ScoreRadar
        breakdown={{
          symbol: '2330',
          calc_date: '2026-04-15',
          value_score: null,
          growth_score: null,
          dividend_score: null,
          quality_score: null,
          total_score: null,
        }}
      />,
    )
    expect(screen.getByText('總分 —')).toBeInTheDocument()
  })
})
```

- [ ] **Step 5: 執行 + 靜態**

Run: `cd frontend && pnpm test -- ScoreRadar && pnpm type-check && pnpm lint`

- [ ] **Step 6: commit**

```bash
git add frontend/src/components/stock/ScoreRadar.tsx frontend/src/api/scores.ts frontend/src/api/types.ts frontend/tests/unit/ScoreRadar.test.tsx
git commit -m "feat: add ScoreRadar component and score API client"
```

---

## Task G2: 個股頁整合 `ScoreRadar`

**Files:**
- Modify: `frontend/src/pages/StockPage.tsx`

- [ ] **Step 1: 讀現有 `StockPage.tsx` 確認 layout，在「關鍵指標」區塊旁加入 `ScoreRadar`**

```tsx
// 新增 import
import { useQuery } from '@tanstack/react-query'
import { fetchStockScore } from '@/api/scores'
import { ScoreRadar } from '@/components/stock/ScoreRadar'

// 在 component 內：
const { data: scoreData } = useQuery({
  queryKey: ['stock-score', symbol],
  queryFn: () => fetchStockScore(symbol!),
  enabled: !!symbol,
})

// 在 JSX 的「關鍵指標」區塊旁或下方加入：
{scoreData?.latest && <ScoreRadar breakdown={scoreData.latest} />}
```

- [ ] **Step 2: 驗證 + 靜態**

Run: `cd frontend && pnpm type-check && pnpm lint`

- [ ] **Step 3: 手動驗收指引**

```cmd
cd frontend
pnpm dev
REM 瀏覽 http://localhost:5173/stocks/2330 確認雷達圖顯示
```

- [ ] **Step 4: 使用者回報 OK 後 commit**

```bash
git add frontend/src/pages/StockPage.tsx
git commit -m "feat: integrate ScoreRadar into stock detail page"
```

**🛑 群組 G 驗收節點** — 停下等使用者驗證個股頁雷達圖。

---

## Task H1: `portfolios` API client

**Files:**
- Create: `frontend/src/api/portfolios.ts`
- Modify: `frontend/src/api/types.ts`（加 `Portfolio` / `RecommendResponse`）

- [ ] **Step 1: 在 `types.ts` 加**

```typescript
export type PortfolioStyle = 'conservative' | 'balanced' | 'aggressive'

export interface Holding {
  symbol: string
  name: string
  weight: number
  score_breakdown: FactorBreakdown
}

export interface Portfolio {
  style: PortfolioStyle
  label: string
  is_top_pick: boolean
  holdings: Holding[]
  expected_yield: number | null
  risk_score: number | null
  reasoning_ref: string | null
}

export interface RecommendResponse {
  generated_at: string
  calc_date: string
  portfolios: Portfolio[]
}
```

- [ ] **Step 2: `api/portfolios.ts`**

```typescript
import { apiClient } from './client'
import type { PortfolioStyle, RecommendResponse } from './types'

export async function recommendPortfolios(
  style?: PortfolioStyle,
): Promise<RecommendResponse> {
  const { data } = await apiClient.post<RecommendResponse>(
    '/portfolios/recommend',
    null,
    { params: style ? { style } : undefined },
  )
  return data
}
```

- [ ] **Step 3: 靜態檢查**

Run: `cd frontend && pnpm type-check && pnpm lint`

- [ ] **Step 4: commit**

```bash
git add frontend/src/api/portfolios.ts frontend/src/api/types.ts
git commit -m "feat: add portfolios API client and types"
```

---

## Task H2: `/portfolios` 頁面（tab 切換）

**Files:**
- Create: `frontend/src/pages/PortfoliosPage.tsx`
- Create: `frontend/src/components/portfolio/PortfolioTabs.tsx`
- Create: `frontend/src/components/portfolio/HoldingsTable.tsx`
- Modify: `frontend/src/App.tsx`（加 `/portfolios` 路由）

- [ ] **Step 1: `HoldingsTable.tsx`**

```tsx
import type { Holding } from '@/api/types'

interface HoldingsTableProps {
  holdings: Holding[]
}

export function HoldingsTable({ holdings }: HoldingsTableProps) {
  if (holdings.length === 0) {
    return <p className="text-gray-500">此組合無持股候選。</p>
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left">
          <th className="py-2">代號</th>
          <th className="py-2">名稱</th>
          <th className="py-2 text-right">權重</th>
          <th className="py-2 text-right">總分</th>
        </tr>
      </thead>
      <tbody>
        {holdings.map((h) => (
          <tr key={h.symbol} className="border-b">
            <td className="py-2">{h.symbol}</td>
            <td className="py-2">{h.name}</td>
            <td className="py-2 text-right">
              {(h.weight * 100).toFixed(1)}%
            </td>
            <td className="py-2 text-right">
              {h.score_breakdown.total_score?.toFixed(1) ?? '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

- [ ] **Step 2: `PortfolioTabs.tsx`**

```tsx
import { useState } from 'react'
import type { Portfolio, PortfolioStyle } from '@/api/types'
import { HoldingsTable } from './HoldingsTable'

interface PortfolioTabsProps {
  portfolios: Portfolio[]
}

const STYLE_ORDER: PortfolioStyle[] = ['conservative', 'balanced', 'aggressive']

export function PortfolioTabs({ portfolios }: PortfolioTabsProps) {
  const sorted = STYLE_ORDER.map((s) =>
    portfolios.find((p) => p.style === s),
  ).filter((p): p is Portfolio => p !== undefined)

  const [active, setActive] = useState<PortfolioStyle>(
    sorted.find((p) => p.is_top_pick)?.style ?? sorted[0]?.style ?? 'balanced',
  )

  const current = sorted.find((p) => p.style === active)

  return (
    <div>
      <div className="mb-4 flex gap-2 border-b">
        {sorted.map((p) => (
          <button
            type="button"
            key={p.style}
            onClick={() => setActive(p.style)}
            className={`px-4 py-2 ${
              active === p.style
                ? 'border-b-2 border-blue-600 font-semibold'
                : 'text-gray-600'
            }`}
          >
            {p.label}
            {p.is_top_pick && (
              <span className="ml-2 rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                最推薦
              </span>
            )}
          </button>
        ))}
      </div>
      {current && (
        <div>
          <div className="mb-3 flex gap-6 text-sm text-gray-600">
            <span>
              預期殖利率：
              {current.expected_yield?.toFixed(2) ?? '—'}%
            </span>
            <span>
              風險分數：{current.risk_score?.toFixed(1) ?? '—'}
            </span>
          </div>
          <HoldingsTable holdings={current.holdings} />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: `PortfoliosPage.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { recommendPortfolios } from '@/api/portfolios'
import { PortfolioTabs } from '@/components/portfolio/PortfolioTabs'

export function PortfoliosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['portfolios-recommend'],
    queryFn: () => recommendPortfolios(),
  })

  if (isLoading) return <p>載入中…</p>
  if (error) return <p className="text-red-600">載入失敗：{String(error)}</p>
  if (!data) return null

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-2 text-2xl font-bold">投資組合推薦</h1>
      <p className="mb-6 text-sm text-gray-600">
        計算日：{data.calc_date}
      </p>
      <PortfolioTabs portfolios={data.portfolios} />
    </div>
  )
}
```

- [ ] **Step 4: `App.tsx` 加路由**

```tsx
// 新增 import
import { PortfoliosPage } from '@/pages/PortfoliosPage'

// 在 <Routes> 內加：
<Route path="/portfolios" element={<PortfoliosPage />} />
```

- [ ] **Step 5: 靜態檢查**

Run: `cd frontend && pnpm type-check && pnpm lint`

- [ ] **Step 6: 手動驗收**

```cmd
cd frontend
pnpm dev
REM 瀏覽 http://localhost:5173/portfolios 確認三個 tab 可切換、平衡組有「最推薦」徽章、持股表顯示
```

- [ ] **Step 7: 使用者回報 OK 後 commit**

```bash
git add frontend/src/pages/PortfoliosPage.tsx frontend/src/components/portfolio/ frontend/src/App.tsx
git commit -m "feat: add portfolios recommendation page with style tabs"
```

---

## Task H3: Header 加入「組合推薦」連結

**Files:**
- Modify: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: 讀現有 AppLayout，加入 nav link**

在 header 適當位置加：

```tsx
import { Link } from 'react-router-dom'

// 在 header 內：
<Link to="/portfolios" className="text-sm hover:underline">
  組合推薦
</Link>
```

- [ ] **Step 2: 靜態 + 手動驗收**

Run: `cd frontend && pnpm type-check && pnpm lint`

```cmd
REM 點 header「組合推薦」跳轉成功
```

- [ ] **Step 3: commit**

```bash
git add frontend/src/layouts/AppLayout.tsx
git commit -m "feat: add portfolios link in app header"
```

**🛑 群組 H 驗收節點** — 停下等使用者驗證 portfolios 頁面完整可用。

---

## Task I1: Playwright E2E — portfolios 頁

**Files:**
- Create: `frontend/tests/e2e/portfolios.spec.ts`
- Create: `frontend/tests/fixtures/portfolios-recommend.json`

- [ ] **Step 1: Fixture**

```json
{
  "generated_at": "2026-04-15T20:00:00Z",
  "calc_date": "2026-04-15",
  "portfolios": [
    {
      "style": "conservative",
      "label": "保守組",
      "is_top_pick": false,
      "holdings": [
        {
          "symbol": "2330",
          "name": "台積電",
          "weight": 0.3,
          "score_breakdown": {
            "symbol": "2330",
            "calc_date": "2026-04-15",
            "value_score": 60,
            "growth_score": 70,
            "dividend_score": 80,
            "quality_score": 90,
            "total_score": 80
          }
        }
      ],
      "expected_yield": 3.5,
      "risk_score": 20,
      "reasoning_ref": null
    },
    {
      "style": "balanced",
      "label": "平衡組",
      "is_top_pick": true,
      "holdings": [
        {
          "symbol": "2454",
          "name": "聯發科",
          "weight": 0.25,
          "score_breakdown": {
            "symbol": "2454",
            "calc_date": "2026-04-15",
            "value_score": 70,
            "growth_score": 80,
            "dividend_score": 60,
            "quality_score": 75,
            "total_score": 71
          }
        }
      ],
      "expected_yield": 4.0,
      "risk_score": 40,
      "reasoning_ref": null
    },
    {
      "style": "aggressive",
      "label": "積極組",
      "is_top_pick": false,
      "holdings": [
        {
          "symbol": "2603",
          "name": "長榮",
          "weight": 0.2,
          "score_breakdown": {
            "symbol": "2603",
            "calc_date": "2026-04-15",
            "value_score": 80,
            "growth_score": 95,
            "dividend_score": 40,
            "quality_score": 60,
            "total_score": 75
          }
        }
      ],
      "expected_yield": 2.5,
      "risk_score": 65,
      "reasoning_ref": null
    }
  ]
}
```

- [ ] **Step 2: E2E**

```typescript
// frontend/tests/e2e/portfolios.spec.ts
import { expect, test } from '@playwright/test'
import fixture from '../fixtures/portfolios-recommend.json'

test.describe('Portfolios page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/portfolios/recommend**', (route) =>
      route.fulfill({ status: 200, body: JSON.stringify(fixture) }),
    )
  })

  test('shows three tabs and top pick badge on balanced', async ({ page }) => {
    await page.goto('/portfolios')
    await expect(page.getByText('投資組合推薦')).toBeVisible()
    await expect(page.getByRole('button', { name: /保守組/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /平衡組.*最推薦/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /積極組/ })).toBeVisible()
  })

  test('switches tab and shows different holdings', async ({ page }) => {
    await page.goto('/portfolios')
    // 預設應該顯示 balanced（最推薦）
    await expect(page.getByText('聯發科')).toBeVisible()

    await page.getByRole('button', { name: /積極組/ }).click()
    await expect(page.getByText('長榮')).toBeVisible()

    await page.getByRole('button', { name: /保守組/ }).click()
    await expect(page.getByText('台積電')).toBeVisible()
  })
})
```

- [ ] **Step 3: 執行**

Run: `cd frontend && pnpm e2e portfolios`
Expected: 2 passed

- [ ] **Step 4: commit**

```bash
git add frontend/tests/e2e/portfolios.spec.ts frontend/tests/fixtures/portfolios-recommend.json
git commit -m "test: add E2E for portfolios page tabs and top pick badge"
```

---

## Task I2: Backend 整合測試補強（score + recommend end-to-end）

**Files:**
- Create: `backend/tests/integration/test_score_then_recommend.py`

- [ ] **Step 1: 測試**

```python
# backend/tests/integration/test_score_then_recommend.py
"""完整流程：seed → score job → recommend API，所有資料走實際 pipeline。"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alpha_lab.storage.models import (
    FinancialStatement,
    PriceDaily,
    RevenueMonthly,
    Stock,
)


def test_score_then_recommend_flow(
    test_session: Session, client: TestClient
) -> None:
    for i, sym in enumerate(["2330", "2454", "2603", "1301", "2882"]):
        test_session.add(
            Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 2}")
        )
        test_session.add(
            PriceDaily(
                symbol=sym,
                trade_date=date(2026, 4, 15),
                open=100,
                high=110,
                low=95,
                close=100 + i,
                volume=1000,
            )
        )
        for q in ["2026Q1", "2025Q4", "2025Q3", "2025Q2", "2025Q1", "2024Q4", "2024Q3", "2024Q2"]:
            test_session.add(
                FinancialStatement(
                    symbol=sym,
                    period=q,
                    statement_type="income",
                    revenue=100 + i,
                    gross_profit=30 + i,
                    net_income=20 + i,
                    eps=1.0 + i * 0.5,
                )
            )
        test_session.add(
            FinancialStatement(
                symbol=sym,
                period="2026Q1",
                statement_type="balance",
                total_assets=1000,
                total_liabilities=400 - i * 20,
                total_equity=600 + i * 20,
            )
        )
        for year in (2025, 2026):
            for month in range(1, 13):
                test_session.add(
                    RevenueMonthly(
                        symbol=sym,
                        year=year,
                        month=month,
                        revenue=10 + month + i,
                    )
                )
    test_session.commit()

    # 算分
    r = client.post(
        "/api/jobs/collect",
        json={"job_type": "score", "params": {"date": "2026-04-15"}},
    )
    assert r.status_code == 200

    # 推薦
    r2 = client.post("/api/portfolios/recommend")
    assert r2.status_code == 200
    data = r2.json()
    assert len(data["portfolios"]) == 3
    balanced = next(p for p in data["portfolios"] if p["style"] == "balanced")
    assert balanced["is_top_pick"]
    assert len(balanced["holdings"]) > 0
```

- [ ] **Step 2: 執行**

Run: `cd backend && pytest tests/integration/test_score_then_recommend.py -v`
Expected: PASS

- [ ] **Step 3: 全靜態**

Run: `cd backend && ruff check . && mypy src && cd ../frontend && pnpm type-check && pnpm lint`

- [ ] **Step 4: commit**

```bash
git add backend/tests/integration/test_score_then_recommend.py
git commit -m "test: add integration test for score-then-recommend flow"
```

**🛑 群組 I 驗收節點** — 停下等使用者確認測試全綠。

---

## Task J1: 知識庫更新

**Files:**
- Create: `docs/knowledge/domain/factors.md`
- Create: `docs/knowledge/domain/scoring.md`
- Create: `docs/knowledge/features/portfolio/recommender.md`
- Create: `docs/knowledge/features/portfolio/weights.md`
- Create: `docs/knowledge/collectors/mops-cashflow.md`
- Modify: `docs/knowledge/architecture/data-flow.md`
- Modify: `docs/knowledge/architecture/data-models.md`

- [ ] **Step 1: `domain/factors.md`**

```markdown
---
domain: domain/factors
updated: 2026-04-15
related: [scoring.md, ../features/portfolio/recommender.md]
---

# 多因子指標

## 目的

定義四因子（Value / Growth / Dividend / Quality）各自的指標與計算公式。

## 現行實作（Phase 3）

| 因子 | 指標 | 來源 | 方向 |
|------|------|------|------|
| Value | PE | price.close / Σ(income.eps × 4Q) | 越低越佳 |
| Value | PB | 目前 None（缺 shares_outstanding） | — |
| Growth | 營收 YoY | 近 12M revenue / 前 12M revenue | 越高越佳 |
| Growth | EPS YoY | 近 4Q EPS 和 / 前 4Q EPS 和 | 越高越佳 |
| Dividend | 當期殖利率 | 目前 None（資料來源待補） | 越高越佳 |
| Quality | ROE | Σ(net_income 4Q) / total_equity | 越高越佳 |
| Quality | 毛利率 | Σ(gross_profit 4Q) / Σ(revenue 4Q) | 越高越佳 |
| Quality | 負債比 | total_liabilities / total_assets | 越低越佳 |
| Quality | FCF | Σ(operating_cf 4Q)（未扣 CapEx） | 越高越佳 |

## 關鍵檔案

- [backend/src/alpha_lab/analysis/factor_value.py](../../backend/src/alpha_lab/analysis/factor_value.py)
- [backend/src/alpha_lab/analysis/factor_growth.py](../../backend/src/alpha_lab/analysis/factor_growth.py)
- [backend/src/alpha_lab/analysis/factor_dividend.py](../../backend/src/alpha_lab/analysis/factor_dividend.py)
- [backend/src/alpha_lab/analysis/factor_quality.py](../../backend/src/alpha_lab/analysis/factor_quality.py)
- [backend/src/alpha_lab/analysis/normalize.py](../../backend/src/alpha_lab/analysis/normalize.py)

## 修改時注意事項

- 新增指標 → 在對應 factor module 的 snapshot dict 加 key、在 `pipeline.build_snapshot` 填值
- 調整方向（高/低為佳） → 選用 `percentile_rank` 或 `percentile_rank_inverted`
- Dividend 與 PB 目前缺資料來源；Phase 4/5 補時同步更新此表
```

- [ ] **Step 2: `domain/scoring.md`**

```markdown
---
domain: domain/scoring
updated: 2026-04-15
related: [factors.md, ../features/portfolio/weights.md]
---

# 評分流程

## 目的

將四因子 0-100 分數組合為單一總分，儲存至 `scores` 表供組合推薦使用。

## 現行實作（Phase 3）

- **橫截面歸一化**：單一 `calc_date` 所有 symbol 一起排名、轉百分位
- **Ties**：同值共享平均 rank
- **None**：不參與排名、結果保留 None
- **風格權重加權**：`scores.total_score` 儲存 balanced 權重總分；recommend 時 runtime 以 conservative/aggressive 權重重算
- **None 因子處理**：`weighted_total` 略過 None，剩餘權重再正規化

## 關鍵檔案

- [backend/src/alpha_lab/analysis/pipeline.py](../../backend/src/alpha_lab/analysis/pipeline.py)
- [backend/src/alpha_lab/analysis/weights.py](../../backend/src/alpha_lab/analysis/weights.py)
- [backend/scripts/compute_scores.py](../../backend/scripts/compute_scores.py)

## 觸發方式

- CLI：`python scripts/compute_scores.py --date YYYY-MM-DD`
- API：`POST /api/jobs/collect` with `job_type='score'`

## 修改時注意事項

- 加新因子 → `Score` model 加欄位、`pipeline` 填、`weighted_total` 加參數、`STYLE_WEIGHTS` 調整
- 改歸一化策略 → 改 `normalize.py`（目前為百分位；若改 z-score 要注意 score 範圍不再是 0-100）
- `scores` 表只存當日快照；歷史分數多次 upsert 會覆寫同日 row
```

- [ ] **Step 3: `features/portfolio/recommender.md`**

```markdown
---
domain: features/portfolio/recommender
updated: 2026-04-15
related: [weights.md, ../../domain/scoring.md]
---

# 組合推薦

## 目的

依風格產出持股配置與權重，供 `/portfolios` 頁呈現。

## 現行實作（Phase 3）

- **候選池**：讀 `scores` 最新 calc_date 所有 row，排除 total_score=None
- **Top 30**：按風格加權總分排序取前 30
- **產業分散**：同產業最多 5 檔
- **最終持股**：取前 10 檔
- **權重**：softmax(total / 20)，單檔 cap 30%，超出者平均分配到未 cap 檔
- **四組**：conservative / balanced / aggressive，balanced 標 `is_top_pick=true`
- **expected_yield**：目前 None（待股利資料接入）
- **risk_score**：`100 - 平均 quality_score`

## 關鍵檔案

- [backend/src/alpha_lab/analysis/portfolio.py](../../backend/src/alpha_lab/analysis/portfolio.py)
- [backend/src/alpha_lab/api/routes/portfolios.py](../../backend/src/alpha_lab/api/routes/portfolios.py)
- [frontend/src/pages/PortfoliosPage.tsx](../../frontend/src/pages/PortfoliosPage.tsx)
- [frontend/src/components/portfolio/PortfolioTabs.tsx](../../frontend/src/components/portfolio/PortfolioTabs.tsx)

## 修改時注意事項

- 改參數（TOP_N、MAX_PER_INDUSTRY、FINAL_HOLDINGS、MAX_WEIGHT）→ 檔頂常數
- `is_top_pick` 目前硬編碼為 `style == 'balanced'`；若要動態判定需改 `generate_portfolio` 並引入市場訊號
- 組合儲存、追蹤、回測留 Phase 6
```

- [ ] **Step 4: `features/portfolio/weights.md`**

```markdown
---
domain: features/portfolio/weights
updated: 2026-04-15
related: [recommender.md, ../../domain/factors.md]
---

# 風格權重

## 目的

四因子在不同風格下的加權比例。

## 現行實作（Phase 3）

| Style | Value | Growth | Dividend | Quality |
|-------|-------|--------|----------|---------|
| conservative | 0.20 | 0.10 | 0.35 | 0.35 |
| balanced | 0.25 | 0.25 | 0.25 | 0.25 |
| aggressive | 0.15 | 0.50 | 0.05 | 0.30 |

## 關鍵檔案

- [backend/src/alpha_lab/analysis/weights.py](../../backend/src/alpha_lab/analysis/weights.py)

## 修改時注意事項

- 改權重必須保持總和 = 1；對應單元測試會檢查
- 新增 style → 加入 `STYLE_WEIGHTS`、`STYLE_LABELS`、`Style` Literal、前端 `STYLE_ORDER`
```

- [ ] **Step 5: `collectors/mops-cashflow.md`**

```markdown
---
domain: collectors/mops-cashflow
updated: 2026-04-15
related: [../architecture/data-models.md]
---

# MOPS 現金流量表 Collector

## 目的

抓取 MOPS t164sb05 的季現金流，寫入 `financial_statements.statement_type='cashflow'`。

## 現行實作（Phase 3）

- **來源**：`POST https://mops.twse.com.tw/mops/web/ajax_t164sb05`
- **參數**：`TYPEK=sii`、`co_id=<symbol>`、`year=<民國年>`、`season=1-4`
- **解析**：BS4 抓以「營業活動之淨現金流入」「投資活動之淨現金流入」「籌資活動之淨現金流入」為列標頭的 `<tr>`，取第一個純數字 cell
- **括號處理**：`(1,234)` → `-1234`
- **單位**：千元（TWSE 慣例，不做換算）

## 關鍵檔案

- [backend/src/alpha_lab/collectors/mops_cashflow.py](../../backend/src/alpha_lab/collectors/mops_cashflow.py)
- [backend/tests/fixtures/mops_t164sb05_2330_2026Q1.html](../../backend/tests/fixtures/)

## 觸發方式

- API：`POST /api/jobs/collect` with `job_type='cashflow'`, `params={'symbol': '2330', 'period': '2026Q1'}`

## 修改時注意事項

- MOPS 表格結構變動 → 調整 `_LABELS` 與 `_find_row`
- 若要支援上櫃（otc）→ 加 `TYPEK=otc` 參數
- FCF 未扣 CapEx（Phase 3 簡化）；日後引入 CapEx 需另解析「購置不動產、廠房及設備」
```

- [ ] **Step 6: 更新 `architecture/data-flow.md`** — 在 Phase 3 段落加入 scoring / recommend 資料流；`data-models.md` 加入 `Score` 表。依現有檔案結構插入。

- [ ] **Step 7: 中文亂碼掃描**

Run: `grep -rn "��" docs/knowledge/` (shell bash)
Expected: 無 match

- [ ] **Step 8: commit**

```bash
git add docs/knowledge/
git commit -m "docs: add Phase 3 knowledge base entries (factors, scoring, recommender, weights, mops-cashflow)"
```

---

## Task J2: USER_GUIDE + Phase 驗收

**Files:**
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/superpowers/specs/2026-04-14-alpha-lab-design.md`（Phase 3 狀態更新）

- [ ] **Step 1: 在 `USER_GUIDE.md` 加入 Phase 3 使用說明**

新增段落：
- 如何跑評分（CLI + API）
- 如何取得組合推薦
- `/portfolios` 頁面四 tab 意義

- [ ] **Step 2: 更新 spec 第 15 節 Phase 表 — Phase 3 標記為完成**

- [ ] **Step 3: 靜態檢查最終一輪**

Run: `cd backend && ruff check . && mypy src && cd ../frontend && pnpm type-check && pnpm lint && pnpm test && pnpm e2e`

- [ ] **Step 4: 使用者 Phase 最終驗收**

```cmd
REM 端到端：抓資料 → 算分 → 推薦 → 個股雷達 → 組合頁 tab 切換
cd backend
.venv\Scripts\uvicorn.exe alpha_lab.api.main:app --reload

REM 另開：
cd frontend
pnpm dev

REM 瀏覽器確認：
REM 1. /stocks/2330 的雷達圖
REM 2. /portfolios 三個 tab 可切換、平衡組有「最推薦」
REM 3. 每組顯示持股、權重、總分
```

- [ ] **Step 5: 使用者回報「Phase 3 驗證通過」後**

```bash
git add docs/USER_GUIDE.md docs/superpowers/specs/2026-04-14-alpha-lab-design.md
git commit -m "docs: mark Phase 3 as complete in spec and user guide"
git tag -a phase-3-complete -m "Phase 3: multi-factor scoring engine + portfolio recommender"
```

---

## 完成後

Phase 3 全部 24 tasks 結束。停下等使用者指示是否進入 Phase 4（功能 E — 推薦理由、L2 詳解、報告儲存、回顧模式）。依 Phase 轉換 SOP，下一 Phase 計畫待使用者明確指示後才撰寫。
