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
        expected_yield=None,
        risk_score=_risk_score(filtered),
        reasoning_ref=None,
    )


def _cap_weights(weights: list[float], cap: float) -> list[float]:
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
    qs = [s.quality_score for s, _, _ in items if s.quality_score is not None]
    if not qs:
        return None
    return round(100.0 - sum(qs) / len(qs), 1)
