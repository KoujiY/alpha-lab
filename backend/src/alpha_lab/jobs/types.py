"""Job 類型列舉。新增 collector 時在此加一個 value 並在 service.run_job_sync 分派。"""

from enum import StrEnum


class JobType(StrEnum):
    TWSE_PRICES = "twse_prices"
    TWSE_PRICES_BATCH = "twse_prices_batch"  # 多 symbol 一次抓當月，前端用
    TWSE_STOCK_INFO = "twse_stock_info"
    MOPS_REVENUE = "mops_revenue"
    TWSE_INSTITUTIONAL = "twse_institutional"
    TWSE_MARGIN = "twse_margin"
    MOPS_EVENTS = "mops_events"
    MOPS_FINANCIALS = "mops_financials"
    MOPS_CASHFLOW = "mops_cashflow"
    SCORE = "score"
    YAHOO_PRICES = "yahoo_prices"
    PROCESSED_INDICATORS = "processed_indicators"
    PROCESSED_RATIOS = "processed_ratios"
    DAILY_BRIEFING = "daily_briefing"
