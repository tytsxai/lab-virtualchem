"""缓存管理器测试"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.core.cache_manager import (
    CacheEntry,
    CacheManager,
    CacheStrategy,
    close_cache_manager,
    get_cache_manager,
)


class TestCacheManager:
    """缓存管理器测试类"""

    def setup_method(self):
        """测试前准备"""
        self.cache_manager = CacheManager(
            max_size=10, strategy=CacheStrategy.LRU, ttl=300
        )

    def teardown_method(self):
        """测试后清理"""
        self.cache_manager.close()

    def test_cache_manager_initialization(self):
        """测试缓存管理器初始化"""
        assert self.cache_manager.max_size == 10
        assert self.cache_manager.strategy == CacheStrategy.LRU
        assert self.cache_manager.ttl == 300
        assert len(self.cache_manager.cache) == 0

    def test_set_and_get(self):
        """测试设置和获取缓存"""
        # 设置缓存
        self.cache_manager.set("key1", "value1")

        # 获取缓存
        value = self.cache_manager.get("key1")
        assert value == "value1"

        # 检查缓存统计
        assert self.cache_manager.stats["hits"] == 1
        assert self.cache_manager.stats["misses"] == 0

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        value = self.cache_manager.get("nonexistent")
        assert value is None
        assert self.cache_manager.stats["misses"] == 1

    def test_cache_expiration(self):
        """测试缓存过期"""
        # 设置短期TTL
        self.cache_manager.ttl = 1

        # 设置缓存
        self.cache_manager.set("key1", "value1")

        # 等待过期
        time.sleep(1.1)

        # 获取过期缓存
        value = self.cache_manager.get("key1")
        assert value is None

    def test_lru_eviction(self):
        """测试LRU淘汰策略"""
        # 填满缓存
        for i in range(10):
            self.cache_manager.set(f"key{i}", f"value{i}")

        # 访问第一个键，使其成为最近使用
        self.cache_manager.get("key0")

        # 添加新键，应该淘汰最久未使用的
        self.cache_manager.set("key10", "value10")

        # 检查key1被淘汰
        assert self.cache_manager.get("key1") is None
        assert self.cache_manager.get("key0") == "value0"

    def test_lfu_eviction(self):
        """测试LFU淘汰策略"""
        cache_manager = CacheManager(max_size=3, strategy=CacheStrategy.LFU)

        try:
            # 设置缓存
            cache_manager.set("key1", "value1")
            cache_manager.set("key2", "value2")
            cache_manager.set("key3", "value3")

            # 多次访问key1和key2
            cache_manager.get("key1")
            cache_manager.get("key1")
            cache_manager.get("key2")

            # 添加新键，应该淘汰访问次数最少的key3
            cache_manager.set("key4", "value4")

            assert cache_manager.get("key3") is None
            assert cache_manager.get("key1") == "value1"
            assert cache_manager.get("key2") == "value2"
        finally:
            cache_manager.close()

    def test_fifo_eviction(self):
        """测试FIFO淘汰策略"""
        cache_manager = CacheManager(max_size=3, strategy=CacheStrategy.FIFO)

        try:
            # 按顺序设置缓存
            cache_manager.set("key1", "value1")
            cache_manager.set("key2", "value2")
            cache_manager.set("key3", "value3")

            # 添加新键，应该淘汰最早设置的key1
            cache_manager.set("key4", "value4")

            assert cache_manager.get("key1") is None
            assert cache_manager.get("key2") == "value2"
            assert cache_manager.get("key3") == "value3"
            assert cache_manager.get("key4") == "value4"
        finally:
            cache_manager.close()

    def test_ttl_eviction(self):
        """测试TTL淘汰策略"""
        cache_manager = CacheManager(max_size=10, strategy=CacheStrategy.TTL)

        try:
            # 设置不同TTL的缓存
            cache_manager.set("key1", "value1", ttl=1)
            cache_manager.set("key2", "value2", ttl=2)

            # 等待第一个过期
            time.sleep(1.1)

            # 添加新键触发清理
            cache_manager.set("key3", "value3")

            assert cache_manager.get("key1") is None
            assert cache_manager.get("key2") == "value2"
            assert cache_manager.get("key3") == "value3"
        finally:
            cache_manager.close()

    def test_delete(self):
        """测试删除缓存"""
        self.cache_manager.set("key1", "value1")
        assert self.cache_manager.get("key1") == "value1"

        # 删除缓存
        self.cache_manager.delete("key1")
        assert self.cache_manager.get("key1") is None

    def test_clear(self):
        """测试清空缓存"""
        # 设置多个缓存
        for i in range(5):
            self.cache_manager.set(f"key{i}", f"value{i}")

        # 清空缓存
        self.cache_manager.clear()

        # 检查缓存为空
        assert len(self.cache_manager.cache) == 0
        for i in range(5):
            assert self.cache_manager.get(f"key{i}") is None

    def test_get_stats(self):
        """测试获取统计信息"""
        # 设置和获取缓存
        self.cache_manager.set("key1", "value1")
        self.cache_manager.get("key1")
        self.cache_manager.get("nonexistent")

        stats = self.cache_manager.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.5

    def test_context_manager(self):
        """测试上下文管理器"""
        with CacheManager() as cache:
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"
        # 上下文退出后应该自动清理

    def test_singleton_pattern(self):
        """测试单例模式"""
        # 获取全局缓存管理器
        cache1 = get_cache_manager()
        cache2 = get_cache_manager()

        # 应该是同一个实例
        assert cache1 is cache2

        # 清理
        close_cache_manager()

    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        import time

        results = []

        def worker(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                self.cache_manager.set(key, value)
                retrieved = self.cache_manager.get(key)
                results.append((thread_id, i, retrieved == value))
                time.sleep(0.001)

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查所有操作都成功
        for thread_id, i, success in results:
            assert success, f"Thread {thread_id}, iteration {i} failed"

    def test_memory_usage(self):
        """测试内存使用"""
        # 设置大量缓存
        for i in range(1000):
            self.cache_manager.set(f"key{i}", f"value{i}")

        # 检查内存使用统计
        stats = self.cache_manager.get_stats()
        assert stats["size"] <= self.cache_manager.max_size
        assert stats["memory_usage_mb"] > 0

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效策略
        with pytest.raises(ValueError):
            CacheManager(strategy="invalid")

        # 测试负数大小
        with pytest.raises(ValueError):
            CacheManager(max_size=-1)

        # 测试负数TTL
        with pytest.raises(ValueError):
            CacheManager(ttl=-1)

    def test_cache_entry(self):
        """测试缓存条目"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=now,
            expires_at=now + timedelta(seconds=300),
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.created_at == now
        assert entry.expires_at == now + timedelta(seconds=300)
        assert entry.access_count == 0
        assert entry.last_accessed is None
        assert entry.size_bytes == 0

    def test_redis_integration(self):
        """测试Redis集成"""
        with patch("redis.Redis") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client

            # 测试Redis连接
            cache_manager = CacheManager(
                use_redis=True, redis_url="redis://localhost:6379"
            )

            try:
                assert cache_manager.use_redis is True
                assert cache_manager.redis_client is not None
            finally:
                cache_manager.close()

    def test_performance(self):
        """测试性能"""
        import time

        # 测试设置性能
        start_time = time.time()
        for i in range(1000):
            self.cache_manager.set(f"key{i}", f"value{i}")
        set_time = time.time() - start_time

        # 测试获取性能
        start_time = time.time()
        for i in range(1000):
            self.cache_manager.get(f"key{i}")
        get_time = time.time() - start_time

        # 性能应该合理
        assert set_time < 1.0  # 1000次设置应该在1秒内
        assert get_time < 1.0  # 1000次获取应该在1秒内

        print(f"Set performance: {set_time:.3f}s for 1000 operations")
        print(f"Get performance: {get_time:.3f}s for 1000 operations")


if __name__ == "__main__":
    pytest.main([__file__])
