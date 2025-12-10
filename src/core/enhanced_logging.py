#!/usr/bin/env python3
"""
增强的日志记录系统
提供结构化日志、性能监控、错误追踪、审计日志等功能
"""

import json
import logging
import logging.handlers
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import SensitiveDataFilter

logger = logging.getLogger(__name__)


def _ensure_sensitive_filter(target: logging.Handler | logging.Logger) -> None:
    """Ensure SensitiveDataFilter is attached once."""
    filters = getattr(target, "filters", [])
    if not any(isinstance(f, SensitiveDataFilter) for f in filters):
        target.addFilter(SensitiveDataFilter())


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志分类"""
    SYSTEM = "system"
    USER = "user"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class LogContext:
    """日志上下文"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    context: LogContext
    exception_info: Optional[str] = None
    performance_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuredFormatter(logging.Formatter):
    """结构化格式化器"""

    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础信息
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加上下文信息
        if self.include_context and hasattr(record, 'context'):
            context = getattr(record, 'context', None)
            if context and hasattr(context, 'user_id') and context.user_id:
                log_data["user_id"] = context.user_id
            if context and hasattr(context, 'session_id') and context.session_id:
                log_data["session_id"] = context.session_id
            if context and hasattr(context, 'request_id') and context.request_id:
                log_data["request_id"] = context.request_id
            if context and hasattr(context, 'operation') and context.operation:
                log_data["operation"] = context.operation
            if context and hasattr(context, 'component') and context.component:
                log_data["component"] = context.component
            if context and hasattr(context, 'extra_data') and context.extra_data:
                log_data["extra_data"] = context.extra_data

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加性能数据
        if hasattr(record, 'performance_data'):
            log_data["performance"] = getattr(record, 'performance_data', None)

        # 添加额外数据
        if hasattr(record, 'extra_data'):
            log_data["extra"] = getattr(record, 'extra_data', None)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.performance_data: Dict[str, List[float]] = {}
        self.lock = threading.Lock()

    def start_timer(self, operation: str) -> float:
        """开始计时"""
        start_time = time.time()
        with self.lock:
            if operation not in self.performance_data:
                self.performance_data[operation] = []
            self.performance_data[operation].append(start_time)
        return start_time

    def end_timer(self, operation: str, start_time: float, context: Optional[LogContext] = None) -> float:
        """结束计时"""
        end_time = time.time()
        duration = end_time - start_time

        # 记录性能日志
        performance_data = {
            "operation": operation,
            "duration": duration,
            "start_time": start_time,
            "end_time": end_time
        }

        # 更新统计
        with self.lock:
            if operation in self.performance_data:
                self.performance_data[operation].append(duration)

        # 记录日志
        self.logger.info(
            f"性能监控: {operation}",
            extra={
                'context': context or LogContext(),
                'performance_data': performance_data
            }
        )

        return duration

    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """获取性能统计"""
        stats = {}
        with self.lock:
            for operation, durations in self.performance_data.items():
                if durations:
                    stats[operation] = {
                        "count": len(durations),
                        "total_time": sum(durations),
                        "avg_time": sum(durations) / len(durations),
                        "min_time": min(durations),
                        "max_time": max(durations)
                    }
        return stats


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.audit_events: List[LogEntry] = []
        self.lock = threading.Lock()

    def log_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录审计事件"""
        context = LogContext(
            user_id=user_id,
            session_id=session_id,
            extra_data=extra_data or {}
        )

        entry = LogEntry(
            timestamp=time.time(),
            level=LogLevel.INFO,
            category=LogCategory.AUDIT,
            message=f"审计事件: {event_type} - {description}",
            context=context
        )

        with self.lock:
            self.audit_events.append(entry)

        self.logger.info(
            f"审计事件: {event_type} - {description}",
            extra={'context': context}
        )

    def get_audit_events(self, limit: Optional[int] = None) -> List[LogEntry]:
        """获取审计事件"""
        with self.lock:
            events = self.audit_events.copy()
            if limit:
                events = events[-limit:]
            return events


class ErrorTracker:
    """错误追踪器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.error_patterns: Dict[str, int] = {}
        self.error_history: List[LogEntry] = []
        self.lock = threading.Lock()

    def track_error(
        self,
        error: Exception,
        context: Optional[LogContext] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """追踪错误"""
        error_type = type(error).__name__
        error_message = str(error)

        # 更新错误模式统计
        with self.lock:
            pattern_key = f"{error_type}:{error_message[:100]}"
            self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1

        # 创建错误条目
        entry = LogEntry(
            timestamp=time.time(),
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message=f"错误追踪: {error_type} - {error_message}",
            context=context or LogContext(),
            exception_info=traceback.format_exc(),
            metadata=extra_data or {}
        )

        with self.lock:
            self.error_history.append(entry)

        # 记录错误日志
        self.logger.error(
            f"错误追踪: {error_type} - {error_message}",
            exc_info=True,
            extra={
                'context': context or LogContext(),
                'extra_data': extra_data or {}
            }
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self.lock:
            return {
                "total_errors": len(self.error_history),
                "error_patterns": self.error_patterns.copy(),
                "recent_errors": self.error_history[-10:] if self.error_history else []
            }


class EnhancedLogger:
    """增强日志记录器"""

    def __init__(self, name: str = "virtualchemlab"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 上下文栈
        self.context_stack: List[LogContext] = []
        self.context_lock = threading.RLock()

        # 子组件
        self.performance_logger = PerformanceLogger(self.logger)
        self.audit_logger = AuditLogger(self.logger)
        self.error_tracker = ErrorTracker(self.logger)

        # 配置
        self._configured = False
        self._configure_logging()

        logger.info(f"增强日志记录器初始化完成: {name}")


    def _configure_logging(self) -> None:
        """配置日志系统"""
        if self._configured:
            return

        # 清除现有处理器
        self.logger.handlers.clear()

        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(StructuredFormatter(include_context=True))
        _ensure_sensitive_filter(console_handler)
        self.logger.addHandler(console_handler)

        # 文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter(include_context=True))
        _ensure_sensitive_filter(file_handler)
        self.logger.addHandler(file_handler)

        # 错误文件处理器
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(include_context=True))
        _ensure_sensitive_filter(error_handler)
        self.logger.addHandler(error_handler)

        # 审计文件处理器
        audit_handler = logging.handlers.RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(StructuredFormatter(include_context=True))
        _ensure_sensitive_filter(audit_handler)
        self.logger.addHandler(audit_handler)

        _ensure_sensitive_filter(self.logger)
        self._configured = True

    def push_context(self, context: LogContext) -> None:
        """推入上下文"""
        with self.context_lock:
            self.context_stack.append(context)

    def pop_context(self) -> Optional[LogContext]:
        """弹出上下文"""
        with self.context_lock:
            return self.context_stack.pop() if self.context_stack else None

    def get_current_context(self) -> Optional[LogContext]:
        """获取当前上下文"""
        with self.context_lock:
            return self.context_stack[-1] if self.context_stack else None

    @contextmanager
    def context(self, **kwargs):
        """上下文管理器"""
        context = LogContext(**kwargs)
        self.push_context(context)
        try:
            yield context
        finally:
            self.pop_context()

    def _log(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        exc_info: bool = False,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """内部日志方法"""
        context = self.get_current_context() or LogContext()

        # 创建日志记录
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.value),
            "", 0, message, (), None
        )

        # 添加上下文
        if hasattr(record, 'context'):
            record.context = context

        # 添加额外数据
        if extra_data and hasattr(record, 'extra_data'):
            record.extra_data = extra_data

        # 处理日志
        self.logger.handle(record)

    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self._log(LogLevel.DEBUG, message, LogCategory.DEBUG, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self._log(LogLevel.INFO, message, LogCategory.SYSTEM, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self._log(LogLevel.WARNING, message, LogCategory.SYSTEM, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """错误日志"""
        self._log(LogLevel.ERROR, message, LogCategory.ERROR, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """严重错误日志"""
        self._log(LogLevel.CRITICAL, message, LogCategory.ERROR, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """异常日志"""
        self._log(LogLevel.ERROR, message, LogCategory.ERROR, exc_info=True, **kwargs)

    def audit(self, event_type: str, description: str, **kwargs) -> None:
        """审计日志"""
        self.audit_logger.log_event(event_type, description, **kwargs)

    def track_error(self, error: Exception, **kwargs) -> None:
        """追踪错误"""
        self.error_tracker.track_error(error, **kwargs)

    @contextmanager
    def performance_timer(self, operation: str):
        """性能计时器"""
        start_time = self.performance_logger.start_timer(operation)
        try:
            yield
        finally:
            self.performance_logger.end_timer(operation, start_time, self.get_current_context())

    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """获取性能统计"""
        return self.performance_logger.get_performance_stats()

    def get_audit_events(self, limit: Optional[int] = None) -> List[LogEntry]:
        """获取审计事件"""
        return self.audit_logger.get_audit_events(limit)

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return self.error_tracker.get_error_stats()

    def generate_logging_report(self) -> str:
        """生成日志报告"""
        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 日志记录报告")
        report.append("=" * 80)
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"日志记录器: {self.name}")
        report.append("")

        # 性能统计
        perf_stats = self.get_performance_stats()
        if perf_stats:
            report.append("## 性能统计")
            for operation, stats in perf_stats.items():
                report.append(f"### {operation}")
                report.append(f"执行次数: {stats['count']}")
                report.append(f"总时间: {stats['total_time']:.3f}秒")
                report.append(f"平均时间: {stats['avg_time']:.3f}秒")
                report.append(f"最小时间: {stats['min_time']:.3f}秒")
                report.append(f"最大时间: {stats['max_time']:.3f}秒")
                report.append("")

        # 错误统计
        error_stats = self.get_error_stats()
        if error_stats:
            report.append("## 错误统计")
            report.append(f"总错误数: {error_stats['total_errors']}")
            report.append("")

            if error_stats['error_patterns']:
                report.append("### 错误模式")
                for pattern, count in error_stats['error_patterns'].items():
                    report.append(f"- {pattern}: {count} 次")
                report.append("")

        # 审计事件
        audit_events = self.get_audit_events(10)
        if audit_events:
            report.append("## 最近审计事件")
            for event in audit_events:
                report.append(f"- {time.strftime('%H:%M:%S', time.localtime(event.timestamp))}: {event.message}")
            report.append("")

        return "\n".join(report)


# 全局实例
enhanced_logger = EnhancedLogger()


def get_enhanced_logger(name: Optional[str] = None) -> EnhancedLogger:
    """获取增强日志记录器"""
    if name:
        return EnhancedLogger(name)
    return enhanced_logger


def log_context(**kwargs):
    """日志上下文装饰器"""
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **func_kwargs):
            with enhanced_logger.context(**kwargs):
                return func(*args, **func_kwargs)
        return wrapper
    return decorator


def log_performance(operation: str):
    """性能日志装饰器"""
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with enhanced_logger.performance_timer(operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def log_errors(func):
    """错误日志装饰器"""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            enhanced_logger.track_error(e)
            raise
    return wrapper
