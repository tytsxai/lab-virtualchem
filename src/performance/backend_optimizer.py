"""
后端性能优化器
提供数据库查询优化、API响应优化、批处理等功能
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueryMetrics:
    """查询性能指标"""

    query_text: str
    execution_time: float
    result_count: int
    timestamp: float
    cache_hit: bool = False


class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self.query_cache: dict[
            str, tuple[Any, float]
        ] = {}  # query -> (result, timestamp)
        self.query_metrics: list[QueryMetrics] = []
        self.cache_ttl = 300  # 5分钟
        self.slow_query_threshold = 1.0  # 1秒

        logger.info("查询优化器初始化完成")

    def execute_query(
        self, query: str, params: tuple = (), use_cache: bool = True
    ) -> tuple[Any, QueryMetrics]:
        """执行查询（带缓存和性能追踪）"""
        cache_key = self._make_cache_key(query, params)
        start_time = time.time()

        # 检查缓存
        if use_cache and cache_key in self.query_cache:
            result, cached_time = self.query_cache[cache_key]

            # 检查是否过期
            if time.time() - cached_time < self.cache_ttl:
                execution_time = time.time() - start_time

                metrics = QueryMetrics(
                    query_text=query,
                    execution_time=execution_time,
                    result_count=len(result)
                    if isinstance(result, (list, tuple))
                    else 1,
                    timestamp=time.time(),
                    cache_hit=True,
                )

                self.query_metrics.append(metrics)
                logger.debug(
                    f"缓存命中: {query[:50]}... ({execution_time * 1000:.2f}ms)"
                )

                return result, metrics

        # 实际执行查询（这里需要实际的数据库连接）
        # 这只是示例接口
        result = self._execute_actual_query(query, params)
        execution_time = time.time() - start_time

        # 缓存结果
        if use_cache:
            self.query_cache[cache_key] = (result, time.time())

        # 记录指标
        metrics = QueryMetrics(
            query_text=query,
            execution_time=execution_time,
            result_count=len(result) if isinstance(result, (list, tuple)) else 1,
            timestamp=time.time(),
            cache_hit=False,
        )

        self.query_metrics.append(metrics)

        # 警告慢查询
        if execution_time > self.slow_query_threshold:
            logger.warning(f"慢查询: {query[:100]}... ({execution_time:.2f}s)")

        return result, metrics

    def _execute_actual_query(self, _query: str, _params: tuple) -> Any:
        """实际执行查询（需要实现）"""
        # 这里应该连接到实际的数据库
        # 示例返回空列表
        return []

    def _make_cache_key(self, query: str, params: tuple) -> str:
        """生成缓存键"""
        import hashlib

        key = f"{query}:{params}"
        return hashlib.sha256(key.encode()).hexdigest()

    def get_slow_queries(self, threshold: float | None = None) -> list[QueryMetrics]:
        """获取慢查询"""
        threshold = threshold or self.slow_query_threshold
        return [m for m in self.query_metrics if m.execution_time > threshold]

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        total_queries = len(self.query_metrics)
        cache_hits = sum(1 for m in self.query_metrics if m.cache_hit)

        return {
            "total_queries": total_queries,
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hits / total_queries if total_queries > 0 else 0,
            "cache_size": len(self.query_cache),
            "avg_execution_time": (
                sum(m.execution_time for m in self.query_metrics) / total_queries
                if total_queries > 0
                else 0
            ),
        }

    def clear_cache(self):
        """清空缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")

    def optimize_query(self, query: str) -> str:
        """优化查询（简单的优化建议）"""
        optimized = query

        # 添加LIMIT子句（如果没有）
        if "LIMIT" not in query.upper() and "SELECT" in query.upper():
            optimized = f"{optimized} LIMIT 1000"

        # 其他优化规则...

        return optimized


class BatchProcessor:
    """批处理器 - 优化批量操作"""

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.pending_operations: list[tuple[Callable, tuple]] = []

        logger.info(f"批处理器初始化完成 (批大小: {batch_size})")

    def add_operation(self, operation: Callable, *args):
        """添加操作到批处理队列"""
        self.pending_operations.append((operation, args))

        if len(self.pending_operations) >= self.batch_size:
            self.flush()

    def flush(self):
        """执行批处理"""
        if not self.pending_operations:
            return

        start_time = time.time()
        results = []

        for operation, args in self.pending_operations:
            try:
                result = operation(*args)
                results.append(result)
            except Exception as e:
                logger.error(f"批处理操作失败: {e}")
                results.append(None)

        execution_time = time.time() - start_time
        logger.info(
            f"批处理完成: {len(self.pending_operations)} 个操作 ({execution_time:.2f}s)"
        )

        self.pending_operations.clear()
        return results


