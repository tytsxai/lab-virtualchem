import pytest


def test_decorator_helpers_preview_truncate_and_hash():
    from src.backend.redis_cache import RedisCacheDecorator

    assert RedisCacheDecorator._safe_preview("abc", max_len=3) == "abc"
    assert RedisCacheDecorator._safe_preview("abcd", max_len=3) == "abc…"

    assert RedisCacheDecorator._truncate("abc", max_len=3) == "abc"
    assert RedisCacheDecorator._truncate("abcd", max_len=3) == "abc"

    digest = RedisCacheDecorator._hash_key("hello")
    assert isinstance(digest, str)
    assert len(digest) == 64
    # Deterministic
    assert digest == RedisCacheDecorator._hash_key("hello")


def test_cached_decorator_uses_key_builder_and_caches_result():
    from src.backend.redis_cache import RedisCacheDecorator

    class _InMemoryCache:
        def __init__(self):
            self._store = {}
            self.get_calls = []
            self.set_calls = []

        def get(self, key):
            self.get_calls.append(key)
            return self._store.get(key)

        def set(self, key, value, ttl=None):
            self.set_calls.append((key, value, ttl))
            self._store[key] = value
            return True

    cache = _InMemoryCache()
    decorator = RedisCacheDecorator(cache=cache)  # type: ignore[arg-type]

    def key_builder(x, y=0):
        # Include a deliberately long/sensitive raw key; decorator should hash it.
        return f"raw:{'S'*5000}:{x}:{y}"

    calls = {"n": 0}

    @decorator.cached(ttl=5, key_prefix="my_prefix", key_builder=key_builder)
    def add(x, y=0):
        calls["n"] += 1
        return x + y

    assert add(1, y=2) == 3
    assert add(1, y=2) == 3  # cache hit
    assert calls["n"] == 1

    assert cache.get_calls
    assert cache.set_calls
    for key in cache.get_calls:
        assert key.startswith("my_prefix:")
        assert len(key) <= 128


def test_clear_pattern_returns_zero_when_unlink_and_delete_unavailable():
    from src.backend.redis_cache import RedisCache

    class _NoDeleteNoUnlink:
        def scan(self, *args, **kwargs):  # pragma: no cover
            _ = (args, kwargs)
            return 0, []

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = _NoDeleteNoUnlink()
    cache.prefix = "vcl:"
    cache.clear_allowed_prefixes = ("cache:",)

    assert cache.clear_pattern("cache:*") == 0


def test_clear_pattern_handles_scan_exception_gracefully(caplog):
    from src.backend.redis_cache import RedisCache

    class _BadScan:
        def scan(self, *args, **kwargs):
            _ = (args, kwargs)
            raise RuntimeError("boom")

        def unlink(self, *keys):  # pragma: no cover
            _ = keys
            return 0

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = _BadScan()
    cache.prefix = "vcl:"
    cache.clear_allowed_prefixes = ("cache:",)

    caplog.set_level("ERROR")
    assert cache.clear_pattern("cache:*") == 0
    assert any("Redis模式删除失败" in r.getMessage() for r in caplog.records)


def test_health_check_false_on_ping_exception():
    from src.backend.redis_cache import RedisCache

    class _BadPing:
        def ping(self):
            raise RuntimeError("nope")

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = _BadPing()
    assert cache.health_check() is False


def test_health_check_true_when_ping_ok():
    from src.backend.redis_cache import RedisCache

    class _PingOk:
        def ping(self):
            return True

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = _PingOk()
    assert cache.health_check() is True


def test_incr_and_bulk_fallback_branches_are_covered():
    from src.backend.redis_cache import RedisCache

    class _FallbackCache:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ttl=None):
            _ = ttl
            self.data[key] = value
            return True

    cache = RedisCache.__new__(RedisCache)
    cache.available = False
    cache.prefix = "vcl:"
    cache._fallback = _FallbackCache()

    assert cache.incr("ctr", 3) == 3
    assert cache.incr("ctr", 2) == 5
    assert cache.expire("ctr", 10) is False
    assert cache.get_many(["a", "b"]) == {"a": None, "b": None}
    assert cache.set_many({"a": 1, "b": 2}, ttl=1) is True
    assert cache.get_many(["a", "b"]) == {"a": 1, "b": 2}
    assert cache.clear_pattern("cache:*") == 0


def test_get_many_and_set_many_exception_paths_return_safe_defaults(caplog):
    from src.backend.redis_cache import RedisCache

    class _BadRedis:
        def mget(self, *_a, **_k):
            raise RuntimeError("boom")

        def pipeline(self):
            raise RuntimeError("boom")

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = _BadRedis()
    cache.prefix = "vcl:"

    caplog.set_level("ERROR")
    assert cache.get_many(["a"]) == {}
    assert cache.set_many({"a": 1}) is False


def test_set_many_without_ttl_uses_set_operation():
    from src.backend.redis_cache import RedisCache

    class _Pipeline:
        def __init__(self):
            self.ops = []

        def set(self, key, value):
            self.ops.append(("set", key, value))
            return self

        def setex(self, key, ttl, value):  # pragma: no cover
            self.ops.append(("setex", key, ttl, value))
            return self

        def execute(self):
            return True

    class _Client:
        def __init__(self):
            self.pipeline_obj = _Pipeline()

        def pipeline(self):
            return self.pipeline_obj

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = _Client()
    cache.prefix = "vcl:"

    assert cache.set_many({"cache:a": 1}, ttl=None) is True
    assert cache.client.pipeline_obj.ops
    assert cache.client.pipeline_obj.ops[0][0] == "set"


def test_clear_pattern_delete_batches_when_unlink_missing():
    from src.backend.redis_cache import RedisCache

    class _FakeDeleteOnly:
        def __init__(self, keys):
            self._keys = list(keys)
            self.delete_calls = []

        def scan(self, cursor=0, match=None, count=None):
            _ = (match, count)
            if cursor != 0:
                return 0, []
            return 0, list(self._keys)

        def delete(self, *keys):
            self.delete_calls.append(list(keys))
            return len(keys)

    keys = [f"vcl:cache:{i}" for i in range(800)]
    client = _FakeDeleteOnly(keys)

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = client
    cache.prefix = "vcl:"
    cache.clear_allowed_prefixes = ("cache:",)

    assert cache.clear_pattern("cache:*") == 800
    assert client.delete_calls
    assert all(len(batch) <= 500 for batch in client.delete_calls)
    assert sum(len(batch) for batch in client.delete_calls) == 800


def test_import_without_redis_hits_fallback_constructor_path(monkeypatch):
    import builtins
    import importlib.util
    import types

    src_path = "src/backend/redis_cache/__init__.py"
    spec = importlib.util.spec_from_file_location("tmp_no_redis_cache", src_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "redis":
            raise ImportError("no redis")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Execute module under a temporary name; coverage still attributes by file path.
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    assert getattr(module, "REDIS_AVAILABLE") is False
    cache = module.RedisCache()  # type: ignore[attr-defined]
    assert cache.available is False
    assert cache.client is None


def test_constructor_success_path_and_deserialize_none(monkeypatch, caplog):
    import src.backend.redis_cache as rc

    class _RedisClient:
        def __init__(self, **_kwargs):
            pass

        def ping(self):
            return True

    monkeypatch.setattr(rc, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(rc, "redis", type("R", (), {"Redis": _RedisClient}))

    caplog.set_level("INFO")
    cache = rc.RedisCache()
    assert cache.available is True
    assert cache.client is not None

    # Cover _deserialize(None) branch explicitly.
    assert cache._deserialize(None) is None
