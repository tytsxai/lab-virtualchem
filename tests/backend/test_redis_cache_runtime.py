import pytest


class _FallbackCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ttl=None):
        self.data[key] = value
        return True

    def delete(self, key):
        return self.data.pop(key, None) is not None

    def exists(self, key):
        return key in self.data


class _RaisingRedis:
    def __init__(self):
        self.calls = []

    def get(self, *_a, **_k):
        raise RuntimeError("boom")

    def set(self, *_a, **_k):
        raise RuntimeError("boom")

    def setex(self, *_a, **_k):
        raise RuntimeError("boom")

    def delete(self, *_a, **_k):
        raise RuntimeError("boom")

    def exists(self, *_a, **_k):
        raise RuntimeError("boom")

    def incrby(self, *_a, **_k):
        raise RuntimeError("boom")

    def expire(self, *_a, **_k):
        raise RuntimeError("boom")


def test_redis_cache_fallback_path_when_unavailable():
    from src.backend.redis_cache import RedisCache

    cache = RedisCache.__new__(RedisCache)
    cache.available = False
    cache.prefix = "vcl:"
    cache._fallback = _FallbackCache()

    assert cache.get("k") is None
    assert cache.set("k", {"a": 1}) is True
    assert cache.get("k") == {"a": 1}
    assert cache.exists("k") is True
    assert cache.delete("k") is True


def test_redis_cache_handles_client_exceptions_gracefully(caplog):
    from src.backend.redis_cache import RedisCache

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.prefix = "vcl:"
    cache.client = _RaisingRedis()

    caplog.set_level("ERROR")
    assert cache.get("k") is None
    assert cache.set("k", 1, ttl=1) is False
    assert cache.delete("k") is False
    assert cache.exists("k") is False
    assert cache.incr("k") == 0
    assert cache.expire("k", 1) is False


def test_clear_pattern_empty_or_whitespace_is_noop():
    from src.backend.redis_cache import RedisCache

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.prefix = "vcl:"
    cache.client = object()
    cache.clear_allowed_prefixes = ("cache:",)

    assert cache.clear_pattern("") == 0
    assert cache.clear_pattern("   ") == 0


def test_global_redis_cache_helpers_smoke():
    import src.backend.redis_cache as rc

    rc._redis_cache = None
    cache1 = rc.get_redis_cache()
    cache2 = rc.get_redis_cache()
    assert cache1 is cache2

    cache3 = rc.init_redis_cache(host="localhost", port=6379)
    assert cache3 is rc.get_redis_cache()
