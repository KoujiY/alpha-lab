"""MOPS 季報 collector 單元測試 — 本 Task 只驗證 income。"""

import respx

from alpha_lab.collectors.mops_financials import fetch_income_statement
from alpha_lab.schemas.financial_statement import FinancialStatement, StatementType

SAMPLE_INCOME = [
    {
        "出表日期": "1150515",
        "年度": "115",
        "季別": "1",
        "公司代號": "2330",
        "公司名稱": "台積電",
        "營業收入": "300000000",
        "營業毛利(毛損)": "180000000",
        "營業利益(損失)": "120000000",
        "本期淨利(淨損)": "100000000",
        "基本每股盈餘(元)": "10.50",
    },
    {
        "出表日期": "1150515",
        "年度": "115",
        "季別": "1",
        "公司代號": "2317",
        "公司名稱": "鴻海",
        "營業收入": "500000000",
        "營業毛利(毛損)": "50000000",
        "營業利益(損失)": "20000000",
        "本期淨利(淨損)": "15000000",
        "基本每股盈餘(元)": "2.30",
    },
]


async def test_fetch_income_statement_parses_sample() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap06_L_ci").respond(json=SAMPLE_INCOME)

        rows = await fetch_income_statement(symbols=["2330"])

    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, FinancialStatement)
    assert r.symbol == "2330"
    assert r.period == "2026Q1"
    assert r.statement_type == StatementType.INCOME
    assert r.revenue == 300_000_000
    assert r.gross_profit == 180_000_000
    assert r.operating_income == 120_000_000
    assert r.net_income == 100_000_000
    assert r.eps == 10.50


async def test_fetch_income_statement_all_symbols_when_none() -> None:
    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap06_L_ci").respond(json=SAMPLE_INCOME)
        rows = await fetch_income_statement(symbols=None)
    assert len(rows) == 2
