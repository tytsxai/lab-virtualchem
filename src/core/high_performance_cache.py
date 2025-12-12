"""
高性能缓存系统
实现O(1)操作的LRU/LFU缓存，支持批量操作、缓存预热和自动清理
"""

import atexit
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime | None
    access_count: int = 0
    last_accessed: datetime = field(default=None)
    size_bytes: int = 0  # 估算的内存占用

    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """检查是否过期"""
        return self.expires_at is not None and datetime.now() > self.expires_at


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    expired: int = 0
    total_size: int = 0

    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'evictions': self.evictions,
            'expired': self.expired,
            'total_size': self.total_size,
            'hit_rate': self.hit_rate()
        }


class HighPerformanceLRUCache:
    """高性能LRU缓存

    特性：
    - O(1) 查询、插入、删除
    - 线程安全
    - 自动过期清理
    - 批量操作
    - 详细统计
    - 内存限制
    """

    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,
        max_memory_mb: int = 100,
        auto_cleanup: bool = True,
        cleanup_interval: int = 300  # 5分钟
    ):
        """初始化缓存

        Args:
            max_size: 最大条目数
            default_ttl: 默认过期时间（秒）
            max_memory_mb: 最大内存占用（MB）
            auto_cleanup: 是否自动清理过期条目
            cleanup_interval: 清理间隔（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

        # 缓存数据
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 统计信息
        self._stats = CacheStats()

        # 自动清理
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval = cleanup_interval
        self._cleanup_thread = None
        if auto_cleanup:
            self._start_cleanup_thread()
            atexit.register(self.stop)

        logger.info(f"高性能LRU缓存初始化完成 (max_size={max_size}, max_memory={max_memory_mb}MB)")

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值 - O(1)

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return default

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._stats.expired += 1
                self._stats.misses += 1
                self._stats.total_size -= entry.size_bytes
                return default

            # 更新访问信息并移到末尾（最近使用）
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._cache.move_to_end(key)

            self._stats.hits += 1
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        size_bytes: int | None = None
    ) -> None:
        """设置缓存值 - O(1)

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
            size_bytes: 值的大小（字节），None自动估算
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        # 估算大小
        if size_bytes is None:
            size_bytes = self._estimate_size(value)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            size_bytes=size_bytes
        )

        with self._lock:
            # 如果键已存在，更新
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.total_size -= old_entry.size_bytes
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                # 检查是否需要驱逐
                while len(self._cache) >= self.max_size or \
                      self._stats.total_size + size_bytes > self.max_memory_bytes:
                    if not self._cache:
                        break
                    # 移除最旧的条目（第一个）
                    evicted_key, evicted_entry = self._cache.popitem(last=False)
                    self._stats.evictions += 1
                    self._stats.total_size -= evicted_entry.size_bytes

                # 添加新条目
                self._cache[key] = entry

            self._stats.sets += 1
            self._stats.total_size += size_bytes

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """批量获取 - O(n)

        Args:
            keys: 键列表

        Returns:
            键值对字典
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """批量设置 - O(n)

        Args:
            items: 键值对字典
            ttl: 过期时间
        """
        for key, value in items.items():
            self.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """删除缓存条目 - O(1)

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self._stats.deletes += 1
                self._stats.total_size -= entry.size_bytes
                return True
            return False

    def delete_many(self, keys: list[str]) -> int:
        """批量删除 - O(n)

        Args:
            keys: 键列表

        Returns:
            删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._stats.total_size = 0

    def exists(self, key: str) -> bool:
        """检查键是否存在 - O(1)"""
        with self._lock:
            if key not in self._cache:
                return False
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._stats.expired += 1
                self._stats.total_size -= entry.size_bytes
                return False
            return True

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """清理过期条目

        Returns:
            清理的数量
        """
        with self._lock:
            expired_keys = []
            now = datetime.now()

            for key, entry in self._cache.items():
                if entry.expires_at and now > entry.expires_at:
                    expired_keys.append(key)

            for key in expired_keys:
                entry = self._cache[key]
                del self._cache[key]
                self._stats.expired += 1
                self._stats.total_size -= entry.size_bytes

            count = len(expired_keys)
            if count > 0:
                logger.debug(f"清理了 {count} 个过期条目")

            return count

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.to_dict()
            stats['current_size'] = len(self._cache)
            stats['max_size'] = self.max_size
            stats['memory_mb'] = self._stats.total_size / 1024 / 1024
            stats['max_memory_mb'] = self.max_memory_bytes / 1024 / 1024
            return stats

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats = CacheStats(total_size=self._stats.total_size)

    def get_top_accessed(self, n: int = 10) -> list[tuple[str, int]]:
        """获取访问最多的条目

        Args:
            n: 返回数量

        Returns:
            (键, 访问次数) 列表
        """
        with self._lock:
            items = [(k, e.access_count) for k, e in self._cache.items()]
            items.sort(key=lambda x: x[1], reverse=True)
            return items[:n]

    def warmup(self, loader: Callable[[str], Any], keys: list[str]) -> int:
        """缓存预热

        Args:
            loader: 数据加载函数
            keys: 要预热的键列表

        Returns:
            预热的数量
        """
        count = 0
        for key in keys:
            if not self.exists(key):
                try:
                    value = loader(key)
                    self.set(key, value)
                    count += 1
                except Exception as e:
                    logger.error(f"预热失败 {key}: {e}")

        logger.info(f"缓存预热完成，加载了 {count} 个条目")
        return count

    def _estimate_size(self, value: Any) -> int:
        """估算值的大小（字节）"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(v) for v in value) + 64
            elif isinstance(value, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items()) + 128
            else:
                # 默认估算
                return 256
        except Exception:
            return 256

    def _start_cleanup_thread(self) -> None:
        """启动自动清理线程"""
        def cleanup_loop():
            while self.auto_cleanup:
                time.sleep(self.cleanup_interval)
                try:
                    self.cleanup_expired()
                except Exception as e:
                    logger.error(f"自动清理失败: {e}")

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.debug("自动清理线程已启动")

    def stop(self) -> None:
        """停止缓存（清理资源）"""
        self.auto_cleanup = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1)
        logger.info("缓存已停止")

    def __del__(self):
        """析构函数"""
        try:
            self.stop()
        except Exception:
            pass


def create_high_performance_cache(
    strategy: str = "lru",
    **kwargs
) -> HighPerformanceLRUCache:
    """创建高性能缓存实例

    Args:
        strategy: 缓存策略（目前只支持lru）
        **kwargs: 其他参数传递给缓存构造函数

    Returns:
        缓存实例
    """
    if strategy.lower() == "lru":
        return HighPerformanceLRUCache(**kwargs)
    else:
        raise ValueError(f"不支持的缓存策略: {strategy}")
