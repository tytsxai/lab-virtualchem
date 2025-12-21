import sqlite3

import pytest

from src.backend.db_optimizer import IndexAnalyzer
from src.core.auth import AuthContext, Role, Token, User


def _make_context(*roles: Role) -> AuthContext:
    user = User(
        id="u1",
        username="user",
        email="u1@example.com",
        password_hash="x",
        roles=list(roles),
    )
    token = Token(access_token="t")
    return AuthContext(user=user, token=token, permissions=set())


def test_create_index_rejects_unsafe_identifiers() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    analyzer = IndexAnalyzer(conn)

    ok = analyzer.create_index(
        table_name="demo",
        column_name="name); DROP TABLE demo; --",
        index_name="idx_demo_name",
    )
    assert ok is False

    # Table must still exist (no injection).
    conn.execute("SELECT 1 FROM demo LIMIT 1").fetchall()


def test_auto_optimize_table_requires_admin() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    analyzer = IndexAnalyzer(conn)

    with pytest.raises(PermissionError):
        analyzer.auto_optimize_table("demo", [], context=_make_context(Role.STUDENT))


def test_auto_optimize_table_enforces_rate_limit() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    analyzer = IndexAnalyzer(conn)
    admin_ctx = _make_context(Role.ADMIN)

    for _ in range(5):
        report = analyzer.auto_optimize_table("demo", [], context=admin_ctx)
        assert report["table"] == "demo"

    with pytest.raises(RuntimeError):
        analyzer.auto_optimize_table("demo", [], context=admin_ctx)

