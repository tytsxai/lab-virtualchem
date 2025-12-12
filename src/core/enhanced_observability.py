"""
增强可观测性系统
提供统一的日志、追踪、指标收集和分布式监控功能
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .enhanced_event_bus import EventPriority, publish_event
from .error_handler import get_error_handler

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TraceType(Enum):
    """追踪类型"""
    REQUEST = "request"
    DATABASE = "database"
    CACHE = "cache"
    NETWORK = "network"
    UI = "ui"
    BUSINESS = "business"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: float
    level: LogLevel
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    trace_id: str | None = None
    span_id: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "thread_id": self.thread_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "tags": self.tags,
            "extra_data": self.extra_data
        }


@dataclass
class TraceSpan:
    """追踪跨度"""
    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    trace_type: TraceType = TraceType.REQUEST
    tags: dict[str, str] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def finish(self) -> None:
        """完成跨度"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    def add_log(self, level: LogLevel, message: str, **kwargs) -> None:
        """添加日志"""
        self.logs.append({
            "timestamp": time.time(),
            "level": level.value,
            "message": message,
            **kwargs
        })

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "trace_type": self.trace_type.value,
            "tags": self.tags,
            "logs": self.logs,
            "error": self.error
        }


@dataclass
class MetricData:
    """指标数据"""
    name: str
    value: float
    timestamp: float
    tags: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "unit": self.unit
        }


