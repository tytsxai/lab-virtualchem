import logging
import queue
import sqlite3
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any

try:
    import psycopg2
    from psycopg2 import pool

    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    psycopg2 = None
    pool = None

try:
    import pymysql

    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    pymysql = None

"""数据库连接池管理器"""

logger = logging.getLogger(__name__)

INTEGRITY_ERRORS: tuple[type[Exception], ...] = (sqlite3.IntegrityError,)

if POSTGRESQL_AVAILABLE:
    from psycopg2 import IntegrityError as PostgresIntegrityError

    INTEGRITY_ERRORS = INTEGRITY_ERRORS + (PostgresIntegrityError,)  # type: ignore[assignment]

if MYSQL_AVAILABLE:
    from pymysql.err import IntegrityError as MySQLIntegrityError

    INTEGRITY_ERRORS = INTEGRITY_ERRORS + (MySQLIntegrityError,)  # type: ignore[assignment]


@dataclass
class ConnectionInfo:
    """连接信息"""

    connection_id: str
    created_at: datetime
    last_used: datetime
    use_count: int
    is_active: bool = True


class DatabasePool:
    """数据库连接池"""

    def __init__(
        self,
        db_type: str = "sqlite",
        config: dict | None = None,
        min_connections: int = 2,
        max_connections: int = 10,
        connection_timeout: int = 30,
        idle_timeout: int = 300,
    ):
        """初始化数据库连接池

        Args:
            db_type: 数据库类型 (sqlite, postgresql, mysql)
            config: 数据库配置
            min_connections: 最小连接数
            max_connections: 最大连接数
            connection_timeout: 连接超时时间（秒）
            idle_timeout: 空闲超时时间（秒）
        """
        self.db_type = db_type
        self.config = config or {}
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout

        # 连接池
        self.available_connections = queue.Queue(maxsize=max_connections)
        self.all_connections: dict[str, Any] = {}
        self.connection_info: dict[str, ConnectionInfo] = {}

        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "connection_requests": 0,
            "connection_waits": 0,
            "connection_errors": 0,
        }

        self._lock = threading.RLock()
        self._connection_counter = 0

        # 初始化连接池
        self._initialize_pool()

        logger.info(
            f"数据库连接池已初始化 ({db_type}, 最小: {min_connections}, 最大: {max_connections})"
        )

    def _initialize_pool(self) -> None:
        """初始化连接池"""
        try:
            # 创建最小连接数
            for _ in range(self.min_connections):
                self._create_connection()

            logger.info(f"已创建 {self.min_connections} 个初始连接")
        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")
            raise

    def _create_connection(self) -> str | None:
        """创建新连接

        Returns:
            连接ID
        """
        try:
            if self.db_type == "sqlite":
                connection = self._create_sqlite_connection()
            elif self.db_type == "postgresql":
                connection = self._create_postgresql_connection()
            elif self.db_type == "mysql":
                connection = self._create_mysql_connection()
            else:
                raise ValueError(f"不支持的数据库类型: {self.db_type}")

            if connection:
                with self._lock:
                    self._connection_counter += 1
                    connection_id = (
                        f"conn_{self._connection_counter}_{int(time.time())}"
                    )

                    self.all_connections[connection_id] = connection
                    self.connection_info[connection_id] = ConnectionInfo(
                        connection_id=connection_id,
                        created_at=datetime.now(),
                        last_used=datetime.now(),
                        use_count=0,
                    )

                    self.available_connections.put(connection_id)
                    self.stats["total_connections"] += 1
                    self.stats["idle_connections"] += 1

                logger.debug(f"创建新连接: {connection_id}")
                return connection_id

        except Exception as e:
            logger.error(f"创建连接失败: {e}")
            self.stats["connection_errors"] += 1
            return None

    def _create_sqlite_connection(self) -> sqlite3.Connection | None:
        """创建SQLite连接"""
        try:
            db_path = self.config.get("database", ":memory:")
            connection = sqlite3.connect(
                db_path, timeout=self.connection_timeout, check_same_thread=False
            )
            connection.row_factory = sqlite3.Row
            return connection
        except Exception as e:
            logger.error(f"SQLite连接创建失败: {e}")
            return None

    def _create_postgresql_connection(self) -> Any | None:
        """创建PostgreSQL连接"""
        if not POSTGRESQL_AVAILABLE:
            raise ImportError("PostgreSQL驱动未安装")

        try:
            connection = psycopg2.connect(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5432),
                database=self.config.get("database", "postgres"),
                user=self.config.get("user", "postgres"),
                password=self.config.get("password", ""),
                connect_timeout=self.connection_timeout,
            )
            return connection
        except Exception as e:
            logger.error(f"PostgreSQL连接创建失败: {e}")
            return None

    def _create_mysql_connection(self) -> Any | None:
        """创建MySQL连接"""
        if not MYSQL_AVAILABLE:
            raise ImportError("MySQL驱动未安装")

        try:
            connection = pymysql.connect(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 3306),
                database=self.config.get("database", "mysql"),
                user=self.config.get("user", "root"),
                password=self.config.get("password", ""),
                connect_timeout=self.connection_timeout,
            )
            return connection
        except Exception as e:
            logger.error(f"MySQL连接创建失败: {e}")
            return None

    def get_connection(self) -> str | None:
        """获取连接

        Returns:
            连接ID
        """
        self.stats["connection_requests"] += 1

        try:
            # 尝试从可用连接中获取
            connection_id = self.available_connections.get(timeout=5)

            # 检查连接是否有效
            if self._is_connection_valid(connection_id):
                with self._lock:
                    self.connection_info[connection_id].last_used = datetime.now()
                    self.connection_info[connection_id].use_count += 1
                    self.stats["active_connections"] += 1
                    self.stats["idle_connections"] -= 1

                logger.debug(f"获取连接: {connection_id}")
                return connection_id
            else:
                # 连接无效，移除并创建新连接
                self._remove_connection(connection_id)
                return self.get_connection()

        except queue.Empty:
            # 没有可用连接，尝试创建新连接
            if len(self.all_connections) < self.max_connections:
                new_connection_id = self._create_connection()
                if new_connection_id:
                    return self.get_connection()

            self.stats["connection_waits"] += 1
            logger.warning("连接池已满，等待可用连接")
            return None

    def return_connection(self, connection_id: str) -> None:
        """归还连接

        Args:
            connection_id: 连接ID
        """
        if connection_id not in self.all_connections:
            logger.warning(f"尝试归还不存在的连接: {connection_id}")
            return

        with self._lock:
            if connection_id in self.connection_info:
                self.connection_info[connection_id].last_used = datetime.now()

            self.stats["active_connections"] -= 1
            self.stats["idle_connections"] += 1

        try:
            self.available_connections.put(connection_id, timeout=1)
            logger.debug(f"归还连接: {connection_id}")
        except queue.Full:
            logger.warning(f"连接池已满，无法归还连接: {connection_id}")

    def _is_connection_valid(self, connection_id: str) -> bool:
        """检查连接是否有效

        Args:
            connection_id: 连接ID

        Returns:
            是否有效
        """
        if connection_id not in self.all_connections:
            return False

        connection = self.all_connections[connection_id]

        try:
            if self.db_type == "sqlite":
                connection.execute("SELECT 1").fetchone()
            elif self.db_type == "postgresql" or self.db_type == "mysql":
                connection.cursor().execute("SELECT 1")

            return True
        except Exception:
            return False

    def _remove_connection(self, connection_id: str) -> None:
        """移除连接

        Args:
            connection_id: 连接ID
        """
        with self._lock:
            if connection_id in self.all_connections:
                with suppress(Exception):
                    self.all_connections[connection_id].close()
                del self.all_connections[connection_id]

            if connection_id in self.connection_info:
                del self.connection_info[connection_id]

            self.stats["total_connections"] -= 1
            self.stats["idle_connections"] -= 1

        logger.debug(f"移除连接: {connection_id}")

    def cleanup_idle_connections(self) -> int:
        """清理空闲连接

        Returns:
            清理的连接数量
        """
        current_time = datetime.now()
        idle_connections = []

        with self._lock:
            for connection_id, info in self.connection_info.items():
                if (current_time - info.last_used).total_seconds() > self.idle_timeout:
                    idle_connections.append(connection_id)

        # 保留最小连接数
        connections_to_remove = max(0, len(idle_connections) - self.min_connections)

        for connection_id in idle_connections[:connections_to_remove]:
            self._remove_connection(connection_id)

        if connections_to_remove > 0:
            logger.info(f"清理了 {connections_to_remove} 个空闲连接")

        return connections_to_remove

    def get_statistics(self) -> dict[str, Any]:
        """获取连接池统计信息

        Returns:
            统计信息
        """
        with self._lock:
            return {
                "db_type": self.db_type,
                "total_connections": self.stats["total_connections"],
                "active_connections": self.stats["active_connections"],
                "idle_connections": self.stats["idle_connections"],
                "connection_requests": self.stats["connection_requests"],
                "connection_waits": self.stats["connection_waits"],
                "connection_errors": self.stats["connection_errors"],
                "min_connections": self.min_connections,
                "max_connections": self.max_connections,
                "available_queue_size": self.available_connections.qsize(),
            }

    def close_all(self) -> None:
        """关闭所有连接"""
        with self._lock:
            for connection_id, connection in self.all_connections.items():
                try:
                    connection.close()
                except Exception as e:
                    logger.error(f"关闭连接失败 {connection_id}: {e}")

            self.all_connections.clear()
            self.connection_info.clear()

            # 清空队列
            while not self.available_connections.empty():
                try:
                    self.available_connections.get_nowait()
                except queue.Empty:
                    break

        logger.info("所有数据库连接已关闭")

    @contextmanager
    def get_connection_context(self) -> Any:
        """获取连接上下文管理器

        Yields:
            连接ID
        """
        connection_id = self.get_connection()
        if not connection_id:
            raise RuntimeError("无法获取数据库连接")
        connection = self.all_connections.get(connection_id)

        try:
            yield connection_id
        except INTEGRITY_ERRORS as exc:
            logger.warning("数据库操作违反完整性约束: %s", exc)
            if connection:
                with suppress(Exception):
                    connection.rollback()
        finally:
            self.return_connection(connection_id)


