"""
分布式追踪模块

功能:
- Trace ID生成和传播
- 跨度(Span)管理
- 调用链追踪
- 性能分析
"""

import json
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class TracingContext:
    """追踪上下文"""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    baggage: dict[str, Any] = field(default_factory=dict)

    def fork_child(self) -> "TracingContext":
        """创建子上下文"""
        return TracingContext(
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.span_id,
            baggage=self.baggage.copy(),
        )

    def to_headers(self) -> dict[str, str]:
        """转换为HTTP头"""
        headers = {
            "X-Trace-Id": self.trace_id,
            "X-Span-Id": self.span_id,
        }
        if self.parent_span_id:
            headers["X-Parent-Span-Id"] = self.parent_span_id

        return headers

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> Optional["TracingContext"]:
        """从HTTP头创建"""
        trace_id = headers.get("X-Trace-Id")
        if not trace_id:
            return None

        return cls(
            trace_id=trace_id,
            span_id=headers.get("X-Span-Id", generate_span_id()),
            parent_span_id=headers.get("X-Parent-Span-Id"),
        )


@dataclass
class Span:
    """追踪跨度"""

    span_id: str
    trace_id: str
    operation_name: str
    start_time: float
    parent_span_id: str | None = None
    end_time: float | None = None
    duration_ms: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"

    def finish(self) -> None:
        """完成跨度"""
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = (self.end_time - self.start_time) * 1000

    def log_event(self, event: str, **fields) -> None:
        """记录事件"""
        self.logs.append({"timestamp": time.time(), "event": event, **fields})

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
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
        }


class TraceManager:
    """追踪管理器"""

    def __init__(self, service_name: str = "VirtualChemLab"):
        self.service_name = service_name
        self._active_spans: dict[str, Span] = {}
        self._completed_traces: defaultdict = defaultdict(list)
        self._lock = threading.Lock()
        self._local = threading.local()

        # 日志配置
        self.log_dir = Path("logs/traces")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def start_trace(
        self, operation_name: str, context: TracingContext | None = None, **tags
    ) -> TracingContext:
        """
        启动追踪

        Args:
            operation_name: 操作名称
            context: 父追踪上下文
            **tags: 标签

        Returns:
            追踪上下文
        """
        if context:
            # 继续现有追踪
            trace_id = context.trace_id
            parent_span_id = context.span_id
        else:
            # 创建新追踪
            trace_id = generate_trace_id()
            parent_span_id = None

        span_id = generate_span_id()

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=time.time(),
            parent_span_id=parent_span_id,
            tags={"service.name": self.service_name, **tags},
        )

        with self._lock:
            self._active_spans[span_id] = span

        # 保存到线程本地
        ctx = TracingContext(
            trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id
        )
        self._set_current_context(ctx)

        return ctx

    def finish_span(self, context: TracingContext, status: str = "ok", **tags) -> None:
        """完成跨度"""
        with self._lock:
            span = self._active_spans.get(context.span_id)
            if not span:
                return

            # 更新标签
            span.tags.update(tags)
            span.status = status
            span.finish()

            # 移除活跃跨度
            del self._active_spans[context.span_id]

            # 添加到完成的追踪
            self._completed_traces[span.trace_id].append(span)

        # 写入日志
        self._write_span_log(span)

        # 清除线程本地
        self._clear_current_context()

    @contextmanager
    def trace(self, operation_name: str, context: TracingContext | None = None, **tags):
        """追踪上下文管理器"""
        ctx = self.start_trace(operation_name, context, **tags)
        try:
            yield ctx
            self.finish_span(ctx, status="ok")
        except Exception as e:
            span = self._active_spans.get(ctx.span_id)
            if span:
                span.set_error(e)
            self.finish_span(ctx, status="error")
            raise

    def log_event(
        self, event: str, context: TracingContext | None = None, **fields
    ) -> None:
        """记录事件到当前跨度"""
        if not context:
            context = self._get_current_context()

        if not context:
            return

        with self._lock:
            span = self._active_spans.get(context.span_id)
            if span:
                span.log_event(event, **fields)

    def set_tag(
        self, key: str, value: Any, context: TracingContext | None = None
    ) -> None:
        """设置标签到当前跨度"""
        if not context:
            context = self._get_current_context()

        if not context:
            return

        with self._lock:
            span = self._active_spans.get(context.span_id)
            if span:
                span.set_tag(key, value)

    def get_trace(self, trace_id: str) -> list[Span]:
        """获取完整追踪"""
        with self._lock:
            return self._completed_traces.get(trace_id, []).copy()

    def get_trace_tree(self, trace_id: str) -> dict[str, Any]:
        """获取追踪树结构"""
        spans = self.get_trace(trace_id)
        if not spans:
            return {}

        # 按父子关系组织
        span_map = {s.span_id: s for s in spans}
        root_spans = []

        for span in spans:
            if span.parent_span_id is None:
                root_spans.append(self._build_span_tree(span, span_map))

        return {
            "trace_id": trace_id,
            "spans": root_spans,
            "total_duration_ms": max(s.duration_ms for s in spans if s.duration_ms)
            if spans
            else 0,
        }

    def _build_span_tree(self, span: Span, span_map: dict[str, Span]) -> dict[str, Any]:
        """构建跨度树"""
        children = [
            self._build_span_tree(s, span_map)
            for s in span_map.values()
            if s.parent_span_id == span.span_id
        ]

        return {**span.to_dict(), "children": children}

    def get_statistics(self, since_minutes: int = 60) -> dict[str, Any]:
        """获取统计信息"""
        cutoff_time = time.time() - (since_minutes * 60)

        with self._lock:
            all_spans = []
            for spans in self._completed_traces.values():
                all_spans.extend(s for s in spans if s.start_time >= cutoff_time)

        if not all_spans:
            return {"total_traces": 0, "total_spans": 0}

        # 统计
        by_operation = defaultdict(list)
        by_status = defaultdict(int)

        for span in all_spans:
            by_operation[span.operation_name].append(span.duration_ms or 0)
            by_status[span.status] += 1

        # 计算每个操作的统计
        operation_stats = {}
        for op, durations in by_operation.items():
            operation_stats[op] = {
                "count": len(durations),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
            }

        return {
            "total_traces": len(self._completed_traces),
            "total_spans": len(all_spans),
            "by_status": dict(by_status),
            "by_operation": operation_stats,
        }

    def _set_current_context(self, context: TracingContext) -> None:
        """设置当前上下文"""
        self._local.context = context

    def _get_current_context(self) -> TracingContext | None:
        """获取当前上下文"""
        return getattr(self._local, "context", None)

    def _clear_current_context(self) -> None:
        """清除当前上下文"""
        if hasattr(self._local, "context"):
            delattr(self._local, "context")

    def _write_span_log(self, span: Span) -> None:
        """写入跨度日志"""
        try:
            log_file = (
                self.log_dir / f"traces_{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(span.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass


def generate_trace_id() -> str:
    """生成追踪ID"""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """生成跨度ID"""
    return uuid.uuid4().hex[:16]


def trace_function(operation_name: str | None = None):
    """追踪函数装饰器"""

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"

        def wrapper(*args, **kwargs):
            trace_manager = get_trace_manager()
            with trace_manager.trace(op_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# 全局追踪管理器
_trace_manager: TraceManager | None = None


def get_trace_manager() -> TraceManager:
    """获取全局追踪管理器"""
    global _trace_manager
    if _trace_manager is None:
        _trace_manager = TraceManager()
    return _trace_manager
