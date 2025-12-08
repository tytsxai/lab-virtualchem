"""轻量级监控桩，避免真实监控组件的副作用。"""

import uuid
from dataclasses import dataclass, field
from typing import Any


class StubAPM:
    """记录调用参数的简易APM桩。"""

    def __init__(self) -> None:
        self.counters: list[dict[str, Any]] = []
        self.gauges: list[dict[str, Any]] = []
        self.histograms: list[dict[str, Any]] = []

    def increment_counter(self, name: str, value: float = 1.0, **tags: Any) -> None:
        self.counters.append({"name": name, "value": value, "tags": tags})

    def set_gauge(self, name: str, value: float, **tags: Any) -> None:
        self.gauges.append({"name": name, "value": value, "tags": tags})

    def record_histogram(self, name: str, value: float, **tags: Any) -> None:
        self.histograms.append({"name": name, "value": value, "tags": tags})


class StubMonitor:
    """伪造的监控实例，仅暴露apm接口。"""

    def __init__(self) -> None:
        self.apm = StubAPM()


@dataclass
class StubTraceContext:
    """模拟追踪上下文."""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_span_id: str | None = None


class StubTraceManager:
    """记录追踪调用的桩。"""

    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.finished: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.tags: list[dict[str, Any]] = []

    def start_trace(self, operation_name: str, context: StubTraceContext | None = None, **tags: Any) -> StubTraceContext:
        ctx = StubTraceContext(
            trace_id=context.trace_id if context else uuid.uuid4().hex,
            parent_span_id=context.span_id if context else None,
        )
        self.started.append({"operation": operation_name, "tags": tags, "context": ctx})
        return ctx

    def log_event(self, event: str, context: StubTraceContext | None = None, **fields: Any) -> None:
        self.events.append({"event": event, "context": context, "fields": fields})

    def set_tag(self, key: str, value: Any, context: StubTraceContext | None = None) -> None:
        self.tags.append({"key": key, "value": value, "context": context})

    def finish_span(self, context: StubTraceContext, status: str = "ok", **tags: Any) -> None:
        self.finished.append({"context": context, "status": status, "tags": tags})


class StubMetricsCollector:
    """记录实验运行数据的桩。"""

    def __init__(self) -> None:
        self.recorded: list[dict[str, Any]] = []

    def record_experiment_run(self, **payload: Any) -> None:
        self.recorded.append(payload)


def build_monitoring_stubs() -> tuple[StubMonitor, StubTraceManager, StubMetricsCollector]:
    """创建一组监控桩供测试注入使用。"""
    return StubMonitor(), StubTraceManager(), StubMetricsCollector()
