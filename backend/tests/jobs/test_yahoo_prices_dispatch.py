"""TWSE_PRICES dispatch 的 fallback 行為與 YAHOO_PRICES dispatch。"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.schemas.price import DailyPrice
from alpha_lab.storage.models import Job, PriceDaily


@pytest.mark.asyncio
async def test_twse_prices_falls_back_to_yahoo_on_transient_error(session_factory):
    """TWSE 拋非 WAF ValueError → 自動 fallback Yahoo。最後 row.source == 'yahoo'。"""
    yahoo_rows = [
        DailyPrice(
            symbol="2330", trade_date=date(2026, 4, 10),
            open=700.0, high=705.0, low=698.0, close=702.0,
            volume=1_000_000, source="yahoo",
        )
    ]

    with session_factory() as s:
        job = create_job(s, job_type=JobType.TWSE_PRICES, params={"symbol": "2330", "year_month": "2026-04"})
        s.commit()
        job_id = job.id

    with patch("alpha_lab.jobs.service.fetch_daily_prices", new=AsyncMock(side_effect=ValueError("TWSE returned non-OK stat: 系統忙線中"))), \
         patch("alpha_lab.jobs.service.fetch_yahoo_daily_prices", new=AsyncMock(return_value=yahoo_rows)):
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "completed"
        assert done.result_summary is not None
        assert "yahoo" in done.result_summary
        row = s.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 10)})
        assert row is not None
        assert row.source == "yahoo"


@pytest.mark.asyncio
async def test_twse_prices_does_not_fallback_on_waf(session_factory):
    """WAF 錯誤直接 fail，不走 Yahoo。"""
    from alpha_lab.collectors._twse_common import TWSERateLimitError

    with session_factory() as s:
        job = create_job(s, job_type=JobType.TWSE_PRICES, params={"symbol": "2330", "year_month": "2026-04"})
        s.commit()
        job_id = job.id

    yahoo_mock = AsyncMock()
    with patch("alpha_lab.jobs.service.fetch_daily_prices", new=AsyncMock(side_effect=TWSERateLimitError("WAF"))), \
         patch("alpha_lab.jobs.service.fetch_yahoo_daily_prices", new=yahoo_mock):
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    yahoo_mock.assert_not_called()
    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "failed"


@pytest.mark.asyncio
async def test_yahoo_prices_direct_dispatch(session_factory):
    yahoo_rows = [
        DailyPrice(
            symbol="2330", trade_date=date(2026, 4, 11),
            open=700.0, high=705.0, low=698.0, close=702.0,
            volume=1_000_000, source="yahoo",
        )
    ]
    with session_factory() as s:
        job = create_job(
            s,
            job_type=JobType.YAHOO_PRICES,
            params={"symbol": "2330", "start": "2026-04-11", "end": "2026-04-11"},
        )
        s.commit()
        job_id = job.id

    with patch("alpha_lab.jobs.service.fetch_yahoo_daily_prices", new=AsyncMock(return_value=yahoo_rows)):
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as s:
        done = s.get(Job, job_id)
        assert done is not None
        assert done.status == "completed"
        row = s.get(PriceDaily, {"symbol": "2330", "trade_date": date(2026, 4, 11)})
        assert row is not None
        assert row.source == "yahoo"
