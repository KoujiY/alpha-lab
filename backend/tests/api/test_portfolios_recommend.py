"""POST /api/portfolios/recommend 整合測試。"""

import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alpha_lab.api.main import app
from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.models import Base, Score, Stock


def _make_test_engine() -> Engine:
    return create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _override_engine(test_engine: Engine) -> None:
    Base.metadata.create_all(test_engine)
    engine_module._engine = test_engine
    engine_module._SessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )


def test_recommend_all_styles() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        for i in range(12):
            sym = f"C{i:03d}"
            s.add(Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 3}"))
            s.add(
                Score(
                    symbol=sym,
                    calc_date=date(2026, 4, 15),
                    value_score=50 + i,
                    growth_score=50 + i,
                    dividend_score=50 + i,
                    quality_score=50 + i,
                    total_score=50 + i,
                )
            )

    with TestClient(app) as client:
        r = client.post("/api/portfolios/recommend")

    assert r.status_code == 200
    data = r.json()
    assert len(data["portfolios"]) == 3
    styles = [p["style"] for p in data["portfolios"]]
    assert set(styles) == {"conservative", "balanced", "aggressive"}
    balanced = next(p for p in data["portfolios"] if p["style"] == "balanced")
    assert balanced["is_top_pick"] is True
    # Phase 4：每檔 holding 至少帶一條理由
    assert balanced["holdings"], "balanced 應至少有一檔"
    for h in balanced["holdings"]:
        assert isinstance(h["reasons"], list)
        assert len(h["reasons"]) >= 1


def test_recommend_single_style() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        s.add(
            Score(
                symbol="2330",
                calc_date=date(2026, 4, 15),
                value_score=80,
                growth_score=80,
                dividend_score=80,
                quality_score=80,
                total_score=80,
            )
        )

    with TestClient(app) as client:
        r = client.post("/api/portfolios/recommend?style=aggressive")

    assert r.status_code == 200
    data = r.json()
    assert len(data["portfolios"]) == 1
    assert data["portfolios"][0]["style"] == "aggressive"


def test_recommend_save_report_writes_markdown_and_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        for i in range(6):
            sym = f"D{i:03d}"
            s.add(Stock(symbol=sym, name=f"股{i}", industry=f"產業{i % 2}"))
            s.add(
                Score(
                    symbol=sym,
                    calc_date=date(2026, 4, 15),
                    value_score=60 + i,
                    growth_score=60 + i,
                    dividend_score=60 + i,
                    quality_score=60 + i,
                    total_score=60 + i,
                )
            )

    with TestClient(app) as client:
        r = client.post("/api/portfolios/recommend?save_report=true")

    assert r.status_code == 200

    analysis_dir = tmp_path / "analysis"
    md_path = analysis_dir / "portfolio-2026-04-15.md"
    assert md_path.exists()
    md = md_path.read_text(encoding="utf-8")
    assert "本次推薦組合" in md
    assert "date: '2026-04-15'" in md or "date: 2026-04-15" in md
    assert "Top Pick" in md

    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    ids = [item["id"] for item in index["reports"]]
    assert "portfolio-2026-04-15" in ids

    summary = json.loads(
        (tmp_path / "summaries" / "2026-04-15.json").read_text(encoding="utf-8")
    )
    assert summary and "Top Pick" in summary[-1]["summary"]


def test_recommend_without_save_flag_does_not_touch_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)
    monkeypatch.setenv("ALPHA_LAB_REPORTS_ROOT", str(tmp_path))

    from alpha_lab.storage.engine import session_scope

    with session_scope() as s:
        s.add(Stock(symbol="2330", name="台積電", industry="半導體"))
        s.add(
            Score(
                symbol="2330",
                calc_date=date(2026, 4, 15),
                value_score=80,
                growth_score=80,
                dividend_score=80,
                quality_score=80,
                total_score=80,
            )
        )

    with TestClient(app) as client:
        r = client.post("/api/portfolios/recommend")

    assert r.status_code == 200
    assert not (tmp_path / "index.json").exists()
    assert not (tmp_path / "analysis").exists()


def test_recommend_409_when_no_scores() -> None:
    test_engine = _make_test_engine()
    _override_engine(test_engine)

    with TestClient(app) as client:
        r = client.post("/api/portfolios/recommend")

    assert r.status_code == 409
