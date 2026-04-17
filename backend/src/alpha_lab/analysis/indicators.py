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
    prices: list[tuple[date, float, float, float]],
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
