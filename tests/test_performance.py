"""性能测试"""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from src.core.async_service import AsyncCache, AsyncRateLimiter, AsyncServiceManager
from src.core.cache_manager import CacheManager, CacheStrategy
from src.core.database_pool import DatabasePool
from src.core.testing_framework import PerformanceTest


class TestAsyncServiceManager(unittest.TestCase):
    """异步服务管理器测试"""

    def setUp(self):
        self.async_manager = AsyncServiceManager(max_workers=2, max_processes=1)

    def tearDown(self):
        self.async_manager.shutdown()

    def test_submit_task(self):
        """测试任务提交"""

        def test_func(x, y):
            return x + y

        task_id = self.async_manager.submit_task(test_func, 1, 2)
        self.assertIsNotNone(task_id)

        # 等待任务完成
        result = self.async_manager.wait_for_task(task_id, timeout=5)
        self.assertEqual(result, 3)

    def test_task_status(self):
        """测试任务状态"""

        def slow_func():
            time.sleep(0.1)
            return "done"

        task_id = self.async_manager.submit_task(slow_func)

        # 检查状态
        status = self.async_manager.get_task_status(task_id)
        self.assertIsNotNone(status)
        self.assertIn("status", status)

    def test_parallel_execution(self):
        """测试并行执行"""

        def test_func(duration):
            time.sleep(duration)
            return duration

        # 提交多个任务
        task_ids = []
        for _ in range(3):
            task_id = self.async_manager.submit_task(test_func, 0.1)
            task_ids.append(task_id)

        # 等待所有任务完成
        start_time = time.time()
        for task_id in task_ids:
            self.async_manager.wait_for_task(task_id, timeout=5)
        end_time = time.time()

        # 并行执行应该比串行快
        self.assertLess(end_time - start_time, 0.5)

    def test_task_statistics(self):
        """测试任务统计"""

        def test_func():
            return "test"

        # 提交任务
        task_id = self.async_manager.submit_task(test_func)
        self.async_manager.wait_for_task(task_id)

        # 获取统计信息
        stats = self.async_manager.get_task_statistics()
        self.assertGreater(stats["total_tasks"], 0)
        self.assertGreater(stats["completed_tasks"], 0)


class TestAsyncCache(unittest.TestCase):
    """异步缓存测试"""

    def setUp(self):
        self.cache = AsyncCache(max_size=10, ttl=1)

    def test_get_set(self):
        """测试缓存获取和设置"""
        key = "test_key"
        value = "test_value"

        # 设置缓存
        self.cache.set(key, value)

        # 获取缓存
        result = self.cache.get(key)
        self.assertEqual(result, value)

    def test_expiration(self):
        """测试缓存过期"""
        key = "test_key"
        value = "test_value"

        # 设置缓存
        self.cache.set(key, value)

        # 等待过期
        time.sleep(1.1)

        # 缓存应该过期
        result = self.cache.get(key)
        self.assertIsNone(result)

    def test_size_limit(self):
        """测试大小限制"""
        # 添加超过限制的条目
        for i in range(15):
            self.cache.set(f"key_{i}", f"value_{i}")

        # 检查大小
        self.assertLessEqual(len(self.cache.cache), 10)

    def test_cleanup_expired(self):
        """测试清理过期条目"""
        # 添加一些条目
        for i in range(5):
            self.cache.set(f"key_{i}", f"value_{i}")

        # 等待过期
        time.sleep(1.1)

        # 清理过期条目
        cleaned = self.cache.cleanup_expired()
        self.assertGreater(cleaned, 0)


class TestAsyncRateLimiter(unittest.TestCase):
    """异步速率限制器测试"""

    def setUp(self):
        self.rate_limiter = AsyncRateLimiter(max_requests=3, time_window=1)

    def test_rate_limiting(self):
        """测试速率限制"""
        key = "test_key"

        # 前3个请求应该被允许
        for _ in range(3):
            self.assertTrue(self.rate_limiter.is_allowed(key))

        # 第4个请求应该被拒绝
        self.assertFalse(self.rate_limiter.is_allowed(key))

    def test_remaining_requests(self):
        """测试剩余请求数"""
        key = "test_key"

        # 初始应该有3个剩余请求
        remaining = self.rate_limiter.get_remaining_requests(key)
        self.assertEqual(remaining, 3)

        # 使用一个请求
        self.rate_limiter.is_allowed(key)

        # 剩余请求应该减少
        remaining = self.rate_limiter.get_remaining_requests(key)
        self.assertEqual(remaining, 2)

    def test_reset(self):
        """测试重置"""
        key = "test_key"

        # 使用所有请求
        for _ in range(3):
            self.rate_limiter.is_allowed(key)

        # 重置
        self.rate_limiter.reset(key)

        # 应该可以再次使用
        self.assertTrue(self.rate_limiter.is_allowed(key))


