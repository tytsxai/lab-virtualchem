"""
高级缓存系统
提供多级缓存、智能预取、缓存预热等功能
"""

from __future__ import annotations

import hashlib
import pickle
import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


class CacheLevel(Enum):
    """缓存级别"""

    L1 = "l1"  # 内存缓存
    L2 = "l2"  # 磁盘缓存
    L3 = "l3"  # 分布式缓存


class CachePolicy(Enum):
    """缓存策略"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用
    FIFO = "fifo"  # 先进先出
    TTL = "ttl"  # 基于时间


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl: timedelta | None = None
    level: CacheLevel = CacheLevel.L1

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.now() - self.created_at > self.ttl

    def update_access(self) -> None:
        """更新访问信息"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheStats:
    """缓存统计"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size_bytes = 0
        self.entries_count = 0
        self.last_reset = datetime.now()

    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def reset(self) -> None:
        """重置统计"""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size_bytes = 0
        self.entries_count = 0
        self.last_reset = datetime.now()


class L1Cache:
    """L1内存缓存"""

    def __init__(self, max_size: int = 1000, policy: CachePolicy = CachePolicy.LRU):
        """初始化L1缓存

        Args:
            max_size: 最大条目数
            policy: 缓存策略
        """
        self.max_size = max_size
        self.policy = policy
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.stats = CacheStats()

        logger.info(f"L1缓存已初始化: max_size={max_size}, policy={policy.value}")

    def get(self, key: str) -> Any | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self.stats.misses += 1
                self.stats.entries_count -= 1
                return None

            # 更新访问信息
            entry.update_access()

            # LRU策略：移动到末尾
            if self.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            self.stats.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间
        """
        with self._lock:
            # 检查是否需要淘汰
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict()

            # 计算大小
            size_bytes = self._calculate_size(value)

            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=size_bytes,
                ttl=ttl,
                level=CacheLevel.L1,
            )

            # 存储
            self._cache[key] = entry
            self.stats.entries_count += 1
            self.stats.size_bytes += size_bytes

            logger.debug(f"L1缓存已设置: {key}")

    def delete(self, key: str) -> bool:
        """删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self.stats.entries_count -= 1
                self.stats.size_bytes -= entry.size_bytes
                logger.debug(f"L1缓存已删除: {key}")
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self.stats.entries_count = 0
            self.stats.size_bytes = 0
            logger.info("L1缓存已清空")

    def _evict(self) -> None:
        """淘汰缓存条目"""
        if not self._cache:
            return

        if self.policy == CachePolicy.LRU:
            # 淘汰最久未使用的
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        elif self.policy == CachePolicy.LFU:
            # 淘汰使用次数最少的
            least_used_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[least_used_key]
        elif self.policy == CachePolicy.FIFO:
            # 淘汰最早创建的
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]

        self.stats.evictions += 1
        logger.debug("L1缓存条目已淘汰")

    def _calculate_size(self, value: Any) -> int:
        """计算值的大小

        Args:
            value: 值

        Returns:
            大小（字节）
        """
        try:
            return len(pickle.dumps(value))
        except Exception:
            return len(str(value).encode("utf-8"))

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": self.stats.hit_rate(),
            "evictions": self.stats.evictions,
            "entries_count": self.stats.entries_count,
            "size_bytes": self.stats.size_bytes,
            "max_size": self.max_size,
            "policy": self.policy.value,
            "last_reset": self.stats.last_reset.isoformat(),
        }


class L2Cache:
    """L2磁盘缓存"""

    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        """初始化L2缓存

        Args:
            cache_dir: 缓存目录
            max_size_mb: 最大大小（MB）
        """
        import os

        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        self.stats = CacheStats()

        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)

        logger.info(f"L2缓存已初始化: dir={cache_dir}, max_size={max_size_mb}MB")

    def get(self, key: str) -> Any | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        import os

        with self._lock:
            file_path = self._get_file_path(key)

            if not os.path.exists(file_path):
                self.stats.misses += 1
                return None

            try:
                with open(file_path, "rb") as f:
                    data = pickle.load(f)

                # 检查是否过期
                if data.get("expires_at") and datetime.now() > data["expires_at"]:
                    os.remove(file_path)
                    self.stats.misses += 1
                    return None

                self.stats.hits += 1
                return data["value"]

            except Exception as e:
                logger.error(f"L2缓存读取失败: {e}")
                self.stats.misses += 1
                return None

    def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间
        """

        with self._lock:
            file_path = self._get_file_path(key)

            try:
                # 准备数据
                data = {
                    "value": value,
                    "created_at": datetime.now(),
                    "expires_at": datetime.now() + ttl if ttl else None,
                }

                # 写入文件
                with open(file_path, "wb") as f:
                    pickle.dump(data, f)

                self.stats.entries_count += 1
                logger.debug(f"L2缓存已设置: {key}")

            except Exception as e:
                logger.error(f"L2缓存写入失败: {e}")

    def delete(self, key: str) -> bool:
        """删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        import os

        with self._lock:
            file_path = self._get_file_path(key)

            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.stats.entries_count -= 1
                    logger.debug(f"L2缓存已删除: {key}")
                    return True
                except Exception as e:
                    logger.error(f"L2缓存删除失败: {e}")
            return False

    def clear(self) -> None:
        """清空缓存"""
        import os

        with self._lock:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".cache"):
                        os.remove(os.path.join(self.cache_dir, filename))
                self.stats.entries_count = 0
                logger.info("L2缓存已清空")
            except Exception as e:
                logger.error(f"L2缓存清空失败: {e}")

    def _get_file_path(self, key: str) -> str:
        """获取文件路径

        Args:
            key: 缓存键

        Returns:
            文件路径
        """
        import os

        # 使用哈希避免文件名冲突
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.cache")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": self.stats.hit_rate(),
            "entries_count": self.stats.entries_count,
            "cache_dir": self.cache_dir,
            "max_size_mb": self.max_size_bytes // (1024 * 1024),
            "last_reset": self.stats.last_reset.isoformat(),
        }


class AdvancedCache:
    """高级缓存系统"""

    def __init__(
        self,
        l1_max_size: int = 1000,
        l2_cache_dir: str = "cache",
        l2_max_size_mb: int = 100,
        policy: CachePolicy = CachePolicy.LRU,
    ):
        """初始化高级缓存系统

        Args:
            l1_max_size: L1缓存最大条目数
            l2_cache_dir: L2缓存目录
            l2_max_size_mb: L2缓存最大大小（MB）
            policy: 缓存策略
        """
        self.l1_cache = L1Cache(max_size=l1_max_size, policy=policy)
        self.l2_cache = L2Cache(cache_dir=l2_cache_dir, max_size_mb=l2_max_size_mb)

        # 预取配置
        self.prefetch_enabled = True
        self.prefetch_patterns: list[str] = []

        # 预热配置
        self.warmup_enabled = True
        self.warmup_data: dict[str, Any] = {}

        logger.info("高级缓存系统已初始化")

    def get(self, key: str) -> Any | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        # 先尝试L1缓存
        value = self.l1_cache.get(key)
        if value is not None:
            return value

        # 再尝试L2缓存
        value = self.l2_cache.get(key)
        if value is not None:
            # 回填到L1缓存
            self.l1_cache.set(key, value)
            return value

        return None

    def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间
        """
        # 设置L1缓存
        self.l1_cache.set(key, value, ttl)

        # 设置L2缓存
        self.l2_cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        l1_result = self.l1_cache.delete(key)
        l2_result = self.l2_cache.delete(key)
        return l1_result or l2_result

    def clear(self) -> None:
        """清空缓存"""
        self.l1_cache.clear()
        self.l2_cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()

        return {
            "l1": l1_stats,
            "l2": l2_stats,
            "total_hits": l1_stats["hits"] + l2_stats["hits"],
            "total_misses": l1_stats["misses"] + l2_stats["misses"],
            "total_hit_rate": (
                (l1_stats["hits"] + l2_stats["hits"])
                / (l1_stats["hits"] + l2_stats["hits"] + l1_stats["misses"] + l2_stats["misses"])
                if (l1_stats["hits"] + l2_stats["hits"] + l1_stats["misses"] + l2_stats["misses"]) > 0
                else 0.0
            ),
        }

    def warmup(self, data: dict[str, Any]) -> None:
        """缓存预热

        Args:
            data: 预热数据
        """
        if not self.warmup_enabled:
            return

        logger.info(f"开始缓存预热: {len(data)} 个条目")

        for key, value in data.items():
            try:
                self.set(key, value)
            except Exception as e:
                logger.error(f"预热失败: {key} - {e}")

        logger.info("缓存预热完成")

    def prefetch(self, keys: list[str]) -> None:
        """预取缓存

        Args:
            keys: 要预取的键列表
        """
        if not self.prefetch_enabled:
            return

        logger.info(f"开始预取: {len(keys)} 个键")

        for key in keys:
            try:
                # 尝试从L2缓存预取到L1缓存
                value = self.l2_cache.get(key)
                if value is not None:
                    self.l1_cache.set(key, value)
            except Exception as e:
                logger.error(f"预取失败: {key} - {e}")

        logger.info("预取完成")

    def optimize(self) -> None:
        """优化缓存"""
        logger.info("开始缓存优化")

        # 清理过期条目
        self._cleanup_expired()

        # 调整缓存大小
        self._adjust_cache_size()

        logger.info("缓存优化完成")

    def _cleanup_expired(self) -> None:
        """清理过期条目"""
        # L1缓存清理
        expired_keys = []
        for key, entry in self.l1_cache._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            self.l1_cache.delete(key)

        logger.info(f"清理了 {len(expired_keys)} 个过期条目")

    def _adjust_cache_size(self) -> None:
        """调整缓存大小"""
        # 根据命中率调整缓存大小
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()

        # 如果L1命中率低，增加L1缓存大小
        if l1_stats["hit_rate"] < 0.7:
            self.l1_cache.max_size = min(2000, self.l1_cache.max_size + 100)
            logger.info(f"L1缓存大小调整为: {self.l1_cache.max_size}")

        # 如果L2命中率高，增加L2缓存大小
        if l2_stats["hit_rate"] > 0.8:
            self.l2_cache.max_size_bytes = min(500 * 1024 * 1024, self.l2_cache.max_size_bytes + 50 * 1024 * 1024)
            logger.info(f"L2缓存大小调整为: {self.l2_cache.max_size_bytes // (1024 * 1024)}MB")
