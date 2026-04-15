"""季報三表 Pydantic 模型。

來源：MOPS t164sb03（合併綜合損益表）、t164sb04（合併資產負債表）、t164sb05（合併現金流量表）
period 格式：`"2026Q1"`；statement_type：income | balance | cashflow。

寬表策略：三表共用同一 schema，各表常用欄位獨立存放；raw_json 保留所有原始項目。
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StatementType(StrEnum):
    INCOME = "income"
    BALANCE = "balance"
    CASHFLOW = "cashflow"


class FinancialStatement(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    period: str = Field(..., pattern=r"^\d{4}Q[1-4]$")
    statement_type: StatementType

    # income
    revenue: int | None = Field(None, description="營業收入（千元）")
    gross_profit: int | None = Field(None, description="營業毛利（千元）")
    operating_income: int | None = Field(None, description="營業利益（千元）")
    net_income: int | None = Field(None, description="本期淨利（千元）")
    eps: float | None = Field(None, description="每股盈餘（元）")

    # balance
    total_assets: int | None = Field(None, description="資產總額（千元）")
    total_liabilities: int | None = Field(None, description="負債總額（千元）")
    total_equity: int | None = Field(None, description="權益總額（千元）")

    # cashflow
    operating_cf: int | None = Field(None, description="營業活動現金流量（千元）")
    investing_cf: int | None = Field(None, description="投資活動現金流量（千元）")
    financing_cf: int | None = Field(None, description="籌資活動現金流量（千元）")

    raw_json: dict[str, Any] = Field(default_factory=dict, description="原始欄位保留")
