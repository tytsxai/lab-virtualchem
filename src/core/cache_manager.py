import hashlib
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

"""智能缓存管理器"""

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: datetime
    expires_at: datetime | None
    access_count: int = 0
    last_accessed: datetime | None = None
    size_bytes: int = 0

    def __post_init__(self):
        pass


class CacheStrategy:
    """缓存策略枚举"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用
    FIFO = "fifo"  # 先进先出
    TTL = "ttl"  # 基于时间


class CacheManager:
    """智能缓存管理器"""

    def __init__(
        self,
        max_size: int = 1000,  # 适中的默认大小
        default_ttl: int = 3600,
        strategy: str = CacheStrategy.LRU,
        use_redis: bool = False,
        redis_config: dict | None = None,
        max_memory_mb: int = 100,  # 最大内存使用限制
        ttl: int | None = None,
        redis_url: str | None = None,
    ):
        """初始化缓存管理器

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认生存时间（秒）
            strategy: 缓存策略
            use_redis: 是否使用Redis
            redis_config: Redis配置
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")

        valid_strategies = {
            CacheStrategy.LRU,
            CacheStrategy.LFU,
            CacheStrategy.FIFO,
            CacheStrategy.TTL,
        }
        if strategy not in valid_strategies:
            raise ValueError("Invalid cache strategy")

        if ttl is not None:
            if ttl < 0:
                raise ValueError("ttl must be non-negative")
            default_ttl = ttl

        self.max_size = max_size
        self.default_ttl = default_ttl
        self.ttl = default_ttl
        self.strategy = strategy
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.max_memory_mb = max_memory_mb

        # 内存缓存
        self.cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # 内存使用跟踪
        self._current_memory_mb = 0.0

        # Redis连接
        self.redis_client = None
        if self.use_redis and redis is not None:
            try:
                base_config = {"decode_responses": True}
                if redis_url:
                    config = {"url": redis_url} | (redis_config or {})
                else:
                    config = redis_config or {
                        "host": "localhost",
                        "port": 6379,
                        "db": 0,
                    }
                config = base_config | config
                self.redis_client = redis.Redis(**config)
                # 测试连接
                self.redis_client.ping()
                logger.info("Redis连接成功")
            except Exception as e:
                logger.warning(f"Redis连接失败，回退到内存缓存: {e}")
                self.use_redis = False
                self.redis_client = None

        # 统计信息
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "size": 0}

        logger.info(f"缓存管理器已初始化 (策略: {strategy}, Redis: {self.use_redis})")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 清理资源"""
        self.close()

    def close(self):
        """关闭缓存管理器，清理资源"""
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis连接已关闭")
            except Exception as e:
                logger.warning(f"关闭Redis连接失败: {e}")
            finally:
                self.redis_client = None
                self.use_redis = False

        # 清理内存缓存
        self.cache.clear()
        self.stats.clear()
        logger.info("缓存管理器资源已清理")

    def _generate_key(self, key: str | tuple | dict) -> str:
        """生成缓存键

        Args:
            key: 原始键

        Returns:
            生成的键
        """
        if isinstance(key, str):
            return key
        elif isinstance(key, (tuple, list)):
            return hashlib.sha256(str(key).encode()).hexdigest()
        elif isinstance(key, dict):
            return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
        else:
            return str(key)

    def _serialize_value(self, value: Any) -> str:
        """序列化值

        Args:
            value: 要序列化的值

        Returns:
            序列化后的字符串
        """
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"序列化失败: {e}")
            return str(value)

    def _deserialize_value(self, value: str) -> Any:
        """反序列化值

        Args:
            value: 序列化后的字符串

        Returns:
            反序列化后的值
        """
        try:
            return json.loads(value)
        except Exception:
            return value

    def _calculate_size(self, value: Any) -> int:
        """计算值的大小

        Args:
            value: 值

        Returns:
            大小（字节）
        """
        try:
            return len(self._serialize_value(value).encode("utf-8"))
        except Exception:
            return 0

    def _is_expired(self, entry: CacheEntry) -> bool:
        """检查条目是否过期

        Args:
            entry: 缓存条目

        Returns:
            是否过期
        """
        if entry.expires_at is None:
            return False
        return datetime.now() > entry.expires_at

    def _evict_entry(self) -> str | None:
        """根据策略驱逐条目（优化版本）

        Returns:
            被驱逐的键
        """
        if not self.cache:
            return None

        # 使用更高效的算法
        if self.strategy == CacheStrategy.LRU:
            # 最近最少使用 - O(n) 查找
            oldest_time = None
            key_to_evict = None
            for key, entry in self.cache.items():
                access_time = entry.last_accessed or entry.created_at
                if oldest_time is None or access_time < oldest_time:
                    oldest_time = access_time
                    key_to_evict = key
        elif self.strategy == CacheStrategy.LFU:
            # 最少使用 - O(n) 查找
            min_count = float("inf")
            key_to_evict = None
            for key, entry in self.cache.items():
                if entry.access_count < min_count:
                    min_count = entry.access_count
                    key_to_evict = key
        elif self.strategy == CacheStrategy.FIFO:
            # 先进先出 - O(n) 查找
            oldest_time = None
            key_to_evict = None
            for key, entry in self.cache.items():
                if oldest_time is None or entry.created_at < oldest_time:
                    oldest_time = entry.created_at
                    key_to_evict = key
        else:  # TTL
            # 基于时间，驱逐最旧的
            oldest_time = None
            key_to_evict = None
            for key, entry in self.cache.items():
                if oldest_time is None or entry.created_at < oldest_time:
                    oldest_time = entry.created_at
                    key_to_evict = key

        return key_to_evict

    def _force_cleanup(self) -> None:
        """强制清理缓存以释放内存"""
        try:
            # 清理过期条目
            self.cleanup_expired()

            # 如果内存仍然超限，清理最旧的条目
            while self._current_memory_mb > self.max_memory_mb * 0.8 and self.cache:
                key_to_evict = self._evict_entry()
                if key_to_evict:
                    evicted_entry = self.cache[key_to_evict]
                    self._current_memory_mb -= evicted_entry.size_bytes / (1024 * 1024)
                    del self.cache[key_to_evict]
                    self.stats["evictions"] += 1
                else:
                    break

            logger.debug(
                f"强制清理完成，当前内存使用: {self._current_memory_mb:.2f} MB"
            )

        except Exception as e:
            logger.error(f"强制清理失败: {e}")

    def get(self, key: str | tuple | dict) -> Any | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        cache_key = self._generate_key(key)

        with self._lock:
            # 先检查内存缓存
            if cache_key in self.cache:
                entry = self.cache[cache_key]

                # 检查是否过期
                if self._is_expired(entry):
                    del self.cache[cache_key]
                    self.stats["misses"] += 1
                    return None

                # 更新访问信息
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self.stats["hits"] += 1

                return entry.value

            # 检查Redis缓存
            if self.use_redis and self.redis_client:
                try:
                    redis_value = self.redis_client.get(f"cache:{cache_key}")
                    if redis_value:
                        value = self._deserialize_value(redis_value)
                        self.stats["hits"] += 1
                        return value
                except Exception as e:
                    logger.error(f"Redis读取失败: {e}")

            self.stats["misses"] += 1
            return None

    def set(self, key: str | tuple | dict, value: Any, ttl: int | None = None) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
        """
        cache_key = self._generate_key(key)
        ttl = ttl if ttl is not None else self.ttl

        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
        size_bytes = self._calculate_size(value)

        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            size_bytes=size_bytes,
        )

        with self._lock:
            # 检查内存使用限制
            new_memory_mb = (self._current_memory_mb * 1024 * 1024 + size_bytes) / (
                1024 * 1024
            )
            if new_memory_mb > self.max_memory_mb and cache_key not in self.cache:
                # 内存超限，强制清理
                self._force_cleanup()

            # 检查缓存大小
            if len(self.cache) >= self.max_size and cache_key not in self.cache:
                key_to_evict = self._evict_entry()
                if key_to_evict:
                    evicted_entry = self.cache[key_to_evict]
                    self._current_memory_mb -= evicted_entry.size_bytes / (1024 * 1024)
                    del self.cache[key_to_evict]
                    self.stats["evictions"] += 1

            # 更新内存使用
            if cache_key in self.cache:
                old_entry = self.cache[cache_key]
                self._current_memory_mb -= old_entry.size_bytes / (1024 * 1024)

            self._current_memory_mb += size_bytes / (1024 * 1024)

            # 设置内存缓存
            self.cache[cache_key] = entry

            # 设置Redis缓存
            if self.use_redis and self.redis_client:
                try:
                    serialized_value = self._serialize_value(value)
                    self.redis_client.setex(f"cache:{cache_key}", ttl, serialized_value)
                except Exception as e:
                    logger.error(f"Redis写入失败: {e}")

            self.stats["size"] = len(self.cache)

    def delete(self, key: str | tuple | dict) -> bool:
        """删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        cache_key = self._generate_key(key)

        with self._lock:
            deleted = False

            # 删除内存缓存
            if cache_key in self.cache:
                entry = self.cache[cache_key]
                self._current_memory_mb -= entry.size_bytes / (1024 * 1024)
                del self.cache[cache_key]
                deleted = True

            # 删除Redis缓存
            if self.use_redis and self.redis_client:
                try:
                    self.redis_client.delete(f"cache:{cache_key}")
                except Exception as e:
                    logger.error(f"Redis删除失败: {e}")

            if deleted:
                self.stats["size"] = len(self.cache)

            return deleted

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self._current_memory_mb = 0.0

            if self.use_redis and self.redis_client:
                try:
                    # 删除所有缓存键
                    keys = self.redis_client.keys("cache:*")
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.error(f"Redis清空失败: {e}")

            self.stats["size"] = 0

    def cleanup_expired(self) -> int:
        """清理过期条目

        Returns:
            清理的条目数量
        """
        with self._lock:
            expired_keys = []

            for key, entry in self.cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)

            for key in expired_keys:
                entry = self.cache[key]
                self._current_memory_mb -= entry.size_bytes / (1024 * 1024)
                del self.cache[key]

            if expired_keys:
                self.stats["size"] = len(self.cache)
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")

            return len(expired_keys)

    def get_statistics(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息
        """
        with self._lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                "size": self.stats["size"],
                "max_size": self.max_size,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self.stats["evictions"],
                "strategy": self.strategy,
                "use_redis": self.use_redis,
            }

    def warm_up(self, data: dict[str, Any]) -> None:
        """预热缓存

        Args:
            data: 要预热的数据
        """
        logger.info(f"开始预热缓存，数据量: {len(data)}")

        for key, value in data.items():
            self.set(key, value)

        logger.info("缓存预热完成")

    def get_memory_usage(self) -> dict[str, Any]:
        """获取内存使用情况

        Returns:
            内存使用信息
        """
        with self._lock:
            total_size = sum(entry.size_bytes for entry in self.cache.values())

            return {
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "entry_count": len(self.cache),
                "average_entry_size": total_size / len(self.cache) if self.cache else 0,
            }

    def get_stats(self) -> dict[str, Any]:
        """获取综合统计信息"""
        stats = self.get_statistics()
        memory = self.get_memory_usage()
        stats["memory_usage_mb"] = memory["total_size_mb"]
        return stats


