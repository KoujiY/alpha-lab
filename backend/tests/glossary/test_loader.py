"""Glossary loader 測試。"""

from pathlib import Path

import pytest

from alpha_lab.glossary.loader import load_terms
from alpha_lab.schemas.glossary import GlossaryTerm


def test_load_default_terms_yaml() -> None:
    load_terms.cache_clear()
    terms = load_terms()
    assert "PE" in terms
    assert terms["PE"].term == "本益比"


def test_load_custom_path(tmp_path: Path) -> None:
    load_terms.cache_clear()
    yaml_text = """
EPS:
  term: 每股盈餘
  short: 公司每股賺多少
"""
    p = tmp_path / "terms.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    terms = load_terms(p)
    assert isinstance(terms["EPS"], GlossaryTerm)
    assert terms["EPS"].short == "公司每股賺多少"


def test_load_rejects_non_mapping(tmp_path: Path) -> None:
    load_terms.cache_clear()
    p = tmp_path / "terms.yaml"
    p.write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_terms(p)
