"""Glossary YAML loader。

- 載入時驗證每條為 `GlossaryTerm`
- 預設檔採單例快取（個人工具，不需 hot reload）
- 自訂路徑的呼叫不快取（供測試與未來多檔案場景）
"""

from functools import lru_cache
from pathlib import Path

import yaml

from alpha_lab.schemas.glossary import GlossaryTerm

_DEFAULT_PATH = Path(__file__).parent / "terms.yaml"


def _load_from_path(src: Path) -> dict[str, GlossaryTerm]:
    if not src.exists():
        return {}
    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{src}: top-level must be a mapping")
    try:
        return {key: GlossaryTerm(**value) for key, value in raw.items()}
    except Exception as exc:
        raise ValueError(f"{src}: failed to parse terms — {exc}") from exc


@lru_cache(maxsize=1)
def _load_default_cached() -> dict[str, GlossaryTerm]:
    return _load_from_path(_DEFAULT_PATH)


def load_terms(path: Path | None = None) -> dict[str, GlossaryTerm]:
    """載入整份 terms.yaml 為 {key: GlossaryTerm}。

    path 為 None 時走單例快取；傳入自訂路徑時每次重讀（測試用）。
    """
    if path is None:
        return _load_default_cached()
    return _load_from_path(path)


def clear_cache() -> None:
    """測試用：清空預設檔案快取。"""
    _load_default_cached.cache_clear()


def get_term(key: str) -> GlossaryTerm | None:
    """取單一術語；找不到回 None。"""
    return load_terms().get(key)
