"""增强的错误处理器"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandler(QObject):
    """增强的错误处理器"""

    # 信号
    error_occurred = Signal(str, str)  # 错误类型, 错误消息
    warning_occurred = Signal(str, str)  # 警告类型, 警告消息
    info_message = Signal(str, str)  # 信息类型, 信息消息

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.error_count = 0
        self.warning_count = 0
        self.show_dialogs = True
        self.log_errors = True

    def handle_error(
        self,
        error: Exception,
        context: str = "",
        show_dialog: bool = True,
        log_error: bool = True,
    ) -> None:
        """处理错误"""
        self.error_count += 1

        error_type = type(error).__name__
        error_message = str(error)
        full_context = f"{context}: {error_message}" if context else error_message

        # 记录错误
        if log_error and self.log_errors:
            logger.error(f"错误 [{error_type}]: {full_context}")
            logger.debug(f"错误堆栈: {traceback.format_exc()}")

        # 发送信号
        self.error_occurred.emit(error_type, full_context)

        # 显示对话框
        if show_dialog and self.show_dialogs:
            self._show_error_dialog(error_type, full_context)

    def handle_warning(
        self,
        warning: str,
        context: str = "",
        show_dialog: bool = False,
        log_warning: bool = True,
    ) -> None:
        """处理警告"""
        self.warning_count += 1

        full_context = f"{context}: {warning}" if context else warning

        # 记录警告
        if log_warning:
            logger.warning(f"警告: {full_context}")

        # 发送信号
        self.warning_occurred.emit("Warning", full_context)

        # 显示对话框
        if show_dialog and self.show_dialogs:
            self._show_warning_dialog(full_context)

    def handle_info(
        self,
        message: str,
        context: str = "",
        show_dialog: bool = False,
        log_info: bool = True,
    ) -> None:
        """处理信息"""
        full_context = f"{context}: {message}" if context else message

        # 记录信息
        if log_info:
            logger.info(f"信息: {full_context}")

        # 发送信号
        self.info_message.emit("Info", full_context)

        # 显示对话框
        if show_dialog and self.show_dialogs:
            self._show_info_dialog(full_context)

    def _show_error_dialog(self, error_type: str, message: str) -> None:
        """显示错误对话框"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("错误")
            msg_box.setText(f"发生错误: {error_type}")
            msg_box.setDetailedText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}")

    def _show_warning_dialog(self, message: str) -> None:
        """显示警告对话框"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("警告")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception as e:
            logger.error(f"显示警告对话框失败: {e}")

    def _show_info_dialog(self, message: str) -> None:
        """显示信息对话框"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("信息")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception as e:
            logger.error(f"显示信息对话框失败: {e}")

    def set_dialog_enabled(self, enabled: bool) -> None:
        """设置是否显示对话框"""
        self.show_dialogs = enabled
        logger.info(f"错误对话框显示: {'启用' if enabled else '禁用'}")

    def set_logging_enabled(self, enabled: bool) -> None:
        """设置是否记录日志"""
        self.log_errors = enabled
        logger.info(f"错误日志记录: {'启用' if enabled else '禁用'}")

    def get_statistics(self) -> dict[str, int]:
        """获取错误统计"""
        return {
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }

    def reset_statistics(self) -> None:
        """重置统计"""
        self.error_count = 0
        self.warning_count = 0
        logger.info("错误统计已重置")

    def safe_execute(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> tuple[bool, Any]:
        """安全执行函数"""
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            self.handle_error(e, f"执行函数 {func.__name__}")
            return False, None


class ErrorContext:
    """错误上下文管理器"""

    def __init__(self, error_handler: ErrorHandler, context: str) -> None:
        self.error_handler = error_handler
        self.context = context

    def __enter__(self) -> ErrorContext:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            self.error_handler.handle_error(exc_val, self.context)
            return True  # 抑制异常
        return False

    def handle_error(self, error: Exception) -> None:
        """处理错误"""
        self.error_handler.handle_error(error, self.context)

    def handle_warning(self, warning: str) -> None:
        """处理警告"""
        self.error_handler.handle_warning(warning, self.context)

    def handle_info(self, message: str) -> None:
        """处理信息"""
        self.error_handler.handle_info(message, self.context)


# 全局错误处理器实例
error_handler = ErrorHandler()
