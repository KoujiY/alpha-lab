"""Glossary YAML loader。

- 載入時驗證每條為 `GlossaryTerm`
- 單例快取：第一次讀檔後常駐記憶體（個人工具，不需 hot reload）
"""

from functools import lru_cache
from pathlib import Path

import yaml

from alpha_lab.schemas.glossary import GlossaryTerm

_DEFAULT_PATH = Path(__file__).parent / "terms.yaml"


@lru_cache(maxsize=1)
def load_terms(path: Path | None = None) -> dict[str, GlossaryTerm]:
    """載入整份 terms.yaml 為 {key: GlossaryTerm}。"""
    src = path or _DEFAULT_PATH
    if not src.exists():
        return {}
    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{src}: top-level must be a mapping")
    return {key: GlossaryTerm(**value) for key, value in raw.items()}


def get_term(key: str) -> GlossaryTerm | None:
    """取單一術語；找不到回 None。"""
    return load_terms().get(key)
