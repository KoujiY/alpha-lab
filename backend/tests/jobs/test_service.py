"""Job service 單元測試。"""

import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alpha_lab.jobs.service import create_job, run_job_sync
from alpha_lab.jobs.types import JobType
from alpha_lab.storage.models import Base, Job, PriceDaily


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def test_create_job_returns_pending(session_factory) -> None:
    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        assert job.id is not None
        assert job.status == "pending"
        assert job.job_type == "twse_prices"


async def test_run_job_sync_twse_prices_happy_path(session_factory) -> None:
    twse_payload = {
        "stat": "OK",
        "fields": [
            "日期", "成交股數", "成交金額", "開盤價", "最高價",
            "最低價", "收盤價", "漲跌價差", "成交筆數",
        ],
        "data": [
            ["115/04/01", "1000", "0", "100", "110", "99", "105", "+5", "1"],
        ],
    }

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(json=twse_payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.finished_at is not None
        assert session.query(PriceDaily).count() == 1


async def test_run_job_sync_marks_failed_on_error(session_factory) -> None:
    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_PRICES,
            params={"symbol": "2330", "year_month": "2026-04"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/afterTrading/STOCK_DAY").respond(500)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        failed = session.get(Job, job_id)
        assert failed is not None
        assert failed.status == "failed"
        assert failed.error_message is not None


@pytest.mark.asyncio
async def test_run_job_sync_twse_institutional_happy_path(session_factory) -> None:
    payload = {
        "stat": "OK",
        "fields": [
            "證券代號", "證券名稱",
            "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
            "外陸資買賣超股數(不含外資自營商)",
            "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
            "投信買進股數", "投信賣出股數", "投信買賣超股數",
            "自營商買賣超股數",
            "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)",
            "自營商買賣超股數(自行買賣)",
            "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
            "三大法人買賣超股數",
        ],
        "data": [
            ["2330", "台積電"] + ["0"] * 16 + ["1000"],
        ],
    }

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_INSTITUTIONAL,
            params={"trade_date": "2026-04-01"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/fund/T86").respond(json=payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import InstitutionalTrade as ITRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(ITRow).count() == 1


@pytest.mark.asyncio
async def test_run_job_sync_twse_margin_happy_path(session_factory) -> None:
    fields = [
        "代號", "名稱",
        "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額", "可用額度",
        "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額", "可用額度",
        "資券互抵", "註記",
    ]
    groups = [
        {"title": "股票", "span": 2},
        {"title": "融資", "span": 6},
        {"title": "融券", "span": 6},
        {"title": "", "span": 1},
        {"title": "", "span": 1},
    ]
    payload = {
        "stat": "OK",
        "tables": [
            {
                "title": "信用交易總計",
                "fields": ["項目", "買進"],
                "data": [],
            },
            {
                "title": "信用交易彙總",
                "groups": groups,
                "fields": fields,
                "data": [
                    [
                        "2330", "台積電",
                        "500", "400", "0", "10,100", "10,200", "999,999",
                        "30", "50", "0", "220", "200", "99,999",
                        "0", "",
                    ],
                ],
            },
        ],
    }

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.TWSE_MARGIN,
            params={"trade_date": "2026-04-01"},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://www.twse.com.tw") as mock:
        mock.get("/rwd/zh/marginTrading/MI_MARGN").respond(json=payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import MarginTrade as MTRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(MTRow).count() == 1


@pytest.mark.asyncio
async def test_run_job_sync_mops_events_happy_path(session_factory) -> None:
    payload = [
        {
            "出表日期": "1150411",
            "發言日期": "1150410",
            "發言時間": "143020",
            "公司代號": "2330",
            "公司名稱": "台積電",
            "主旨": "配息案",
            "符合條款": "第五款",
            "說明": "每股 11 元",
        },
    ]

    with session_factory() as session:
        job = create_job(
            session,
            job_type=JobType.MOPS_EVENTS,
            params={"symbols": ["2330"]},
        )
        session.commit()
        job_id = job.id

    with respx.mock(base_url="https://openapi.twse.com.tw") as mock:
        mock.get("/v1/opendata/t187ap04_L").respond(json=payload)
        await run_job_sync(job_id=job_id, session_factory=session_factory)

    with session_factory() as session:
        from alpha_lab.storage.models import Event as EventRow
        completed = session.get(Job, job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert session.query(EventRow).count() == 1