# 全局数据库连接池
db_pool = DatabasePool()


def with_database_connection(func: Callable) -> Callable:
    """数据库连接装饰器

    Args:
        func: 要装饰的函数

    Returns:
        装饰后的函数
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with db_pool.get_connection_context() as connection_id:
            connection = db_pool.all_connections[connection_id]
            return func(connection, *args, **kwargs)

    return wrapper


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, pool: DatabasePool):
        self.pool = pool

    def execute_query(self, query: str, params: tuple | None = None) -> list[dict]:
        """执行查询

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果
        """
        with self.pool.get_connection_context() as connection_id:
            connection = self.pool.all_connections[connection_id]
            cursor = connection.cursor()

            try:
                cursor.execute(query, params or ())

                if query.strip().upper().startswith("SELECT"):
                    # 查询操作
                    if self.pool.db_type == "sqlite":
                        return [dict(row) for row in cursor.fetchall()]
                    else:
                        columns = [desc[0] for desc in cursor.description]
                        return [
                            dict(zip(columns, row, strict=False))
                            for row in cursor.fetchall()
                        ]
                else:
                    # 非查询操作
                    connection.commit()
                    return []

            except Exception as e:
                connection.rollback()
                logger.error(f"查询执行失败: {e}")
                raise
            finally:
                cursor.close()

    def execute_batch(self, queries: list[tuple[str, tuple | None]]) -> list[Any]:
        """批量执行查询

        Args:
            queries: 查询列表 [(query, params), ...]

        Returns:
            执行结果列表
        """
        results = []

        with self.pool.get_connection_context() as connection_id:
            connection = self.pool.all_connections[connection_id]
            cursor = connection.cursor()

            try:
                for query, params in queries:
                    cursor.execute(query, params or ())
                    if query.strip().upper().startswith("SELECT"):
                        if self.pool.db_type == "sqlite":
                            results.append([dict(row) for row in cursor.fetchall()])
                        else:
                            columns = [desc[0] for desc in cursor.description]
                            results.append(
                                [
                                    dict(zip(columns, row, strict=False))
                                    for row in cursor.fetchall()
                                ]
                            )
                    else:
                        results.append(cursor.rowcount)

                connection.commit()
                return results

            except Exception as e:
                connection.rollback()
                logger.error(f"批量查询执行失败: {e}")
                raise
            finally:
                cursor.close()

    def get_table_info(self, table_name: str) -> list[dict]:
        """获取表信息

        Args:
            table_name: 表名

        Returns:
            表信息
        """
        if self.pool.db_type == "sqlite":
            query = "PRAGMA table_info(?)"
            return self.execute_query(query, (table_name,))
        elif self.pool.db_type == "postgresql":
            query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
            """
            return self.execute_query(query, (table_name,))
        elif self.pool.db_type == "mysql":
            query = """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
            """
            return self.execute_query(query, (table_name,))
        else:
            return []


# 全局数据库管理器
db_manager = DatabaseManager(db_pool)
