"""
性能系统

提供性能监控、优化和内存管理功能
"""

import gc
import logging
import threading
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import (
    Any,
    TypeVar,
)

import psutil

from .cache import MemoryCache, get_cache_manager
from .event_system import EventBus

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PerformanceMetric(Enum):
    """性能指标"""

    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_USAGE = "network_usage"
    FPS = "fps"
    FRAME_TIME = "frame_time"
    RENDER_TIME = "render_time"
    UPDATE_TIME = "update_time"


class MemoryPool:
    """内存池"""

    def __init__(self, initial_size: int = 1000, max_size: int = 10000):
        self.initial_size = initial_size
        self.max_size = max_size
        self.pool: list[Any] = []
        self._lock = threading.RLock()
        self._total_allocated = 0
        self._total_freed = 0

        # 初始化内存池
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """初始化内存池"""
        with self._lock:
            for _ in range(self.initial_size):
                obj = self._create_object()
                self.pool.append(obj)
                self._total_allocated += 1

    def _create_object(self) -> Any:
        """创建对象"""
        return {}

    def get_object(self) -> Any:
        """获取对象"""
        with self._lock:
            if self.pool:
                obj = self.pool.pop()
                self._total_freed += 1
                return obj
            else:
                # 池为空，创建新对象
                obj = self._create_object()
                self._total_allocated += 1
                return obj

    def return_object(self, obj: Any) -> None:
        """归还对象"""
        with self._lock:
            if len(self.pool) < self.max_size:
                self._reset_object(obj)
                self.pool.append(obj)
                self._total_freed -= 1

    def _reset_object(self, obj: Any) -> None:
        """重置对象"""
        if isinstance(obj, (dict, list)):
            obj.clear()
        # 可以添加更多类型的重置逻辑

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "pool_size": len(self.pool),
                "max_size": self.max_size,
                "total_allocated": self._total_allocated,
                "total_freed": self._total_freed,
                "usage_rate": (
                    (self._total_allocated - len(self.pool)) / self._total_allocated if self._total_allocated > 0 else 0
                ),
            }


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self.metrics: dict[PerformanceMetric, list[float]] = {}
        self.monitoring = False
        self.monitor_thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self.interval = 1.0  # 监控间隔（秒）
        self.max_samples = 1000  # 最大样本数

        # 初始化指标
        for metric in PerformanceMetric:
            self.metrics[metric] = []

    def start_monitoring(self, interval: float = 1.0) -> None:
        """开始监控"""
        if self.monitoring:
            return

        self.interval = interval
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        logger.info("性能监控已启动")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

        logger.info("性能监控已停止")

    def _monitor_loop(self) -> None:
        """监控循环"""
        while self.monitoring:
            try:
                # 收集性能指标
                metrics = self._collect_metrics()

                # 更新指标
                with self._lock:
                    for metric, value in metrics.items():
                        if metric in self.metrics:
                            self.metrics[metric].append(value)

                            # 限制样本数量
                            if len(self.metrics[metric]) > self.max_samples:
                                self.metrics[metric] = self.metrics[metric][-self.max_samples :]

                # 发送事件
                if self.event_bus:
                    self.event_bus.emit("performance.metrics", metrics)

                time.sleep(self.interval)

            except Exception as e:
                logger.error(f"性能监控错误: {e}")
                time.sleep(self.interval)

    def _collect_metrics(self) -> dict[PerformanceMetric, float]:
        """收集性能指标"""
        metrics = {}

        try:
            # CPU使用率
            metrics[PerformanceMetric.CPU_USAGE] = psutil.cpu_percent()

            # 内存使用率
            process = psutil.Process()
            memory_info = process.memory_info()
            metrics[PerformanceMetric.MEMORY_USAGE] = memory_info.rss / 1024 / 1024  # MB

            # 磁盘使用率
            disk_usage = psutil.disk_usage("/")
            metrics[PerformanceMetric.DISK_USAGE] = (disk_usage.used / disk_usage.total) * 100

            # 网络使用率（简化）
            metrics[PerformanceMetric.NETWORK_USAGE] = 0.0  # 需要更复杂的实现

        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")

        return metrics

    def get_metrics(self, metric: PerformanceMetric, limit: int | None = None) -> list[float]:
        """获取指标数据"""
        with self._lock:
            data = self.metrics.get(metric, [])
            if limit:
                data = data[-limit:]
            return data.copy()

    def get_current_metrics(self) -> dict[PerformanceMetric, float]:
        """获取当前指标"""
        return self._collect_metrics()

    def get_average_metrics(self, window: int = 10) -> dict[PerformanceMetric, float]:
        """获取平均指标"""
        averages = {}

        with self._lock:
            for metric, values in self.metrics.items():
                if values:
                    recent_values = values[-window:] if len(values) >= window else values
                    averages[metric] = sum(recent_values) / len(recent_values)
                else:
                    averages[metric] = 0.0

        return averages


