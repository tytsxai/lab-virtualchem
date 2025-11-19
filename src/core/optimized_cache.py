"""
优化的缓存管理器
实现O(1)的LRU算法，提升缓存性能
"""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = None

    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at


class OptimizedLRUCache:
    """优化的LRU缓存实现"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值 - O(1)"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._cache[key]
                return None

            # 更新访问信息并移到末尾
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._cache.move_to_end(key)

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值 - O(1)"""
        if ttl is None:
            ttl = self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at
        )

        with self._lock:
            # 如果键已存在，更新并移到末尾
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                # 检查缓存大小
                if len(self._cache) >= self.max_size:
                    # 移除最旧的条目（第一个）
                    self._cache.popitem(last=False)

                # 添加新条目
                self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """删除缓存条目 - O(1)"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = []
            now = datetime.now()

            for key, entry in self._cache.items():
                if entry.expires_at and now > entry.expires_at:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_access = sum(entry.access_count for entry in self._cache.values())
            avg_access = total_access / len(self._cache) if self._cache else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_access": total_access,
                "average_access": avg_access,
            }


class OptimizedLFUCache:
    """优化的LFU缓存实现"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}
        self._freq_map: dict[int, OrderedDict[str, None]] = {}  # 频率 -> 键列表
        self._key_freq: dict[str, int] = {}  # 键 -> 频率
        self._min_freq = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.expires_at and datetime.now() > entry.expires_at:
                self._remove_key(key)
                return None

            # 更新频率
            self._update_frequency(key)
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at
        )

        with self._lock:
            if key in self._cache:
                # 更新现有条目
                self._cache[key] = entry
                self._update_frequency(key)
            else:
                # 检查缓存大小
                if len(self._cache) >= self.max_size:
                    self._evict_least_frequent()

                # 添加新条目
                self._cache[key] = entry
                self._key_freq[key] = 1
                self._min_freq = 1

                if 1 not in self._freq_map:
                    self._freq_map[1] = OrderedDict()
                self._freq_map[1][key] = None

    def _update_frequency(self, key: str) -> None:
        """更新键的频率"""
        freq = self._key_freq[key]
        self._key_freq[key] = freq + 1

        # 从旧频率列表中移除
        del self._freq_map[freq][key]
        if not self._freq_map[freq]:
            del self._freq_map[freq]
            if freq == self._min_freq:
                self._min_freq += 1

        # 添加到新频率列表
        if freq + 1 not in self._freq_map:
            self._freq_map[freq + 1] = OrderedDict()
        self._freq_map[freq + 1][key] = None

    def _evict_least_frequent(self) -> None:
        """驱逐最少使用的条目"""
        if not self._freq_map[self._min_freq]:
            return

        # 移除最旧的条目
        key_to_remove = next(iter(self._freq_map[self._min_freq]))
        self._remove_key(key_to_remove)

    def _remove_key(self, key: str) -> None:
        """移除键"""
        if key not in self._cache:
            return

        freq = self._key_freq[key]
        del self._cache[key]
        del self._key_freq[key]
        del self._freq_map[freq][key]

        if not self._freq_map[freq]:
            del self._freq_map[freq]

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._freq_map.clear()
            self._key_freq.clear()
            self._min_freq = 0

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = []
            now = datetime.now()

            for key, entry in self._cache.items():
                if entry.expires_at and now > entry.expires_at:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_key(key)

            return len(expired_keys)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_access = sum(entry.access_count for entry in self._cache.values())
            avg_access = total_access / len(self._cache) if self._cache else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_access": total_access,
                "average_access": avg_access,
                "min_frequency": self._min_freq,
            }


def create_optimized_cache(strategy: str = "lru", max_size: int = 1000, default_ttl: int = 3600):
    """创建优化的缓存实例"""
    if strategy.lower() == "lru":
        return OptimizedLRUCache(max_size, default_ttl)
    elif strategy.lower() == "lfu":
        return OptimizedLFUCache(max_size, default_ttl)
    else:
        raise ValueError(f"Unsupported cache strategy: {strategy}")