# 全局缓存管理器（线程安全）
_cache_manager: CacheManager | None = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器（线程安全）"""
    global _cache_manager
    if _cache_manager is None:
        with _cache_manager_lock:
            if _cache_manager is None:  # 双重检查锁
                _cache_manager = CacheManager()
    return _cache_manager


def close_cache_manager():
    """关闭全局缓存管理器"""
    global _cache_manager
    if _cache_manager is not None:
        with _cache_manager_lock:
            if _cache_manager is not None:
                _cache_manager.close()
                _cache_manager = None


# 向后兼容的别名
cache_manager = get_cache_manager()


def cached(ttl: int | None = None, key_func: Callable | None = None):
    """缓存装饰器

    Args:
        ttl: 生存时间（秒）
        key_func: 自定义键生成函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))

            # 尝试从缓存获取
            manager = get_cache_manager()
            result = manager.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            manager.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def cache_invalidate(pattern: str | None = None):
    """缓存失效装饰器

    Args:
        pattern: 失效模式
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # 清空相关缓存
            manager = get_cache_manager()
            if pattern:
                # 这里可以实现基于模式的缓存失效
                pass
            else:
                manager.clear()

            return result

        return wrapper

    return decorator


class CacheMiddleware:
    """缓存中间件"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    def process_request(self, request_data: dict[str, Any]) -> Any | None:
        """处理请求，检查缓存

        Args:
            request_data: 请求数据

        Returns:
            缓存的结果或None
        """
        cache_key = f"request:{hashlib.sha256(str(request_data).encode()).hexdigest()}"
        return self.cache_manager.get(cache_key)

    def process_response(
        self, request_data: dict[str, Any], response_data: Any, ttl: int = 300
    ) -> None:
        """处理响应，缓存结果

        Args:
            request_data: 请求数据
            response_data: 响应数据
            ttl: 缓存时间
        """
        cache_key = f"request:{hashlib.sha256(str(request_data).encode()).hexdigest()}"
        self.cache_manager.set(cache_key, response_data, ttl)


# 全局缓存中间件
cache_middleware = CacheMiddleware(get_cache_manager())
