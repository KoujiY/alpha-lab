"""驗證 init_database() 在既存舊 schema DB 上能補欄位。"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from alpha_lab.storage import engine as engine_module
from alpha_lab.storage.init_db import init_database


def test_init_database_adds_parent_columns_to_existing_old_schema():
    test_engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 模擬舊版 schema：手動建表但不含 parent_id / parent_nav_at_fork
    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE portfolios_saved (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    style VARCHAR(16) NOT NULL,
                    label VARCHAR(32) NOT NULL,
                    note TEXT,
                    holdings_json TEXT NOT NULL,
                    base_date DATE NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    saved_engine = engine_module._engine
    saved_session_local = engine_module._SessionLocal
    engine_module._engine = test_engine
    engine_module._SessionLocal = None
    try:
        init_database()

        cols = {
            c["name"] for c in inspect(test_engine).get_columns("portfolios_saved")
        }
        assert "parent_id" in cols
        assert "parent_nav_at_fork" in cols
    finally:
        engine_module._engine = saved_engine
        engine_module._SessionLocal = saved_session_local
