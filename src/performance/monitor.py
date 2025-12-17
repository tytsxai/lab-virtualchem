"""
性能监控系统
实时监控系统性能指标
"""

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import psutil  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""

    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_history: int = 1000):
        """
        初始化收集器

        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self._metrics: dict[str, deque[PerformanceMetric]] = {}

    def record(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        记录指标

        Args:
            name: 指标名称
            value: 指标值
            unit: 单位
            tags: 标签
        """
        metric = PerformanceMetric(name=name, value=value, unit=unit, tags=tags or {})

        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=self.max_history)

        self._metrics[name].append(metric)

    def get_latest(self, name: str) -> PerformanceMetric | None:
        """
        获取最新指标

        Args:
            name: 指标名称

        Returns:
            指标或None
        """
        if name in self._metrics and self._metrics[name]:
            return self._metrics[name][-1]
        return None

    def get_history(
        self, name: str, duration: timedelta | None = None
    ) -> list[PerformanceMetric]:
        """
        获取历史指标

        Args:
            name: 指标名称
            duration: 时间范围

        Returns:
            指标列表
        """
        if name not in self._metrics:
            return []

        metrics = list(self._metrics[name])

        if duration:
            cutoff = datetime.now() - duration
            metrics = [m for m in metrics if m.timestamp >= cutoff]

        return metrics

    def get_statistics(self, name: str) -> dict[str, float]:
        """
        获取指标统计

        Args:
            name: 指标名称

        Returns:
            统计信息
        """
        metrics = self.get_history(name)

        if not metrics:
            return {}

        values = [m.value for m in metrics]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
        }


class SystemMonitor:
    """系统监控器"""

    def __init__(self, collector: MetricsCollector):
        """
        初始化监控器

        Args:
            collector: 指标收集器
        """
        self.collector = collector
        self._process = psutil.Process()

    def collect_cpu_metrics(self) -> None:
        """收集CPU指标"""
        # 系统CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.collector.record("system.cpu.percent", cpu_percent, "%")

        # 进程CPU使用率
        process_cpu = self._process.cpu_percent()
        self.collector.record("process.cpu.percent", process_cpu, "%")

        # CPU核心数
        cpu_count = psutil.cpu_count()
        self.collector.record("system.cpu.count", cpu_count, "cores")

    def collect_memory_metrics(self) -> None:
        """收集内存指标"""
        # 系统内存
        mem = psutil.virtual_memory()
        self.collector.record("system.memory.total", mem.total / 1024 / 1024, "MB")
        self.collector.record("system.memory.used", mem.used / 1024 / 1024, "MB")
        self.collector.record("system.memory.percent", mem.percent, "%")

        # 进程内存
        process_mem = self._process.memory_info()
        self.collector.record("process.memory.rss", process_mem.rss / 1024 / 1024, "MB")
        self.collector.record("process.memory.vms", process_mem.vms / 1024 / 1024, "MB")

    def collect_disk_metrics(self) -> None:
        """收集磁盘指标"""
        disk = psutil.disk_usage("/")
        self.collector.record(
            "system.disk.total", disk.total / 1024 / 1024 / 1024, "GB"
        )
        self.collector.record("system.disk.used", disk.used / 1024 / 1024 / 1024, "GB")
        self.collector.record("system.disk.percent", disk.percent, "%")

    def collect_network_metrics(self) -> None:
        """收集网络指标"""
        net_io = psutil.net_io_counters()
        self.collector.record(
            "system.network.bytes_sent", net_io.bytes_sent / 1024 / 1024, "MB"
        )
        self.collector.record(
            "system.network.bytes_recv", net_io.bytes_recv / 1024 / 1024, "MB"
        )

    def collect_all(self) -> None:
        """收集所有指标"""
        try:
            self.collect_cpu_metrics()
            self.collect_memory_metrics()
            self.collect_disk_metrics()
            self.collect_network_metrics()
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")


