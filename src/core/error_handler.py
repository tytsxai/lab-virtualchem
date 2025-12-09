"""
统一错误处理器
提供应用程序级别的错误处理、恢复和报告功能

本模块同时承担两类职责：
1. 新版系统错误处理（基于 VirtualChemLabError）
2. 兼容旧版/测试使用的错误上下文与统计接口（ErrorContext 等）
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .common_error_handlers import (
    safe_execute_with_default as _common_safe_execute_with_default,
)
from .common_exceptions import (
    ErrorCategory as CoreErrorCategory,
)
from .common_exceptions import (
    ErrorSeverity as CoreErrorSeverity,
)
from .common_exceptions import (
    VirtualChemLabError,
)
from .event_bus import close_event_bus, get_event_bus
from .service_registration import get_configured_container, reset_container

logger = logging.getLogger(__name__)

EMERGENCY_STATE_DIR_ENV = "VCL_EMERGENCY_STATE_DIR"


class ErrorSeverity(str, Enum):
    """错误严重程度（测试/兼容用）"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """错误分类（测试/兼容用）"""

    SYSTEM = "system"
    USER = "user"
    NETWORK = "network"
    DATABASE = "database"
    FILE = "file"
    VALIDATION = "validation"
    BUSINESS = "business"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """错误上下文（测试/兼容用）"""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """错误记录（测试/兼容用）"""

    id: str
    timestamp: float
    exception: Exception
    context: ErrorContext
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    traceback: str
    recoverable: bool
    handled: bool
    recovery_attempts: int
    max_recovery_attempts: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ErrorHandler:
    """统一错误处理器（兼容新版与测试接口）"""

    def __init__(self):
        # 新版错误处理所需结构（VirtualChemLabError）
        self._error_callbacks: Dict[CoreErrorCategory, List[Callable[[VirtualChemLabError], None]]] = {}
        self._error_stats: Dict[str, int] = {}
        self._recovery_strategies: Dict[Type[VirtualChemLabError], Callable[[VirtualChemLabError], Any]] = {}

        # 兼容测试要求的接口
        self.error_handlers: Dict[Type[Exception], Callable[[Exception, ErrorContext], Any]] = {}
        self.error_records: List[ErrorRecord] = []
        self.max_error_records: int = 1000

        # 注册一个默认处理器，保证 error_handlers 非空
        self.register_handler(Exception, self._default_legacy_handler)

    def register_callback(
        self,
        category: CoreErrorCategory,
        callback: Callable[[VirtualChemLabError], None],
    ) -> None:
        """注册错误回调"""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)

    def register_recovery_strategy(
        self,
        error_type: Type[VirtualChemLabError],
        strategy: Callable[[VirtualChemLabError], Any],
    ) -> None:
        """注册恢复策略"""
        self._recovery_strategies[error_type] = strategy

    # -------- 新版 VirtualChemLabError 处理逻辑 --------

    def handle_error(self, error: Union[VirtualChemLabError, Exception], context: Optional[ErrorContext] = None) -> Any:
        """
        处理错误

        - 对 VirtualChemLabError 使用新版错误恢复逻辑
        - 对普通 Exception 使用测试期望的 handler + 记录机制
        """
        if isinstance(error, VirtualChemLabError) and context is None:
            # 兼容历史接口：仅传入 VirtualChemLabError
            error_key = f"{error.category.value}_{error.severity.value}"
            self._error_stats[error_key] = self._error_stats.get(error_key, 0) + 1

            if error.category in self._error_callbacks:
                for callback in self._error_callbacks[error.category]:
                    try:
                        callback(error)
                    except Exception as e:  # pragma: no cover - 防御性日志
                        logger.error(f"Error callback failed: {e}")

            return self._attempt_recovery(error)

        # 普通异常：走测试期望的处理路径
        if context is None:
            context = ErrorContext()

        return self._handle_legacy_error(error, context)

    def _attempt_recovery(self, error: VirtualChemLabError) -> Any:
        """尝试错误恢复"""
        error_type = type(error)

        # 查找恢复策略
        for registered_type, strategy in self._recovery_strategies.items():
            if issubclass(error_type, registered_type):
                try:
                    return strategy(error)
                except Exception as e:
                    logger.error(f"Recovery strategy failed: {e}")

        # 默认恢复策略
        return self._default_recovery(error)

    def _default_recovery(self, error: VirtualChemLabError) -> Any:
        """默认恢复策略（改进版）"""
        if error.severity == CoreErrorSeverity.CRITICAL:
            logger.critical(f"Critical error occurred: {error}")
            # 紧急恢复逻辑
            try:
                # 尝试保存当前状态
                self._emergency_save_state()
                # 尝试重启关键组件
                self._restart_critical_components()
            except Exception as e:
                logger.critical(f"Emergency recovery failed: {e}")
            return None
        elif error.severity == CoreErrorSeverity.HIGH:
            logger.error(f"High severity error: {error}")
            # 尝试降级处理
            return self._fallback_operation(error)
        else:
            logger.warning(f"Error occurred: {error}")
            # 记录错误但继续执行
            return None

    def _emergency_save_state(self) -> None:
        """紧急保存状态"""
        try:
            base_dir = Path(os.getenv(EMERGENCY_STATE_DIR_ENV, "logs/emergency"))
            base_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            snapshot_path = base_dir / f"state_{timestamp}.json"

            recent_records = [self._serialize_error_record(r) for r in self.error_records[-20:]]
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "error_stats": self._error_stats.copy(),
                "recent_errors": recent_records,
            }

            snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Emergency state save completed: %s", snapshot_path)
        except Exception as e:  # pragma: no cover - 防御性日志
            logger.error(f"Emergency save failed: {e}")

    def _restart_critical_components(self) -> None:
        """重启关键组件"""
        restarted: list[str] = []
        errors: list[str] = []

        if callable(close_event_bus) and callable(get_event_bus):
            try:
                close_event_bus()
                get_event_bus()
                restarted.append("event_bus")
            except Exception as exc:  # pragma: no cover - 防御性日志
                errors.append(f"event_bus restart failed: {exc}")
        else:
            logger.debug("Event bus restart skipped (not available)")

        if callable(reset_container) and callable(get_configured_container):
            try:
                reset_container()
                get_configured_container()
                restarted.append("di_container")
            except Exception as exc:  # pragma: no cover - 防御性日志
                errors.append(f"DI container restart failed: {exc}")
        else:
            logger.debug("DI container restart skipped (not available)")

        if restarted:
            logger.info("Critical components restart completed: %s", ", ".join(restarted))
        if errors:
            for message in errors:
                logger.error(message)

    def _fallback_operation(self, error: VirtualChemLabError) -> Any:
        """降级操作"""
        try:
            # 根据错误类型执行降级操作
            if error.category.value == "database":
                # 数据库错误降级到缓存
                logger.info("Falling back to cache for database error")
                return None
            elif error.category.value == "network":
                # 网络错误降级到离线模式
                logger.info("Falling back to offline mode for network error")
                return None
            else:
                # 其他错误使用默认处理
                return None
        except Exception as e:
            logger.error(f"Fallback operation failed: {e}")
            return None

    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计"""
        return self._error_stats.copy()

    def clear_stats(self) -> None:
        """清除错误统计"""
        self._error_stats.clear()

    # -------- 兼容旧版/测试用错误处理逻辑 --------

    def _default_legacy_handler(self, error: Exception, context: ErrorContext) -> bool:
        """默认错误处理器：记录并认为已处理"""
        logger.error(f"Handled error: {error} (component={context.component}, operation={context.operation})")
        return True

    def register_handler(self, error_type: Type[Exception], handler: Callable[[Exception, ErrorContext], Any]) -> None:
        """注册基于异常类型的处理器（测试使用）"""
        self.error_handlers[error_type] = handler

    def unregister_handler(self, error_type: Type[Exception]) -> bool:
        """注销处理器（测试使用）"""
        if error_type in self.error_handlers:
            del self.error_handlers[error_type]
            return True
        return False

    def _append_error_record(
        self,
        error: Exception,
        context: ErrorContext,
        handled: bool,
        recovery_attempts: int = 0,
    ) -> None:
        """添加错误记录并维护最大数量"""
        record = ErrorRecord(
            id=f"error_{len(self.error_records) + 1}",
            timestamp=__import__("time").time(),
            exception=error,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.UNKNOWN,
            message=str(error),
            traceback=traceback.format_exc(),
            recoverable=True,
            handled=handled,
            recovery_attempts=recovery_attempts,
            max_recovery_attempts=self.max_error_records,
            metadata=context.metadata.copy(),
        )
        self.error_records.append(record)

        if len(self.error_records) > self.max_error_records:
            # 仅保留最新的 max_error_records 条（测试有断言）
            self.error_records = self.error_records[-self.max_error_records :]

    def _serialize_error_record(self, record: ErrorRecord) -> Dict[str, Any]:
        """将错误记录转换为可持久化的字典"""
        return {
            "id": record.id,
            "timestamp": record.timestamp,
            "exception_type": type(record.exception).__name__,
            "message": record.message,
            "handled": record.handled,
            "severity": record.severity.value,
            "category": record.category.value,
            "recoverable": record.recoverable,
            "recovery_attempts": record.recovery_attempts,
            "metadata": record.metadata,
            "traceback": record.traceback,
            "context": {
                "user_id": record.context.user_id,
                "session_id": record.context.session_id,
                "component": record.context.component,
                "operation": record.context.operation,
                "metadata": record.context.metadata,
            },
        }

    def _handle_legacy_error(self, error: Exception, context: ErrorContext) -> bool:
        """测试/旧版路径：按异常类型调用处理器并记录"""
        handler = self.error_handlers.get(type(error)) or self.error_handlers.get(Exception)

        handled = True
        try:
            if handler is not None:
                result = handler(error, context)
                handled = bool(result) is not False
        except Exception as e:  # pragma: no cover - 防御性日志
            logger.error(f"Legacy error handler failed: {e}")
            handled = False

        self._append_error_record(error, context, handled)
        return True

    def get_error_records(self, limit: Optional[int] = None) -> List[ErrorRecord]:
        """获取错误记录（测试使用）"""
        records = self.error_records
        if limit is not None:
            return records[-limit:]
        return list(records)

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计（测试使用）"""
        total = len(self.error_records)
        handled = sum(1 for r in self.error_records if r.handled)
        unhandled = total - handled

        type_counts: Dict[str, int] = {}
        for r in self.error_records:
            name = type(r.exception).__name__
            type_counts[name] = type_counts.get(name, 0) + 1

        return {
            "total_errors": total,
            "handled_errors": handled,
            "unhandled_errors": unhandled,
            "type_counts": type_counts,
        }


# 全局错误处理器实例
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    return _global_error_handler


@contextmanager
def error_context(
    category: CoreErrorCategory = CoreErrorCategory.SYSTEM,
    severity: CoreErrorSeverity = CoreErrorSeverity.MEDIUM,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
):
    """错误上下文管理器（新版 VirtualChemLabError 用）"""
    try:
        yield
    except VirtualChemLabError:
        raise
    except Exception as e:
        raise error_class(
            message=f"Unexpected error: {str(e)}",
            category=category,
            severity=severity,
            cause=e,
        ) from e


def safe_execute(
    func: Callable,
    *args,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: CoreErrorCategory = CoreErrorCategory.SYSTEM,
    severity: CoreErrorSeverity = CoreErrorSeverity.MEDIUM,
    fallback_value: Any = None,
    default_return: Any = None,
    **kwargs,
) -> Any:
    """
    安全执行函数

    兼容测试用的 default_return 参数，内部仍使用新版错误系统。
    """
    try:
        return func(*args, **kwargs)
    except VirtualChemLabError:
        raise
    except Exception as e:
        error = error_class(
            message=f"Error executing {func.__name__}: {str(e)}",
            category=category,
            severity=severity,
            cause=e,
        )

        # 处理错误
        result = _global_error_handler.handle_error(error)

        if result is not None:
            return result

        # 兼容两种参数名
        if fallback_value is not None:
            return fallback_value
        if default_return is not None:
            return default_return

        raise error from e


def log_and_continue(
    error: Exception,
    message: str = "Error occurred but continuing",
    level: int = logging.WARNING
) -> None:
    """记录错误但继续执行"""
    logger.log(level, f"{message}: {error}")
    logger.log(level, traceback.format_exc())


def log_and_raise(
    error: Exception,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: CoreErrorCategory = CoreErrorCategory.SYSTEM,
    severity: CoreErrorSeverity = CoreErrorSeverity.MEDIUM,
) -> None:
    """记录错误并重新抛出"""
    logger.error(f"Error occurred: {error}")
    logger.error(traceback.format_exc())

    raise error_class(
        message=str(error),
        category=category,
        severity=severity,
        cause=error
    )


# 预定义的错误处理策略
def create_ui_error_handler() -> Callable[[VirtualChemLabError], None]:
    """创建UI错误处理器"""
    def handler(error: VirtualChemLabError) -> None:
        try:
            from PySide6.QtWidgets import QMessageBox

            # 根据严重程度选择消息框类型
            if error.severity == CoreErrorSeverity.CRITICAL:
                QMessageBox.critical(None, "严重错误", error.message)
            elif error.severity == CoreErrorSeverity.HIGH:
                QMessageBox.warning(None, "错误", error.message)
            else:
                QMessageBox.information(None, "提示", error.message)
        except ImportError:
            # PySide6不可用时的回退处理
            logger.error(f"UI Error Handler: {error.message}")

    return handler


def create_logging_error_handler() -> Callable[[VirtualChemLabError], None]:
    """创建日志错误处理器"""
    def handler(error: VirtualChemLabError) -> None:
        log_level = {
            CoreErrorSeverity.LOW: logging.DEBUG,
            CoreErrorSeverity.MEDIUM: logging.INFO,
            CoreErrorSeverity.HIGH: logging.WARNING,
            CoreErrorSeverity.CRITICAL: logging.ERROR,
        }.get(error.severity, logging.ERROR)

        logger.log(log_level, f"[{error.category.value}] {error.message}")
        if error.details:
            logger.log(log_level, f"Details: {error.details}")

    return handler


# 初始化默认错误处理器
def initialize_default_handlers() -> None:
    """初始化默认错误处理器"""
    # 注册日志处理器
    _global_error_handler.register_callback(
        CoreErrorCategory.SYSTEM,
        create_logging_error_handler(),
    )

    # 注册UI处理器
    _global_error_handler.register_callback(
        CoreErrorCategory.UI,
        create_ui_error_handler(),
    )


# 自动初始化
initialize_default_handlers()


class ErrorContextManager:
    """
    错误上下文管理器（测试/兼容用）

    with ErrorContextManager(component, operation, user_id=...) as ctx:
        ...
    """

    def __init__(self, component: str, operation: str, **metadata: Any) -> None:
        self.component = component
        self.operation = operation
        self.metadata = metadata
        self.context = ErrorContext(component=component, operation=operation, metadata=dict(metadata))

    def __enter__(self) -> ErrorContext:
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            return False

        # 构造上下文并交由 handle_error_func 处理
        handle_error_func(exc_val, self.context)
        # 异常按照测试预期重新抛出
        return False


def handle_error_func(error: Exception, context: ErrorContext) -> bool:
    """测试使用的便捷错误处理函数"""
    handler = get_error_handler()
    return bool(handler.handle_error(error, context))


def safe_execute_with_default(default_value: Any, func: Callable, *args, **kwargs) -> Any:
    """
    兼容测试签名的 safe_execute_with_default

    tests 中调用: safe_execute_with_default(\"default\", func)
    实际委托给 common_error_handlers.safe_execute_with_default。
    """
    return _common_safe_execute_with_default(func, default_value, *args, **kwargs)