class EnhancedObservability:
    """增强可观测性系统"""

    def __init__(self, config: dict[str, Any] | None = None):
        self._config = config or {}
        self._error_handler = get_error_handler()

        # 日志系统
        self._log_entries: list[LogEntry] = []
        self._log_file: Path | None = None
        self._log_level = LogLevel.INFO
        self._max_log_entries = self._config.get("max_log_entries", 10000)

        # 追踪系统
        self._active_spans: dict[str, TraceSpan] = {}
        self._completed_spans: list[TraceSpan] = []
        self._trace_context: dict[str, str] = {}
        self._max_spans = self._config.get("max_spans", 1000)

        # 指标系统
        self._metrics: dict[str, list[MetricData]] = {}
        self._metric_aggregates: dict[str, dict[str, float]] = {}
        self._max_metrics = self._config.get("max_metrics", 5000)

        # 统计信息
        self._stats = {
            "logs_count": 0,
            "spans_count": 0,
            "metrics_count": 0,
            "errors_count": 0
        }

        # 初始化日志文件
        self._setup_log_file()

        # 启动后台任务
        self._running = True
        self._background_task = threading.Thread(target=self._background_worker, daemon=True)
        self._background_task.start()

    def _setup_log_file(self) -> None:
        """设置日志文件"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self._log_file = log_dir / f"observability_{timestamp}.json"

    def _background_worker(self) -> None:
        """后台工作线程"""
        while self._running:
            try:
                # 清理过期数据
                self._cleanup_expired_data()

                # 写入日志文件
                self._write_logs_to_file()

                # 计算指标聚合
                self._calculate_metric_aggregates()

                time.sleep(5)  # 每5秒执行一次
            except Exception as e:
                logger.error(f"Background worker error: {e}")
                time.sleep(10)

    def _cleanup_expired_data(self) -> None:
        """清理过期数据"""
        # 清理日志条目
        if len(self._log_entries) > self._max_log_entries:
            self._log_entries = self._log_entries[-self._max_log_entries:]

        # 清理完成的跨度
        if len(self._completed_spans) > self._max_spans:
            self._completed_spans = self._completed_spans[-self._max_spans:]

        # 清理指标数据
        for metric_name in list(self._metrics.keys()):
            if len(self._metrics[metric_name]) > self._max_metrics:
                self._metrics[metric_name] = self._metrics[metric_name][-self._max_metrics:]

    def _write_logs_to_file(self) -> None:
        """写入日志到文件"""
        if not self._log_file or not self._log_entries:
            return

        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                for entry in self._log_entries[-100:]:  # 只写入最近的100条
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write logs to file: {e}")

    def _calculate_metric_aggregates(self) -> None:
        """计算指标聚合"""
        for metric_name, data_points in self._metrics.items():
            if not data_points:
                continue

            values = [dp.value for dp in data_points]
            self._metric_aggregates[metric_name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1]
            }

    def log(
        self,
        level: LogLevel,
        message: str,
        module: str = "",
        function: str = "",
        line_number: int = 0,
        **kwargs
    ) -> None:
        """记录日志"""
        if level.value not in [lvl.value for lvl in LogLevel]:
            return

        # 检查日志级别
        if self._should_log(level):
            entry = LogEntry(
                timestamp=time.time(),
                level=level,
                message=message,
                module=module,
                function=function,
                line_number=line_number,
                thread_id=threading.get_ident(),
                trace_id=self._trace_context.get("trace_id"),
                span_id=self._trace_context.get("span_id"),
                tags=self._trace_context.copy(),
                extra_data=kwargs
            )

            self._log_entries.append(entry)
            self._stats["logs_count"] += 1

            # 发布日志事件
            publish_event("observability_log", entry.to_dict(), priority=EventPriority.NORMAL)

    def _should_log(self, level: LogLevel) -> bool:
        """检查是否应该记录日志"""
        level_values = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }

        return level_values[level] >= level_values[self._log_level]

    def start_trace(
        self,
        operation_name: str,
        trace_type: TraceType = TraceType.REQUEST,
        parent_span_id: str | None = None,
        **tags
    ) -> str:
        """开始追踪"""
        trace_id = self._trace_context.get("trace_id") or str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            trace_type=trace_type,
            tags=tags
        )

        self._active_spans[span_id] = span

        # 更新追踪上下文
        self._trace_context["trace_id"] = trace_id
        self._trace_context["span_id"] = span_id

        # 发布追踪事件
        publish_event("observability_trace_start", span.to_dict(), priority=EventPriority.NORMAL)

        return span_id

    def finish_trace(self, span_id: str, error: str | None = None) -> None:
        """完成追踪"""
        if span_id not in self._active_spans:
            return

        span = self._active_spans.pop(span_id)
        span.finish()

        if error:
            span.error = error

        self._completed_spans.append(span)
        self._stats["spans_count"] += 1

        # 发布追踪事件
        publish_event("observability_trace_finish", span.to_dict(), priority=EventPriority.NORMAL)

    def add_trace_log(self, span_id: str, level: LogLevel, message: str, **kwargs) -> None:
        """添加追踪日志"""
        if span_id in self._active_spans:
            self._active_spans[span_id].add_log(level, message, **kwargs)

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        **tags
    ) -> None:
        """记录指标"""
        metric_data = MetricData(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags,
            unit=unit
        )

        if name not in self._metrics:
            self._metrics[name] = []

        self._metrics[name].append(metric_data)
        self._stats["metrics_count"] += 1

        # 发布指标事件
        publish_event("observability_metric", metric_data.to_dict(), priority=EventPriority.NORMAL)

    def increment_counter(self, name: str, value: float = 1.0, **tags) -> None:
        """增加计数器"""
        self.record_metric(f"{name}_counter", value, **tags)

    def record_histogram(self, name: str, value: float, **tags) -> None:
        """记录直方图"""
        self.record_metric(f"{name}_histogram", value, **tags)

    def record_gauge(self, name: str, value: float, **tags) -> None:
        """记录仪表盘"""
        self.record_metric(f"{name}_gauge", value, **tags)

    @contextmanager
    def trace_span(
        self,
        operation_name: str,
        trace_type: TraceType = TraceType.REQUEST,
        **tags
    ):
        """追踪跨度上下文管理器"""
        span_id = self.start_trace(operation_name, trace_type, **tags)
        try:
            yield span_id
        except Exception as e:
            self.finish_trace(span_id, str(e))
            raise
        else:
            self.finish_trace(span_id)

    def get_logs(
        self,
        level: LogLevel | None = None,
        module: str | None = None,
        limit: int | None = None
    ) -> list[LogEntry]:
        """获取日志"""
        logs = self._log_entries.copy()

        # 过滤级别
        if level:
            logs = [log for log in logs if log.level == level]

        # 过滤模块
        if module:
            logs = [log for log in logs if log.module == module]

        # 限制数量
        if limit:
            logs = logs[-limit:]

        return logs

    def get_traces(
        self,
        trace_id: str | None = None,
        operation_name: str | None = None,
        limit: int | None = None
    ) -> list[TraceSpan]:
        """获取追踪"""
        traces = self._completed_spans.copy()

        # 过滤追踪ID
        if trace_id:
            traces = [trace for trace in traces if trace.trace_id == trace_id]

        # 过滤操作名称
        if operation_name:
            traces = [trace for trace in traces if trace.operation_name == operation_name]

        # 限制数量
        if limit:
            traces = traces[-limit:]

        return traces

    def get_metrics(
        self,
        name: str | None = None,
        limit: int | None = None
    ) -> dict[str, list[MetricData]]:
        """获取指标"""
        if name:
            return {name: self._metrics.get(name, [])}

        metrics = {}
        for metric_name, data_points in self._metrics.items():
            if limit:
                metrics[metric_name] = data_points[-limit:]
            else:
                metrics[metric_name] = data_points

        return metrics

    def get_metric_aggregates(self, name: str | None = None) -> dict[str, dict[str, float]]:
        """获取指标聚合"""
        if name:
            return {name: self._metric_aggregates.get(name, {})}

        return self._metric_aggregates.copy()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "active_spans": len(self._active_spans),
            "completed_spans": len(self._completed_spans),
            "metrics_count": sum(len(data) for data in self._metrics.values()),
            "log_file": str(self._log_file) if self._log_file else None
        }

    def export_data(self, output_dir: Path) -> None:
        """导出数据"""
        output_dir.mkdir(exist_ok=True)

        # 导出日志
        logs_file = output_dir / "logs.json"
        with open(logs_file, 'w', encoding='utf-8') as f:
            json.dump([log.to_dict() for log in self._log_entries], f, indent=2, ensure_ascii=False)

        # 导出追踪
        traces_file = output_dir / "traces.json"
        with open(traces_file, 'w', encoding='utf-8') as f:
            json.dump([trace.to_dict() for trace in self._completed_spans], f, indent=2, ensure_ascii=False)

        # 导出指标
        metrics_file = output_dir / "metrics.json"
        metrics_data = {}
        for name, data_points in self._metrics.items():
            metrics_data[name] = [dp.to_dict() for dp in data_points]

        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(metrics_data, f, indent=2, ensure_ascii=False)

        # 导出统计
        stats_file = output_dir / "stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.get_stats(), f, indent=2, ensure_ascii=False)

    def cleanup(self) -> None:
        """清理资源"""
        self._running = False
        if self._background_task:
            self._background_task.join(timeout=5)

        # 清理数据
        self._log_entries.clear()
        self._active_spans.clear()
        self._completed_spans.clear()
        self._metrics.clear()
        self._metric_aggregates.clear()


# 全局可观测性系统实例
_global_observability = EnhancedObservability()


def get_observability() -> EnhancedObservability:
    """获取全局可观测性系统"""
    return _global_observability


def log(level: LogLevel, message: str, **kwargs) -> None:
    """记录日志"""
    _global_observability.log(level, message, **kwargs)


def start_trace(operation_name: str, trace_type: TraceType = TraceType.REQUEST, **tags) -> str:
    """开始追踪"""
    return _global_observability.start_trace(operation_name, trace_type, **tags)


def finish_trace(span_id: str, error: str | None = None) -> None:
    """完成追踪"""
    _global_observability.finish_trace(span_id, error)


def record_metric(name: str, value: float, unit: str = "", **tags) -> None:
    """记录指标"""
    _global_observability.record_metric(name, value, unit, **tags)


def increment_counter(name: str, value: float = 1.0, **tags) -> None:
    """增加计数器"""
    _global_observability.increment_counter(name, value, **tags)


def record_histogram(name: str, value: float, **tags) -> None:
    """记录直方图"""
    _global_observability.record_histogram(name, value, **tags)


def record_gauge(name: str, value: float, **tags) -> None:
    """记录仪表盘"""
    _global_observability.record_gauge(name, value, **tags)


def trace_span(operation_name: str, trace_type: TraceType = TraceType.REQUEST, **tags):
    """追踪跨度上下文管理器"""
    return _global_observability.trace_span(operation_name, trace_type, **tags)
