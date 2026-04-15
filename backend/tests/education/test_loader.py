"""education/loader.py 單元測試。"""

from pathlib import Path

import pytest

from alpha_lab.education import loader as loader_module
from alpha_lab.education.loader import (
    _split_frontmatter,
    clear_cache,
    get_l2_topic,
    load_l2_topics,
)


@pytest.fixture(autouse=True)
def _clear_l2_cache() -> None:
    clear_cache()


def test_split_frontmatter_ok() -> None:
    text = "---\nid: foo\ntitle: Foo\n---\n\n# Body\n\npara"
    fm, body = _split_frontmatter(text)
    assert fm == {"id": "foo", "title": "Foo"}
    assert body.startswith("# Body")


def test_split_frontmatter_missing_leading_marker() -> None:
    with pytest.raises(ValueError, match="leading"):
        _split_frontmatter("# no frontmatter")


def test_split_frontmatter_missing_closing_marker() -> None:
    with pytest.raises(ValueError, match="closing"):
        _split_frontmatter("---\ntitle: x\n\n# body without closing ---")


def test_load_default_l2_topics_contains_core_entries() -> None:
    topics = load_l2_topics()
    assert "PE" in topics
    assert "ROE" in topics
    assert "dividend-yield" in topics
    assert "monthly-revenue" in topics
    assert "multi-factor-scoring" in topics


def test_get_l2_topic_returns_full_payload() -> None:
    topic = get_l2_topic("PE")
    assert topic is not None
    assert topic.id == "PE"
    assert "本益比" in topic.title
    assert topic.body_markdown.startswith("# 本益比是什麼")
    assert "EPS" in topic.related_terms


def test_get_l2_topic_missing_returns_none() -> None:
    assert get_l2_topic("nope-xyz") is None


def test_load_from_custom_path(tmp_path: Path) -> None:
    md = "---\nid: custom\ntitle: 自訂\nrelated_terms: [foo]\n---\n\n內文"
    (tmp_path / "custom.md").write_text(md, encoding="utf-8")
    topics = load_l2_topics(tmp_path)
    assert "custom" in topics
    assert topics["custom"].title == "自訂"
    assert topics["custom"].related_terms == ["foo"]


def test_custom_path_missing_title_raises(tmp_path: Path) -> None:
    md = "---\nid: bad\n---\n\n內文"
    (tmp_path / "bad.md").write_text(md, encoding="utf-8")
    with pytest.raises(ValueError, match="title"):
        load_l2_topics(tmp_path)


def test_empty_directory_returns_empty(tmp_path: Path) -> None:
    assert load_l2_topics(tmp_path) == {}


def test_default_cache_used(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    real = loader_module._load_from_dir

    def spy(path: Path) -> dict[str, object]:
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(loader_module, "_load_from_dir", spy)
    clear_cache()
    load_l2_topics()
    load_l2_topics()
    assert calls["n"] == 1
