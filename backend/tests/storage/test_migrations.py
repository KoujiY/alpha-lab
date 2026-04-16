"""storage.migrations helper 單元測試。"""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect
from sqlalchemy.pool import StaticPool

from alpha_lab.storage.migrations import add_column_if_missing


def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_add_column_if_missing_adds_new_column():
    engine = _make_engine()
    meta = MetaData()
    Table("foo", meta, Column("id", Integer, primary_key=True))
    meta.create_all(engine)

    assert add_column_if_missing(engine, "foo", "note", "TEXT") is True

    cols = {c["name"] for c in inspect(engine).get_columns("foo")}
    assert "note" in cols


def test_add_column_if_missing_skips_when_present():
    engine = _make_engine()
    meta = MetaData()
    Table(
        "foo",
        meta,
        Column("id", Integer, primary_key=True),
        Column("note", String),
    )
    meta.create_all(engine)

    # 呼叫兩次不會炸
    add_column_if_missing(engine, "foo", "note", "TEXT")
    assert add_column_if_missing(engine, "foo", "note", "TEXT") is False

    cols = {c["name"] for c in inspect(engine).get_columns("foo")}
    assert "note" in cols


def test_add_column_if_missing_table_not_exist_raises():
    engine = _make_engine()

    with pytest.raises(ValueError, match="table 'foo' not found"):
        add_column_if_missing(engine, "foo", "note", "TEXT")
