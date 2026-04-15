"""Glossary 測試共用 fixtures。"""

import pytest

from alpha_lab.glossary.loader import clear_cache


@pytest.fixture(autouse=True)
def _clear_glossary_cache() -> None:
    clear_cache()
