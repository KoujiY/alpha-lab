"""SavedPortfolioCreate schema 驗證測試（Phase 7）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from alpha_lab.schemas.saved_portfolio import SavedHolding, SavedPortfolioCreate


def _holding(symbol: str, weight: float) -> SavedHolding:
    return SavedHolding(symbol=symbol, name=symbol, weight=weight, base_price=100.0)


def test_create_accepts_valid_weights_summing_to_one():
    payload = SavedPortfolioCreate(
        style="balanced",
        label="ok",
        holdings=[_holding("2330", 0.6), _holding("2317", 0.4)],
    )
    assert sum(h.weight for h in payload.holdings) == pytest.approx(1.0)


def test_create_accepts_float_drift_within_1e6():
    # 典型 buildMergedHoldings 產生的浮點漂移
    payload = SavedPortfolioCreate(
        style="balanced",
        label="drift",
        holdings=[
            _holding("2330", 0.54),
            _holding("2317", 0.36),
            _holding("9999", 0.10000000001),  # 漂移在 1e-6 以內
        ],
    )
    assert len(payload.holdings) == 3


def test_create_rejects_weights_not_summing_to_one():
    with pytest.raises(ValidationError, match=r"weights must sum to 1\.0"):
        SavedPortfolioCreate(
            style="balanced",
            label="bad-sum",
            holdings=[_holding("2330", 0.6), _holding("2317", 0.3)],
        )


def test_create_accepts_drift_at_tolerance_boundary():
    # 剛好落在 1e-6 容許值邊界：|sum - 1.0| == 1e-6 應通過
    payload = SavedPortfolioCreate(
        style="balanced",
        label="boundary",
        holdings=[
            _holding("2330", 0.5),
            _holding("2317", 0.5 - 1e-6),
        ],
    )
    assert len(payload.holdings) == 2


def test_create_rejects_drift_just_over_tolerance():
    # 超過 1e-6 tolerance 應被拒絕；證明 tolerance 常數確實接上
    with pytest.raises(ValidationError, match=r"weights must sum to 1\.0"):
        SavedPortfolioCreate(
            style="balanced",
            label="over",
            holdings=[
                _holding("2330", 0.5),
                _holding("2317", 0.5 - 1e-3),
            ],
        )


def test_create_rejects_duplicate_symbols():
    with pytest.raises(ValidationError, match="duplicate symbol"):
        SavedPortfolioCreate(
            style="balanced",
            label="dup",
            holdings=[_holding("2330", 0.5), _holding("2330", 0.5)],
        )


def test_create_accepts_parent_id_optional():
    payload = SavedPortfolioCreate(
        style="balanced",
        label="fork",
        holdings=[_holding("2330", 1.0)],
        parent_id=7,
    )
    assert payload.parent_id == 7


def test_create_defaults_parent_id_none():
    payload = SavedPortfolioCreate(
        style="balanced",
        label="solo",
        holdings=[_holding("2330", 1.0)],
    )
    assert payload.parent_id is None
