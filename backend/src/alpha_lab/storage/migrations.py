"""極簡 idempotent schema migration helper。

SQLite 新增欄位一律走 ALTER TABLE ADD COLUMN；只在欄位不存在時執行。
遇到欄位型別不相容不做任何轉換——這套只負責補欄位，不處理型別遷移。

安全性注意：呼叫方必須確保 `table` / `column` / `column_type_sql` 皆為伺服器端
硬寫常數，不得來自外部輸入；SQLAlchemy 的 `text()` 並不會對 DDL 識別字做參數化。
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def add_column_if_missing(
    engine: Engine, table: str, column: str, column_type_sql: str
) -> bool:
    """若 `table.column` 不存在則 ALTER TABLE 新增。回傳是否實際新增。

    `column_type_sql`：原始 SQL 型別字串（例如 "INTEGER", "FLOAT", "TEXT"）。

    警告：`table` / `column` / `column_type_sql` 直接內插至 DDL，呼叫方須確保
    三者皆為硬寫常數，不可來自外部輸入。
    """

    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        raise ValueError(f"table '{table}' not found")
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return False
    with engine.begin() as conn:
        conn.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type_sql}")
        )
    return True