class ResponseTimeTracker:
    """响应时间追踪器"""

    def __init__(self, collector: MetricsCollector):
        """
        初始化追踪器

        Args:
            collector: 指标收集器
        """
        self.collector = collector

    def track(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        响应时间追踪装饰器

        Args:
            name: 操作名称
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.collector.record(
                        f"response_time.{name}",
                        duration * 1000,  # 转换为毫秒
                        "ms",
                    )

            return wrapper

        return decorator

    def track_async(
        self, name: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        异步响应时间追踪装饰器

        Args:
            name: 操作名称
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.collector.record(
                        f"response_time.{name}", duration * 1000, "ms"
                    )

            return wrapper

        return decorator


class ThroughputMonitor:
    """吞吐量监控器"""

    def __init__(self, collector: MetricsCollector):
        """
        初始化监控器

        Args:
            collector: 指标收集器
        """
        self.collector = collector
        self._counters: dict[str, int] = {}
        self._last_report = datetime.now()

    def increment(self, name: str, amount: int = 1) -> None:
        """
        增加计数

        Args:
            name: 计数器名称
            amount: 增量
        """
        if name not in self._counters:
            self._counters[name] = 0
        self._counters[name] += amount

    def report(self) -> None:
        """报告吞吐量"""
        now = datetime.now()
        duration = (now - self._last_report).total_seconds()

        if duration > 0:
            for name, count in self._counters.items():
                throughput = count / duration
                self.collector.record(f"throughput.{name}", throughput, "ops/s")

        # 重置计数器
        self._counters.clear()
        self._last_report = now


class PerformanceMonitor:
    """性能监控主类"""

    def __init__(self) -> None:
        self.collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.collector)
        self.response_tracker = ResponseTimeTracker(self.collector)
        self.throughput_monitor = ThroughputMonitor(self.collector)

    def get_dashboard_data(self) -> dict[str, Any]:
        """
        获取仪表板数据

        Returns:
            仪表板数据
        """
        return {
            "cpu": self.collector.get_statistics("process.cpu.percent"),
            "memory": self.collector.get_statistics("process.memory.rss"),
            "response_times": {
                name: self.collector.get_statistics(name)
                for name in self.collector._metrics
                if name.startswith("response_time.")
            },
        }

    def generate_report(self) -> str:
        """
        生成性能报告

        Returns:
            报告文本
        """
        lines = ["=== 性能监控报告 ===\n"]

        # CPU
        cpu_stats = self.collector.get_statistics("process.cpu.percent")
        if cpu_stats:
            lines.append(
                f"CPU使用率: {cpu_stats['latest']:.1f}% (平均: {cpu_stats['avg']:.1f}%)"
            )

        # 内存
        mem_stats = self.collector.get_statistics("process.memory.rss")
        if mem_stats:
            lines.append(
                f"内存使用: {mem_stats['latest']:.1f}MB (平均: {mem_stats['avg']:.1f}MB)"
            )

        # 响应时间
        lines.append("\n响应时间:")
        for name in self.collector._metrics:
            if name.startswith("response_time."):
                stats = self.collector.get_statistics(name)
                operation = name.replace("response_time.", "")
                lines.append(
                    f"  {operation}: {stats['latest']:.2f}ms "
                    f"(平均: {stats['avg']:.2f}ms, 最大: {stats['max']:.2f}ms)"
                )

        return "\n".join(lines)


# 全局监控实例
_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def track_performance(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """性能追踪装饰器"""
    monitor = get_performance_monitor()
    return monitor.response_tracker.track(name)


def track_performance_async(
    name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """异步性能追踪装饰器"""
    monitor = get_performance_monitor()
    return monitor.response_tracker.track_async(name)


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 性能监控演示 ===\n")

    monitor = PerformanceMonitor()

    # 收集系统指标
    monitor.system_monitor.collect_all()

    # 模拟一些操作
    @track_performance("test_operation")
    def slow_operation() -> str:
        time.sleep(0.1)
        return "完成"

    for _ in range(5):
        slow_operation()

    # 生成报告
    report = monitor.generate_report()
    logger.info("\n" + report)