class MemoryManager:
    """内存管理器"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self.memory_pools: dict[str, MemoryPool] = {}
        self.memory_threshold = 0.8  # 内存使用阈值
        self.cleanup_interval = 30.0  # 清理间隔（秒）
        self.cleanup_thread: threading.Thread | None = None
        self.cleanup_running = False

        # 启动清理线程
        self._start_cleanup()

    def create_pool(self, name: str, initial_size: int = 1000, max_size: int = 10000) -> MemoryPool:
        """创建内存池"""
        pool = MemoryPool(initial_size, max_size)
        self.memory_pools[name] = pool
        logger.info(f"创建内存池: {name}")
        return pool

    def get_pool(self, name: str) -> MemoryPool | None:
        """获取内存池"""
        return self.memory_pools.get(name)

    def cleanup_memory(self) -> dict[str, Any]:
        """清理内存"""
        cleanup_stats = {"before_gc": self._get_memory_usage(), "gc_collections": 0, "after_gc": 0, "freed_objects": 0}

        try:
            # 强制垃圾回收
            cleanup_stats["gc_collections"] = gc.collect()

            # 获取清理后内存使用
            cleanup_stats["after_gc"] = self._get_memory_usage()

            # 清理内存池
            for name, pool in self.memory_pools.items():
                pool_stats = pool.get_stats()
                cleanup_stats[f"pool_{name}"] = pool_stats

            logger.info(f"内存清理完成: {cleanup_stats}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit("memory.cleaned", cleanup_stats)

        except Exception as e:
            logger.error(f"内存清理失败: {e}")

        return cleanup_stats

    def _get_memory_usage(self) -> float:
        """获取内存使用量（MB）"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def _start_cleanup(self) -> None:
        """启动清理线程"""
        self.cleanup_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        """清理循环"""
        while self.cleanup_running:
            try:
                # 检查内存使用
                memory_usage = self._get_memory_usage()

                if memory_usage > self.memory_threshold * 1000:  # 假设阈值是800MB
                    self.cleanup_memory()

                time.sleep(self.cleanup_interval)

            except Exception as e:
                logger.error(f"内存清理循环错误: {e}")
                time.sleep(self.cleanup_interval)

    def stop_cleanup(self) -> None:
        """停止清理"""
        self.cleanup_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)


