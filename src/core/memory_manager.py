"""
内存管理器
优化内存使用，防止内存泄漏，提供智能垃圾回收

本模块在原有高阶内存管理功能基础上，增加了测试/旧版接口：
- MemoryThreshold 枚举
- check_interval / threshold_warning / threshold_critical 等配置
- start_monitoring / stop_monitoring / get_current_metrics 等方法
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
from typing import Any, Optional
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


class MemoryThreshold(str, Enum):
    """内存阈值枚举（测试/兼容用）"""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MemoryMetrics:
    """内存指标"""

    timestamp: datetime
    rss_mb: float  # 物理内存
    vms_mb: float  # 虚拟内存
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存
    gc_objects: int = 0  # 垃圾回收对象数
    weak_refs: int = 0  # 弱引用数量
    cache_size: int = 0  # 缓存大小
    fragmentation: float = 0.0  # 内存碎片率


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

    def __init__(
        self,
        strategy: MemoryStrategy = MemoryStrategy.BALANCED,
        check_interval: float = 1.0,
        threshold_warning: int = 70,
        threshold_critical: int = 90,
    ):
        # 阈值校验（测试依赖）
        if threshold_warning < 0 or threshold_warning > 100:
            raise ValueError("threshold_warning 必须在 0-100 之间")
        if threshold_critical < 0 or threshold_critical > 100:
            raise ValueError("threshold_critical 必须在 0-100 之间")
        if threshold_warning > threshold_critical:
            raise ValueError("threshold_warning 不能大于 threshold_critical")

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

        # -------- 兼容测试/旧版接口所需字段 --------
        self.check_interval = check_interval
        self.threshold_warning = threshold_warning
        self.threshold_critical = threshold_critical

        self.is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.metrics_history: list[MemoryMetrics] = []
        self.max_history: int = 1000
        self._monitoring_callbacks: list[Callable[[MemoryMetrics], None]] = []

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

            # 同时维护兼容用的列表历史
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history :]

            return metrics

        except Exception as e:
            logger.error(f"获取内存指标失败: {e}")
            return MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=0.0,
                vms_mb=0.0,
                percent=0.0,
                available_mb=0.0,
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

    # -------- 兼容测试/旧版接口的方法 --------

    def start_monitoring(self) -> None:
        """开始后台监控内存使用"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self._stop_event.clear()

        def _monitor_loop() -> None:
            while not self._stop_event.is_set():
                try:
                    metrics = self.get_current_metrics()
                    for callback in list(self._monitoring_callbacks):
                        try:
                            callback(metrics)
                        except Exception as e:  # pragma: no cover - 防御性日志
                            logger.debug(f"监控回调执行失败: {e}")
                except Exception as e:  # pragma: no cover
                    logger.debug(f"监控循环异常: {e}")
                time.sleep(self.check_interval)

        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """停止后台监控"""
        if not self.is_monitoring:
            return

        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        self.is_monitoring = False

    def get_current_metrics(self) -> MemoryMetrics:
        """获取当前内存指标（测试期望接口）"""
        return self.get_memory_metrics()

    def get_memory_usage(self) -> dict[str, Any]:
        """获取当前内存使用情况（简化字典形式）"""
        metrics = self.get_current_metrics()
        return {
            "rss_mb": metrics.rss_mb,
            "vms_mb": metrics.vms_mb,
            "percent": metrics.percent,
            "available_mb": metrics.available_mb,
            "timestamp": metrics.timestamp,
        }

    def check_memory_threshold(self) -> MemoryThreshold:
        """根据当前使用率返回内存阈值等级"""
        metrics = self.get_current_metrics()
        if metrics.percent >= self.threshold_critical:
            return MemoryThreshold.CRITICAL
        if metrics.percent >= self.threshold_warning:
            return MemoryThreshold.WARNING
        return MemoryThreshold.NORMAL

    def optimize_memory(self) -> dict[str, Any]:
        """兼容方法名：调用 optimize_memory_usage"""
        return self.optimize_memory_usage()

    def force_garbage_collection(self) -> None:
        """强制垃圾回收"""
        self._perform_garbage_collection()

    def detect_memory_leak(self) -> bool:
        """检测内存泄漏"""
        leaks = self._detect_memory_leaks()
        return bool(leaks)

    def get_memory_trend(self) -> dict[str, Any]:
        """根据历史数据估算内存趋势"""
        if len(self.metrics_history) < 2:
            return {"direction": "stable", "rate": 0.0, "confidence": 0.0}

        values = [m.rss_mb for m in self.metrics_history[-20:]]
        deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
        avg_delta = sum(deltas) / len(deltas)

        if avg_delta > 0.1:
            direction = "increasing"
        elif avg_delta < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"

        rate = abs(avg_delta)
        confidence = min(1.0, max(0.0, rate / max(values))) if max(values) > 0 else 0.0

        return {"direction": direction, "rate": rate, "confidence": confidence}

    def get_fragmentation_rate(self) -> float:
        """获取碎片率（0-1 之间的浮点数，测试使用）"""
        return max(0.0, min(1.0, self._calculate_fragmentation() / 100.0))

    def get_gc_stats(self) -> dict[str, Any]:
        """获取垃圾回收统计信息"""
        try:
            stats = gc.get_stats()
            total_collections = sum(s.get("collections", 0) for s in stats)
            total_collected = sum(s.get("collected", 0) for s in stats)
            total_uncollectable = sum(s.get("uncollectable", 0) for s in stats)
            return {
                "collections": total_collections,
                "collected": total_collected,
                "uncollectable": total_uncollectable,
            }
        except Exception as e:  # pragma: no cover - 防御性
            logger.debug(f"获取GC统计失败: {e}")
            return {"collections": 0, "collected": 0, "uncollectable": 0}

    def get_memory_alerts(self) -> list[dict[str, Any]]:
        """根据阈值生成内存警报"""
        alerts: list[dict[str, Any]] = []
        metrics = self.get_current_metrics()

        if metrics.percent >= self.threshold_critical:
            alerts.append({"level": "critical", "message": "内存使用已达严重级别"})
        elif metrics.percent >= self.threshold_warning:
            alerts.append({"level": "warning", "message": "内存使用已达警告级别"})

        return alerts

    def add_monitoring_callback(self, callback: Callable[[MemoryMetrics], None]) -> None:
        """添加监控回调（测试使用）"""
        self._monitoring_callbacks.append(callback)

    def _cleanup_history(self) -> None:
        """清理历史记录，保持在 max_history 范围内"""
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history :]

    # 上下文管理器支持
    def __enter__(self) -> "MemoryManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop_monitoring()


# 全局内存管理器实例与便捷函数
memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """获取全局内存管理器单例"""
    return memory_manager


def close_memory_manager() -> None:
    """关闭全局内存管理器（测试使用）"""
    try:
        memory_manager.stop_monitoring()
    except Exception:  # pragma: no cover - 防御性
        pass

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
