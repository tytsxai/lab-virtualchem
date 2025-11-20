"""
数据库优化模块
索引优化、查询优化、连接池管理
"""

import logging
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """查询统计"""

    query: str
    execution_time: float
    timestamp: datetime
    result_count: int = 0
    from_cache: bool = False


class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self._stats: list[QueryStats] = []
        self._slow_query_threshold = 1.0  # 秒

    def record_query(self, query: str, execution_time: float, result_count: int = 0, from_cache: bool = False) -> None:
        """
        记录查询统计

        Args:
            query: SQL查询
            execution_time: 执行时间(秒)
            result_count: 结果数量
            from_cache: 是否来自缓存
        """
        stats = QueryStats(
            query=query,
            execution_time=execution_time,
            timestamp=datetime.now(),
            result_count=result_count,
            from_cache=from_cache,
        )

        self._stats.append(stats)

        # 慢查询警告
        if execution_time > self._slow_query_threshold:
            logger.warning(f"慢查询检测: {execution_time:.3f}s - {query[:100]}")

    def get_slow_queries(self, threshold: float | None = None) -> list[QueryStats]:
        """
        获取慢查询列表

        Args:
            threshold: 时间阈值(秒)

        Returns:
            慢查询列表
        """
        threshold = threshold or self._slow_query_threshold
        return [s for s in self._stats if s.execution_time > threshold]

    def get_query_summary(self) -> dict[str, Any]:
        """
        获取查询摘要

        Returns:
            摘要信息
        """
        if not self._stats:
            return {}

        total_queries = len(self._stats)
        cached_queries = sum(1 for s in self._stats if s.from_cache)
        total_time = sum(s.execution_time for s in self._stats)
        avg_time = total_time / total_queries
        slow_queries = len(self.get_slow_queries())

        return {
            "total_queries": total_queries,
            "cached_queries": cached_queries,
            "cache_hit_rate": cached_queries / total_queries * 100,
            "total_time": total_time,
            "avg_time": avg_time,
            "slow_queries": slow_queries,
        }

    @contextmanager
    def track_query(self, query: str):
        """
        查询追踪上下文管理器

        Args:
            query: SQL查询
        """
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.record_query(query, execution_time)


