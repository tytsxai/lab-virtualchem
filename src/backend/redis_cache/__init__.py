"""
Redis缓存实现
高性能分布式缓存，支持集群和哨兵模式
"""

import json
import logging
import hashlib
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
        serializer: str = "json",
        clear_allowed_prefixes: tuple[str, ...] = ("cache:",),
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
        self.serializer = serializer.lower().strip()
        self.clear_allowed_prefixes = tuple(p.strip() for p in clear_allowed_prefixes)
        if self.serializer != "json":
            raise ValueError(
                "RedisCache only supports JSON serialization. "
                "Pickle-based caching is intentionally disallowed for security."
            )
        self.available = REDIS_AVAILABLE

        if REDIS_AVAILABLE:
            try:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
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
        return json.dumps(value, ensure_ascii=False)

    def _deserialize(self, value: Any) -> Any:
        """反序列化值"""
        if value is None:
            return None

        return json.loads(value)

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
            return {
                k: self._deserialize(v)
                for k, v in zip(keys, values, strict=False)
                if v is not None
            }
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
            cleaned = (pattern or "").strip()
            if not cleaned:
                return 0

            # 限制可清理的前缀范围：仅允许显式声明的命名空间
            # 注意：pattern 传入的是“相对键”（不含 self.prefix）
            if not any(cleaned.startswith(p) for p in self.clear_allowed_prefixes):
                logger.warning("拒绝清理不在允许范围的前缀: %s", cleaned.split(":", 1)[0])
                return 0

            # 使用 SCAN 替代 KEYS，避免阻塞 Redis
            full_pattern = self._make_key(cleaned)

            total_deleted = 0
            cursor = 0
            pending: list[str] = []

            scan_count = 1000
            unlink_batch_size = 500

            unlink_func = getattr(self.client, "unlink", None)
            delete_func = getattr(self.client, "delete", None)
            if not callable(unlink_func) and not callable(delete_func):
                return 0

            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor, match=full_pattern, count=scan_count
                )
                if keys:
                    pending.extend(keys)

                while len(pending) >= unlink_batch_size:
                    batch = pending[:unlink_batch_size]
                    del pending[:unlink_batch_size]
                    if callable(unlink_func):
                        total_deleted += int(unlink_func(*batch) or 0)
                    else:
                        total_deleted += int(delete_func(*batch) or 0)

                if cursor == 0:
                    break

            if pending:
                if callable(unlink_func):
                    total_deleted += int(unlink_func(*pending) or 0)
                else:
                    total_deleted += int(delete_func(*pending) or 0)

            return total_deleted
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

    @staticmethod
    def _safe_preview(text: str, max_len: int = 32) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len] + "…"

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len]

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8", errors="replace")).hexdigest()

    def cached(
        self,
        ttl: int | None = None,
        key_prefix: str = "",
        key_builder: "Callable | None" = None,
    ):
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
                # 限制 key 的原始长度，避免日志/内存异常放大
                max_raw_key_length = 2048
                max_part_length = 256
                max_prefix_length = 64

                # 生成缓存键
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # 默认键生成
                    safe_prefix = (key_prefix or func.__name__).strip()
                    safe_prefix = self._truncate(safe_prefix, max_prefix_length)

                    key_parts: list[str] = [safe_prefix]
                    key_parts.extend(
                        self._truncate(str(arg), max_part_length) for arg in args
                    )
                    key_parts.extend(
                        self._truncate(f"{k}={v}", max_part_length)
                        for k, v in sorted(kwargs.items())
                    )
                    cache_key = ":".join(key_parts)

                cache_key = str(cache_key)
                cache_key = self._truncate(cache_key, max_raw_key_length)

                # 对 cache_key 做 hash 处理，避免泄露敏感信息 & 限制键长度
                digest = self._hash_key(cache_key)
                hashed_key = f"{(key_prefix or func.__name__)[:max_prefix_length]}:{digest}"
                hashed_key = self._truncate(hashed_key, 128)
                key_id = digest[:12]

                # 尝试从缓存获取
                cached_value = self.cache.get(hashed_key)
                if cached_value is not None:
                    logger.debug("缓存命中: %s", f"{(key_prefix or func.__name__)}:{key_id}")
                    return cached_value

                # 执行函数
                result = func(*args, **kwargs)

                # 存入缓存
                self.cache.set(hashed_key, result, ttl)
                logger.debug("缓存存入: %s", f"{(key_prefix or func.__name__)}:{key_id}")

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


if __name__ == "__main__":  # pragma: no cover
    # 演示使用
    logger.info("=== Redis缓存演示 ===\n")

    # 创建缓存
    cache = RedisCache(prefix="demo:")

    if cache.available:
        # 基本操作
        cache.set("key1", "value1", ttl=60)
        logger.info(f"获取: {cache.get('key1')}")

        # 批量操作
        cache.set_many(
            {
                "user:1": {"name": "Alice", "age": 25},
                "user:2": {"name": "Bob", "age": 30},
            }
        )

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
