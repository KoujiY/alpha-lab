"""Phase 1 採用 SQLAlchemy create_all 自動建表；Phase 7 起補上欄位 migration。"""

from pathlib import Path

from alpha_lab.storage.engine import get_engine
from alpha_lab.storage.migrations import add_column_if_missing
from alpha_lab.storage.models import Base


def init_database() -> None:
    """建立所有表（若已存在則跳過）並補上新增欄位。"""
    engine = get_engine()
    url = str(engine.url)
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:"):
        db_path = Path(url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(engine)

    # Phase 7 portfolios_saved 血緣欄位（既存舊 schema DB 用）
    add_column_if_missing(engine, "portfolios_saved", "parent_id", "INTEGER")
    add_column_if_missing(
        engine, "portfolios_saved", "parent_nav_at_fork", "FLOAT"
    )
