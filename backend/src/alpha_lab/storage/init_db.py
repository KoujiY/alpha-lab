"""Phase 1 採用 SQLAlchemy create_all 自動建表。

Phase 1.5 若 schema 變動頻繁，再評估引入 Alembic。
"""

from pathlib import Path

from alpha_lab.storage.engine import get_engine
from alpha_lab.storage.models import Base


def init_database() -> None:
    """建立所有表（若已存在則跳過）。同時確保 sqlite 檔案所在資料夾存在。"""
    engine = get_engine()
    url = str(engine.url)
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(engine)
