"""
性能优化模块
提供缓存、数据库优化、渲染优化、前后端性能优化等功能
"""

from .advanced_cache import AdvancedCache, CacheLevel, CachePolicy, L1Cache, L2Cache
from .backend_optimizer import (
    APIResponseCache,
    BatchProcessor,
    ConnectionPool,
    DataPrefetcher,
    QueryOptimizer,
    get_api_cache,
    get_data_prefetcher,
    get_query_optimizer,
)
from .database_optimizer import DatabaseOptimizer, IndexManager, QueryAnalyzer
from .frontend_optimizer import (
    LazyComponentLoader,
    RequestMerger,
    ResourceLoadConfig,
    ResourceLoader,
    UIRenderOptimizer,
    get_lazy_component_loader,
    get_resource_loader,
    get_ui_render_optimizer,
    load_lazy_component,
    register_lazy_component,
)
from .high_freq_optimizer import (
    ExperimentLoadOptimizer,
    ParticleSystemOptimizer,
    PhysicsEngineOptimizer,
    RenderingOptimizer,
    get_experiment_load_optimizer,
    get_particle_system_optimizer,
    get_physics_engine_optimizer,
    get_rendering_optimizer,
)
from .integrated_optimizer import (
    IntegratedPerformanceOptimizer,
    PerformanceReport,
    get_integrated_optimizer,
    get_performance_summary,
    init_performance_optimizations,
)
from .render_optimizer import RenderOptimizer, RenderStrategy

__all__ = [
    # 高级缓存
    "AdvancedCache",
    "CacheLevel",
    "CachePolicy",
    "L1Cache",
    "L2Cache",
    # 数据库优化
    "DatabaseOptimizer",
    "IndexManager",
    "QueryAnalyzer",
    # 渲染优化
    "RenderOptimizer",
    "RenderStrategy",
    # 后端优化
    "QueryOptimizer",
    "BatchProcessor",
    "APIResponseCache",
    "DataPrefetcher",
    "ConnectionPool",
    "get_query_optimizer",
    "get_api_cache",
    "get_data_prefetcher",
    # 前端优化
    "ResourceLoader",
    "ResourceLoadConfig",
    "UIRenderOptimizer",
    "LazyComponentLoader",
    "RequestMerger",
    "get_resource_loader",
    "get_ui_render_optimizer",
    "get_lazy_component_loader",
    "register_lazy_component",
    "load_lazy_component",
    # 高频操作优化
    "ExperimentLoadOptimizer",
    "ParticleSystemOptimizer",
    "PhysicsEngineOptimizer",
    "RenderingOptimizer",
    "get_experiment_load_optimizer",
    "get_particle_system_optimizer",
    "get_physics_engine_optimizer",
    "get_rendering_optimizer",
    # 集成优化
    "IntegratedPerformanceOptimizer",
    "PerformanceReport",
    "get_integrated_optimizer",
    "init_performance_optimizations",
    "get_performance_summary",
]
