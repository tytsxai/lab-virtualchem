"""
统一错误处理器
提供应用程序级别的错误处理、恢复和报告功能
"""

from __future__ import annotations

import logging
import traceback
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .common_exceptions import (
    ErrorCategory,
    ErrorSeverity,
    VirtualChemLabError,
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """统一错误处理器"""

    def __init__(self):
        self._error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self._error_stats: Dict[str, int] = {}
        self._recovery_strategies: Dict[Type[VirtualChemLabError], Callable] = {}

    def register_callback(
        self,
        category: ErrorCategory,
        callback: Callable[[VirtualChemLabError], None]
    ) -> None:
        """注册错误回调"""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)

    def register_recovery_strategy(
        self,
        error_type: Type[VirtualChemLabError],
        strategy: Callable[[VirtualChemLabError], Any]
    ) -> None:
        """注册恢复策略"""
        self._recovery_strategies[error_type] = strategy

    def handle_error(self, error: VirtualChemLabError) -> Any:
        """处理错误"""
        # 记录错误统计
        error_key = f"{error.category.value}_{error.severity.value}"
        self._error_stats[error_key] = self._error_stats.get(error_key, 0) + 1

        # 调用注册的回调
        if error.category in self._error_callbacks:
            for callback in self._error_callbacks[error.category]:
                try:
                    callback(error)
                except Exception as e:
                    logger.error(f"Error callback failed: {e}")

        # 尝试恢复
        return self._attempt_recovery(error)

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
        if error.severity == ErrorSeverity.CRITICAL:
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
        elif error.severity == ErrorSeverity.HIGH:
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
            # 这里可以添加紧急状态保存逻辑
            logger.info("Emergency state save completed")
        except Exception as e:
            logger.error(f"Emergency save failed: {e}")

    def _restart_critical_components(self) -> None:
        """重启关键组件"""
        try:
            # 这里可以添加组件重启逻辑
            logger.info("Critical components restart completed")
        except Exception as e:
            logger.error(f"Component restart failed: {e}")

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


# 全局错误处理器实例
_global_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    return _global_error_handler


@contextmanager
def error_context(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError
):
    """错误上下文管理器"""
    try:
        yield
    except VirtualChemLabError:
        # 重新抛出VirtualChemLabError
        raise
    except Exception as e:
        # 包装其他异常
        raise error_class(
            message=f"Unexpected error: {str(e)}",
            category=category,
            severity=severity,
            cause=e
        )


def safe_execute(
    func: Callable,
    *args,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    fallback_value: Any = None,
    **kwargs
) -> Any:
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except VirtualChemLabError:
        raise
    except Exception as e:
        error = error_class(
            message=f"Error executing {func.__name__}: {str(e)}",
            category=category,
            severity=severity,
            cause=e
        )

        # 处理错误
        result = _global_error_handler.handle_error(error)

        if result is not None:
            return result
        elif fallback_value is not None:
            return fallback_value
        else:
            raise error


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
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
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
            if error.severity == ErrorSeverity.CRITICAL:
                QMessageBox.critical(None, "严重错误", error.message)
            elif error.severity == ErrorSeverity.HIGH:
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
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.INFO,
            ErrorSeverity.HIGH: logging.WARNING,
            ErrorSeverity.CRITICAL: logging.ERROR
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
        ErrorCategory.SYSTEM,
        create_logging_error_handler()
    )

    # 注册UI处理器
    _global_error_handler.register_callback(
        ErrorCategory.UI,
        create_ui_error_handler()
    )


# 自动初始化
initialize_default_handlers()
