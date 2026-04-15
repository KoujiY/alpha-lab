"""Backfill industry tag onto existing Stock rows.

讀 `src/alpha_lab/storage/industry_map.yaml`，對 DB 中存在的 symbol 更新 industry。
對映表中沒有的 symbol 不動（保留 None 或既有值）。

Usage:
    python -m scripts.backfill_industry
"""

from pathlib import Path

import yaml

from alpha_lab.storage.engine import session_scope
from alpha_lab.storage.models import Stock

_MAP_PATH = (
    Path(__file__).parent.parent
    / "src"
    / "alpha_lab"
    / "storage"
    / "industry_map.yaml"
)


def load_industry_map(path: Path = _MAP_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in raw.items()}


def backfill() -> int:
    mapping = load_industry_map()
    updated = 0
    with session_scope() as session:
        for symbol, industry in mapping.items():
            stock = session.get(Stock, symbol)
            if stock is not None and stock.industry != industry:
                stock.industry = industry
                updated += 1
    return updated


if __name__ == "__main__":
    n = backfill()
    print(f"updated {n} stocks")
