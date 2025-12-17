"""增强的错误处理工具

提供统一的错误处理、用户友好的提示和自动恢复功能
"""

from __future__ import annotations

import functools
import logging
import traceback
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """错误严重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorAction(Enum):
    """错误处理动作"""

    RETRY = "retry"
    IGNORE = "ignore"
    RESET = "reset"
    RESTART = "restart"
    CONTACT_SUPPORT = "contact_support"


class UserFriendlyError:
    """用户友好的错误信息"""

    def __init__(
        self,
        title: str,
        message: str,
        hint: str = "",
        details: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        actions: list[ErrorAction] = None,
        error_code: str = "",
    ):
        self.title = title
        self.message = message
        self.hint = hint
        self.details = details
        self.severity = severity
        self.actions = actions or [ErrorAction.RETRY, ErrorAction.IGNORE]
        self.error_code = error_code


class ErrorHandlerSignals(QObject):
    """错误处理信号"""

    error_occurred = Signal(UserFriendlyError)
    error_recovered = Signal(str)  # 恢复消息


class EnhancedErrorHandler:
    """增强的错误处理器"""

    # 单例
    _instance: EnhancedErrorHandler | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.signals = ErrorHandlerSignals()
            self.error_history: list[UserFriendlyError] = []
            self.max_history = 100
            self.show_dialogs = True
            self._initialized = True

    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        user_message: str = "",
        hint: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        show_dialog: bool = True,
        parent: QWidget = None,
    ) -> UserFriendlyError:
        """处理异常并转换为用户友好的错误

        Args:
            exception: 异常对象
            context: 上下文信息
            user_message: 用户友好的消息
            hint: 解决提示
            severity: 严重程度
            show_dialog: 是否显示对话框
            parent: 父窗口

        Returns:
            用户友好的错误对象
        """
        # 转换为用户友好的错误
        friendly_error = self._convert_to_friendly_error(
            exception, context, user_message, hint, severity
        )

        # 记录错误
        self._log_error(friendly_error, exception)

        # 保存到历史
        self._save_to_history(friendly_error)

        # 发射信号
        self.signals.error_occurred.emit(friendly_error)

        # 显示对话框
        if show_dialog and self.show_dialogs:
            self._show_error_dialog(friendly_error, parent)

        return friendly_error

    def _convert_to_friendly_error(
        self,
        exception: Exception,
        context: str,
        user_message: str,
        hint: str,
        severity: ErrorSeverity,
    ) -> UserFriendlyError:
        """将异常转换为用户友好的错误"""

        # 如果没有提供用户消息，根据异常类型生成
        if not user_message:
            user_message = self._get_default_message(exception)

        # 如果没有提供提示，根据异常类型生成
        if not hint:
            hint = self._get_default_hint(exception)

        # 获取错误详情
        details = f"错误类型: {type(exception).__name__}\n"
        details += f"错误消息: {str(exception)}\n"
        if context:
            details += f"上下文: {context}\n"
        details += f"\n堆栈信息:\n{traceback.format_exc()}"

        # 标题
        title = self._get_error_title(severity)

        # 可用的操作
        actions = self._get_available_actions(exception, severity)

        return UserFriendlyError(
            title=title,
            message=user_message,
            hint=hint,
            details=details,
            severity=severity,
            actions=actions,
            error_code=f"{type(exception).__name__}",
        )

    def _get_default_message(self, exception: Exception) -> str:
        """获取默认的用户消息"""
        if isinstance(exception, FileNotFoundError):
            filename = getattr(exception, "filename", "未知文件")
            return f"找不到文件: {filename}"
        elif isinstance(exception, PermissionError):
            return "权限不足，无法执行此操作"
        elif isinstance(exception, ValueError):
            return f"数据格式错误: {str(exception)}"
        elif isinstance(exception, KeyError):
            return f"配置项缺失: {str(exception)}"
        elif isinstance(exception, TimeoutError):
            return "操作超时，请稍后重试"
        elif isinstance(exception, ConnectionError):
            return "网络连接错误"
        elif isinstance(exception, OSError):
            if "No space left" in str(exception):
                return "磁盘空间不足"
            return f"系统错误: {str(exception)}"
        else:
            return f"发生错误: {str(exception)}"

    def _get_default_hint(self, exception: Exception) -> str:
        """获取默认的解决提示"""
        if isinstance(exception, FileNotFoundError):
            return "请检查文件路径是否正确，或尝试重新创建该文件"
        elif isinstance(exception, PermissionError):
            return "请确保应用有足够的权限访问该文件或目录，可能需要以管理员身份运行"
        elif isinstance(exception, ValueError):
            return "请检查输入的数据格式是否正确，确保符合要求"
        elif isinstance(exception, KeyError):
            return "配置文件可能不完整，请检查配置或重置为默认值"
        elif isinstance(exception, TimeoutError):
            return "操作花费时间过长，请检查网络连接或稍后重试"
        elif isinstance(exception, ConnectionError):
            return "请检查网络连接，确保服务器可访问"
        elif isinstance(exception, OSError):
            if "No space left" in str(exception):
                return "请清理磁盘空间后重试"
            return "可能是系统资源不足或文件被占用，请重试"
        else:
            return "如果问题持续存在，请联系技术支持"

    def _get_error_title(self, severity: ErrorSeverity) -> str:
        """获取错误标题"""
        titles = {
            ErrorSeverity.INFO: "提示",
            ErrorSeverity.WARNING: "警告",
            ErrorSeverity.ERROR: "错误",
            ErrorSeverity.CRITICAL: "严重错误",
        }
        return titles.get(severity, "错误")

    def _get_available_actions(
        self, exception: Exception, severity: ErrorSeverity
    ) -> list[ErrorAction]:
        """获取可用的操作"""
        if severity == ErrorSeverity.CRITICAL:
            return [ErrorAction.RESTART, ErrorAction.CONTACT_SUPPORT]
        elif isinstance(exception, (TimeoutError, ConnectionError)):
            return [ErrorAction.RETRY, ErrorAction.IGNORE]
        elif isinstance(exception, (FileNotFoundError, PermissionError)):
            return [ErrorAction.RETRY, ErrorAction.RESET, ErrorAction.IGNORE]
        else:
            return [ErrorAction.RETRY, ErrorAction.IGNORE]

    def _log_error(self, friendly_error: UserFriendlyError, exception: Exception):
        """记录错误"""
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(friendly_error.severity, logging.ERROR)

        logger.log(
            log_level,
            f"[{friendly_error.error_code}] {friendly_error.message}",
            exc_info=exception,
        )

    def _save_to_history(self, friendly_error: UserFriendlyError):
        """保存到历史"""
        self.error_history.append(friendly_error)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

    def _show_error_dialog(
        self, friendly_error: UserFriendlyError, parent: QWidget = None
    ):
        """显示错误对话框"""
        try:
            msg_box = QMessageBox(parent)

            # 设置图标
            icon_map = {
                ErrorSeverity.INFO: QMessageBox.Icon.Information,
                ErrorSeverity.WARNING: QMessageBox.Icon.Warning,
                ErrorSeverity.ERROR: QMessageBox.Icon.Critical,
                ErrorSeverity.CRITICAL: QMessageBox.Icon.Critical,
            }
            msg_box.setIcon(
                icon_map.get(friendly_error.severity, QMessageBox.Icon.Critical)
            )

            # 设置标题和文本
            msg_box.setWindowTitle(friendly_error.title)
            msg_box.setText(friendly_error.message)

            # 添加提示
            if friendly_error.hint:
                msg_box.setInformativeText(f"💡 {friendly_error.hint}")

            # 添加详细信息
            if friendly_error.details:
                msg_box.setDetailedText(friendly_error.details)

            # 添加按钮
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

            msg_box.exec()
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}", exc_info=True)


# 装饰器函数
def handle_errors(
    context: str = "",
    user_message: str = "",
    hint: str = "",
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    default_return: Any = None,
    show_dialog: bool = True,
    reraise: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """错误处理装饰器

    Args:
        context: 上下文信息
        user_message: 用户友好的消息
        hint: 解决提示
        severity: 严重程度
        default_return: 出错时的默认返回值
        show_dialog: 是否显示对话框
        reraise: 是否重新抛出异常

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取父窗口（如果第一个参数是QWidget）
                parent = args[0] if args and isinstance(args[0], QWidget) else None

                # 处理错误
                error_handler = EnhancedErrorHandler()
                ctx = context or f"{func.__module__}.{func.__name__}"
                error_handler.handle_exception(
                    e, ctx, user_message, hint, severity, show_dialog, parent
                )

                if reraise:
                    raise
                return default_return

        return wrapper

    return decorator


