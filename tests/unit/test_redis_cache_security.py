import pytest


def test_redis_cache_disallows_pickle_serializer():
    from src.backend.redis_cache import RedisCache

    with pytest.raises(ValueError):
        RedisCache(serializer="pickle")

    with pytest.raises(ValueError):
        RedisCache(serializer=" Pickle ")
