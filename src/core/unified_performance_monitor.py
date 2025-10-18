"""
统一性能监控系统
整合所有性能监控功能，提供统一的性能管理接口
"""

from __future__ import annotations

import gc
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import psutil

from .common_exceptions import PerformanceError
from .error_handler import get_error_handler, safe_execute

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_USAGE = "network_usage"
    FPS = "fps"
    FRAME_TIME = "frame_time"
    RENDER_TIME = "render_time"
    UPDATE_TIME = "update_time"
    FUNCTION_TIME = "function_time"
    CACHE_HIT_RATE = "cache_hit_rate"


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    timestamp: float
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "unit": self.unit,
            "tags": self.tags
        }


@dataclass
class PerformanceThreshold:
    """性能阈值"""
    metric_name: str
    threshold_value: float
    comparison: str  # "gt", "lt", "eq"
    severity: str = "warning"
    action: Optional[str] = None


class PerformanceCollector:
    """性能收集器"""

    def __init__(self, max_history: int = 1000):
        self._max_history = max_history
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.RLock()

    def collect_metric(self, metric: PerformanceMetric) -> None:
        """收集指标"""
        with self._lock:
            self._metrics[metric.name].append(metric)

    def get_metric_history(self, metric_name: str, limit: Optional[int] = None) -> List[PerformanceMetric]:
        """获取指标历史"""
        with self._lock:
            history = list(self._metrics[metric_name])
            if limit:
                history = history[-limit:]
            return history

    def get_latest_metric(self, metric_name: str) -> Optional[PerformanceMetric]:
        """获取最新指标"""
        with self._lock:
            if metric_name in self._metrics and self._metrics[metric_name]:
                return self._metrics[metric_name][-1]
            return None

    def get_metric_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """获取指标统计"""
        with self._lock:
            if metric_name not in self._metrics or not self._metrics[metric_name]:
                return None

            values = [m.value for m in self._metrics[metric_name]]
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1]
            }

    def clear_metrics(self, metric_name: Optional[str] = None) -> None:
        """清除指标"""
        with self._lock:
            if metric_name:
                self._metrics[metric_name].clear()
            else:
                self._metrics.clear()


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        self._thresholds: List[PerformanceThreshold] = []
        self._error_handler = get_error_handler()

    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """添加阈值"""
        self._thresholds.append(threshold)

    def check_thresholds(self, metric: PerformanceMetric) -> List[PerformanceThreshold]:
        """检查阈值"""
        triggered = []

        for threshold in self._thresholds:
            if threshold.metric_name != metric.name:
                continue

            if self._compare_value(metric.value, threshold.threshold_value, threshold.comparison):
                triggered.append(threshold)

                # 创建性能错误
                perf_error = PerformanceError(
                    message=f"Performance threshold exceeded: {metric.name} = {metric.value}",
                    metric=metric.name,
                    threshold=threshold.threshold_value,
                    actual_value=metric.value,
                    details={
                        "comparison": threshold.comparison,
                        "severity": threshold.severity,
                        "action": threshold.action
                    }
                )

                self._error_handler.handle_error(perf_error)

        return triggered

    def _compare_value(self, value: float, threshold: float, comparison: str) -> bool:
        """比较值"""
        if comparison == "gt":
            return value > threshold
        elif comparison == "lt":
            return value < threshold
        elif comparison == "eq":
            return abs(value - threshold) < 0.001
        else:
            return False