def safe_file_operation(
    operation_name: str = "文件操作",
    show_dialog: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """文件操作安全装饰器

    自动处理文件操作相关的错误
    """
    return handle_errors(
        context=f"执行{operation_name}",
        user_message=f"{operation_name}失败",
        severity=ErrorSeverity.ERROR,
        show_dialog=show_dialog,
    )


def safe_network_operation(
    operation_name: str = "网络操作",
    max_retries: int = 3,
    show_dialog: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """网络操作安全装饰器

    自动处理网络操作相关的错误，支持重试
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (TimeoutError, ConnectionError) as e:
                    last_error = e
                    logger.warning(
                        f"{operation_name}失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        continue

            # 所有重试都失败
            if last_error and show_dialog:
                error_handler = EnhancedErrorHandler()
                parent = args[0] if args and isinstance(args[0], QWidget) else None
                error_handler.handle_exception(
                    last_error,
                    f"执行{operation_name}",
                    f"{operation_name}失败（已重试{max_retries}次）",
                    "请检查网络连接后重试",
                    ErrorSeverity.ERROR,
                    show_dialog,
                    parent,
                )
            raise last_error

        return wrapper

    return decorator


# 便捷函数
def show_error(
    message: str,
    hint: str = "",
    details: str = "",
    parent: QWidget = None,
):
    """显示错误消息"""
    error = UserFriendlyError(
        title="错误",
        message=message,
        hint=hint,
        details=details,
        severity=ErrorSeverity.ERROR,
    )
    handler = EnhancedErrorHandler()
    handler._show_error_dialog(error, parent)


def show_warning(
    message: str,
    hint: str = "",
    details: str = "",
    parent: QWidget = None,
):
    """显示警告消息"""
    error = UserFriendlyError(
        title="警告",
        message=message,
        hint=hint,
        details=details,
        severity=ErrorSeverity.WARNING,
    )
    handler = EnhancedErrorHandler()
    handler._show_error_dialog(error, parent)


def show_info(
    message: str,
    hint: str = "",
    details: str = "",
    parent: QWidget = None,
):
    """显示信息消息"""
    error = UserFriendlyError(
        title="提示",
        message=message,
        hint=hint,
        details=details,
        severity=ErrorSeverity.INFO,
    )
    handler = EnhancedErrorHandler()
    handler._show_error_dialog(error, parent)


# 全局错误处理器实例
error_handler = EnhancedErrorHandler()


__all__ = [
    "ErrorSeverity",
    "ErrorAction",
    "UserFriendlyError",
    "EnhancedErrorHandler",
    "handle_errors",
    "safe_file_operation",
    "safe_network_operation",
    "show_error",
    "show_warning",
    "show_info",
    "error_handler",
]