class TestCacheManager(unittest.TestCase):
    """缓存管理器测试"""

    def setUp(self):
        self.cache = CacheManager(max_size=100, default_ttl=1)

    def test_basic_operations(self):
        """测试基本操作"""
        key = "test_key"
        value = {"data": "test"}

        # 设置缓存
        self.cache.set(key, value)

        # 获取缓存
        result = self.cache.get(key)
        self.assertEqual(result, value)

        # 删除缓存
        deleted = self.cache.delete(key)
        self.assertTrue(deleted)

        # 缓存应该不存在
        result = self.cache.get(key)
        self.assertIsNone(result)

    def test_cache_strategies(self):
        """测试缓存策略"""
        # 测试LRU策略
        lru_cache = CacheManager(strategy=CacheStrategy.LRU, max_size=2)

        lru_cache.set("key1", "value1")
        lru_cache.set("key2", "value2")
        lru_cache.set("key3", "value3")  # 应该驱逐key1

        self.assertIsNone(lru_cache.get("key1"))
        self.assertEqual(lru_cache.get("key2"), "value2")
        self.assertEqual(lru_cache.get("key3"), "value3")

    def test_ttl_expiration(self):
        """测试TTL过期"""
        key = "test_key"
        value = "test_value"

        # 设置短期缓存
        self.cache.set(key, value, ttl=1)

        # 立即获取应该成功
        result = self.cache.get(key)
        self.assertEqual(result, value)

        # 等待过期
        time.sleep(1.1)

        # 获取应该失败
        result = self.cache.get(key)
        self.assertIsNone(result)

    def test_cache_statistics(self):
        """测试缓存统计"""
        # 添加一些缓存条目
        for i in range(5):
            self.cache.set(f"key_{i}", f"value_{i}")

        # 获取统计信息
        stats = self.cache.get_statistics()
        self.assertEqual(stats["size"], 5)
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)

        # 获取缓存条目
        self.cache.get("key_0")
        self.cache.get("nonexistent")

        # 更新统计信息
        stats = self.cache.get_statistics()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)


class TestDatabasePool(unittest.TestCase):
    """数据库连接池测试"""

    def setUp(self):
        # 使用内存SQLite数据库进行测试
        self.db_pool = DatabasePool(
            db_type="sqlite",
            config={"database": ":memory:"},
            min_connections=1,
            max_connections=3,
        )

    def tearDown(self):
        self.db_pool.close_all()

    def test_connection_pool(self):
        """测试连接池"""
        # 获取连接
        connection_id = self.db_pool.get_connection()
        self.assertIsNotNone(connection_id)

        # 归还连接
        self.db_pool.return_connection(connection_id)

        # 再次获取连接
        connection_id2 = self.db_pool.get_connection()
        self.assertIsNotNone(connection_id2)

    def test_connection_context(self):
        """测试连接上下文"""
        with self.db_pool.get_connection_context() as connection_id:
            self.assertIsNotNone(connection_id)
            connection = self.db_pool.all_connections[connection_id]
            self.assertIsNotNone(connection)

    def test_pool_statistics(self):
        """测试连接池统计"""
        # 获取统计信息
        stats = self.db_pool.get_statistics()
        self.assertGreater(stats["total_connections"], 0)
        self.assertEqual(stats["active_connections"], 0)
        self.assertGreater(stats["idle_connections"], 0)


class TestPerformanceBenchmarks(unittest.TestCase):
    """性能基准测试"""

    def test_cache_performance(self):
        """测试缓存性能"""
        cache = CacheManager(max_size=1000)
        perf_test = PerformanceTest("Cache Performance")

        def cache_operation():
            for i in range(100):
                cache.set(f"key_{i}", f"value_{i}")
                cache.get(f"key_{i}")

        # 基准测试
        results = perf_test.benchmark(cache_operation, iterations=10)

        # 检查性能指标
        self.assertLess(results["mean"], 0.1)  # 平均耗时应该小于0.1秒
        self.assertLess(results["max"], 0.2)  # 最大耗时应该小于0.2秒

    def test_async_performance(self):
        """测试异步性能"""
        async_manager = AsyncServiceManager(max_workers=4)
        perf_test = PerformanceTest("Async Performance")

        def async_task():
            def test_func():
                return sum(range(1000))

            task_id = async_manager.submit_task(test_func)
            return async_manager.wait_for_task(task_id)

        try:
            # 基准测试
            results = perf_test.benchmark(async_task, iterations=5)

            # 检查性能指标
            self.assertLess(results["mean"], 0.5)  # 平均耗时应该小于0.5秒

        finally:
            async_manager.shutdown()

    def test_concurrent_access(self):
        """测试并发访问"""
        cache = CacheManager(max_size=1000)

        def worker(worker_id):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                cache.set(key, f"value_{i}")
                cache.get(key)

        # 并发执行
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(4)]
            for future in futures:
                future.result()
        end_time = time.time()

        # 并发执行应该比串行快
        self.assertLess(end_time - start_time, 2.0)

        # 检查缓存统计
        stats = cache.get_statistics()
        self.assertGreater(stats["hits"], 0)


if __name__ == "__main__":
    unittest.main()
