"""
性能监控模块

监控应用性能指标，包括：
- CPU使用率
- 内存使用
- 响应时间
- 帧率（FPS）
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

import psutil

from .log_safety import sanitize_log_data

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, window_size: int = 60):
        """
        初始化性能监控器

        Args:
            window_size: 滑动窗口大小（保留最近N个数据点）
        """
        self.window_size = window_size
        self.metrics: dict[str, deque] = {
            "cpu": deque(maxlen=window_size),
            "memory": deque(maxlen=window_size),
            "response_time": deque(maxlen=window_size),
        }
        self.process = psutil.Process()
        self._last_check_time = time.time()

    def record_cpu_usage(self) -> PerformanceMetric:
        """记录CPU使用率"""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            metric = PerformanceMetric(
                name="cpu_usage", value=cpu_percent, unit="%", timestamp=datetime.now()
            )
            self.metrics["cpu"].append(metric)
            return metric
        except Exception as e:
            logger.error("记录CPU使用失败: %s", sanitize_log_data(str(e)))
            raise

    def record_memory_usage(self) -> PerformanceMetric:
        """记录内存使用"""
        try:
            mem_info = self.process.memory_info()
            memory_mb = mem_info.rss / (1024**2)
            metric = PerformanceMetric(
                name="memory_usage",
                value=memory_mb,
                unit="MB",
                timestamp=datetime.now(),
                metadata={
                    "rss": mem_info.rss,
                    "vms": mem_info.vms,
                },
            )
            self.metrics["memory"].append(metric)
            return metric
        except Exception as e:
            logger.error("记录内存使用失败: %s", sanitize_log_data(str(e)))
            raise

    def record_response_time(
        self, operation: str, duration_ms: float
    ) -> PerformanceMetric:
        """
        记录操作响应时间

        Args:
            operation: 操作名称
            duration_ms: 持续时间（毫秒）
        """
        try:
            metric = PerformanceMetric(
                name="response_time",
                value=duration_ms,
                unit="ms",
                timestamp=datetime.now(),
                metadata={"operation": operation},
            )
            self.metrics["response_time"].append(metric)
            return metric
        except Exception as e:
            logger.error("记录响应时间失败: %s", sanitize_log_data(str(e)))
            raise

    def get_average_cpu(self) -> float:
        """获取平均CPU使用率"""
        if not self.metrics["cpu"]:
            return 0.0
        return sum(m.value for m in self.metrics["cpu"]) / len(self.metrics["cpu"])

    def get_average_memory(self) -> float:
        """获取平均内存使用（MB）"""
        if not self.metrics["memory"]:
            return 0.0
        return sum(m.value for m in self.metrics["memory"]) / len(
            self.metrics["memory"]
        )

    def get_average_response_time(self) -> float:
        """获取平均响应时间（ms）"""
        if not self.metrics["response_time"]:
            return 0.0
        return sum(m.value for m in self.metrics["response_time"]) / len(
            self.metrics["response_time"]
        )

    def get_peak_memory(self) -> float:
        """获取峰值内存使用（MB）"""
        if not self.metrics["memory"]:
            return 0.0
        return max(m.value for m in self.metrics["memory"])

    def get_summary(self) -> dict:
        """获取性能摘要"""
        return {
            "cpu": {
                "current": self.metrics["cpu"][-1].value if self.metrics["cpu"] else 0,
                "average": self.get_average_cpu(),
                "samples": len(self.metrics["cpu"]),
            },
            "memory": {
                "current": self.metrics["memory"][-1].value
                if self.metrics["memory"]
                else 0,
                "average": self.get_average_memory(),
                "peak": self.get_peak_memory(),
                "samples": len(self.metrics["memory"]),
            },
            "response_time": {
                "average": self.get_average_response_time(),
                "samples": len(self.metrics["response_time"]),
            },
            "timestamp": datetime.now().isoformat(),
        }

    def check_thresholds(self, thresholds: dict | None = None) -> list[str]:
        """
        检查是否超过阈值

        Args:
            thresholds: 阈值配置，如 {'cpu': 80, 'memory': 500}

        Returns:
            超过阈值的警告列表
        """
        if thresholds is None:
            thresholds = {
                "cpu": 80,  # 80%
                "memory": 500,  # 500MB
                "response_time": 1000,  # 1000ms
            }

        warnings = []

        # 检查CPU
        avg_cpu = self.get_average_cpu()
        if avg_cpu > thresholds.get("cpu", 80):
            warnings.append(f"CPU使用率过高: {avg_cpu:.1f}% > {thresholds['cpu']}%")

        # 检查内存
        peak_mem = self.get_peak_memory()
        if peak_mem > thresholds.get("memory", 500):
            warnings.append(
                f"内存使用过高: {peak_mem:.0f}MB > {thresholds['memory']}MB"
            )

        # 检查响应时间
        avg_rt = self.get_average_response_time()
        if avg_rt > thresholds.get("response_time", 1000):
            warnings.append(
                f"响应时间过长: {avg_rt:.0f}ms > {thresholds['response_time']}ms"
            )

        return warnings

    def clear(self) -> None:
        """清空所有指标"""
        for metric_list in self.metrics.values():
            metric_list.clear()


class PerformanceTimer:
    """性能计时器（上下文管理器）"""

    def __init__(self, monitor: PerformanceMonitor, operation: str):
        """
        初始化计时器

        Args:
            monitor: 性能监控器
            operation: 操作名称
        """
        self.monitor = monitor
        self.operation = operation
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.monitor.record_response_time(self.operation, duration_ms)


# 单例实例
_performance_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器单例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
