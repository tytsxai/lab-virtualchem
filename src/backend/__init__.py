"""
后端性能优化模块
"""

from .bff_layer import (
    BFFEndpoint,
    BFFRouter,
    DataPrefetcher,
    ResponseTransformer,
    ServiceAggregator,
    get_aggregator,
    get_bff_endpoint,
    get_router,
)
from .cdn_config import (
    CDNConfig,
    CDNConfigBuilder,
    CDNManager,
    ResourcePreloader,
    StaticResourceOptimizer,
    get_cdn_manager,
    init_cdn,
)
from .db_optimizer import (
    ConnectionPool,
    DatabaseOptimizer,
    IndexAnalyzer,
    QueryCache,
    QueryOptimizer,
)
from .redis_cache import (
    RedisCache,
    RedisCacheDecorator,
    get_redis_cache,
    init_redis_cache,
)

# 兼容 pytest-cov 以路径形式指定模块（例如 `--cov=src/backend/cdn_config`）。
# pytest-cov 会把它当作模块名；这里把该别名指向实际模块对象，确保可统计覆盖率。
import sys as _sys

_cdn_config_mod = _sys.modules.get(__name__ + ".cdn_config")
if _cdn_config_mod is not None:
    _sys.modules.setdefault("src/backend/cdn_config", _cdn_config_mod)

__all__ = [
    # Redis缓存
    "RedisCache",
    "RedisCacheDecorator",
    "get_redis_cache",
    "init_redis_cache",
    # 数据库优化
    "QueryOptimizer",
    "IndexAnalyzer",
    "ConnectionPool",
    "QueryCache",
    "DatabaseOptimizer",
    # BFF层
    "ServiceAggregator",
    "BFFEndpoint",
    "ResponseTransformer",
    "DataPrefetcher",
    "BFFRouter",
    "get_aggregator",
    "get_bff_endpoint",
    "get_router",
    # CDN配置
    "CDNConfig",
    "CDNManager",
    "StaticResourceOptimizer",
    "ResourcePreloader",
    "CDNConfigBuilder",
    "init_cdn",
    "get_cdn_manager",
]
