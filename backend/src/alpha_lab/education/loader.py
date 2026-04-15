"""L2 詳解 markdown 載入器。

每個 topic 為 `l2/<id>.md`，結構：
```
---
id: PE
title: 本益比（PE）深度解說
related_terms: [EPS, PB]
---

# 正文標題

正文內容 markdown...
```
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from alpha_lab.schemas.education import L2Topic

_L2_ROOT = Path(__file__).parent / "l2"


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """將 markdown 拆成 (frontmatter_dict, body)。

    要求第一行 `---`、frontmatter 以第二個 `---` 結尾；不符合格式則報 ValueError。
    """

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing leading '---' frontmatter marker")

    try:
        end_idx = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing '---' frontmatter marker") from exc

    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).strip()
    parsed = yaml.safe_load(fm_text) or {}
    if not isinstance(parsed, dict):
        raise ValueError("frontmatter must be a mapping")
    return parsed, body


def _load_from_dir(src: Path) -> dict[str, L2Topic]:
    if not src.exists():
        return {}

    topics: dict[str, L2Topic] = {}
    for md_path in sorted(src.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        try:
            fm, body = _split_frontmatter(raw)
        except ValueError as exc:
            raise ValueError(f"{md_path}: {exc}") from exc

        topic_id = str(fm.get("id") or md_path.stem)
        title = fm.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{md_path}: frontmatter missing valid 'title'")
        related = fm.get("related_terms") or []
        if not isinstance(related, list):
            raise ValueError(f"{md_path}: related_terms must be a list")
        related_terms = [str(r) for r in related]

        topics[topic_id] = L2Topic(
            id=topic_id,
            title=title,
            related_terms=related_terms,
            body_markdown=body,
        )

    return topics


@lru_cache(maxsize=1)
def _load_default_cached() -> dict[str, L2Topic]:
    return _load_from_dir(_L2_ROOT)


def load_l2_topics(path: Path | None = None) -> dict[str, L2Topic]:
    """載入所有 L2 詳解；path 為 None 走快取。"""

    if path is None:
        return _load_default_cached()
    return _load_from_dir(path)


def get_l2_topic(topic_id: str) -> L2Topic | None:
    return load_l2_topics().get(topic_id)


def clear_cache() -> None:
    _load_default_cached.cache_clear()
