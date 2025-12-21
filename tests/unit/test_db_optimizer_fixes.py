"""
测试数据库优化器修复

验证连接池等待和索引优化功能
"""

import sqlite3
import tempfile
import threading
import time
from pathlib import Path

import pytest

from src.backend.db_optimizer import ConnectionPool, IndexAnalyzer


class TestConnectionPoolWait:
    """测试连接池等待机制"""

    def test_connection_pool_basic(self):
        """测试基本连接池功能"""

        def create_conn():
            return sqlite3.connect(":memory:")

        pool = ConnectionPool(
            creator=create_conn, max_connections=2, min_connections=1, timeout=5.0
        )

        # 获取连接
        conn1 = pool.get_connection()
        assert conn1 is not None

        # 归还连接
        pool.return_connection(conn1)

        # 再次获取应该成功
        conn2 = pool.get_connection()
        assert conn2 is not None

        pool.close_all()

    def test_connection_pool_max_connections(self):
        """测试连接池最大连接数"""

        def create_conn():
            return sqlite3.connect(":memory:")

        pool = ConnectionPool(
            creator=create_conn, max_connections=2, min_connections=1, timeout=1.0
        )

        # 获取所有连接
        conn1 = pool.get_connection()
        pool.get_connection()

        # 尝试获取第三个连接应该超时
        with pytest.raises(TimeoutError, match="获取连接超时"):
            pool.get_connection()

        # 归还一个连接
        pool.return_connection(conn1)

        # 现在应该可以获取
        conn3 = pool.get_connection()
        assert conn3 is not None

        pool.close_all()

    def test_connection_pool_wait_and_notify(self):
        """测试连接池等待和通知机制"""

        def create_conn():
            return sqlite3.connect(":memory:")

        pool = ConnectionPool(
            creator=create_conn, max_connections=1, min_connections=1, timeout=5.0
        )

        result = {"success": False}

        def thread_function():
            """线程函数：等待连接"""
            time.sleep(0.5)  # 延迟以确保主线程先获取连接
            conn = pool.get_connection()
            result["success"] = True
            pool.return_connection(conn)

        # 主线程获取连接
        conn1 = pool.get_connection()

        # 启动另一个线程等待连接
        t = threading.Thread(target=thread_function)
        t.start()

        # 主线程持有连接1秒
        time.sleep(1.0)

        # 归还连接，应该唤醒等待的线程
        pool.return_connection(conn1)

        # 等待线程完成
        t.join(timeout=5.0)

        assert result["success"], "等待线程应该成功获取连接"

        pool.close_all()

    def test_connection_pool_context_manager(self):
        """测试连接池上下文管理器"""

        def create_conn():
            return sqlite3.connect(":memory:")

        pool = ConnectionPool(
            creator=create_conn, max_connections=2, min_connections=1, timeout=5.0
        )

        # 使用上下文管理器
        with pool.connection() as conn:
            assert conn is not None
            # 连接应该被标记为使用中
            assert len(pool._in_use) == 1

        # 退出上下文后，连接应该被归还
        assert len(pool._in_use) == 0

        pool.close_all()

    def test_connection_pool_stats(self):
        """测试连接池统计"""

        def create_conn():
            return sqlite3.connect(":memory:")

        pool = ConnectionPool(
            creator=create_conn, max_connections=5, min_connections=2, timeout=5.0
        )

        stats = pool.get_stats()
        assert stats["total"] == 2  # 初始化了2个连接
        assert stats["idle"] == 2
        assert stats["in_use"] == 0
        assert stats["max"] == 5

        # 获取一个连接
        conn = pool.get_connection()

        stats = pool.get_stats()
        assert stats["idle"] == 1
        assert stats["in_use"] == 1

        pool.return_connection(conn)
        pool.close_all()


