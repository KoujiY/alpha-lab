"""Job 類型列舉。新增 collector 時在此加一個 value 並在 service.run_job_sync 分派。"""

from enum import StrEnum


class JobType(StrEnum):
    TWSE_PRICES = "twse_prices"
    MOPS_REVENUE = "mops_revenue"
    TWSE_INSTITUTIONAL = "twse_institutional"
    TWSE_MARGIN = "twse_margin"
    MOPS_EVENTS = "mops_events"
    MOPS_FINANCIALS = "mops_financials"
    MOPS_CASHFLOW = "mops_cashflow"
    SCORE = "score"
