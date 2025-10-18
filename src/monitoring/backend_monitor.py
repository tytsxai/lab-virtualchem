"""
后端监控模块

功能:
- 日志追踪 (OpenTelemetry风格)
- 性能指标 (APM工具)
- 健康检查
- 资源监控
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""

    COUNTER = "counter"  # 计数器
    GAUGE = "gauge"  # 仪表
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"  # 计时器


@dataclass
class Metric:
    """性能指标"""

    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "unit": self.unit,
        }


@dataclass
class Span:
    """追踪跨度 (类似OpenTelemetry Span)"""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: str = "ok"  # ok, error
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)

    def finish(self) -> None:
        """结束跨度"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def log(self, message: str, **fields) -> None:
        """添加日志"""
        self.logs.append({"timestamp": datetime.now().isoformat(), "message": message, **fields})

    def set_tag(self, key: str, value: Any) -> None:
        """设置标签"""
        self.tags[key] = value

    def set_error(self, error: Exception) -> None:
        """设置错误"""
        self.status = "error"
        self.tags["error"] = True
        self.tags["error.type"] = type(error).__name__
        self.tags["error.message"] = str(error)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
        }


class APMCollector:
    """应用性能监控收集器"""

    def __init__(self, app_name: str = "VirtualChemLab", log_dir: Path | None = None):
        self.app_name = app_name
        self.log_dir = log_dir or Path("logs/apm")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._metrics: deque = deque(maxlen=10000)
        self._spans: deque = deque(maxlen=5000)
        self._lock = threading.Lock()

        # 计数器存储
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}

    def increment_counter(self, name: str, value: float = 1.0, **tags) -> None:
        """增加计数器"""
        with self._lock:
            key = self._metric_key(name, tags)
            self._counters[key] = self._counters.get(key, 0) + value

        self._record_metric(name, MetricType.COUNTER, value, tags)

    def set_gauge(self, name: str, value: float, **tags) -> None:
        """设置仪表值"""
        with self._lock:
            key = self._metric_key(name, tags)
            self._gauges[key] = value

        self._record_metric(name, MetricType.GAUGE, value, tags)

    def record_histogram(self, name: str, value: float, **tags) -> None:
        """记录直方图值"""
        self._record_metric(name, MetricType.HISTOGRAM, value, tags)

    def time_operation(self, operation_name: str, **tags):
        """计时装饰器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start) * 1000
                    self.record_histogram(f"{operation_name}.duration", duration_ms, **tags)
                    self.increment_counter(f"{operation_name}.success", **tags)
                    return result
                except Exception:
                    duration_ms = (time.time() - start) * 1000
                    self.record_histogram(f"{operation_name}.duration", duration_ms, **tags)
                    self.increment_counter(f"{operation_name}.error", **tags)
                    raise

            return wrapper

        return decorator

    def get_metrics(
        self,
        name: str | None = None,
        metric_type: MetricType | None = None,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[Metric]:
        """获取指标"""
        with self._lock:
            metrics = list(self._metrics)

        # 过滤
        if name:
            metrics = [m for m in metrics if m.name == name]
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]

        return metrics[-limit:]

    def get_metric_stats(self, name: str, since: datetime | None = None) -> dict[str, Any]:
        """获取指标统计"""
        metrics = self.get_metrics(name=name, since=since)

        if not metrics:
            return {}

        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "sum": sum(values),
        }

    def _record_metric(self, name: str, metric_type: MetricType, value: float, tags: dict[str, str]) -> None:
        """记录指标"""
        metric = Metric(name=name, metric_type=metric_type, value=value, timestamp=datetime.now(), tags=tags)

        with self._lock:
            self._metrics.append(metric)

        # 写入日志
        self._write_metric_log(metric)

    def _metric_key(self, name: str, tags: dict[str, str]) -> str:
        """生成指标键"""
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]" if tag_str else name

    def _write_metric_log(self, metric: Metric) -> None:
        """写入指标日志"""
        try:
            log_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass


class BackendMonitor:
    """后端监控器"""

    def __init__(self, app_name: str = "VirtualChemLab", enable_resource_monitoring: bool = True):
        self.app_name = app_name
        self.apm = APMCollector(app_name)

        self._start_time = datetime.now()
        self._resource_monitor_thread: threading.Thread | None = None
        self._resource_monitor_running = False

        if enable_resource_monitoring:
            self.start_resource_monitoring()

    def start_resource_monitoring(self, interval_seconds: int = 60) -> None:
        """启动资源监控"""
        if self._resource_monitor_running:
            return

        self._resource_monitor_running = True
        self._resource_monitor_thread = threading.Thread(
            target=self._resource_monitor_loop, args=(interval_seconds,), daemon=True
        )
        self._resource_monitor_thread.start()

    def stop_resource_monitoring(self) -> None:
        """停止资源监控"""
        self._resource_monitor_running = False
        if self._resource_monitor_thread:
            self._resource_monitor_thread.join(timeout=5)

    def _resource_monitor_loop(self, interval: int) -> None:
        """资源监控循环"""
        while self._resource_monitor_running:
            try:
                self._collect_system_metrics()
            except Exception as e:
                logger.info(f"资源监控错误: {e}")

            time.sleep(interval)

    def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        self.apm.set_gauge("system.cpu.percent", cpu_percent)

        # 内存
        memory = psutil.virtual_memory()
        self.apm.set_gauge("system.memory.percent", memory.percent)
        self.apm.set_gauge("system.memory.used_mb", memory.used / 1024 / 1024)
        self.apm.set_gauge("system.memory.available_mb", memory.available / 1024 / 1024)

        # 磁盘
        disk = psutil.disk_usage("/")
        self.apm.set_gauge("system.disk.percent", disk.percent)
        self.apm.set_gauge("system.disk.used_gb", disk.used / 1024 / 1024 / 1024)
        self.apm.set_gauge("system.disk.free_gb", disk.free / 1024 / 1024 / 1024)

        # 进程
        process = psutil.Process()
        self.apm.set_gauge("process.cpu.percent", process.cpu_percent())
        self.apm.set_gauge("process.memory.rss_mb", process.memory_info().rss / 1024 / 1024)
        self.apm.set_gauge("process.threads", process.num_threads())

    def get_health_status(self) -> dict[str, Any]:
        """获取健康状态"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # 判断健康状态
            is_healthy = True
            issues = []

            if cpu_percent > 80:
                is_healthy = False
                issues.append(f"CPU使用率过高: {cpu_percent}%")

            if memory.percent > 80:
                is_healthy = False
                issues.append(f"内存使用率过高: {memory.percent}%")

            if disk.percent > 90:
                is_healthy = False
                issues.append(f"磁盘使用率过高: {disk.percent}%")

            uptime_seconds = (datetime.now() - self._start_time).total_seconds()

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "uptime_seconds": uptime_seconds,
                "issues": issues,
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        # 获取最近的指标
        since = datetime.now() - timedelta(minutes=5)
        metrics = self.apm.get_metrics(since=since)

        # 按类型分组
        by_type = {}
        for metric in metrics:
            metric_type = metric.metric_type.value
            if metric_type not in by_type:
                by_type[metric_type] = []
            by_type[metric_type].append(metric)

        return {
            "total_metrics": len(metrics),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "health": self.get_health_status(),
        }


# 全局监控实例
backend_monitor = BackendMonitor()
