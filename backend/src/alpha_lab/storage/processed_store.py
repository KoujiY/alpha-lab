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
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result
