"""Glossary v1 smoke test：確保 15 條核心術語存在且格式合法。"""

from alpha_lab.glossary.loader import load_terms

EXPECTED_TERMS = [
    "PE", "PB", "EPS", "ROE", "毛利率", "殖利率",
    "月營收", "YoY", "MoM",
    "三大法人", "外資", "投信", "自營商",
    "融資", "融券",
]


def test_v1_covers_15_core_terms() -> None:
    terms = load_terms()
    for key in EXPECTED_TERMS:
        assert key in terms, f"missing term: {key}"
    assert len(EXPECTED_TERMS) == 15


def test_every_term_has_non_empty_short() -> None:
    for key, term in load_terms().items():
        assert term.short.strip(), f"{key} has empty short"
        assert len(term.short) <= 200, f"{key} short too long"
