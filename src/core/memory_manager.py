"""
内存管理器
优化内存使用，防止内存泄漏，提供智能垃圾回收
"""

import gc
import threading
import time
import weakref
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from weakref import WeakSet

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # psutil 不可用时的占位符
    class psutil:  # type: ignore
        @staticmethod
        def Process(pid: int = 0) -> Any:
            class Process:
                def memory_info(self) -> Any:
                    class MemoryInfo:
                        rss = 0
                        vms = 0

                    return MemoryInfo()

                def memory_percent(self) -> float:
                    return 0.0

            return Process()

        @staticmethod
        def virtual_memory() -> Any:
            class VirtualMemory:
                available = 0
            return VirtualMemory()


from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemoryStrategy(str, Enum):
    """内存策略"""

    AGGRESSIVE = "aggressive"  # 激进回收
    BALANCED = "balanced"  # 平衡策略
    CONSERVATIVE = "conservative"  # 保守策略
    MANUAL = "manual"  # 手动控制


@dataclass
class MemoryMetrics:
    """内存指标"""

    timestamp: datetime
    rss_mb: float  # 物理内存
    vms_mb: float  # 虚拟内存
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存
    gc_objects: int  # 垃圾回收对象数
    weak_refs: int  # 弱引用数量
    cache_size: int  # 缓存大小
    fragmentation: float  # 内存碎片率


@dataclass
class MemoryLeak:
    """内存泄漏"""

    object_type: str
    count: int
    size_mb: float
    growth_rate: float
    first_detected: datetime
    last_detected: datetime