class UnifiedPerformanceMonitor:
    """统一性能监控器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._collector = PerformanceCollector(
            max_history=self._config.get("max_history", 1000)
        )
        self._analyzer = PerformanceAnalyzer()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._error_handler = get_error_handler()

        # 系统监控
        self._process = psutil.Process()

        # 性能缓存
        self._cache_stats = {"hits": 0, "misses": 0}

        # 初始化默认阈值
        self._setup_default_thresholds()

    def _setup_default_thresholds(self) -> None:
        """设置默认阈值"""
        # CPU使用率阈值
        self._analyzer.add_threshold(PerformanceThreshold(
            metric_name=MetricType.CPU_USAGE.value,
            threshold_value=80.0,
            comparison="gt",
            severity="warning",
            action="reduce_load"
        ))

        # 内存使用率阈值
        self._analyzer.add_threshold(PerformanceThreshold(
            metric_name=MetricType.MEMORY_USAGE.value,
            threshold_value=85.0,
            comparison="gt",
            severity="warning",
            action="cleanup_memory"
        ))

        # 帧率阈值
        self._analyzer.add_threshold(PerformanceThreshold(
            metric_name=MetricType.FPS.value,
            threshold_value=30.0,
            comparison="lt",
            severity="warning",
            action="optimize_rendering"
        ))

    def start_monitoring(self, interval: float = 1.0) -> None:
        """开始监控"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")

    def _monitor_loop(self, interval: float) -> None:
        """监控循环"""
        while self._monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
                time.sleep(interval)

    def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        current_time = time.time()

        # CPU使用率
        cpu_percent = self._process.cpu_percent()
        self._collector.collect_metric(PerformanceMetric(
            name=MetricType.CPU_USAGE.value,
            value=cpu_percent,
            timestamp=current_time,
            unit="%"
        ))

        # 内存使用率
        memory_info = self._process.memory_info()
        memory_percent = (memory_info.rss / (1024 * 1024 * 1024)) * 100  # GB
        self._collector.collect_metric(PerformanceMetric(
            name=MetricType.MEMORY_USAGE.value,
            value=memory_percent,
            timestamp=current_time,
            unit="%"
        ))

        # 磁盘使用率
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        self._collector.collect_metric(PerformanceMetric(
            name=MetricType.DISK_USAGE.value,
            value=disk_percent,
            timestamp=current_time,
            unit="%"
        ))

    def measure_function(self, func_name: Optional[str] = None):
        """函数性能测量装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = (end_time - start_time) * 1000  # 转换为毫秒

                    self._collector.collect_metric(PerformanceMetric(
                        name=MetricType.FUNCTION_TIME.value,
                        value=duration,
                        timestamp=end_time,
                        unit="ms",
                        tags={"function": func_name or func.__name__}
                    ))
            return wrapper
        return decorator

    @contextmanager
    def measure_context(self, context_name: str):
        """上下文性能测量"""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # 转换为毫秒

            self._collector.collect_metric(PerformanceMetric(
                name=MetricType.FUNCTION_TIME.value,
                value=duration,
                timestamp=end_time,
                unit="ms",
                tags={"context": context_name}
            ))

    def record_fps(self, fps: float) -> None:
        """记录帧率"""
        self._collector.collect_metric(PerformanceMetric(
            name=MetricType.FPS.value,
            value=fps,
            timestamp=time.time(),
            unit="fps"
        ))

    def record_frame_time(self, frame_time: float) -> None:
        """记录帧时间"""
        self._collector.collect_metric(PerformanceMetric(
            name=MetricType.FRAME_TIME.value,
            value=frame_time,
            timestamp=time.time(),
            unit="ms"
        ))

    def record_render_time(self, render_time: float) -> None:
        """记录渲染时间"""
        self._collector.collect_metric(PerformanceMetric(
            name=MetricType.RENDER_TIME.value,
            value=render_time,
            timestamp=time.time(),
            unit="ms"
        ))

    def record_cache_hit(self) -> None:
        """记录缓存命中"""
        self._cache_stats["hits"] += 1
        self._update_cache_hit_rate()

    def record_cache_miss(self) -> None:
        """记录缓存未命中"""
        self._cache_stats["misses"] += 1
        self._update_cache_hit_rate()

    def _update_cache_hit_rate(self) -> None:
        """更新缓存命中率"""
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        if total > 0:
            hit_rate = (self._cache_stats["hits"] / total) * 100
            self._collector.collect_metric(PerformanceMetric(
                name=MetricType.CACHE_HIT_RATE.value,
                value=hit_rate,
                timestamp=time.time(),
                unit="%"
            ))

    def get_metric_history(self, metric_name: str, limit: Optional[int] = None) -> List[PerformanceMetric]:
        """获取指标历史"""
        return self._collector.get_metric_history(metric_name, limit)

    def get_latest_metric(self, metric_name: str) -> Optional[PerformanceMetric]:
        """获取最新指标"""
        return self._collector.get_latest_metric(metric_name)

    def get_metric_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """获取指标统计"""
        return self._collector.get_metric_stats(metric_name)

    def get_all_metrics(self) -> Dict[str, List[PerformanceMetric]]:
        """获取所有指标"""
        return {name: list(metrics) for name, metrics in self._collector._metrics.items()}

    def clear_metrics(self, metric_name: Optional[str] = None) -> None:
        """清除指标"""
        self._collector.clear_metrics(metric_name)

    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """添加阈值"""
        self._analyzer.add_threshold(threshold)

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "timestamp": time.time(),
            "metrics": {},
            "thresholds": len(self._analyzer._thresholds),
            "monitoring": self._monitoring
        }

        # 收集所有指标的统计信息
        for metric_name in self._collector._metrics.keys():
            stats = self._collector.get_metric_stats(metric_name)
            if stats:
                report["metrics"][metric_name] = stats

        return report

    def optimize_performance(self) -> None:
        """优化性能"""
        try:
            # 垃圾回收
            gc.collect()

            # 清理指标历史
            self._collector.clear_metrics()

            logger.info("Performance optimization completed")
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")


# 全局性能监控器实例
_global_performance_monitor = UnifiedPerformanceMonitor()


def get_performance_monitor() -> UnifiedPerformanceMonitor:
    """获取全局性能监控器"""
    return _global_performance_monitor


def measure_performance(func_name: Optional[str] = None):
    """性能测量装饰器"""
    return _global_performance_monitor.measure_function(func_name)


def measure_context(context_name: str):
    """上下文性能测量"""
    return _global_performance_monitor.measure_context(context_name)


def record_fps(fps: float) -> None:
    """记录帧率"""
    _global_performance_monitor.record_fps(fps)


def record_frame_time(frame_time: float) -> None:
    """记录帧时间"""
    _global_performance_monitor.record_frame_time(frame_time)


def record_render_time(render_time: float) -> None:
    """记录渲染时间"""
    _global_performance_monitor.record_render_time(render_time)


def record_cache_hit() -> None:
    """记录缓存命中"""
    _global_performance_monitor.record_cache_hit()


def record_cache_miss() -> None:
    """记录缓存未命中"""
    _global_performance_monitor.record_cache_miss()
