"""
智能缓存系统
提供高效的缓存机制，支持LRU淘汰策略和自动过期
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar

from ..utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class SmartCache:
    """智能缓存类"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认生存时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # 检查是否过期
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            del self._cache[key]
            self._misses += 1
            return None

        # 移动到末尾（LRU）
        self._cache.move_to_end(key)
        self._hits += 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl

        expires_at = time.time() + ttl if ttl > 0 else None

        # 如果键已存在，先删除
        if key in self._cache:
            del self._cache[key]

        # 添加新条目
        self._cache[key] = {"value": value, "expires_at": expires_at, "created_at": time.time()}

        # 检查是否需要淘汰
        self._evict_if_needed()

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_or_set(self, key: str, factory: Callable[[], T], ttl: int | None = None) -> T:
        """
        获取缓存值，如果不存在则调用工厂函数生成

        Args:
            key: 缓存键
            factory: 工厂函数
            ttl: 生存时间（秒）

        Returns:
            缓存值或工厂函数生成的值
        """
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value, ttl)
        return value

    def _evict_if_needed(self) -> None:
        """如果需要，淘汰最旧的条目"""
        while len(self._cache) > self.max_size:
            # 删除最旧的条目（第一个）
            self._cache.popitem(last=False)

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            if entry["expires_at"] and current_time > entry["expires_at"]:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        return key in self._cache


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self._caches: dict[str, SmartCache] = {}

    def get_cache(self, name: str, max_size: int = 1000, default_ttl: int = 3600) -> SmartCache:
        """
        获取或创建缓存

        Args:
            name: 缓存名称
            max_size: 最大大小
            default_ttl: 默认生存时间

        Returns:
            缓存实例
        """
        if name not in self._caches:
            self._caches[name] = SmartCache(max_size, default_ttl)
        return self._caches[name]

    def clear_all(self) -> None:
        """清空所有缓存"""
        for cache in self._caches.values():
            cache.clear()

    def cleanup_all(self) -> int:
        """
        清理所有缓存中的过期条目

        Returns:
            总清理的条目数
        """
        total_cleaned = 0
        for cache in self._caches.values():
            total_cleaned += cache.cleanup_expired()
        return total_cleaned

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """获取所有缓存的统计信息"""
        return {name: cache.get_stats() for name, cache in self._caches.items()}


# 全局缓存管理器实例
_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    return _cache_manager


def cached(ttl: int = 3600, cache_name: str = "default"):
    """
    缓存装饰器

    Args:
        ttl: 缓存生存时间（秒）
        cache_name: 缓存名称

    Example:
        @cached(ttl=1800)
        def expensive_function(param1, param2):
            # 昂贵的计算
            return result
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = get_cache_manager().get_cache(cache_name)

        def wrapper(*args, **kwargs) -> T:
            # 生成缓存键
            key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            return cache.get_or_set(key, lambda: func(*args, **kwargs), ttl)

        return wrapper

    return decorator


class TemplateCache:
    """模板缓存"""

    def __init__(self, cache_size: int = 100):
        self.cache = SmartCache(cache_size, default_ttl=1800)  # 30分钟

    def get_template(self, template_id: str) -> Any | None:
        """获取模板"""
        return self.cache.get(f"template:{template_id}")

    def set_template(self, template_id: str, template: Any) -> None:
        """设置模板"""
        self.cache.set(f"template:{template_id}", template)

    def invalidate_template(self, template_id: str) -> None:
        """使模板缓存失效"""
        self.cache.delete(f"template:{template_id}")

    def clear(self) -> None:
        """清空模板缓存"""
        self.cache.clear()


class ExperimentCache:
    """实验缓存"""

    def __init__(self, cache_size: int = 200):
        self.cache = SmartCache(cache_size, default_ttl=900)  # 15分钟

    def _build_key(self, base: str, namespace: str | None = None) -> str:
        return f"{base}:{namespace}" if namespace else base

    def get_experiment_list(self, namespace: str | None = None) -> list | None:
        """获取实验列表"""
        return self.cache.get(self._build_key("experiment_list", namespace))

    def set_experiment_list(self, experiments: list, namespace: str | None = None) -> None:
        """设置实验列表"""
        self.cache.set(self._build_key("experiment_list", namespace), experiments)

    def get_experiment(self, experiment_id: str) -> Any | None:
        """获取单个实验"""
        return self.cache.get(f"experiment:{experiment_id}")

    def set_experiment(self, experiment_id: str, experiment: Any) -> None:
        """设置单个实验"""
        self.cache.set(f"experiment:{experiment_id}", experiment)

    def invalidate_experiment(self, experiment_id: str) -> None:
        """使实验缓存失效"""
        self.cache.delete(f"experiment:{experiment_id}")
        # 同时使所有实验列表缓存失效（不同模板目录隔离）
        for key in list(self.cache._cache.keys()):
            if key.startswith("experiment_list"):
                self.cache.delete(key)

    def clear(self) -> None:
        """清空实验缓存"""
        self.cache.clear()


# 全局缓存实例
template_cache = TemplateCache()
experiment_cache = ExperimentCache()