class MemoryManager:
    """内存管理器"""

    def __init__(self, strategy: MemoryStrategy = MemoryStrategy.BALANCED):
        self.strategy = strategy
        self.process = psutil.Process()

        # 内存监控
        self.memory_history: deque[MemoryMetrics] = deque(maxlen=100)
        self.leak_detection_enabled = True
        self.gc_threshold_mb = 100  # GC触发阈值
        self.leak_threshold_mb = 50  # 泄漏检测阈值

        # 对象跟踪
        self.tracked_objects: dict[str, WeakSet] = defaultdict(WeakSet)
        self.object_counts: dict[str, int] = defaultdict(int)
        self.object_sizes: dict[str, float] = defaultdict(float)

        # 缓存管理
        self.caches: dict[str, Any] = {}
        self.cache_max_sizes: dict[str, int] = {}
        self.cache_access_times: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=100))

        # 弱引用管理 - 增加大小限制防止无限增长
        self.weak_refs: set[weakref.ref[Any]] = set()
        self.weak_ref_callbacks: dict[weakref.ref[Any], Callable[[], None]] = {}
        self.max_weak_refs = 10000  # 最大弱引用数量

        # 性能统计
        self.gc_count = 0
        self.gc_time_total = 0.0
        self.leak_detections = 0
        self.cleanup_operations = 0

        # 线程安全
        self._lock = threading.RLock()

        # 自动清理定时器
        self.cleanup_interval = 300  # 5分钟
        self.last_cleanup = time.time()

        # 内存泄漏检测阈值
        self.memory_growth_threshold = 50.0  # MB
        self.growth_detection_window = 20  # 检测窗口大小

        logger.info(f"内存管理器初始化完成，策略: {strategy.value}")

    def track_object(self, obj: Any, category: str = "default") -> None:
        """跟踪对象"""
        try:
            with self._lock:
                # 检查弱引用数量限制
                if len(self.weak_refs) >= self.max_weak_refs:
                    logger.warning(f"弱引用数量达到上限 {self.max_weak_refs}，跳过跟踪")
                    return

                # 创建弱引用
                weak_ref = weakref.ref(obj, self._object_finalized)
                self.tracked_objects[category].add(weak_ref)
                self.weak_refs.add(weak_ref)

                # 更新计数
                self.object_counts[category] += 1

                # 估算大小
                try:
                    size = self._estimate_object_size(obj)
                    self.object_sizes[category] += size
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"跟踪对象失败: {e}")

    def _object_finalized(self, weak_ref: weakref.ref[Any]) -> None:
        """对象被回收时的回调"""
        try:
            with self._lock:
                # 移除弱引用
                self.weak_refs.discard(weak_ref)

                # 执行回调
                callback = self.weak_ref_callbacks.pop(weak_ref, None)
                if callback:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"弱引用回调执行失败: {e}")

        except Exception as e:
            logger.debug(f"对象回收回调失败: {e}")

    def _estimate_object_size(self, obj: Any) -> float:
        """估算对象大小（MB）"""
        try:
            import sys

            size = sys.getsizeof(obj)

            # 递归计算容器大小
            if isinstance(obj, (list, tuple, set, dict)):
                for item in obj:
                    size += sys.getsizeof(item)

            return size / 1024 / 1024  # 转换为MB

        except Exception:
            return 0.0

    def register_cache(self, name: str, cache: Any, max_size: int = 100) -> None:
        """注册缓存"""
        try:
            with self._lock:
                self.caches[name] = cache
                self.cache_max_sizes[name] = max_size
                logger.debug(f"注册缓存: {name}, 最大大小: {max_size}")

        except Exception as e:
            logger.error(f"注册缓存失败: {e}")

    def unregister_cache(self, name: str) -> None:
        """注销缓存"""
        try:
            with self._lock:
                self.caches.pop(name, None)
                self.cache_max_sizes.pop(name, None)
                self.cache_access_times.pop(name, None)
                logger.debug(f"注销缓存: {name}")

        except Exception as e:
            logger.error(f"注销缓存失败: {e}")

    def cache_access(self, cache_name: str) -> None:
        """记录缓存访问"""
        try:
            with self._lock:
                self.cache_access_times[cache_name].append(time.time())

        except Exception as e:
            logger.debug(f"记录缓存访问失败: {e}")

    def get_memory_metrics(self) -> MemoryMetrics:
        """获取内存指标"""
        try:
            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()

            # 垃圾回收统计
            gc_stats = gc.get_stats()
            gc_objects = sum(stat["collected"] for stat in gc_stats)

            # 计算内存碎片率
            fragmentation = self._calculate_fragmentation()

            metrics = MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=float(memory_info.rss) / 1024 / 1024,
                vms_mb=float(memory_info.vms) / 1024 / 1024,
                percent=float(self.process.memory_percent()),
                available_mb=float(system_memory.available) / 1024 / 1024,
                gc_objects=gc_objects,
                weak_refs=len(self.weak_refs),
                cache_size=sum(len(cache) for cache in self.caches.values()),
                fragmentation=fragmentation,
            )

            # 更新历史记录
            self.memory_history.append(metrics)

            return metrics

        except Exception as e:
            logger.error(f"获取内存指标失败: {e}")
            return MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=0.0,
                vms_mb=0.0,
                percent=0.0,
                available_mb=0.0,
                gc_objects=0,
                weak_refs=0,
                cache_size=0,
                fragmentation=0.0,
            )

    def _calculate_fragmentation(self) -> float:
        """计算内存碎片率"""
        try:
            if len(self.memory_history) < 2:
                return 0.0

            # 计算内存使用变化
            recent_metrics = list(self.memory_history)[-10:]
            if len(recent_metrics) < 2:
                return 0.0

            # 使用列表推导式优化性能
            memory_changes = [
                abs(recent_metrics[i].rss_mb - recent_metrics[i - 1].rss_mb)
                for i in range(1, len(recent_metrics))
            ]

            if not memory_changes:
                return 0.0

            # 碎片率 = 变化的标准差 / 平均变化
            avg_change = sum(memory_changes) / len(memory_changes)
            if avg_change == 0:
                return 0.0

            variance = sum((change - avg_change) ** 2 for change in memory_changes) / len(memory_changes)
            std_dev = variance**0.5

            return min(100.0, (std_dev / avg_change) * 100)

        except Exception as e:
            logger.debug(f"计算内存碎片率失败: {e}")
            return 0.0

    def should_cleanup(self) -> bool:
        """检查是否需要清理"""
        try:
            current_time = time.time()
            time_since_cleanup = current_time - self.last_cleanup

            # 时间间隔检查
            if time_since_cleanup < self.cleanup_interval:
                return False

            # 内存使用检查
            metrics = self.get_memory_metrics()
            if metrics.rss_mb > self.gc_threshold_mb:
                return True

            # 缓存大小检查
            if metrics.cache_size > 1000:
                return True

            # 弱引用数量检查
            return metrics.weak_refs > 10000

        except Exception as e:
            logger.error(f"检查清理条件失败: {e}")
            return True

    def cleanup_memory(self, force: bool = False) -> dict[str, Any]:
        """清理内存"""
        if not force and not self.should_cleanup():
            return {"skipped": True, "reason": "清理条件未满足"}

        start_time = time.time()
        cleanup_stats = {
            "gc_collected": 0,
            "cache_cleared": 0,
            "weak_refs_cleaned": 0,
            "leaks_detected": 0,
            "duration_ms": 0.0,
        }

        try:
            logger.info("开始内存清理...")

            with self._lock:
                # 1. 垃圾回收
                if self.strategy in [MemoryStrategy.AGGRESSIVE, MemoryStrategy.BALANCED]:
                    cleanup_stats["gc_collected"] = self._perform_garbage_collection()

                # 2. 清理缓存
                if self.strategy in [MemoryStrategy.AGGRESSIVE, MemoryStrategy.BALANCED]:
                    cleanup_stats["cache_cleared"] = self._cleanup_caches()

                # 3. 清理弱引用
                if self.strategy == MemoryStrategy.AGGRESSIVE:
                    cleanup_stats["weak_refs_cleaned"] = self._cleanup_weak_refs()

                # 4. 检测内存泄漏
                if self.leak_detection_enabled:
                    cleanup_stats["leaks_detected"] = self._detect_memory_leaks()

                # 5. 更新统计
                self.cleanup_operations += 1
                self.last_cleanup = time.time()

            cleanup_stats["duration_ms"] = float((time.time() - start_time) * 1000)

            logger.info(f"内存清理完成: {cleanup_stats}")
            return cleanup_stats

        except Exception as e:
            logger.error(f"内存清理失败: {e}")
            cleanup_stats["error"] = str(e)
            cleanup_stats["duration_ms"] = float((time.time() - start_time) * 1000)
            return cleanup_stats

    def _perform_garbage_collection(self) -> int:
        """执行垃圾回收"""
        try:
            start_time = time.time()

            # 获取回收前的对象数
            len(gc.get_objects())

            # 执行垃圾回收
            collected = gc.collect()

            # 更新统计
            gc_time = time.time() - start_time
            self.gc_count += 1
            self.gc_time_total += gc_time

            logger.debug(f"垃圾回收完成: 回收了 {collected} 个对象, 耗时: {gc_time:.3f}秒")

            return collected

        except Exception as e:
            logger.error(f"垃圾回收失败: {e}")
            return 0

    def _cleanup_caches(self) -> int:
        """清理缓存"""
        try:
            cleaned_count = 0

            for cache_name, cache in self.caches.items():
                try:
                    max_size = self.cache_max_sizes.get(cache_name, 100)

                    if hasattr(cache, "clear"):
                        # 简单缓存，直接清理
                        if len(cache) > max_size:
                            cache.clear()
                            cleaned_count += 1
                    elif hasattr(cache, "popitem"):
                        # 字典缓存，移除最旧的项
                        while len(cache) > max_size:
                            cache.popitem()
                            cleaned_count += 1
                    elif hasattr(cache, "pop"):
                        # 列表缓存，移除最旧的项
                        while len(cache) > max_size:
                            cache.pop(0)
                            cleaned_count += 1

                    logger.debug(f"清理缓存 {cache_name}: {len(cache)} 项")

                except Exception as e:
                    logger.error(f"清理缓存 {cache_name} 失败: {e}")

            return cleaned_count

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return 0

    def _cleanup_weak_refs(self) -> int:
        """清理弱引用"""
        try:
            # 清理已死的弱引用
            dead_refs = []
            for weak_ref in self.weak_refs:
                if weak_ref() is None:
                    dead_refs.append(weak_ref)

            for dead_ref in dead_refs:
                self.weak_refs.discard(dead_ref)
                self.weak_ref_callbacks.pop(dead_ref, None)

            logger.debug(f"清理了 {len(dead_refs)} 个死弱引用")
            return len(dead_refs)

        except Exception as e:
            logger.error(f"清理弱引用失败: {e}")
            return 0

    def _detect_memory_leaks(self) -> int:
        """检测内存泄漏（改进版）"""
        try:
            if len(self.memory_history) < self.growth_detection_window:
                return 0

            leaks_detected = 0

            # 分析内存增长趋势
            recent_metrics = list(self.memory_history)[-self.growth_detection_window:]
            memory_values = [m.rss_mb for m in recent_metrics]

            # 计算增长趋势
            if len(memory_values) >= 10:
                # 简单线性回归检测增长趋势
                n = len(memory_values)
                x_sum = sum(range(n))
                y_sum = sum(memory_values)
                xy_sum = sum(i * memory_values[i] for i in range(n))
                x2_sum = sum(i * i for i in range(n))

                denominator = n * x2_sum - x_sum * x_sum
                if denominator != 0:
                    slope = (n * xy_sum - x_sum * y_sum) / denominator

                    # 如果持续增长且超过阈值
                    if slope > self.memory_growth_threshold / 60:  # 转换为MB/分钟
                        leaks_detected += 1
                        logger.warning(f"检测到内存泄漏: 增长趋势 {slope:.2f} MB/分钟")

            # 检测对象数量异常增长
            for category, count in self.object_counts.items():
                if count > 10000:  # 对象数量过多
                    leaks_detected += 1
                    logger.warning(f"检测到对象泄漏: {category} 有 {count} 个对象")

            # 检测弱引用数量异常
            if len(self.weak_refs) > self.max_weak_refs * 0.8:  # 超过80%阈值
                leaks_detected += 1
                logger.warning(f"弱引用数量过多: {len(self.weak_refs)}/{self.max_weak_refs}")

            if leaks_detected > 0:
                self.leak_detections += 1

            return leaks_detected

        except Exception as e:
            logger.error(f"检测内存泄漏失败: {e}")
            return 0

    def optimize_memory_usage(self) -> dict[str, Any]:
        """优化内存使用"""
        try:
            optimization_stats = {"before_mb": 0.0, "after_mb": 0.0, "saved_mb": 0.0, "optimizations": []}

            # 获取优化前内存
            before_metrics = self.get_memory_metrics()
            optimization_stats["before_mb"] = before_metrics.rss_mb

            # 执行优化
            optimizations = []

            # 1. 清理缓存
            cache_cleaned = self._cleanup_caches()
            if cache_cleaned > 0:
                optimizations.append(f"清理了 {cache_cleaned} 个缓存")

            # 2. 垃圾回收
            gc_collected = self._perform_garbage_collection()
            if gc_collected > 0:
                optimizations.append(f"垃圾回收了 {gc_collected} 个对象")

            # 3. 清理弱引用
            weak_refs_cleaned = self._cleanup_weak_refs()
            if weak_refs_cleaned > 0:
                optimizations.append(f"清理了 {weak_refs_cleaned} 个弱引用")

            # 获取优化后内存
            after_metrics = self.get_memory_metrics()
            optimization_stats["after_mb"] = after_metrics.rss_mb
            optimization_stats["saved_mb"] = optimization_stats["before_mb"] - optimization_stats["after_mb"]
            optimization_stats["optimizations"] = optimizations

            logger.info(f"内存优化完成: 节省了 {optimization_stats['saved_mb']:.2f} MB")

            return optimization_stats

        except Exception as e:
            logger.error(f"优化内存使用失败: {e}")
            return {"error": str(e)}

    def get_memory_report(self) -> str:
        """获取内存报告"""
        try:
            metrics = self.get_memory_metrics()

            report = f"""
# 内存使用报告

## 当前状态
- 物理内存: {metrics.rss_mb:.2f} MB
- 虚拟内存: {metrics.vms_mb:.2f} MB
- 内存使用率: {metrics.percent:.1f}%
- 可用内存: {metrics.available_mb:.2f} MB
- 内存碎片率: {metrics.fragmentation:.1f}%

## 对象统计
- 垃圾回收对象: {metrics.gc_objects}
- 弱引用数量: {metrics.weak_refs}
- 缓存大小: {metrics.cache_size}

## 按类别统计
"""

            for category, count in self.object_counts.items():
                size_mb = self.object_sizes[category]
                report += f"- {category}: {count} 个对象, {size_mb:.2f} MB\n"

            report += f"""
## 性能统计
- 垃圾回收次数: {self.gc_count}
- 总GC时间: {self.gc_time_total:.3f} 秒
- 泄漏检测次数: {self.leak_detections}
- 清理操作次数: {self.cleanup_operations}

## 缓存状态
"""

            for cache_name, cache in self.caches.items():
                max_size = self.cache_max_sizes.get(cache_name, 100)
                current_size = len(cache) if hasattr(cache, "__len__") else 0
                report += f"- {cache_name}: {current_size}/{max_size} 项\n"

            report += """
## 建议
"""

            if metrics.rss_mb > self.gc_threshold_mb:
                report += "- 内存使用较高，建议执行垃圾回收\n"

            if metrics.fragmentation > 30:
                report += "- 内存碎片率较高，建议优化内存分配\n"

            if self.leak_detections > 0:
                report += "- 检测到内存泄漏，需要检查代码\n"

            if metrics.cache_size > 1000:
                report += "- 缓存大小较大，建议清理\n"

            return report

        except Exception as e:
            logger.error(f"生成内存报告失败: {e}")
            return f"报告生成失败: {e}"

    def set_strategy(self, strategy: MemoryStrategy) -> None:
        """设置内存策略"""
        self.strategy = strategy
        logger.info(f"内存策略已更新: {strategy.value}")

    def set_gc_threshold(self, threshold_mb: float) -> None:
        """设置GC触发阈值"""
        self.gc_threshold_mb = threshold_mb
        logger.info(f"GC触发阈值已更新: {threshold_mb} MB")

    def enable_leak_detection(self, enabled: bool) -> None:
        """启用/禁用泄漏检测"""
        self.leak_detection_enabled = enabled
        logger.info(f"泄漏检测{'启用' if enabled else '禁用'}")


# 全局内存管理器实例
memory_manager = MemoryManager()
