"""
数据库优化器
提供查询优化、索引管理、连接池等功能
"""

from __future__ import annotations

import asyncio
import contextlib
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class QueryType(Enum):
    """查询类型"""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    DROP = "drop"


class IndexType(Enum):
    """索引类型"""

    PRIMARY = "primary"
    UNIQUE = "unique"
    INDEX = "index"
    FULLTEXT = "fulltext"


@dataclass
class QueryStats:
    """查询统计"""

    query: str
    query_type: QueryType
    execution_time: float
    rows_affected: int
    timestamp: datetime
    parameters: tuple[Any, ...] | None = None


@dataclass
class IndexInfo:
    """索引信息"""

    name: str
    table: str
    columns: list[str]
    index_type: IndexType
    is_unique: bool
    is_primary: bool
    size_bytes: int
    created_at: datetime


class QueryAnalyzer:
    """查询分析器"""

    def __init__(self) -> None:
        """初始化查询分析器"""
        self.query_stats: list[QueryStats] = []
        self.slow_queries: list[QueryStats] = []
        self.query_patterns: dict[str, list[QueryStats]] = defaultdict(list)
        self.slow_query_threshold = 1.0  # 1秒

        logger.info("查询分析器已初始化")

    def record_query(
        self, query: str, execution_time: float, rows_affected: int = 0, parameters: tuple[Any, ...] | None = None
    ) -> None:
        """记录查询统计

        Args:
            query: 查询语句
            execution_time: 执行时间
            rows_affected: 影响行数
            parameters: 查询参数
        """
        query_type = self._detect_query_type(query)

        stats = QueryStats(
            query=query,
            query_type=query_type,
            execution_time=execution_time,
            rows_affected=rows_affected,
            timestamp=datetime.now(),
            parameters=parameters,
        )

        # 记录统计
        self.query_stats.append(stats)

        # 记录慢查询
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append(stats)

        # 记录查询模式
        query_pattern = self._extract_query_pattern(query)
        self.query_patterns[query_pattern].append(stats)

        logger.debug(f"查询已记录: {query_type.value} - {execution_time:.3f}s")

    def _detect_query_type(self, query: str) -> QueryType:
        """检测查询类型

        Args:
            query: 查询语句

        Returns:
            查询类型
        """
        query_lower = query.strip().lower()

        if query_lower.startswith("select"):
            return QueryType.SELECT
        elif query_lower.startswith("insert"):
            return QueryType.INSERT
        elif query_lower.startswith("update"):
            return QueryType.UPDATE
        elif query_lower.startswith("delete"):
            return QueryType.DELETE
        elif query_lower.startswith("create"):
            return QueryType.CREATE
        elif query_lower.startswith("drop"):
            return QueryType.DROP
        else:
            return QueryType.SELECT

    def _extract_query_pattern(self, query: str) -> str:
        """提取查询模式

        Args:
            query: 查询语句

        Returns:
            查询模式
        """
        # 简化查询，移除具体值
        import re

        # 移除字符串字面量
        pattern = re.sub(r"'[^']*'", "'?'", query)
        pattern = re.sub(r'"[^"]*"', '"?"', pattern)

        # 移除数字
        pattern = re.sub(r"\b\d+\b", "?", pattern)

        # 移除多余空格
        pattern = re.sub(r"\s+", " ", pattern).strip()

        return pattern.lower()

    def get_slow_queries(self, limit: int = 10) -> list[QueryStats]:
        """获取慢查询

        Args:
            limit: 限制数量

        Returns:
            慢查询列表
        """
        return sorted(self.slow_queries, key=lambda x: x.execution_time, reverse=True)[:limit]

    def get_query_patterns(self, limit: int = 10) -> dict[str, dict[str, Any]]:
        """获取查询模式统计

        Args:
            limit: 限制数量

        Returns:
            查询模式统计
        """
        patterns = {}

        for pattern, stats_list in self.query_patterns.items():
            if len(stats_list) > 0:
                total_time = sum(s.execution_time for s in stats_list)
                avg_time = total_time / len(stats_list)
                max_time = max(s.execution_time for s in stats_list)

                patterns[pattern] = {
                    "count": len(stats_list),
                    "total_time": total_time,
                    "avg_time": avg_time,
                    "max_time": max_time,
                    "last_executed": max(s.timestamp for s in stats_list).isoformat(),
                }

        # 按总时间排序
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1]["total_time"], reverse=True)
        return dict(sorted_patterns[:limit])

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要

        Returns:
            性能摘要
        """
        if not self.query_stats:
            return {}

        total_queries = len(self.query_stats)
        total_time = sum(s.execution_time for s in self.query_stats)
        avg_time = total_time / total_queries
        max_time = max(s.execution_time for s in self.query_stats)

        # 按查询类型统计
        type_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_time": 0.0})
        for stats in self.query_stats:
            type_stats[stats.query_type.value]["count"] += 1
            type_stats[stats.query_type.value]["total_time"] += stats.execution_time

        return {
            "total_queries": total_queries,
            "total_time": total_time,
            "avg_time": avg_time,
            "max_time": max_time,
            "slow_queries_count": len(self.slow_queries),
            "slow_query_rate": len(self.slow_queries) / total_queries if total_queries > 0 else 0.0,
            "query_types": dict(type_stats),
            "patterns_count": len(self.query_patterns),
        }


class IndexManager:
    """索引管理器"""

    def __init__(self, db_path: str):
        """初始化索引管理器

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.indexes: dict[str, IndexInfo] = {}
        self._lock = threading.RLock()

        # 加载现有索引
        self._load_existing_indexes()

        logger.info(f"索引管理器已初始化: {db_path}")

    def _load_existing_indexes(self) -> None:
        """加载现有索引"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取所有索引信息
                cursor.execute(
                    """
                    SELECT name, tbl_name, sql
                    FROM sqlite_master
                    WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                """
                )

                for name, table, sql in cursor.fetchall():
                    if sql:
                        # 解析索引信息
                        index_info = self._parse_index_sql(sql, table)
                        if index_info:
                            self.indexes[name] = index_info

                logger.info(f"加载了 {len(self.indexes)} 个索引")

        except Exception as e:
            logger.error(f"加载索引失败: {e}")

    def _parse_index_sql(self, sql: str, table: str) -> IndexInfo | None:
        """解析索引SQL

        Args:
            sql: 索引SQL语句
            table: 表名

        Returns:
            索引信息
        """
        import re

        try:
            # 解析索引类型
            if "PRIMARY KEY" in sql.upper():
                index_type = IndexType.PRIMARY
                is_unique = True
                is_primary = True
            elif "UNIQUE" in sql.upper():
                index_type = IndexType.UNIQUE
                is_unique = True
                is_primary = False
            else:
                index_type = IndexType.INDEX
                is_unique = False
                is_primary = False

            # 提取列名
            columns_match = re.search(r"\(([^)]+)\)", sql)
            if columns_match:
                columns = [col.strip() for col in columns_match.group(1).split(",")]
            else:
                columns = []

            # 提取索引名
            name_match = re.search(r"INDEX\s+(\w+)", sql)
            name = name_match.group(1) if name_match else f"idx_{table}_{'_'.join(columns)}"

            return IndexInfo(
                name=name,
                table=table,
                columns=columns,
                index_type=index_type,
                is_unique=is_unique,
                is_primary=is_primary,
                size_bytes=0,  # 需要额外查询
                created_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"解析索引SQL失败: {e}")
            return None

    def create_index(
        self, table: str, columns: list[str], index_type: IndexType = IndexType.INDEX, name: str | None = None
    ) -> bool:
        """创建索引

        Args:
            table: 表名
            columns: 列名列表
            index_type: 索引类型
            name: 索引名

        Returns:
            是否成功创建
        """
        with self._lock:
            try:
                if not name:
                    name = f"idx_{table}_{'_'.join(columns)}"

                # 构建SQL
                if index_type == IndexType.PRIMARY:
                    sql = f"CREATE PRIMARY KEY ({', '.join(columns)})"
                elif index_type == IndexType.UNIQUE:
                    sql = f"CREATE UNIQUE INDEX {name} ON {table} ({', '.join(columns)})"
                else:
                    sql = f"CREATE INDEX {name} ON {table} ({', '.join(columns)})"

                # 执行SQL
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    conn.commit()

                # 更新索引信息
                index_info = IndexInfo(
                    name=name,
                    table=table,
                    columns=columns,
                    index_type=index_type,
                    is_unique=index_type in [IndexType.PRIMARY, IndexType.UNIQUE],
                    is_primary=index_type == IndexType.PRIMARY,
                    size_bytes=0,
                    created_at=datetime.now(),
                )

                self.indexes[name] = index_info

                logger.info(f"索引已创建: {name} on {table}")
                return True

            except Exception as e:
                logger.error(f"创建索引失败: {e}")
                return False

    def drop_index(self, name: str) -> bool:
        """删除索引

        Args:
            name: 索引名

        Returns:
            是否成功删除
        """
        with self._lock:
            try:
                if name not in self.indexes:
                    logger.warning(f"索引不存在: {name}")
                    return False

                # 执行SQL
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"DROP INDEX {name}")
                    conn.commit()

                # 更新索引信息
                del self.indexes[name]

                logger.info(f"索引已删除: {name}")
                return True

            except Exception as e:
                logger.error(f"删除索引失败: {e}")
                return False

    def analyze_indexes(self) -> dict[str, Any]:
        """分析索引使用情况

        Returns:
            索引分析结果
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取索引使用统计
                cursor.execute(
                    """
                    SELECT name, tbl_name, sql
                    FROM sqlite_master
                    WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                """
                )

                analysis: dict[str, Any] = {
                    "total_indexes": len(self.indexes),
                    "indexes_by_table": defaultdict(int),
                    "indexes_by_type": defaultdict(int),
                    "unused_indexes": [],
                    "recommendations": [],
                }

                for name, table, _sql in cursor.fetchall():
                    indexes_by_table: dict[str, int] = analysis["indexes_by_table"]
                    indexes_by_table[table] += 1

                    if name in self.indexes:
                        index_info = self.indexes[name]
                        indexes_by_type: dict[str, int] = analysis["indexes_by_type"]
                        indexes_by_type[index_info.index_type.value] += 1

                # 生成建议
                analysis["recommendations"] = self._generate_index_recommendations()

                return analysis

        except Exception as e:
            logger.error(f"分析索引失败: {e}")
            return {}

    def _generate_index_recommendations(self) -> list[str]:
        """生成索引建议

        Returns:
            建议列表
        """
        recommendations = []

        # 检查是否有重复索引
        table_columns = defaultdict(set)
        for index_info in self.indexes.values():
            key = (index_info.table, tuple(index_info.columns))
            if key in table_columns:
                recommendations.append(f"发现重复索引: {index_info.name}")
            table_columns[key].add(index_info.name)

        # 检查是否有单列索引可以合并
        single_column_indexes = defaultdict(list)
        for index_info in self.indexes.values():
            if len(index_info.columns) == 1:
                single_column_indexes[index_info.table].append(index_info)

        for table, indexes in single_column_indexes.items():
            if len(indexes) > 3:
                recommendations.append(f"表 {table} 有过多单列索引，考虑合并")

        return recommendations

    def get_indexes(self) -> dict[str, IndexInfo]:
        """获取所有索引信息

        Returns:
            索引信息字典
        """
        return self.indexes.copy()


