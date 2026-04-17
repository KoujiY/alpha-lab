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
