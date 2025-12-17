"""
智能缓存管理器
提供多级缓存、智能淘汰、缓存预热和分布式缓存支持
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .enhanced_observability import (
    LogLevel,
    get_observability,
    increment_counter,
    record_metric,
)
from .error_handler import get_error_handler

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""

    L1 = "l1"  # 内存缓存
    L2 = "l2"  # 磁盘缓存
    L3 = "l3"  # 分布式缓存


class EvictionPolicy(Enum):
    """淘汰策略"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用
    TTL = "ttl"  # 基于时间
    RANDOM = "random"  # 随机


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: float | None = None
    size: int = 0
    tags: dict[str, str] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def update_access(self) -> None:
        """更新访问信息"""
        self.accessed_at = time.time()
        self.access_count += 1

    def calculate_size(self) -> int:
        """计算大小"""
        try:
            serialized = json.dumps(self.value, ensure_ascii=False).encode("utf-8")
            self.size = len(serialized)
            return self.size
        except TypeError:
            # 非 JSON 可序列化对象：回退到字符串估算（仅用于统计/淘汰，不用于磁盘持久化）
            self.size = len(repr(self.value).encode("utf-8", errors="replace"))
            return self.size
        except Exception:
            self.size = 0
            return 0


@dataclass
class CacheStats:
    """缓存统计"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0

    def update_hit_rate(self) -> None:
        """更新命中率"""
        total = self.hits + self.misses
        self.hit_rate = self.hits / total if total > 0 else 0.0


class CacheBackend(ABC):
    """缓存后端接口"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """设置缓存"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    @abstractmethod
    def keys(self) -> list[str]:
        """获取所有键"""
        pass

    @abstractmethod
    def size(self) -> int:
        """获取缓存大小"""
        pass


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired():
                    del self._cache[key]
                    return None

                entry.update_access()
                return entry.value
            return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """设置缓存"""
        with self._lock:
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
            )
            entry.calculate_size()

            self._cache[key] = entry

            # 检查大小限制
            if len(self._cache) > self._max_size:
                self._evict_entries()

            return True

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def keys(self) -> list[str]:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

    def _evict_entries(self) -> None:
        """淘汰条目"""
        if not self._cache:
            return

        # 简单的LRU淘汰
        sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].accessed_at)

        # 淘汰最旧的10%
        evict_count = max(1, len(self._cache) // 10)
        for key, _ in sorted_entries[:evict_count]:
            del self._cache[key]


class DiskCacheBackend(CacheBackend):
    """磁盘缓存后端"""

    _KEY_NAMESPACE = "vcl.smart_cache_manager.disk_cache.v1:"

    def __init__(self, cache_dir: Path, max_size_mb: int = 100):
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = threading.RLock()

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用哈希避免文件名过长
        key_hash = hashlib.sha256(f"{self._KEY_NAMESPACE}{key}".encode()).hexdigest()
        return self._cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Any | None:
        """获取缓存"""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            created_at = float(data.get("created_at", 0.0))
            ttl = data.get("ttl")
            ttl_seconds = float(ttl) if ttl is not None else None

            if ttl_seconds is not None and time.time() - created_at > ttl_seconds:
                cache_path.unlink()
                return None

            return data.get("value")
        except Exception as e:
            logger.error(f"Failed to read cache file {cache_path}: {e}")
            # 旧格式或损坏文件，避免重复报错
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """设置缓存"""
        cache_path = self._get_cache_path(key)

        try:
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
            )
            entry.calculate_size()

            payload = {
                "key": entry.key,
                "value": entry.value,
                "created_at": entry.created_at,
                "accessed_at": entry.accessed_at,
                "access_count": entry.access_count,
                "ttl": entry.ttl,
                "tags": entry.tags,
            }

            cache_path.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            # 检查大小限制
            self._check_size_limit()

            return True
        except TypeError:
            # value 不可 JSON 序列化：跳过磁盘缓存（仍可由 L1 内存缓存承载）
            logger.debug("Disk cache skipped for non-JSON-serializable value: %s", key)
            return False
        except Exception as e:
            logger.error(f"Failed to write cache file {cache_path}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        cache_path = self._get_cache_path(key)

        try:
            if cache_path.exists():
                cache_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete cache file {cache_path}: {e}")
            return False

    def clear(self) -> None:
        """清空缓存"""
        try:
            for cache_file in self._cache_dir.glob("*.cache"):
                cache_file.unlink()
        except Exception as e:
            logger.error(f"Failed to clear cache directory: {e}")

    def keys(self) -> list[str]:
        """获取所有键"""
        keys = []
        try:
            for cache_file in self._cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        data = json.load(f)
                    key = data.get("key")
                    if isinstance(key, str):
                        keys.append(key)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Failed to list cache keys: {e}")

        return keys

    def size(self) -> int:
        """获取缓存大小"""
        try:
            return len(list(self._cache_dir.glob("*.cache")))
        except Exception:
            return 0

    def _check_size_limit(self) -> None:
        """检查大小限制"""
        try:
            total_size = sum(f.stat().st_size for f in self._cache_dir.glob("*.cache"))

            if total_size > self._max_size_bytes:
                self._evict_oldest_files()
        except Exception as e:
            logger.error(f"Failed to check size limit: {e}")

    def _evict_oldest_files(self) -> None:
        """淘汰最旧的文件"""
        try:
            files = []
            for cache_file in self._cache_dir.glob("*.cache"):
                stat = cache_file.stat()
                files.append((cache_file, stat.st_mtime))

            # 按修改时间排序
            files.sort(key=lambda x: x[1])

            # 删除最旧的20%
            evict_count = max(1, len(files) // 5)
            for cache_file, _ in files[:evict_count]:
                cache_file.unlink()
        except Exception as e:
            logger.error(f"Failed to evict oldest files: {e}")


class SmartCacheManager:
    """智能缓存管理器"""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._error_handler = get_error_handler()
        self._observability = get_observability()

        # 缓存后端
        self._backends: dict[CacheLevel, CacheBackend] = {}
        self._backend_order = [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]

        # 统计信息
        self._stats = CacheStats()

        # 缓存预热
        self._preload_functions: dict[str, Callable] = {}

        # 初始化后端
        self._setup_backends()

    def _setup_backends(self) -> None:
        """设置缓存后端"""
        # L1 内存缓存
        l1_size = self._config.get("l1_size", 1000)
        self._backends[CacheLevel.L1] = MemoryCacheBackend(l1_size)

        # L2 磁盘缓存
        cache_dir = Path(self._config.get("cache_dir", "cache"))
        l2_size_mb = self._config.get("l2_size_mb", 100)
        self._backends[CacheLevel.L2] = DiskCacheBackend(cache_dir, l2_size_mb)

        # L3 分布式缓存（可选）
        if self._config.get("enable_l3", False):
            # 这里可以集成Redis等分布式缓存
            pass

    def get(self, key: str) -> Any | None:
        """获取缓存"""
        # 按级别顺序查找
        for level in self._backend_order:
            if level in self._backends:
                value = self._backends[level].get(key)
                if value is not None:
                    # 缓存命中，更新统计
                    self._stats.hits += 1
                    self._stats.update_hit_rate()

                    # 记录指标
                    increment_counter("cache_hits", tags={"level": level.value})
                    record_metric("cache_hit_rate", self._stats.hit_rate)

                    # 记录日志
                    self._observability.log(
                        LogLevel.DEBUG,
                        f"Cache hit: {key}",
                        module="SmartCacheManager",
                        function="get",
                        extra_data={"level": level.value},
                    )

                    return value

        # 缓存未命中
        self._stats.misses += 1
        self._stats.update_hit_rate()

        # 记录指标
        increment_counter("cache_misses")
        record_metric("cache_hit_rate", self._stats.hit_rate)

        # 记录日志
        self._observability.log(
            LogLevel.DEBUG,
            f"Cache miss: {key}",
            module="SmartCacheManager",
            function="get",
        )

        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        levels: list[CacheLevel] | None = None,
    ) -> bool:
        """设置缓存"""
        if levels is None:
            levels = [CacheLevel.L1, CacheLevel.L2]

        attempted = 0
        success = False
        for level in levels:
            if level in self._backends:
                attempted += 1
                try:
                    result = self._backends[level].set(key, value, ttl)
                    if result:
                        success = True
                except Exception as e:
                    logger.error(f"Failed to set cache {key} at level {level}: {e}")
                    continue

        if attempted == 0:
            success = False

        # 记录指标
        increment_counter("cache_sets", tags={"success": str(success)})

        # 记录日志
        self._observability.log(
            LogLevel.DEBUG,
            f"Cache set: {key}",
            module="SmartCacheManager",
            function="set",
            extra_data={"levels": [lvl.value for lvl in levels], "success": success},
        )

        return success

    def delete(self, key: str) -> bool:
        """删除缓存"""
        success = True
        for level in self._backend_order:
            if level in self._backends:
                try:
                    result = self._backends[level].delete(key)
                    if not result:
                        success = False
                except Exception as e:
                    logger.error(f"Failed to delete cache {key} at level {level}: {e}")
                    success = False

        # 记录指标
        increment_counter("cache_deletes", tags={"success": str(success)})

        return success

    def clear(self) -> None:
        """清空缓存"""
        for backend in self._backends.values():
            try:
                backend.clear()
            except Exception as e:
                logger.error(f"Failed to clear cache backend: {e}")

        # 重置统计
        self._stats = CacheStats()

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: float | None = None,
        levels: list[CacheLevel] | None = None,
    ) -> Any:
        """获取或设置缓存"""
        value = self.get(key)
        if value is not None:
            return value

        # 缓存未命中，执行工厂函数
        try:
            value = factory()
            self.set(key, value, ttl, levels)
            return value
        except Exception as e:
            logger.error(f"Factory function failed for key {key}: {e}")
            raise

    def async_get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: float | None = None,
        levels: list[CacheLevel] | None = None,
    ) -> Any:
        """异步获取或设置缓存"""
        value = self.get(key)
        if value is not None:
            return value

        # 缓存未命中，执行工厂函数
        try:
            if asyncio.iscoroutinefunction(factory):
                value = asyncio.run(factory())
            else:
                value = factory()
            self.set(key, value, ttl, levels)
            return value
        except Exception as e:
            logger.error(f"Async factory function failed for key {key}: {e}")
            raise

    def register_preload_function(self, key: str, func: Callable) -> None:
        """注册预热函数"""
        self._preload_functions[key] = func

    def preload(self, keys: list[str] | None = None) -> None:
        """预热缓存"""
        if keys is None:
            keys = list(self._preload_functions.keys())

        for key in keys:
            if key in self._preload_functions:
                try:
                    func = self._preload_functions[key]
                    value = func()
                    self.set(key, value)

                    # 记录日志
                    self._observability.log(
                        LogLevel.INFO,
                        f"Cache preloaded: {key}",
                        module="SmartCacheManager",
                        function="preload",
                    )
                except Exception as e:
                    logger.error(f"Failed to preload cache {key}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_rate": self._stats.hit_rate,
            "evictions": self._stats.evictions,
            "backends": {},
        }

        for level, backend in self._backends.items():
            stats["backends"][level.value] = {
                "size": backend.size(),
                "keys": len(backend.keys()),
            }

        return stats

    def export_cache(self, output_dir: Path) -> None:
        """导出缓存"""
        output_dir.mkdir(exist_ok=True)

        # 导出统计信息
        stats_file = output_dir / "cache_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)

        # 导出缓存键
        keys_file = output_dir / "cache_keys.json"
        all_keys = {}
        for level, backend in self._backends.items():
            all_keys[level.value] = backend.keys()

        with open(keys_file, "w", encoding="utf-8") as f:
            json.dump(all_keys, f, indent=2, ensure_ascii=False)


# 全局智能缓存管理器实例
_global_cache_manager = SmartCacheManager()


def get_cache_manager() -> SmartCacheManager:
    """获取全局缓存管理器"""
    return _global_cache_manager


def cache_get(key: str) -> Any | None:
    """获取缓存"""
    return _global_cache_manager.get(key)


def cache_set(key: str, value: Any, ttl: float | None = None) -> bool:
    """设置缓存"""
    return _global_cache_manager.set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """删除缓存"""
    return _global_cache_manager.delete(key)


def cache_clear() -> None:
    """清空缓存"""
    _global_cache_manager.clear()


def cache_get_or_set(
    key: str, factory: Callable[[], Any], ttl: float | None = None
) -> Any:
    """获取或设置缓存"""
    return _global_cache_manager.get_or_set(key, factory, ttl)


def cache_preload(keys: list[str] | None = None) -> None:
    """预热缓存"""
    _global_cache_manager.preload(keys)