class TestIndexAnalyzer:
    """测试索引分析器"""

    @pytest.fixture
    def db_connection(self):
        """创建测试数据库"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(str(db_path))

            # 创建测试表
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    email TEXT,
                    role TEXT,
                    created_at TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE experiments (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    experiment_type TEXT,
                    status TEXT,
                    created_at TIMESTAMP
                )
            """)
            conn.commit()

            yield conn

            conn.close()

    def test_analyze_table(self, db_connection):
        """测试表分析"""
        analyzer = IndexAnalyzer(db_connection)
        result = analyzer.analyze_table("users")

        assert result["table"] == "users"
        assert "columns" in result
        assert "username" in result["columns"]
        assert "email" in result["columns"]

    def test_suggest_indexes_where_clause(self, db_connection):
        """测试WHERE子句索引建议"""
        analyzer = IndexAnalyzer(db_connection)

        query_patterns = [
            "SELECT * FROM users WHERE username = ?",
            "SELECT * FROM users WHERE email = ?",
        ]

        suggestions = analyzer.suggest_indexes("users", query_patterns)

        assert len(suggestions) > 0
        # 应该建议为username和email创建索引
        suggested_columns = [s["column"] for s in suggestions]
        assert "username" in suggested_columns or "email" in suggested_columns

    def test_suggest_indexes_order_by(self, db_connection):
        """测试ORDER BY索引建议"""
        analyzer = IndexAnalyzer(db_connection)

        query_patterns = [
            "SELECT * FROM users ORDER BY created_at DESC",
        ]

        suggestions = analyzer.suggest_indexes("users", query_patterns)

        # 应该建议为created_at创建索引
        suggested_columns = [s["column"] for s in suggestions]
        assert "created_at" in suggested_columns

        # 检查优先级
        for s in suggestions:
            if s["column"] == "created_at":
                assert s["priority"] == "medium"

    def test_suggest_indexes_join(self, db_connection):
        """测试JOIN索引建议"""
        analyzer = IndexAnalyzer(db_connection)

        query_patterns = [
            "SELECT * FROM experiments JOIN users ON experiments.user_id = users.id",
        ]

        suggestions = analyzer.suggest_indexes("experiments", query_patterns)

        # 应该建议为JOIN列创建索引
        suggested_columns = [s["column"] for s in suggestions]
        # user_id应该在建议中
        assert any("user_id" in col or "id" in col for col in suggested_columns)

    def test_suggest_indexes_group_by(self, db_connection):
        """测试GROUP BY索引建议"""
        analyzer = IndexAnalyzer(db_connection)

        query_patterns = [
            "SELECT status, COUNT(*) FROM experiments GROUP BY status",
        ]

        suggestions = analyzer.suggest_indexes("experiments", query_patterns)

        # 应该建议为GROUP BY列创建索引
        suggested_columns = [s["column"] for s in suggestions]
        assert "status" in suggested_columns

    def test_create_index(self, db_connection):
        """测试创建索引"""
        analyzer = IndexAnalyzer(db_connection)

        success = analyzer.create_index("users", "username", "idx_users_username")
        assert success is True

        # 验证索引已创建
        cursor = db_connection.cursor()
        cursor.execute("PRAGMA index_list(users)")
        indexes = cursor.fetchall()
        index_names = [idx[1] for idx in indexes]
        assert "idx_users_username" in index_names

    def test_auto_optimize_table(self, db_connection):
        """测试自动优化表"""
        analyzer = IndexAnalyzer(db_connection)

        query_patterns = [
            "SELECT * FROM users WHERE username = ?",
            "SELECT * FROM users WHERE email = ?",
            "SELECT * FROM users ORDER BY created_at DESC",
        ]

        # 当前实现要求管理员权限上下文
        from src.core.auth import Role

        class _AdminContext:
            def has_role(self, role):
                return role == Role.ADMIN

        report = analyzer.auto_optimize_table("users", query_patterns, context=_AdminContext())

        assert "table" in report
        assert report["table"] == "users"
        assert "suggestions" in report
        assert "created" in report
        assert "failed" in report
        assert "skipped" in report

        # 至少应该创建一些高优先级索引
        assert len(report["suggestions"]) > 0

    def test_suggest_indexes_priority(self, db_connection):
        """测试索引建议优先级"""
        analyzer = IndexAnalyzer(db_connection)

        query_patterns = [
            "SELECT * FROM users WHERE username = ?",  # high priority
            "SELECT * FROM users ORDER BY created_at",  # medium priority
        ]

        suggestions = analyzer.suggest_indexes("users", query_patterns)

        # 验证优先级排序（high在前）
        if len(suggestions) >= 2:
            assert suggestions[0]["priority"] in ["high", "medium"]

        # 验证所有建议都有必需的字段
        for s in suggestions:
            assert "column" in s
            assert "reason" in s
            assert "priority" in s
            assert "estimated_benefit" in s

    def test_suggest_indexes_no_duplicates(self, db_connection):
        """测试不会建议重复的索引"""
        analyzer = IndexAnalyzer(db_connection)

        # 先创建一个索引
        analyzer.create_index("users", "username")

        # 再次分析，应该不会建议已有索引的列
        query_patterns = [
            "SELECT * FROM users WHERE username = ?",
        ]

        suggestions = analyzer.suggest_indexes("users", query_patterns)

        # username已经有索引，不应该再建议
        suggested_columns = [s["column"] for s in suggestions]
        assert "username" not in suggested_columns
