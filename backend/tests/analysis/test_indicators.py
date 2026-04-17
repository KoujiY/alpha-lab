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
