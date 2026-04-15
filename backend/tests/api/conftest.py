"""API 測試共用 fixtures。"""

import pytest

from alpha_lab.glossary.loader import clear_cache


@pytest.fixture(autouse=True)
def _clear_glossary_cache() -> None:
    """每個 API 測試執行前清掉 glossary 預設檔快取。"""
    clear_cache()
