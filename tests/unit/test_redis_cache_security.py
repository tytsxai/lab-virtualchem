import pytest


def test_redis_cache_disallows_pickle_serializer():
    from src.backend.redis_cache import RedisCache

    with pytest.raises(ValueError):
        RedisCache(serializer="pickle")

    with pytest.raises(ValueError):
        RedisCache(serializer=" Pickle ")


class _FakeRedisClient:
    def __init__(self, scan_pages: list[list[str]]):
        self._scan_pages = scan_pages
        self._scan_calls: list[tuple[int, str | None, int | None]] = []
        self.unlink_calls: list[list[str]] = []
        self.delete_calls: list[list[str]] = []

    def keys(self, *_args, **_kwargs):  # pragma: no cover
        raise AssertionError("clear_pattern() should not use KEYS")

    def scan(self, cursor=0, match=None, count=None):
        self._scan_calls.append((int(cursor), match, count))
        if cursor == 0:
            if not self._scan_pages:
                return 0, []
            next_cursor = 1 if len(self._scan_pages) > 1 else 0
            return next_cursor, self._scan_pages[0]
        page_index = cursor
        if page_index >= len(self._scan_pages):
            return 0, []
        next_cursor = page_index + 1
        if next_cursor >= len(self._scan_pages):
            next_cursor = 0
        return next_cursor, self._scan_pages[page_index]

    def unlink(self, *keys):
        self.unlink_calls.append(list(keys))
        return len(keys)

    def delete(self, *keys):
        self.delete_calls.append(list(keys))
        return len(keys)


def _make_test_cache(fake_client, allowed_prefixes=("cache:",)):
    from src.backend.redis_cache import RedisCache

    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = fake_client
    cache.prefix = "vcl:"
    cache.clear_allowed_prefixes = tuple(allowed_prefixes)
    return cache


def test_clear_pattern_uses_scan_and_unlink_in_batches():
    keys1 = [f"vcl:cache:{i}" for i in range(600)]
    keys2 = [f"vcl:cache:{i}" for i in range(600, 1200)]
    fake = _FakeRedisClient(scan_pages=[keys1, keys2])
    cache = _make_test_cache(fake, allowed_prefixes=("cache:",))

    deleted = cache.clear_pattern("cache:*")

    assert deleted == 1200
    assert fake.unlink_calls
    assert all(len(batch) <= 500 for batch in fake.unlink_calls)
    assert sum(len(batch) for batch in fake.unlink_calls) == 1200
    assert fake.delete_calls == []
    assert fake._scan_calls


def test_clear_pattern_rejects_out_of_scope_prefix():
    fake = _FakeRedisClient(scan_pages=[[f"vcl:other:{i}" for i in range(10)]])
    cache = _make_test_cache(fake, allowed_prefixes=("cache:",))

    assert cache.clear_pattern("other:*") == 0
    assert fake._scan_calls == []
    assert fake.unlink_calls == []


def test_decorator_hashes_key_and_does_not_log_raw_key(caplog):
    from src.backend.redis_cache import RedisCacheDecorator

    class _InMemoryCache:
        def __init__(self):
            self._store = {}
            self.seen_keys: list[str] = []

        def get(self, key):
            self.seen_keys.append(key)
            return self._store.get(key)

        def set(self, key, value, ttl=None):
            self.seen_keys.append(key)
            self._store[key] = value
            return True

    cache = _InMemoryCache()
    decorator = RedisCacheDecorator(cache=cache)  # type: ignore[arg-type]

    @decorator.cached(ttl=60, key_prefix="calc")
    def f(text):
        return len(text)

    caplog.set_level("DEBUG")
    long_arg = "A" * 10000
    assert f(long_arg) == 10000
    assert f(long_arg) == 10000  # hit

    assert cache.seen_keys
    for key in cache.seen_keys:
        assert len(key) <= 128
        assert key.startswith("calc:")
        digest = key.split(":", 1)[1]
        assert len(digest) == 64

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert long_arg not in log_text
