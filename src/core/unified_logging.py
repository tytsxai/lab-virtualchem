"""
统一日志记录接口
减少重复的日志记录模式，提供统一的日志接口
"""

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """日志上下文"""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}


class UnifiedLogger:
    """统一日志记录器"""

    def __init__(self, name: str = __name__):
        self.logger = get_logger(name)
        self._context_stack: list[LogContext] = []
        self._lock = threading.RLock()

    def _get_current_context(self) -> Optional[LogContext]:
        """获取当前日志上下文"""
        with self._lock:
            return self._context_stack[-1] if self._context_stack else None

    def _format_message(self, message: str, level: LogLevel, **kwargs) -> str:
        """格式化日志消息"""
        context = self._get_current_context()
        extra_kwargs = dict(kwargs)
        user_tag = extra_kwargs.pop("user_id", None)
        session_tag = extra_kwargs.pop("session_id", None)
        request_tag = extra_kwargs.pop("request_id", None)

        # 基础消息
        formatted = f"[{level.value}] {message}"

        # 添加上下文信息
        if context:
            formatted = f"[{context.component}] {formatted}"
            if context.operation:
                formatted = f"[{context.operation}] {formatted}"
            if context.user_id:
                formatted = f"[user:{context.user_id}] {formatted}"
            if context.session_id:
                formatted = f"[session:{context.session_id}] {formatted}"
            if context.request_id:
                formatted = f"[req:{context.request_id}] {formatted}"
        else:
            if user_tag:
                formatted = f"[user:{user_tag}] {formatted}"
            if session_tag:
                formatted = f"[session:{session_tag}] {formatted}"
            if request_tag:
                formatted = f"[req:{request_tag}] {formatted}"
        # 如果上下文存在但传入了标识信息，保证不会丢失显式传参
        if context:
            if user_tag and f"[user:{user_tag}]" not in formatted:
                formatted = f"[user:{user_tag}] {formatted}"
            if session_tag and f"[session:{session_tag}]" not in formatted:
                formatted = f"[session:{session_tag}] {formatted}"
            if request_tag and f"[req:{request_tag}]" not in formatted:
                formatted = f"[req:{request_tag}] {formatted}"

        # 添加额外数据
        if extra_kwargs:
            extra_info = ", ".join(f"{k}={v}" for k, v in extra_kwargs.items())
            formatted = f"{formatted} | {extra_info}"

        return formatted

    def debug(self, message: str, **kwargs) -> None:
        """记录调试日志"""
        formatted = self._format_message(message, LogLevel.DEBUG, **kwargs)
        self.logger.debug(formatted)

    def info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        formatted = self._format_message(message, LogLevel.INFO, **kwargs)
        self.logger.info(formatted)

    def warning(self, message: str, **kwargs) -> None:
        """记录警告日志"""
        formatted = self._format_message(message, LogLevel.WARNING, **kwargs)
        self.logger.warning(formatted)

    def error(self, message: str, **kwargs) -> None:
        """记录错误日志"""
        formatted = self._format_message(message, LogLevel.ERROR, **kwargs)
        self.logger.error(formatted)

    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误日志"""
        formatted = self._format_message(message, LogLevel.CRITICAL, **kwargs)
        self.logger.critical(formatted)

    @contextmanager
    def context(self, operation: str, component: str, **kwargs):
        """日志上下文管理器"""
        context = LogContext(
            operation=operation,
            component=component,
            **kwargs
        )

        with self._lock:
            self._context_stack.append(context)

        try:
            yield
        finally:
            with self._lock:
                if self._context_stack:
                    self._context_stack.pop()

    def log_operation_start(self, operation: str, component: str, **kwargs) -> None:
        """记录操作开始"""
        self.info(f"开始执行: {operation}", **kwargs)

    def log_operation_end(self, operation: str, component: str, duration: Optional[float] = None, **kwargs) -> None:
        """记录操作结束"""
        message = f"完成执行: {operation}"
        if duration is not None:
            duration_str = f"{duration:.3f}".rstrip("0").rstrip(".")
            message += f" (耗时: {duration_str}秒)"
        self.info(message, **kwargs)

    def log_operation_error(self, operation: str, component: str, error: Exception, **kwargs) -> None:
        """记录操作错误"""
        self.error(f"执行失败: {operation} - {str(error)}", **kwargs)

    def log_performance(self, operation: str, component: str, duration: float, **kwargs) -> None:
        """记录性能日志"""
        level = LogLevel.WARNING if duration > 1.0 else LogLevel.INFO
        duration_str = f"{duration:.3f}".rstrip("0").rstrip(".")
        formatted = self._format_message(f"性能: {operation} 耗时 {duration_str}秒", level, **kwargs)
        getattr(self.logger, level.value.lower())(formatted)

    def log_user_action(self, action: str, user_id: str, **kwargs) -> None:
        """记录用户操作"""
        self.info(f"用户操作: {action}", user_id=user_id, **kwargs)

    def log_system_event(self, event: str, **kwargs) -> None:
        """记录系统事件"""
        self.info(f"系统事件: {event}", **kwargs)

    def log_security_event(self, event: str, severity: LogLevel = LogLevel.WARNING, **kwargs) -> None:
        """记录安全事件"""
        formatted = self._format_message(f"安全事件: {event}", severity, **kwargs)
        getattr(self.logger, severity.value.lower())(formatted)


# 全局统一日志记录器
_unified_logger = UnifiedLogger()


def get_unified_logger(name: str = __name__) -> UnifiedLogger:
    """获取统一日志记录器"""
    return UnifiedLogger(name)


def log_operation(operation: str, component: str, **kwargs):
    """操作日志装饰器"""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            logger = get_unified_logger()
            start_time = datetime.now()

            logger.log_operation_start(operation, component, **kwargs)

            try:
                result = func(*args, **func_kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.log_operation_end(operation, component, duration, **kwargs)
                return result
            except Exception as e:
                logger.log_operation_error(operation, component, e, **kwargs)
                raise

        return wrapper
    return decorator


def log_performance(operation: str, component: str, duration: Optional[float] = None, **kwargs):
    """
    性能日志装饰器或便捷函数

    - 作为装饰器: @log_performance("op", "component")
    - 作为函数: log_performance("op", "component", 0.5)
    """
    if duration is not None and not callable(duration):
        _unified_logger.log_performance(operation, component, float(duration), **kwargs)
        return None

    def decorator(func):
        def wrapper(*args, **func_kwargs):
            logger = get_unified_logger()
            start_time = datetime.now()

            try:
                result = func(*args, **func_kwargs)
                duration_value = (datetime.now() - start_time).total_seconds()
                logger.log_performance(operation, component, duration_value, **kwargs)
                return result
            except Exception as e:
                logger.log_operation_error(operation, component, e, **kwargs)
                raise

        return wrapper

    if callable(duration):
        # 支持 @log_performance 直接装饰函数的写法
        func = duration
        return decorator(func)

    return decorator


def log_user_action(action: str, user_id: str, **kwargs):
    """
    用户操作日志装饰器，同时允许直接记录一次用户行为
    """
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            runtime_logger = get_unified_logger()
            runtime_logger.log_user_action(action, user_id, **kwargs)
            return func(*args, **func_kwargs)

        return wrapper

    # 直接调用时先记录一条用户操作日志
    _unified_logger.log_user_action(action, user_id, **kwargs)
    return decorator


# 便捷函数
def debug(message: str, **kwargs) -> None:
    """记录调试日志"""
    _unified_logger.debug(message, **kwargs)


def info(message: str, **kwargs) -> None:
    """记录信息日志"""
    _unified_logger.info(message, **kwargs)


def warning(message: str, **kwargs) -> None:
    """记录警告日志"""
    _unified_logger.warning(message, **kwargs)


def error(message: str, **kwargs) -> None:
    """记录错误日志"""
    _unified_logger.error(message, **kwargs)


def critical(message: str, **kwargs) -> None:
    """记录严重错误日志"""
    _unified_logger.critical(message, **kwargs)


def log_operation_start(operation: str, component: str, **kwargs) -> None:
    """记录操作开始"""
    _unified_logger.log_operation_start(operation, component, **kwargs)


def log_operation_end(operation: str, component: str, duration: Optional[float] = None, **kwargs) -> None:
    """记录操作结束"""
    _unified_logger.log_operation_end(operation, component, duration, **kwargs)


def log_operation_error(operation: str, component: str, error: Exception, **kwargs) -> None:
    """记录操作错误"""
    _unified_logger.log_operation_error(operation, component, error, **kwargs)


# 这些函数已在上面定义，避免重复


def log_system_event(event: str, **kwargs) -> None:
    """记录系统事件"""
    _unified_logger.log_system_event(event, **kwargs)


def log_security_event(event: str, severity: LogLevel = LogLevel.WARNING, **kwargs) -> None:
    """记录安全事件"""
    _unified_logger.log_security_event(event, severity, **kwargs)


@contextmanager
def log_context(operation: str, component: str, **kwargs):
    """日志上下文管理器"""
    with _unified_logger.context(operation, component, **kwargs):
        yield
