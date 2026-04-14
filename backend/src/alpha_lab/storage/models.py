"""SQLAlchemy declarative models。

Phase 1 scope:
- Stock: 股票基本資料
- PriceDaily: 日股價（TWSE 來源）
- RevenueMonthly: 月營收（MOPS 來源）
- Job: 抓取任務紀錄

Phase 1.5 將新增：FinancialStatement、InstitutionalTrade、MarginTrade、Event
"""

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Stock(Base):
    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    listed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    prices: Mapped[list["PriceDaily"]] = relationship(back_populates="stock")
    revenues: Mapped[list["RevenueMonthly"]] = relationship(back_populates="stock")


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

    stock: Mapped[Stock] = relationship(back_populates="prices")


class RevenueMonthly(Base):
    __tablename__ = "revenues_monthly"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(Integer, primary_key=True)
    revenue: Mapped[int] = mapped_column(Integer, nullable=False)
    yoy_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    mom_growth: Mapped[float | None] = mapped_column(Float, nullable=True)

    stock: Mapped[Stock] = relationship(back_populates="revenues")


class Job(Base):
    """抓取任務紀錄。

    status 生命週期：pending -> running -> (completed | failed)
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