class APIResponseCache:
    """API响应缓存"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache: dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hit_count = 0
        self.miss_count = 0

        logger.info(f"API响应缓存初始化完成 (大小: {max_size}, TTL: {ttl}s)")

    def get(self, key: str) -> Any | None:
        """获取缓存"""
        if key in self.cache:
            value, timestamp = self.cache[key]

            # 检查是否过期
            if time.time() - timestamp < self.ttl:
                self.hit_count += 1
                return value
            else:
                del self.cache[key]

        self.miss_count += 1
        return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        # 检查大小限制
        if len(self.cache) >= self.max_size:
            self._evict()

        self.cache[key] = (value, time.time())

    def _evict(self):
        """驱逐策略（LRU - 移除最早的条目）"""
        if not self.cache:
            return

        # 找到最早的条目
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[oldest_key]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        total = self.hit_count + self.miss_count
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": self.hit_count / total if total > 0 else 0,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
        }

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        logger.info("API响应缓存已清空")


class DataPrefetcher:
    """数据预取器"""

    def __init__(self):
        self.prefetch_rules: dict[str, list[Callable]] = defaultdict(list)
        self.prefetch_cache: dict[str, Any] = {}

        logger.info("数据预取器初始化完成")

    def register_rule(self, event: str, prefetch_func: Callable):
        """注册预取规则"""
        self.prefetch_rules[event].append(prefetch_func)
        logger.debug(f"注册预取规则: {event}")

    async def trigger_prefetch(self, event: str, context: dict[str, Any]):
        """触发预取"""
        if event not in self.prefetch_rules:
            return

        logger.info(f"触发预取: {event}")

        tasks = []
        for prefetch_func in self.prefetch_rules[event]:
            tasks.append(self._execute_prefetch(prefetch_func, context))

        await asyncio.gather(*tasks)

    async def _execute_prefetch(self, prefetch_func: Callable, context: dict[str, Any]):
        """执行预取"""
        try:
            result = prefetch_func(context)

            # 如果是协程，等待它
            if asyncio.iscoroutine(result):
                result = await result

            # 缓存结果
            cache_key = f"{prefetch_func.__name__}:{hash(str(context))}"
            self.prefetch_cache[cache_key] = result

            logger.debug(f"预取完成: {prefetch_func.__name__}")
        except Exception as e:
            logger.error(f"预取失败: {prefetch_func.__name__} - {e}")

    def get_prefetched(self, func_name: str, context: dict[str, Any]) -> Any | None:
        """获取预取的数据"""
        cache_key = f"{func_name}:{hash(str(context))}"
        return self.prefetch_cache.get(cache_key)


class ConnectionPool:
    """连接池管理器"""

    def __init__(
        self, creator: Callable, min_connections: int = 2, max_connections: int = 10
    ):
        self.creator = creator
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.available: list[Any] = []
        self.in_use: set[Any] = set()

        # 初始化最小连接数
        for _ in range(min_connections):
            conn = creator()
            self.available.append(conn)

        logger.info(
            f"连接池初始化完成 (最小: {min_connections}, 最大: {max_connections})"
        )

    def acquire(self) -> Any:
        """获取连接"""
        # 从可用连接中获取
        if self.available:
            conn = self.available.pop()
            self.in_use.add(conn)
            return conn

        # 创建新连接
        if len(self.in_use) < self.max_connections:
            conn = self.creator()
            self.in_use.add(conn)
            return conn

        # 等待连接可用（简化实现）
        raise RuntimeError("连接池已满")

    def release(self, conn: Any):
        """释放连接"""
        if conn in self.in_use:
            self.in_use.remove(conn)
            self.available.append(conn)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "available": len(self.available),
            "in_use": len(self.in_use),
            "total": len(self.available) + len(self.in_use),
            "max_connections": self.max_connections,
        }


# 全局实例
_query_optimizer: QueryOptimizer | None = None
_api_cache: APIResponseCache | None = None
_data_prefetcher: DataPrefetcher | None = None


def get_query_optimizer() -> QueryOptimizer:
    """获取全局查询优化器"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer


def get_api_cache() -> APIResponseCache:
    """获取全局API缓存"""
    global _api_cache
    if _api_cache is None:
        _api_cache = APIResponseCache()
    return _api_cache


def get_data_prefetcher() -> DataPrefetcher:
    """获取全局数据预取器"""
    global _data_prefetcher
    if _data_prefetcher is None:
        _data_prefetcher = DataPrefetcher()
    return _data_prefetcher