class ConnectionPool:
    """连接池"""

    def __init__(self, db_path: str, max_connections: int = 10, min_connections: int = 2):
        """初始化连接池

        Args:
            db_path: 数据库路径
            max_connections: 最大连接数
            min_connections: 最小连接数
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.min_connections = min_connections

        self._connections: list[sqlite3.Connection] = []
        self._in_use: set[sqlite3.Connection] = set()
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)

        # 初始化连接
        self._initialize_connections()

        logger.info(f"连接池已初始化: {min_connections}-{max_connections} 连接")

    def _initialize_connections(self) -> None:
        """初始化连接"""
        for _ in range(self.min_connections):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式
            conn.execute("PRAGMA synchronous=NORMAL")  # 优化同步模式
            self._connections.append(conn)

    def get_connection(self, timeout: float = 30.0) -> sqlite3.Connection:
        """获取连接

        Args:
            timeout: 超时时间

        Returns:
            数据库连接
        """
        with self._condition:
            # 等待可用连接
            start_time = time.time()
            while not self._connections and len(self._in_use) >= self.max_connections:
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time <= 0:
                    raise TimeoutError("获取连接超时")

                self._condition.wait(remaining_time)

            # 获取连接
            if self._connections:
                conn = self._connections.pop()
            else:
                # 创建新连接
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")

            self._in_use.add(conn)
            return conn

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """归还连接

        Args:
            conn: 数据库连接
        """
        with self._condition:
            if conn in self._in_use:
                self._in_use.remove(conn)

                # 检查连接是否有效
                try:
                    conn.execute("SELECT 1")
                    self._connections.append(conn)
                except Exception:
                    # 连接无效，关闭它
                    with contextlib.suppress(Exception):
                        conn.close()

                self._condition.notify()

    def close_all(self) -> None:
        """关闭所有连接"""
        with self._lock:
            # 关闭所有连接
            for conn in self._connections + list(self._in_use):
                with contextlib.suppress(Exception):
                    conn.close()

            self._connections.clear()
            self._in_use.clear()

            logger.info("所有连接已关闭")

    def get_stats(self) -> dict[str, Any]:
        """获取连接池统计

        Returns:
            统计信息
        """
        with self._lock:
            return {
                "total_connections": len(self._connections) + len(self._in_use),
                "available_connections": len(self._connections),
                "in_use_connections": len(self._in_use),
                "max_connections": self.max_connections,
                "min_connections": self.min_connections,
            }


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self, db_path: str):
        """初始化数据库优化器

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.query_analyzer = QueryAnalyzer()
        self.index_manager = IndexManager(db_path)
        self.connection_pool = ConnectionPool(db_path)

        # 优化配置
        self.auto_optimize = True
        self.optimization_interval = 3600  # 1小时
        self._optimization_task: asyncio.Task[None] | None = None

        # 启动自动优化
        if self.auto_optimize:
            self._start_auto_optimization()

        logger.info(f"数据库优化器已初始化: {db_path}")

    def _start_auto_optimization(self) -> None:
        """启动自动优化"""

        async def optimize_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self.optimization_interval)
                    self.optimize()
                except Exception as e:
                    logger.error(f"自动优化失败: {e}")

        self._optimization_task = asyncio.create_task(optimize_loop())

    def execute_query(self, query: str, parameters: tuple[Any, ...] | None = None) -> Any:
        """执行查询

        Args:
            query: 查询语句
            parameters: 查询参数

        Returns:
            查询结果
        """
        start_time = time.time()
        conn = None

        try:
            # 获取连接
            conn = self.connection_pool.get_connection()
            cursor = conn.cursor()

            # 执行查询
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)

            # 获取结果
            result: Any
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
            else:
                result = cursor.rowcount

            # 提交事务
            conn.commit()

            # 记录查询统计
            execution_time = time.time() - start_time
            self.query_analyzer.record_query(query, execution_time, cursor.rowcount, parameters)

            return result

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"查询执行失败: {e}")
            raise

        finally:
            if conn:
                self.connection_pool.return_connection(conn)

    def optimize(self) -> None:
        """执行数据库优化"""
        logger.info("开始数据库优化")

        try:
            # 1. 分析查询性能
            performance_summary = self.query_analyzer.get_performance_summary()
            logger.info(f"查询性能摘要: {performance_summary}")

            # 2. 分析慢查询
            slow_queries = self.query_analyzer.get_slow_queries()
            if slow_queries:
                logger.warning(f"发现 {len(slow_queries)} 个慢查询")
                for query in slow_queries[:5]:  # 显示前5个
                    logger.warning(f"慢查询: {query.query} - {query.execution_time:.3f}s")

            # 3. 分析索引
            index_analysis = self.index_manager.analyze_indexes()
            logger.info(f"索引分析: {index_analysis}")

            # 4. 执行VACUUM
            self.execute_query("VACUUM")
            logger.info("数据库VACUUM完成")

            # 5. 更新统计信息
            self.execute_query("ANALYZE")
            logger.info("统计信息更新完成")

            logger.info("数据库优化完成")

        except Exception as e:
            logger.error(f"数据库优化失败: {e}")

    def get_optimization_report(self) -> dict[str, Any]:
        """获取优化报告

        Returns:
            优化报告
        """
        return {
            "performance": self.query_analyzer.get_performance_summary(),
            "slow_queries": [
                {"query": q.query, "execution_time": q.execution_time, "timestamp": q.timestamp.isoformat()}
                for q in self.query_analyzer.get_slow_queries()
            ],
            "query_patterns": self.query_analyzer.get_query_patterns(),
            "indexes": self.index_manager.analyze_indexes(),
            "connection_pool": self.connection_pool.get_stats(),
        }

    def close(self) -> None:
        """关闭优化器"""
        if self._optimization_task:
            self._optimization_task.cancel()

        self.connection_pool.close_all()
        logger.info("数据库优化器已关闭")
