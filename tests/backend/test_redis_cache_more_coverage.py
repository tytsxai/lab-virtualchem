import pytest


class _Pipeline:
    def __init__(self, client):
        self.client = client
        self.ops = []

    def set(self, key, value):
        self.ops.append(("set", key, value))
        return self

    def setex(self, key, ttl, value):
        self.ops.append(("setex", key, ttl, value))
        return self

    def execute(self):
        for op in self.ops:
            if op[0] == "set":
                _, key, value = op
                self.client._data[key] = value
            else:
                _, key, _ttl, value = op
                self.client._data[key] = value
        self.ops.clear()
        return True


class _FakeRedis:
    def __init__(self):
        self._data = {}
        self._scans = []

    def ping(self):
        return True

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
        return True

    def setex(self, key, ttl, value):
        _ = ttl
        self._data[key] = value
        return True

    def delete(self, *keys):
        deleted = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                deleted += 1
        return deleted

    def exists(self, key):
        return 1 if key in self._data else 0

    def incrby(self, key, amount):
        current = int(self._data.get(key, "0"))
        current += amount
        self._data[key] = str(current)
        return current

    def expire(self, key, ttl):
        _ = (key, ttl)
        return True

    def mget(self, keys):
        return [self._data.get(k) for k in keys]

    def pipeline(self):
        return _Pipeline(self)

    def scan(self, cursor=0, match=None, count=None):
        self._scans.append((cursor, match, count))
        # one-page scan
        keys = [k for k in self._data.keys() if match is None or k.startswith(match[:-1])]
        return 0, keys


def test_redis_cache_roundtrip_and_bulk_operations():
    from src.backend.redis_cache import RedisCache

    fake = _FakeRedis()
    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = fake
    cache.prefix = "vcl:"
    cache.clear_allowed_prefixes = ("cache:",)

    assert cache.set("cache:k1", {"x": 1}) is True
    assert cache.get("cache:k1") == {"x": 1}
    assert cache.exists("cache:k1") is True
    assert cache.incr("cache:ctr", 2) == 2
    assert cache.expire("cache:k1", 10) is True
    assert cache.delete("cache:k1") is True

    assert cache.set_many({"cache:a": 1, "cache:b": 2}, ttl=5) is True
    got = cache.get_many(["cache:a", "cache:b", "cache:missing"])
    assert got == {"cache:a": 1, "cache:b": 2}


def test_clear_pattern_falls_back_to_delete_when_unlink_missing():
    from src.backend.redis_cache import RedisCache

    fake = _FakeRedis()
    fake._data["vcl:cache:1"] = "1"
    fake._data["vcl:cache:2"] = "2"
    # remove unlink attribute if present
    if hasattr(fake, "unlink"):
        delattr(fake, "unlink")

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = fake
    cache.prefix = "vcl:"
    cache.clear_allowed_prefixes = ("cache:",)

    assert cache.clear_pattern("cache:*") == 2


def test_init_path_redis_available_but_connect_fails(monkeypatch):
    # Cover the constructor branch where redis is installed but connection fails.
    import src.backend.redis_cache as rc

    class _RedisFactory:
        def __init__(self, **_kwargs):
            pass

        def ping(self):
            raise RuntimeError("no server")

    monkeypatch.setattr(rc, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(rc, "redis", type("R", (), {"Redis": _RedisFactory}))

    cache = rc.RedisCache()
    assert cache.available is False


def test_health_check_false_when_unavailable():
    from src.backend.redis_cache import RedisCache

    cache = RedisCache.__new__(RedisCache)
    cache.available = False
    assert cache.health_check() is False