class PerformanceOptimizer:
    """性能优化器"""

    def __init__(self, monitor: PerformanceMonitor, memory_manager: MemoryManager):
        self.monitor = monitor
        self.memory_manager = memory_manager
        self.optimization_rules: list[Callable[[dict[PerformanceMetric, float]], bool]] = []
        self.optimization_actions: list[Callable[[], None]] = []

        # 注册默认优化规则
        self._register_default_rules()

    def add_optimization_rule(self, rule: Callable[[dict[PerformanceMetric, float]], bool]) -> None:
        """添加优化规则"""
        self.optimization_rules.append(rule)

    def add_optimization_action(self, action: Callable[[], None]) -> None:
        """添加优化动作"""
        self.optimization_actions.append(action)

    def optimize(self) -> bool:
        """执行优化"""
        current_metrics = self.monitor.get_current_metrics()

        # 检查优化规则
        for rule in self.optimization_rules:
            if rule(current_metrics):
                # 执行优化动作
                for action in self.optimization_actions:
                    try:
                        action()
                    except Exception as e:
                        logger.error(f"优化动作执行失败: {e}")

                return True

        return False

    def _register_default_rules(self) -> None:
        """注册默认优化规则"""

        # 内存使用过高
        def high_memory_rule(metrics: dict[PerformanceMetric, float]) -> bool:
            return metrics.get(PerformanceMetric.MEMORY_USAGE, 0) > 500  # 500MB

        # CPU使用过高
        def high_cpu_rule(metrics: dict[PerformanceMetric, float]) -> bool:
            return metrics.get(PerformanceMetric.CPU_USAGE, 0) > 80  # 80%

        self.add_optimization_rule(high_memory_rule)
        self.add_optimization_rule(high_cpu_rule)

        # 默认优化动作
        def cleanup_action():
            self.memory_manager.cleanup_memory()

        self.add_optimization_action(cleanup_action)


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        self.profiles: dict[str, list[float]] = {}
        self._lock = threading.RLock()

    def profile(self, name: str):
        """性能分析装饰器"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    duration = end_time - start_time

                    with self._lock:
                        if name not in self.profiles:
                            self.profiles[name] = []
                        self.profiles[name].append(duration)

                    logger.debug(f"性能分析: {name} - {duration:.6f}秒")

            return wrapper

        return decorator

    def get_profile_stats(self, name: str) -> dict[str, float] | None:
        """获取性能统计"""
        with self._lock:
            if name not in self.profiles or not self.profiles[name]:
                return None

            durations = self.profiles[name]
            return {
                "count": len(durations),
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "total": sum(durations),
            }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """获取所有性能统计"""
        with self._lock:
            stats = {}
            for name in self.profiles:
                stats[name] = self.get_profile_stats(name)
            return stats

    def clear_profile(self, name: str) -> None:
        """清除性能数据"""
        with self._lock:
            if name in self.profiles:
                del self.profiles[name]

    def clear_all_profiles(self) -> None:
        """清除所有性能数据"""
        with self._lock:
            self.profiles.clear()


class CacheOptimizer:
    """缓存优化器"""

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.optimization_interval = 60.0  # 优化间隔（秒）
        self.optimization_thread: threading.Thread | None = None
        self.optimization_running = False

    def start_optimization(self) -> None:
        """开始优化"""
        if self.optimization_running:
            return

        self.optimization_running = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()

        logger.info("缓存优化已启动")

    def stop_optimization(self) -> None:
        """停止优化"""
        self.optimization_running = False
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5.0)

        logger.info("缓存优化已停止")

    def _optimization_loop(self) -> None:
        """优化循环"""
        while self.optimization_running:
            try:
                self._optimize_caches()
                time.sleep(self.optimization_interval)
            except Exception as e:
                logger.error(f"缓存优化错误: {e}")
                time.sleep(self.optimization_interval)

    def _optimize_caches(self) -> None:
        """优化缓存"""
        try:
            # 获取默认缓存
            default_cache = self.cache_manager.get_cache("default")

            if isinstance(default_cache, MemoryCache) and default_cache.size() > default_cache.max_size * 0.8:
                # 清理过期缓存
                default_cache.clear()
                logger.info("缓存已清理")

        except Exception as e:
            logger.error(f"缓存优化失败: {e}")


# 全局性能系统
_global_performance_monitor = PerformanceMonitor()
_global_memory_manager = MemoryManager()
_global_performance_profiler = PerformanceProfiler()


def get_global_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return _global_performance_monitor


def get_global_memory_manager() -> MemoryManager:
    """获取全局内存管理器"""
    return _global_memory_manager


def get_global_performance_profiler() -> PerformanceProfiler:
    """获取全局性能分析器"""
    return _global_performance_profiler


# 便捷函数
def start_performance_monitoring(interval: float = 1.0) -> None:
    """开始性能监控"""
    _global_performance_monitor.start_monitoring(interval)


def stop_performance_monitoring() -> None:
    """停止性能监控"""
    _global_performance_monitor.stop_monitoring()


def cleanup_memory() -> dict[str, Any]:
    """清理内存"""
    return _global_memory_manager.cleanup_memory()


def get_current_metrics() -> dict[PerformanceMetric, float]:
    """获取当前指标"""
    return _global_performance_monitor.get_current_metrics()


def get_average_metrics(window: int = 10) -> dict[PerformanceMetric, float]:
    """获取平均指标"""
    return _global_performance_monitor.get_average_metrics(window)


# 性能分析装饰器
def profile_performance(name: str):
    """性能分析装饰器"""
    return _global_performance_profiler.profile(name)


def get_performance_stats(name: str) -> dict[str, float] | None:
    """获取性能统计"""
    return _global_performance_profiler.get_profile_stats(name)


# 内存池装饰器
def use_memory_pool(pool_name: str = "default"):
    """使用内存池装饰器"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            pool = _global_memory_manager.get_pool(pool_name)
            if pool:
                obj = pool.get_object()
                try:
                    return func(*args, **kwargs)
                finally:
                    pool.return_object(obj)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 性能系统演示 ===\n")

    # 1. 性能监控
    logger.info("1. 性能监控:")

    monitor = PerformanceMonitor()
    monitor.start_monitoring(0.5)

    # 等待一些时间收集数据
    time.sleep(2)

    current_metrics = monitor.get_current_metrics()
    logger.info(f"当前指标: {current_metrics}")

    average_metrics = monitor.get_average_metrics()
    logger.info(f"平均指标: {average_metrics}")

    monitor.stop_monitoring()

    logger.info("")

    # 2. 内存管理
    logger.info("2. 内存管理:")

    memory_manager = MemoryManager()

    # 创建内存池
    pool = memory_manager.create_pool("demo", initial_size=100, max_size=500)

    # 使用内存池
    obj = pool.get_object()
    obj["data"] = "test"
    pool.return_object(obj)

    pool_stats = pool.get_stats()
    logger.info(f"内存池统计: {pool_stats}")

    # 清理内存
    cleanup_stats = memory_manager.cleanup_memory()
    logger.info(f"内存清理统计: {cleanup_stats}")

    logger.info("")

    # 3. 性能分析
    logger.info("3. 性能分析:")

    profiler = PerformanceProfiler()

    @profiler.profile("demo_function")
    def demo_function():
        time.sleep(0.1)
        return "完成"

    # 执行多次
    for _ in range(5):
        demo_function()

    stats = profiler.get_profile_stats("demo_function")
    logger.info(f"性能统计: {stats}")

    logger.info("")

    # 4. 性能优化
    logger.info("4. 性能优化:")

    optimizer = PerformanceOptimizer(monitor, memory_manager)

    # 执行优化
    optimized = optimizer.optimize()
    logger.info(f"优化结果: {optimized}")

    logger.info("")

    # 5. 缓存优化
    logger.info("5. 缓存优化:")

    cache_manager = get_cache_manager()
    cache_optimizer = CacheOptimizer(cache_manager)

    cache_optimizer.start_optimization()
    time.sleep(1)
    cache_optimizer.stop_optimization()

    logger.info("性能系统演示完成！")
