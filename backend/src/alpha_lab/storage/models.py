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


class InstitutionalTrade(Base):
    """三大法人買賣超（TWSE T86）。單位：股。"""

    __tablename__ = "institutional_trades"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    foreign_net: Mapped[int] = mapped_column(Integer, nullable=False)
    trust_net: Mapped[int] = mapped_column(Integer, nullable=False)
    dealer_net: Mapped[int] = mapped_column(Integer, nullable=False)
    total_net: Mapped[int] = mapped_column(Integer, nullable=False)


class MarginTrade(Base):
    """融資融券（TWSE MI_MARGN）。單位：張。"""

    __tablename__ = "margin_trades"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    margin_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_buy: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_sell: Mapped[int] = mapped_column(Integer, nullable=False)
    short_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    short_sell: Mapped[int] = mapped_column(Integer, nullable=False)
    short_cover: Mapped[int] = mapped_column(Integer, nullable=False)


class Event(Base):
    """重大訊息（MOPS t146sb05）。

    主鍵為 autoincrement id — 同公司同時刻可能多則訊息，且內容需保留全文。
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), nullable=False, index=True
    )
    event_datetime: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")


class FinancialStatement(Base):
    """季報三表（MOPS t164sb03 / t164sb04 / t164sb05）。

    寬表策略：統一 (symbol, period, statement_type) 主鍵；三類欄位集都 nullable。
    raw_json_text 保留原始項目（SQLite 用 Text 儲存 JSON 字串）。
    """

    __tablename__ = "financial_statements"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    period: Mapped[str] = mapped_column(String(8), primary_key=True)  # "2026Q1"
    statement_type: Mapped[str] = mapped_column(String(16), primary_key=True)

    # income
    revenue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gross_profit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operating_income: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_income: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)

    # balance
    total_assets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_liabilities: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_equity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # cashflow
    operating_cf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investing_cf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financing_cf: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_json_text: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class Score(Base):
    """多因子評分（Phase 3）。

    每個因子 0-100 分，total_score 為加權平均（權重隨風格調整時在 runtime 算）。
    本表儲存四個因子的「中性」分數；組合推薦時讀取並按風格權重加權。
    """

    __tablename__ = "scores"

    symbol: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.symbol"), primary_key=True
    )
    calc_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    growth_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class SavedPortfolio(Base):
    """使用者儲存的組合（來自推薦 snapshot 或由其他組合 fork 而來）。

    holdings_json：list of {symbol, name, weight, base_price}
    parent_id / parent_nav_at_fork：若此組合由另一組合「加入個股」建立，記錄血緣。
    parent_nav_at_fork 存 fork 當下父組合的 latest_nav，讓績效頁能把父段與 self 段
    NAV 接成連續曲線顯示。
    """

    __tablename__ = "portfolios_saved"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    style: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    holdings_json: Mapped[str] = mapped_column(Text, nullable=False)
    base_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utc_now
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("portfolios_saved.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_nav_at_fork: Mapped[float | None] = mapped_column(Float, nullable=True)


class PortfolioSnapshot(Base):
    """每日 NAV 快照（選用：`GET /saved/{id}/performance` 會同步寫一份）。"""

    __tablename__ = "portfolio_snapshots"

    portfolio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portfolios_saved.id"), primary_key=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav: Mapped[float] = mapped_column(Float, nullable=False)
    holdings_json: Mapped[str] = mapped_column(Text, nullable=False)