class IndexAnalyzer:
    """索引分析器"""

    def __init__(self, connection):
        """
        初始化索引分析器

        Args:
            connection: 数据库连接
        """
        self.connection = connection

    def analyze_table(self, table_name: str) -> dict[str, Any]:
        """
        分析表结构和索引

        Args:
            table_name: 表名

        Returns:
            分析结果
        """
        # 注意：这里的实现取决于具体的数据库类型
        # 以下是SQLite的示例

        result = {"table": table_name, "indexes": [], "missing_indexes": [], "unused_indexes": []}

        try:
            cursor = self.connection.cursor()

            # 获取表信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # 获取索引信息
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()

            result["columns"] = [col[1] for col in columns]
            result["indexes"] = [idx[1] for idx in indexes]

            # 分析建议
            # 1. 检查外键列是否有索引
            # 2. 检查频繁查询的列是否有索引
            # 3. 检查是否有冗余索引

        except Exception as e:
            logger.error(f"分析表失败 {table_name}: {e}")

        return result

    def suggest_indexes(self, table_name: str, query_patterns: list[str]) -> list[dict[str, Any]]:
        """
        建议索引

        Args:
            table_name: 表名
            query_patterns: 查询模式列表

        Returns:
            索引建议列表，每项包含：
            - column: 列名
            - reason: 建议原因
            - priority: 优先级 (high/medium/low)
            - estimated_benefit: 预估收益
        """
        suggestions = []
        analyzed_columns = set()

        # 获取当前表的索引
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA index_list({table_name})")
            existing_indexes = cursor.fetchall()
            indexed_columns = set()

            for idx in existing_indexes:
                cursor.execute(f"PRAGMA index_info({idx[1]})")
                index_info = cursor.fetchall()
                for col in index_info:
                    indexed_columns.add(col[2])
        except Exception as e:
            logger.error(f"获取索引信息失败: {e}")
            indexed_columns = set()

        # 分析查询模式，提取常用的WHERE、JOIN、ORDER BY列
        for pattern in query_patterns:
            pattern_upper = pattern.upper()

            # 提取WHERE子句中的列
            if "WHERE" in pattern_upper:
                # 简化的列提取（支持常见模式）
                where_pos = pattern_upper.find("WHERE")
                where_clause = pattern[where_pos + 5 :]

                # 提取比较操作中的列名
                for op in ["=", ">", "<", ">=", "<=", "!=", "LIKE", "IN"]:
                    if op in where_clause.upper():
                        parts = where_clause.split(op)
                        if parts:
                            col_name = parts[0].strip().split()[-1].strip("()")
                            if col_name and col_name not in indexed_columns and col_name not in analyzed_columns:
                                suggestions.append(
                                    {
                                        "column": col_name,
                                        "reason": f"WHERE子句频繁过滤条件（操作符: {op}）",
                                        "priority": "high",
                                        "estimated_benefit": "查询速度可提升50-90%",
                                    }
                                )
                                analyzed_columns.add(col_name)

            # 提取ORDER BY列
            if "ORDER BY" in pattern_upper:
                order_pos = pattern_upper.find("ORDER BY")
                order_clause = pattern[order_pos + 8 :].split("LIMIT")[0].split("GROUP")[0]
                col_name = order_clause.strip().split()[0].strip(",")

                if col_name and col_name not in indexed_columns and col_name not in analyzed_columns:
                    suggestions.append(
                        {
                            "column": col_name,
                            "reason": "排序操作列",
                            "priority": "medium",
                            "estimated_benefit": "排序速度可提升30-70%",
                        }
                    )
                    analyzed_columns.add(col_name)

            # 提取JOIN列
            if "JOIN" in pattern_upper:
                on_pos = pattern_upper.find(" ON ")
                if on_pos > 0:
                    on_clause = pattern[on_pos + 4 :].split("WHERE")[0].split("ORDER")[0]
                    # 提取JOIN条件中的列
                    if "=" in on_clause:
                        parts = on_clause.split("=")
                        for part in parts:
                            col_with_table = part.strip().split()[-1]
                            if "." in col_with_table:
                                col_name = col_with_table.split(".")[-1]
                                if col_name not in indexed_columns and col_name not in analyzed_columns:
                                    suggestions.append(
                                        {
                                            "column": col_name,
                                            "reason": "JOIN连接条件列",
                                            "priority": "high",
                                            "estimated_benefit": "JOIN性能可提升60-95%",
                                        }
                                    )
                                    analyzed_columns.add(col_name)

            # 提取GROUP BY列
            if "GROUP BY" in pattern_upper:
                group_pos = pattern_upper.find("GROUP BY")
                group_clause = pattern[group_pos + 8 :].split("HAVING")[0].split("ORDER")[0]
                col_name = group_clause.strip().split()[0].strip(",")

                if col_name and col_name not in indexed_columns and col_name not in analyzed_columns:
                    suggestions.append(
                        {
                            "column": col_name,
                            "reason": "GROUP BY分组列",
                            "priority": "medium",
                            "estimated_benefit": "分组速度可提升40-80%",
                        }
                    )
                    analyzed_columns.add(col_name)

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return suggestions

    def create_index(self, table_name: str, column_name: str, index_name: str | None = None) -> bool:
        """
        创建索引

        Args:
            table_name: 表名
            column_name: 列名
            index_name: 索引名（可选）

        Returns:
            是否成功
        """
        if not index_name:
            index_name = f"idx_{table_name}_{column_name}"

        try:
            cursor = self.connection.cursor()
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
            cursor.execute(sql)
            self.connection.commit()
            logger.info(f"成功创建索引: {index_name} on {table_name}({column_name})")
            return True
        except Exception as e:
            logger.error(f"创建索引失败 {index_name}: {e}")
            return False

    def auto_optimize_table(self, table_name: str, query_patterns: list[str]) -> dict[str, Any]:
        """
        自动优化表（分析并创建建议的索引）

        Args:
            table_name: 表名
            query_patterns: 查询模式列表

        Returns:
            优化报告
        """
        report = {
            "table": table_name,
            "suggestions": [],
            "created": [],
            "failed": [],
            "skipped": [],
        }

        # 获取索引建议
        suggestions = self.suggest_indexes(table_name, query_patterns)
        report["suggestions"] = suggestions

        # 自动创建高优先级索引
        for suggestion in suggestions:
            if suggestion["priority"] == "high":
                col_name = suggestion["column"]
                success = self.create_index(table_name, col_name)

                if success:
                    report["created"].append({"column": col_name, "reason": suggestion["reason"]})
                else:
                    report["failed"].append({"column": col_name, "error": "创建失败"})
            else:
                report["skipped"].append(
                    {
                        "column": suggestion["column"],
                        "reason": f"优先级为{suggestion['priority']}，建议手动创建",
                    }
                )

        return report


