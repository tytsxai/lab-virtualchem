"""
优化的缓存管理器测试
"""

import time

import pytest

from src.core.optimized_cache import (
    OptimizedLFUCache,
    OptimizedLRUCache,
    create_optimized_cache,
)


class TestOptimizedLRUCache:
    """测试优化的LRU缓存"""

    def test_basic_operations(self):
        """测试基本操作"""
        cache = OptimizedLRUCache(max_size=3)

        # 设置值
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 获取值
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # 测试LRU行为
        cache.set("key4", "value4")  # 应该驱逐key1
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

        # 访问key2，使其成为最近使用的
        cache.get("key2")
        cache.set("key5", "value5")  # 应该驱逐key3
        assert cache.get("key3") is None
        assert cache.get("key2") == "value2"

    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = OptimizedLRUCache(max_size=10, default_ttl=1)

        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=0)  # 永不过期

        # 立即获取
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # 等待过期
        time.sleep(1.1)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cleanup_expired(self):
        """测试清理过期条目"""
        cache = OptimizedLRUCache(max_size=10, default_ttl=1)

        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=0)

        time.sleep(1.1)

        cleaned = cache.cleanup_expired()
        assert cleaned == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_delete_and_clear(self):
        """测试删除和清空"""
        cache = OptimizedLRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 删除
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key3") is False

        # 清空
        cache.clear()
        assert cache.get("key2") is None

    def test_statistics(self):
        """测试统计信息"""
        cache = OptimizedLRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.get("key1")
        cache.get("key1")
        cache.get("key2")

        stats = cache.get_statistics()
        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["total_access"] == 3
        assert stats["average_access"] == 1.5


class TestOptimizedLFUCache:
    """测试优化的LFU缓存"""

    def test_basic_operations(self):
        """测试基本操作"""
        cache = OptimizedLFUCache(max_size=3)

        # 设置值
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 获取值
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        # 测试LFU行为
        cache.get("key1")  # key1访问次数: 2
        cache.get("key2")  # key2访问次数: 2
        cache.get("key1")  # key1访问次数: 3

        cache.set("key4", "value4")  # 应该驱逐key3（访问次数最少）
        assert cache.get("key3") is None
        assert cache.get("key4") == "value4"

    def test_frequency_tracking(self):
        """测试频率跟踪"""
        cache = OptimizedLFUCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 增加key1的访问频率
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")

        # 增加key2的访问频率
        cache.get("key2")
        cache.get("key2")

        # key3访问次数最少，应该被驱逐
        cache.set("key4", "value4")
        assert cache.get("key3") is None
        assert cache.get("key4") == "value4"

    def test_ttl_expiration(self):
        """测试TTL过期"""
        cache = OptimizedLFUCache(max_size=10, default_ttl=1)

        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=0)  # 永不过期

        # 立即获取
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # 等待过期
        time.sleep(1.1)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cleanup_expired(self):
        """测试清理过期条目"""
        cache = OptimizedLFUCache(max_size=10, default_ttl=1)

        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=0)

        time.sleep(1.1)

        cleaned = cache.cleanup_expired()
        assert cleaned == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_delete_and_clear(self):
        """测试删除和清空"""
        cache = OptimizedLFUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 删除
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key3") is False

        # 清空
        cache.clear()
        assert cache.get("key2") is None

    def test_statistics(self):
        """测试统计信息"""
        cache = OptimizedLFUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.get("key1")
        cache.get("key1")
        cache.get("key2")

        stats = cache.get_statistics()
        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["total_access"] == 3
        assert stats["average_access"] == 1.5
        assert "min_frequency" in stats


class TestCreateOptimizedCache:
    """测试缓存创建函数"""

    def test_create_lru_cache(self):
        """测试创建LRU缓存"""
        cache = create_optimized_cache("lru", max_size=5, default_ttl=300)
        assert isinstance(cache, OptimizedLRUCache)
        assert cache.max_size == 5
        assert cache.default_ttl == 300

    def test_create_lfu_cache(self):
        """测试创建LFU缓存"""
        cache = create_optimized_cache("lfu", max_size=5, default_ttl=300)
        assert isinstance(cache, OptimizedLFUCache)
        assert cache.max_size == 5
        assert cache.default_ttl == 300

    def test_invalid_strategy(self):
        """测试无效策略"""
        with pytest.raises(ValueError, match="Unsupported cache strategy"):
            create_optimized_cache("invalid", max_size=5, default_ttl=300)


class TestPerformance:
    """性能测试"""

    def test_lru_performance(self):
        """测试LRU缓存性能"""
        cache = OptimizedLRUCache(max_size=1000)

        # 大量设置操作
        start_time = time.time()
        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")
        set_time = time.time() - start_time

        # 大量获取操作
        start_time = time.time()
        for i in range(1000):
            cache.get(f"key{i}")
        get_time = time.time() - start_time

        # 性能断言（这些值可能需要根据实际环境调整）
        assert set_time < 1.0  # 设置操作应该在1秒内完成
        assert get_time < 1.0  # 获取操作应该在1秒内完成

    def test_lfu_performance(self):
        """测试LFU缓存性能"""
        cache = OptimizedLFUCache(max_size=1000)

        # 大量设置操作
        start_time = time.time()
        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")
        set_time = time.time() - start_time

        # 大量获取操作
        start_time = time.time()
        for i in range(1000):
            cache.get(f"key{i}")
        get_time = time.time() - start_time

        # 性能断言（这些值可能需要根据实际环境调整）
        assert set_time < 1.0  # 设置操作应该在1秒内完成
        assert get_time < 1.0  # 获取操作应该在1秒内完成


if __name__ == "__main__":
    pytest.main([__file__])
