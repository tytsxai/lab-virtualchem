"""
高级缓存系统

支持多种缓存策略和分布式缓存
"""

import asyncio
import hashlib
import json
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheStrategy(Enum):
    """缓存策略"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""

    key: str
    value: T
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: int | None = None  # 秒

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl

    def touch(self):
        """更新访问时间"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class ICache(ABC, Generic[T]):
    """缓存接口"""

    @abstractmethod
    def get(self, key: str) -> T | None:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """设置缓存值"""
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
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    def size(self) -> int:
        """获取缓存大小"""
        pass


class MemoryCache(ICache[T]):
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.strategy = strategy
        self._cache: dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> T | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                return None

            entry.touch()
            return entry.value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        with self._lock:
            # 如果缓存已满，执行淘汰策略
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict()

            self._cache[key] = CacheEntry(key=key, value=value, ttl=ttl)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            entry = self._cache[key]
            return not entry.is_expired()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def _evict(self) -> None:
        """执行缓存淘汰"""
        if not self._cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # 移除最少最近使用的
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        elif self.strategy == CacheStrategy.LFU:
            # 移除最少使用频率的
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
        elif self.strategy == CacheStrategy.FIFO:
            # 移除最早创建的
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        else:  # TTL
            # 移除最早过期的
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)

        del self._cache[oldest_key]


class DistributedCache(ICache[T]):
    """分布式缓存（Redis风格接口）"""

    def __init__(self, redis_client=None, prefix: str = "vcl:"):
        self.redis = redis_client
        self.prefix = prefix
        # 如果没有Redis，降级到本地缓存
        self.fallback = MemoryCache[T]() if redis_client is None else None

    def _make_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def get(self, key: str) -> T | None:
        if self.fallback:
            return self.fallback.get(key)

        value = self.redis.get(self._make_key(key))
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        if self.fallback:
            return self.fallback.set(key, value, ttl)

        serialized = json.dumps(value)
        if ttl:
            self.redis.setex(self._make_key(key), ttl, serialized)
        else:
            self.redis.set(self._make_key(key), serialized)

    def delete(self, key: str) -> bool:
        if self.fallback:
            return self.fallback.delete(key)

        return bool(self.redis.delete(self._make_key(key)))

    def clear(self) -> None:
        if self.fallback:
            return self.fallback.clear()

        pattern = f"{self.prefix}*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

    def exists(self, key: str) -> bool:
        if self.fallback:
            return self.fallback.exists(key)

        return bool(self.redis.exists(self._make_key(key)))

    def size(self) -> int:
        if self.fallback:
            return self.fallback.size()

        pattern = f"{self.prefix}*"
        return len(self.redis.keys(pattern))


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self._caches: dict[str, ICache] = {}
        self._default_cache = MemoryCache()

    def register(self, name: str, cache: ICache) -> None:
        """注册缓存"""
        self._caches[name] = cache

    def get_cache(self, name: str = "default") -> ICache:
        """获取缓存实例"""
        if name == "default":
            return self._default_cache
        return self._caches.get(name, self._default_cache)

    def clear_all(self) -> None:
        """清空所有缓存"""
        self._default_cache.clear()
        for cache in self._caches.values():
            cache.clear()


# 全局缓存管理器
_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    return _cache_manager


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: int | None = None, cache_name: str = "default", key_func: Callable | None = None):
    """缓存装饰器"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{cache_key(*args, **kwargs)}"

            # 尝试从缓存获取
            cache = get_cache_manager().get_cache(cache_name)
            result = cache.get(key)

            if result is not None:
                return result

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(key, result, ttl)

            return result

        return wrapper

    return decorator


def async_cached(ttl: int | None = None, cache_name: str = "default", key_func: Callable | None = None):
    """异步缓存装饰器"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{cache_key(*args, **kwargs)}"

            # 尝试从缓存获取
            cache = get_cache_manager().get_cache(cache_name)
            result = cache.get(key)

            if result is not None:
                return result

            # 执行异步函数
            result = await func(*args, **kwargs)

            # 存入缓存
            cache.set(key, result, ttl)

            return result

        return wrapper

    return decorator


class CacheWarmer:
    """缓存预热器"""

    def __init__(self, cache: ICache):
        self.cache = cache
        self._tasks: dict[str, Callable] = {}

    def register_task(self, name: str, task: Callable, keys: list) -> None:
        """注册预热任务"""
        self._tasks[name] = (task, keys)

    def warm(self, task_name: str | None = None) -> None:
        """执行预热"""
        tasks = [self._tasks[task_name]] if task_name else self._tasks.values()

        for task, keys in tasks:
            for key in keys:
                result = task(key)
                self.cache.set(key, result)

    async def async_warm(self, task_name: str | None = None) -> None:
        """异步预热"""
        tasks = [self._tasks[task_name]] if task_name else self._tasks.values()

        for task, keys in tasks:
            await asyncio.gather(*[self._warm_single(task, key) for key in keys])

    async def _warm_single(self, task: Callable, key: str) -> None:
        """预热单个键"""
        if asyncio.iscoroutinefunction(task):
            result = await task(key)
        else:
            result = task(key)
        self.cache.set(key, result)


class MultiLevelCache(ICache[T]):
    """多级缓存"""

    def __init__(self, *caches: ICache[T]):
        self.caches = list(caches)

    def get(self, key: str) -> T | None:
        for i, cache in enumerate(self.caches):
            value = cache.get(key)
            if value is not None:
                # 回填到更高级的缓存
                for upper_cache in self.caches[:i]:
                    upper_cache.set(key, value)
                return value
        return None

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        # 设置到所有级别
        for cache in self.caches:
            cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        deleted = False
        for cache in self.caches:
            if cache.delete(key):
                deleted = True
        return deleted

    def clear(self) -> None:
        for cache in self.caches:
            cache.clear()

    def exists(self, key: str) -> bool:
        return any(cache.exists(key) for cache in self.caches)

    def size(self) -> int:
        return self.caches[0].size() if self.caches else 0


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 缓存系统演示 ===\n")

    # 1. 基础缓存
    logger.info("1. 基础缓存:")
    cache = MemoryCache[str](max_size=3, strategy=CacheStrategy.LRU)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    logger.info(f"获取 key1: {cache.get('key1')}")
    logger.info(f"缓存大小: {cache.size()}\n")

    # 2. TTL缓存
    logger.info("2. TTL缓存:")
    cache.set("expire_key", "expire_value", ttl=2)
    logger.info(f"立即获取: {cache.get('expire_key')}")
    import time

    time.sleep(3)
    logger.info(f"3秒后获取: {cache.get('expire_key')}\n")

    # 3. 缓存装饰器
    logger.info("3. 缓存装饰器:")

    @cached(ttl=60)
    def expensive_function(x: int) -> int:
        logger.info(f"  执行计算: {x}")
        return x * x

    logger.info(f"第一次调用: {expensive_function(5)}")
    logger.info(f"第二次调用: {expensive_function(5)}")  # 从缓存读取
    logger.info(f"不同参数: {expensive_function(6)}\n")

    # 4. 多级缓存
    logger.info("4. 多级缓存:")
    l1 = MemoryCache[str](max_size=10)
    l2 = MemoryCache[str](max_size=100)
    multi_cache = MultiLevelCache(l1, l2)

    multi_cache.set("test", "value")
    logger.info(f"多级缓存获取: {multi_cache.get('test')}")