class ConnectionPool:
    """数据库连接池"""

    def __init__(
        self,
        creator: Callable,
        max_connections: int = 10,
        min_connections: int = 2,
        timeout: float = 30.0,
    ):
        """
        初始化连接池

        Args:
            creator: 连接创建函数
            max_connections: 最大连接数
            min_connections: 最小连接数
            timeout: 获取连接超时(秒)
        """
        self.creator = creator
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.timeout = timeout

        self._pool: list[Any] = []
        self._in_use: set = set()
        self._created_count = 0
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

        # 初始化最小连接数
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """初始化连接池"""
        for _ in range(self.min_connections):
            conn = self.creator()
            self._pool.append(conn)
            self._created_count += 1

        logger.info(f"连接池初始化: {self.min_connections} 个连接")

    def get_connection(self) -> Any:
        """
        获取连接

        Returns:
            数据库连接

        Raises:
            TimeoutError: 等待超时
        """
        with self._condition:
            start_time = time.time()

            while True:
                # 从池中获取空闲连接
                if self._pool:
                    conn = self._pool.pop()
                    self._in_use.add(id(conn))
                    return conn

                # 如果未达到最大连接数，创建新连接
                if self._created_count < self.max_connections:
                    conn = self.creator()
                    self._created_count += 1
                    self._in_use.add(id(conn))
                    logger.debug(f"创建新连接: {self._created_count}/{self.max_connections}")
                    return conn

                # 计算剩余等待时间
                elapsed = time.time() - start_time
                remaining = self.timeout - elapsed

                if remaining <= 0:
                    logger.error(f"连接池等待超时: {self.timeout}秒")
                    raise TimeoutError(f"获取连接超时({self.timeout}秒)")

                # 等待可用连接
                logger.warning(f"连接池已满，等待可用连接（剩余{remaining:.1f}秒）")
                self._condition.wait(timeout=remaining)

    def return_connection(self, conn: Any) -> None:
        """
        归还连接

        Args:
            conn: 数据库连接
        """
        with self._condition:
            conn_id = id(conn)
            if conn_id in self._in_use:
                self._in_use.remove(conn_id)
                self._pool.append(conn)
                # 通知等待的线程
                self._condition.notify()

    @contextmanager
    def connection(self):
        """
        连接上下文管理器

        Yields:
            数据库连接
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)

    def close_all(self) -> None:
        """关闭所有连接"""
        for conn in self._pool:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")

        self._pool.clear()
        self._in_use.clear()
        logger.info("连接池已关闭")

    def get_stats(self) -> dict[str, int]:
        """
        获取连接池统计

        Returns:
            统计信息
        """
        return {
            "total": self._created_count,
            "idle": len(self._pool),
            "in_use": len(self._in_use),
            "max": self.max_connections,
        }


class QueryCache:
    """查询结果缓存"""

    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        初始化查询缓存

        Args:
            max_size: 最大缓存数量
            ttl: 缓存有效期(秒)
        """
        from src.core.cache import CacheStrategy, MemoryCache

        self._cache = MemoryCache(max_size=max_size, strategy=CacheStrategy.LRU)
        self.ttl = ttl

    def get(self, query: str, params: tuple = ()) -> Any | None:
        """
        获取缓存的查询结果

        Args:
            query: SQL查询
            params: 查询参数

        Returns:
            查询结果或None
        """
        cache_key = self._make_key(query, params)
        return self._cache.get(cache_key)

    def set(self, query: str, params: tuple, result: Any) -> None:
        """
        缓存查询结果

        Args:
            query: SQL查询
            params: 查询参数
            result: 查询结果
        """
        cache_key = self._make_key(query, params)
        self._cache.set(cache_key, result, ttl=self.ttl)

    def invalidate(self, pattern: str = None) -> None:
        """
        失效缓存

        Args:
            pattern: 匹配模式(None表示全部)
        """
        if pattern is None:
            self._cache.clear()
        else:
            # 简化实现：清空全部
            self._cache.clear()

    def _make_key(self, query: str, params: tuple) -> str:
        """生成缓存键"""
        import hashlib

        key_str = f"{query}:{str(params)}"
        return hashlib.sha256(key_str.encode()).hexdigest()


class DatabaseOptimizer:
    """数据库优化器 - 整合各种优化功能"""

    def __init__(self, connection):
        """
        初始化优化器

        Args:
            connection: 数据库连接
        """
        self.connection = connection
        self.query_optimizer = QueryOptimizer()
        self.index_analyzer = IndexAnalyzer(connection)
        self.query_cache = QueryCache()

    def execute_query(self, query: str, params: tuple = (), use_cache: bool = True) -> Any:
        """
        执行优化的查询

        Args:
            query: SQL查询
            params: 查询参数
            use_cache: 是否使用缓存

        Returns:
            查询结果
        """
        # 尝试从缓存获取
        if use_cache:
            cached_result = self.query_cache.get(query, params)
            if cached_result is not None:
                self.query_optimizer.record_query(query, 0.0, len(cached_result), from_cache=True)
                return cached_result

        # 执行查询
        with self.query_optimizer.track_query(query):
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()

        # 缓存结果
        if use_cache:
            self.query_cache.set(query, params, result)

        return result

    def generate_optimization_report(self) -> dict[str, Any]:
        """
        生成优化报告

        Returns:
            优化报告
        """
        return {
            "query_summary": self.query_optimizer.get_query_summary(),
            "slow_queries": [
                {"query": s.query, "time": s.execution_time, "timestamp": s.timestamp.isoformat()}
                for s in self.query_optimizer.get_slow_queries()
            ],
        }


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 数据库优化演示 ===\n")

    # 查询优化器
    optimizer = QueryOptimizer()

    # 模拟查询
    optimizer.record_query("SELECT * FROM users", 0.5, 100)
    optimizer.record_query("SELECT * FROM orders WHERE user_id = ?", 1.5, 50)
    optimizer.record_query("SELECT * FROM products", 0.3, 200, from_cache=True)

    # 获取摘要
    summary = optimizer.get_query_summary()
    logger.info("查询摘要:")
    for key, value in summary.items():
        logger.info(f"  {key}: {value}")

    logger.info(f"\n慢查询数量: {len(optimizer.get_slow_queries())}")
