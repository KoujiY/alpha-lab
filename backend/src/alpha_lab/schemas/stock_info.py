"""上市公司基本資料 Pydantic 模型。

來源：TWSE OpenAPI `v1/opendata/t187ap03_L`（上市公司基本資料）。
目的：補上 `stocks` 表的 `name` / `industry` / `listed_date`（Phase 1 collector 僅建 placeholder）。
"""

from datetime import date

from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    """單一上市公司的基本資料。"""

    symbol: str = Field(..., min_length=1, max_length=10, description="公司代號")
    name: str = Field(..., min_length=1, max_length=64, description="公司簡稱")
    industry: str | None = Field(
        None, max_length=64, description="產業別；TWSE 可能為空字串"
    )
    listed_date: date | None = Field(
        None, description="上市日期；TWSE 以民國格式提供，collector 解析為西元 date"
    )
