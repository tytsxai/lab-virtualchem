"""
指标收集器

收集和聚合各种应用指标
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """通用指标"""

    name: str
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        """初始化指标收集器"""
        self.metrics: list[Metric] = []
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}

    def counter(self, name: str, value: int = 1, tags: dict | None = None) -> None:
        """
        记录计数器指标

        Args:
            name: 指标名称
            value: 增加值
            tags: 标签
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value

        metric = Metric(
            name=name,
            value=self.counters[name],
            tags=tags or {},
            timestamp=datetime.now(),
        )
        self.metrics.append(metric)

    def gauge(self, name: str, value: float, tags: dict | None = None) -> None:
        """
        记录仪表指标

        Args:
            name: 指标名称
            value: 当前值
            tags: 标签
        """
        self.gauges[name] = value

        metric = Metric(
            name=name, value=value, tags=tags or {}, timestamp=datetime.now()
        )
        self.metrics.append(metric)

    def get_metrics(
        self, name: str | None = None, since: datetime | None = None
    ) -> list[Metric]:
        """
        获取指标

        Args:
            name: 指标名称过滤
            since: 时间过滤

        Returns:
            指标列表
        """
        filtered = self.metrics

        if name:
            filtered = [m for m in filtered if m.name == name]

        if since:
            filtered = [m for m in filtered if m.timestamp >= since]

        return filtered

    def get_counter_value(self, name: str) -> int:
        """获取计数器当前值"""
        return self.counters.get(name, 0)

    def get_gauge_value(self, name: str) -> float | None:
        """获取仪表当前值"""
        return self.gauges.get(name)

    def clear_old_metrics(self, older_than: timedelta = timedelta(hours=1)) -> int:
        """
        清理旧指标

        Args:
            older_than: 保留时长

        Returns:
            清理的指标数量
        """
        cutoff = datetime.now() - older_than
        original_count = len(self.metrics)
        self.metrics = [m for m in self.metrics if m.timestamp >= cutoff]
        return original_count - len(self.metrics)

    def get_summary(self) -> dict:
        """获取指标摘要"""
        return {
            "total_metrics": len(self.metrics),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "oldest_metric": min((m.timestamp for m in self.metrics), default=None),
            "newest_metric": max((m.timestamp for m in self.metrics), default=None),
        }


# 单例实例
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器单例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
