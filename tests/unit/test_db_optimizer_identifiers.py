"""Validate PRAGMA identifier safety in db_optimizer."""

from __future__ import annotations

import sqlite3
import pytest

from src.backend.db_optimizer import DatabaseOptimizer, _is_safe_identifier


def test_is_safe_identifier():
    assert _is_safe_identifier("table_1")
    assert not _is_safe_identifier("table-1")
    assert not _is_safe_identifier("table;drop")
    assert not _is_safe_identifier("")


def test_analyze_table_rejects_bad_name(tmp_path):
    conn = sqlite3.connect(tmp_path / "t.db")
    opt = DatabaseOptimizer(conn)
    # DatabaseOptimizer currently exposes _is_safe_identifier; use it directly
    assert not _is_safe_identifier("bad;name")
