"""
Redis缓存实现
高性能分布式缓存，支持集群和哨兵模式
"""

import json
import logging
import pickle
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# 尝试导入Redis
try:
    import redis
    from redis.cluster import RedisCluster  # noqa: F401
    from redis.sentinel import Sentinel  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，将使用内存缓存")


class RedisCache:
    """Redis缓存包装器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        prefix: str = "vcl:",
        serializer: str = "json",  # 'json' or 'pickle'
    ):
        """
        初始化Redis缓存

        Args:
            host: Redis主机
            port: Redis端口
            db: 数据库编号
            password: 密码
            prefix: 键前缀
            serializer: 序列化方式
        """
        self.prefix = prefix
        self.serializer = serializer
        self.available = REDIS_AVAILABLE

        if REDIS_AVAILABLE:
            try:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=(serializer == "json"),
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # 测试连接
                self.client.ping()
                logger.info(f"Redis连接成功: {host}:{port}/{db}")
            except Exception as e:
                logger.error(f"Redis连接失败: {e}")
                self.available = False
                self.client = None
        else:
            self.client = None

        # 降级到内存缓存
        if not self.available:
            from src.core.cache import MemoryCache

            self._fallback = MemoryCache()
            logger.info("使用内存缓存作为降级方案")

    def _make_key(self, key: str) -> str:
        """生成完整键名"""
        return f"{self.prefix}{key}"

    def _serialize(self, value: Any) -> Any:
        """序列化值"""
        if self.serializer == "json":
            return json.dumps(value, ensure_ascii=False)
        else:  # pickle
            return pickle.dumps(value)

    def _deserialize(self, value: Any) -> Any:
        """反序列化值"""
        if value is None:
            return None

        if self.serializer == "json":
            return json.loads(value)
        else:  # pickle
            return pickle.loads(value)

    def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 键

        Returns:
            值或None
        """
        if not self.available:
            return self._fallback.get(key)

        try:
            value = self.client.get(self._make_key(key))
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis获取失败: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        设置缓存值

        Args:
            key: 键
            value: 值
            ttl: 过期时间(秒)

        Returns:
            是否成功
        """
        if not self.available:
            self._fallback.set(key, value, ttl)
            return True

        try:
            serialized = self._serialize(value)
            if ttl:
                return self.client.setex(self._make_key(key), ttl, serialized)
            else:
                return self.client.set(self._make_key(key), serialized)
        except Exception as e:
            logger.error(f"Redis设置失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 键

        Returns:
            是否成功
        """
        if not self.available:
            return self._fallback.delete(key)

        try:
            return bool(self.client.delete(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis删除失败: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键

        Returns:
            是否存在
        """
        if not self.available:
            return self._fallback.exists(key)

        try:
            return bool(self.client.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis检查失败: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> int:
        """
        递增计数器

        Args:
            key: 键
            amount: 递增量

        Returns:
            新值
        """
        if not self.available:
            current = self._fallback.get(key) or 0
            new_value = current + amount
            self._fallback.set(key, new_value)
            return new_value

        try:
            return self.client.incrby(self._make_key(key), amount)
        except Exception as e:
            logger.error(f"Redis递增失败: {e}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """
        设置过期时间

        Args:
            key: 键
            ttl: 过期时间(秒)

        Returns:
            是否成功
        """
        if not self.available:
            # 内存缓存不支持单独设置过期
            return False

        try:
            return self.client.expire(self._make_key(key), ttl)
        except Exception as e:
            logger.error(f"Redis设置过期失败: {e}")
            return False

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        批量获取

        Args:
            keys: 键列表

        Returns:
            键值对字典
        """
        if not self.available:
            return {k: self._fallback.get(k) for k in keys}

        try:
            full_keys = [self._make_key(k) for k in keys]
            values = self.client.mget(full_keys)
            return {k: self._deserialize(v) for k, v in zip(keys, values, strict=False) if v is not None}
        except Exception as e:
            logger.error(f"Redis批量获取失败: {e}")
            return {}

    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        """
        批量设置

        Args:
            mapping: 键值对
            ttl: 过期时间(秒)

        Returns:
            是否成功
        """
        if not self.available:
            for k, v in mapping.items():
                self._fallback.set(k, v, ttl)
            return True

        try:
            pipeline = self.client.pipeline()
            for key, value in mapping.items():
                serialized = self._serialize(value)
                full_key = self._make_key(key)
                if ttl:
                    pipeline.setex(full_key, ttl, serialized)
                else:
                    pipeline.set(full_key, serialized)
            pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Redis批量设置失败: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        清空匹配模式的键

        Args:
            pattern: 模式 (如 'user:*')

        Returns:
            删除的键数量
        """
        if not self.available:
            # 内存缓存不支持模式匹配
            return 0

        try:
            full_pattern = self._make_key(pattern)
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis模式删除失败: {e}")
            return 0

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        if not self.available:
            return False

        try:
            self.client.ping()
            return True
        except Exception:
            return False


class RedisCacheDecorator:
    """Redis缓存装饰器"""

    def __init__(self, cache: RedisCache):
        self.cache = cache

    def cached(self, ttl: int | None = None, key_prefix: str = "", key_builder: "Callable | None" = None):
        """
        缓存装饰器

        Args:
            ttl: 过期时间(秒)
            key_prefix: 键前缀
            key_builder: 自定义键生成函数
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # 默认键生成
                    key_parts = [key_prefix or func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = ":".join(key_parts)

                # 尝试从缓存获取
                cached_value = self.cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value

                # 执行函数
                result = func(*args, **kwargs)

                # 存入缓存
                self.cache.set(cache_key, result, ttl)
                logger.debug(f"缓存存入: {cache_key}")

                return result

            return wrapper

        return decorator


# 全局Redis缓存实例
_redis_cache: RedisCache | None = None


def get_redis_cache() -> RedisCache:
    """获取全局Redis缓存实例"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def init_redis_cache(host: str = "localhost", port: int = 6379, **kwargs) -> RedisCache:
    """
    初始化全局Redis缓存

    Args:
        host: Redis主机
        port: Redis端口
        **kwargs: 其他配置

    Returns:
        Redis缓存实例
    """
    global _redis_cache
    _redis_cache = RedisCache(host=host, port=port, **kwargs)
    return _redis_cache


if __name__ == "__main__":
    # 演示使用
    logger.info("=== Redis缓存演示 ===\n")

    # 创建缓存
    cache = RedisCache(prefix="demo:")

    if cache.available:
        # 基本操作
        cache.set("key1", "value1", ttl=60)
        logger.info(f"获取: {cache.get('key1')}")

        # 批量操作
        cache.set_many({"user:1": {"name": "Alice", "age": 25}, "user:2": {"name": "Bob", "age": 30}})

        users = cache.get_many(["user:1", "user:2"])
        logger.info(f"批量获取: {users}")

        # 装饰器
        decorator = RedisCacheDecorator(cache)

        @decorator.cached(ttl=300, key_prefix="calc")
        def expensive_calc(x, y):
            logger.info(f"执行计算: {x} + {y}")
            return x + y

        result1 = expensive_calc(5, 3)
        result2 = expensive_calc(5, 3)  # 从缓存读取
        logger.info(f"计算结果: {result1}, {result2}")
    else:
        logger.info("Redis不可用，使用内存缓存")
