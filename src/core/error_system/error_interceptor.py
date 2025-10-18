"""
全局错误拦截器

提供Qt应用程序的全局异常拦截和处理
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Any

from .error_codes import ErrorCodeRegistry
from .error_handler import error_handler
from .error_recovery import recovery_manager
from .error_reporter import NotificationChannel, error_reporter
from .exceptions import BaseAppException, from_standard_exception

# 尝试导入PySide6（可选依赖）
HAS_PYQT = False
try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

    HAS_PYQT = True
except ImportError:
    # PySide6 不可用，定义虚拟类以避免导入错误
    QObject = type("QObject", (object,), {})  # type: ignore[assignment]
    QApplication = type("QApplication", (object,), {})  # type: ignore[assignment]
    QMessageBox = type("QMessageBox", (object,), {})  # type: ignore[assignment]
    QWidget = type("QWidget", (object,), {})  # type: ignore[assignment]
    QFont = type("QFont", (object,), {})  # type: ignore[assignment]

    def Signal(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]  # noqa: ARG001
        """虚拟的Signal装饰器"""
        return None


logger = logging.getLogger(__name__)


class ErrorInterceptor(QObject if HAS_PYQT else object):  # type: ignore
    """错误拦截器（Qt版本）"""

    # 信号：错误发生（仅在PyQt6可用时）
    if HAS_PYQT:
        error_occurred = Signal(object, str)  # (exception, context)

    def __init__(self, app: Any = None):
        """
        初始化错误拦截器

        Args:
            app: Qt应用程序实例
        """
        if HAS_PYQT:
            super().__init__()

        if not HAS_PYQT and app is not None:
            logger.warning("PyQt6不可用，Qt应用错误拦截功能将受限")

        self.app = app
        self._installed = False
        self._show_error_dialog = True and HAS_PYQT
        self._auto_recovery = True

    def install(self) -> None:
        """安装全局异常钩子"""
        if self._installed:
            logger.warning("错误拦截器已安装")
            return

        # 安装Python异常钩子
        sys.excepthook = self._exception_hook

        # 如果是Qt应用，安装Qt异常处理
        if self.app:
            # 重写QApplication.notify来捕获Qt事件处理中的异常
            self._original_notify = self.app.notify
            self.app.notify = self._qt_notify_wrapper

        self._installed = True
        logger.info("错误拦截器已安装")

    def uninstall(self) -> None:
        """卸载全局异常钩子"""
        if not self._installed:
            return

        # 恢复原始异常钩子
        sys.excepthook = sys.__excepthook__

        # 恢复Qt notify
        if self.app and hasattr(self, "_original_notify"):
            self.app.notify = self._original_notify

        self._installed = False
        logger.info("错误拦截器已卸载")

    def _exception_hook(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        """Python异常钩子"""
        # 忽略KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 处理异常
        if isinstance(exc_value, Exception):
            self._handle_exception(exc_value, "全局未捕获异常")

        # 打印到stderr
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    def _qt_notify_wrapper(self, receiver: Any, event: Any) -> bool:
        """Qt notify包装器"""
        try:
            result = self._original_notify(receiver, event)
            return bool(result)
        except Exception as e:
            self._handle_exception(e, f"Qt事件处理 ({type(event).__name__})")
            return False

    def _handle_exception(self, exception: Exception, context: str) -> None:
        """
        处理异常

        Args:
            exception: 异常对象
            context: 上下文信息
        """
        try:
            # 转换为应用异常
            if isinstance(exception, BaseAppException):
                app_exception = exception
            else:
                app_exception = from_standard_exception(exception, context)

            # 记录错误
            error_handler.handle_exception(app_exception, context)

            # 生成错误报告
            report = error_reporter.report_error(
                app_exception,
                context,
                notify=True,
                notification_channels=[NotificationChannel.LOG],
            )

            # 发射信号（仅在PyQt6可用时）
            if HAS_PYQT and hasattr(self, "error_occurred"):
                self.error_occurred.emit(app_exception, context)

            # 尝试自动恢复
            if self._auto_recovery and app_exception.error_code.recoverable:
                strategy = recovery_manager.get_strategy(app_exception)
                if strategy.auto_recover:
                    logger.info(f"尝试自动恢复: {app_exception.error_code.name}")
                    # 注意：这里我们无法重试原始操作，只能记录

            # 显示错误对话框
            if self._show_error_dialog and self.app:
                self._show_error_message(app_exception, report.report_id)

        except Exception as e:
            # 错误处理器本身出错，使用最基本的日志记录
            logger.critical(f"错误处理器失败: {e}", exc_info=True)
            print(f"CRITICAL: Error handler failed: {e}", file=sys.stderr)

    def _show_error_message(self, exception: BaseAppException, report_id: str) -> None:
        """显示错误消息对话框"""
        try:
            from PySide6.QtWidgets import QMessageBox, QWidget

            # 查找主窗口
            app = QApplication.instance()
            if not app:
                return

            main_window = None
            # 查找主窗口
            if hasattr(app, "allWidgets"):
                for widget in app.allWidgets():
                    if isinstance(widget, QWidget) and widget.objectName() == "mainWindow":
                        main_window = widget
                        break
            elif hasattr(app, "activeWindow"):
                main_window = app.activeWindow()

            if not main_window:
                return

            # 创建错误消息
            title = f"错误 - {exception.error_code.name}"
            message = f"错误代码: {exception.error_code.code}\n"
            message += f"错误描述: {exception.message}\n"
            message += f"报告ID: {report_id}\n\n"

            if exception.error_code.recoverable:
                message += "此错误可以自动恢复，系统将尝试继续运行。"
            else:
                message += "这是一个严重错误，可能需要重启应用程序。"

            # 显示消息框
            msg_box = QMessageBox(main_window)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Icon.Critical)

            # 添加按钮
            if exception.error_code.recoverable:
                msg_box.addButton("重试", QMessageBox.ButtonRole.ActionRole)
                msg_box.addButton("忽略", QMessageBox.ButtonRole.ActionRole)
            else:
                msg_box.addButton("重启应用", QMessageBox.ButtonRole.ActionRole)

            msg_box.addButton("查看详情", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton("关闭", QMessageBox.ButtonRole.RejectRole)

            # 显示对话框
            result = msg_box.exec()

            # 处理用户选择
            if result == 0 and exception.error_code.recoverable:  # 重试
                logger.info(f"用户选择重试: {exception.error_code.name}")
                self._handle_retry(exception, main_window)
            elif result == 1 and exception.error_code.recoverable:  # 忽略
                logger.info(f"用户选择忽略: {exception.error_code.name}")
            elif result == 0 and not exception.error_code.recoverable:  # 重启应用
                logger.info(f"用户选择重启应用: {exception.error_code.name}")
                self._handle_restart(main_window)
            elif result == 1 or result == 2:  # 查看详情
                self._show_error_details(exception, report_id, main_window)

        except Exception as e:
            logger.error(f"显示错误消息失败: {e}", exc_info=True)

    def _handle_retry(self, exception: BaseAppException, main_window: Any) -> None:
        """
        处理重试逻辑

        Args:
            exception: 异常对象
            main_window: 主窗口实例
        """
        try:
            logger.info(f"开始重试操作: {exception.error_code.name}")

            # 尝试自动恢复
            recovery_success = recovery_manager.recover_from_error(exception, {})

            if recovery_success:
                # 恢复成功，显示通知
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(main_window, "重试成功", f"已成功恢复从错误: {exception.message}")
                logger.info("重试操作成功")
            else:
                # 恢复失败，询问用户
                from PySide6.QtWidgets import QMessageBox

                retry_result = QMessageBox.question(
                    main_window,
                    "重试失败",
                    f"自动恢复失败。\n\n错误: {exception.message}\n\n是否重新加载当前视图？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )

                if retry_result == QMessageBox.StandardButton.Yes:
                    # 重新加载当前实验或视图
                    self._reload_current_view(main_window)
                    logger.info("已重新加载当前视图")
                else:
                    logger.info("用户取消重新加载")

        except Exception as e:
            logger.error(f"处理重试失败: {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(main_window, "重试失败", f"重试操作时发生错误: {str(e)}")

    def _handle_restart(self, main_window: Any) -> None:
        """
        处理重启应用逻辑

        Args:
            main_window: 主窗口实例
        """
        try:
            from PySide6.QtWidgets import QMessageBox

            # 确认重启
            result = QMessageBox.question(
                main_window,
                "确认重启",
                "重启应用将关闭所有窗口并重新启动程序。\n\n未保存的数据可能会丢失。\n\n是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if result == QMessageBox.StandardButton.Yes:
                logger.info("用户确认重启应用")

                # 保存应用状态
                try:
                    if hasattr(main_window, "save_state"):
                        logger.info("保存应用状态...")
                        main_window.save_state()
                except Exception as e:
                    logger.warning(f"保存应用状态失败: {e}")

                # 重启应用
                self._restart_application()
            else:
                logger.info("用户取消重启")

        except Exception as e:
            logger.error(f"处理重启失败: {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(main_window, "重启失败", f"重启应用时发生错误: {str(e)}")

    def _reload_current_view(self, main_window: Any) -> None:
        """
        重新加载当前视图

        Args:
            main_window: 主窗口实例
        """
        try:
            # 尝试重新加载当前实验
            if hasattr(main_window, "current_experiment_view") and main_window.current_experiment_view:
                logger.info("重新加载当前实验视图")
                current_exp_id = getattr(main_window.current_experiment_view, "experiment_id", None)
                if current_exp_id:
                    # 关闭当前视图
                    main_window.current_experiment_view.close()
                    # 重新加载
                    main_window.load_experiment(current_exp_id)
                else:
                    logger.warning("无法获取当前实验ID")
            else:
                logger.info("没有当前活动的实验视图")

        except Exception as e:
            logger.error(f"重新加载视图失败: {e}", exc_info=True)
            raise

    def _restart_application(self) -> None:
        """重启应用程序"""
        try:
            import os
            import sys

            logger.info("正在重启应用...")

            # 获取Python可执行文件和脚本路径
            python = sys.executable
            script = sys.argv[0]

            # 使用os.execl重启（Unix系统）或subprocess（Windows）
            if sys.platform == "win32":
                import subprocess

                # Windows系统使用subprocess
                subprocess.Popen([python, script] + sys.argv[1:])
                # 退出当前进程
                if self.app:
                    self.app.quit()
                sys.exit(0)
            else:
                # Unix系统使用os.execl
                os.execl(python, python, script, *sys.argv[1:])

        except Exception as e:
            logger.error(f"重启应用失败: {e}", exc_info=True)
            raise

    def _show_error_details(self, exception: BaseAppException, report_id: str, parent: Any) -> None:
        """显示错误详情"""
        try:
            from PySide6.QtWidgets import (
                QDialog,
                QHBoxLayout,
                QPushButton,
                QTextEdit,
                QVBoxLayout,
            )

            dialog = QDialog(parent)
            dialog.setWindowTitle("错误详情")
            dialog.setModal(True)
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)

            # 错误详情文本
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setFont(QFont("Consolas", 9))

            # 构建详情内容
            details = "错误报告详情\n"
            details += "=" * 50 + "\n\n"
            details += f"报告ID: {report_id}\n"
            details += f"错误代码: {exception.error_code.code}\n"
            details += f"错误名称: {exception.error_code.name}\n"
            details += f"错误描述: {exception.message}\n"
            details += f"严重程度: {exception.error_code.severity}\n"
            details += f"是否可恢复: {'是' if exception.error_code.recoverable else '否'}\n"
            details += f"发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            if hasattr(exception, "context") and exception.context:
                details += "错误上下文:\n"
                for key, value in exception.context.items():
                    details += f"  {key}: {value}\n"
                details += "\n"

            if hasattr(exception, "__traceback__") and exception.__traceback__:
                import traceback

                details += "堆栈跟踪:\n"
                details += traceback.format_exc()

            details_text.setPlainText(details)
            layout.addWidget(details_text)

            # 按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            copy_button = QPushButton("复制详情")
            copy_button.clicked.connect(lambda: self._copy_to_clipboard(details))
            button_layout.addWidget(copy_button)

            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)

            dialog.exec()

        except Exception as e:
            logger.error(f"显示错误详情失败: {e}", exc_info=True)

    def _copy_to_clipboard(self, text: str) -> None:
        """复制文本到剪贴板"""
        try:
            from PySide6.QtWidgets import QApplication

            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            logger.info("错误详情已复制到剪贴板")
        except Exception as e:
            logger.error(f"复制到剪贴板失败: {e}")

    def set_show_error_dialog(self, show: bool) -> None:
        """
        设置是否显示错误对话框

        Args:
            show: 是否显示
        """
        self._show_error_dialog = show

    def set_auto_recovery(self, enabled: bool) -> None:
        """
        设置是否启用自动恢复

        Args:
            enabled: 是否启用
        """
        self._auto_recovery = enabled


# 全局错误拦截器实例（不自动创建，需要在应用启动时创建）
global_error_interceptor: ErrorInterceptor | None = None


def install_error_interceptor(
    app: Any = None,
    show_error_dialog: bool = True,
    auto_recovery: bool = True,
) -> ErrorInterceptor:
    """
    安装全局错误拦截器

    Args:
        app: Qt应用程序实例
        show_error_dialog: 是否显示错误对话框
        auto_recovery: 是否启用自动恢复

    Returns:
        错误拦截器实例
    """
    global global_error_interceptor

    if global_error_interceptor is not None:
        logger.warning("全局错误拦截器已存在")
        return global_error_interceptor

    interceptor = ErrorInterceptor(app)
    interceptor.set_show_error_dialog(show_error_dialog)
    interceptor.set_auto_recovery(auto_recovery)
    interceptor.install()

    global_error_interceptor = interceptor
    logger.info("全局错误拦截器已安装")

    return interceptor


def uninstall_error_interceptor() -> None:
    """卸载全局错误拦截器"""
    global global_error_interceptor

    if global_error_interceptor:
        global_error_interceptor.uninstall()
        global_error_interceptor = None
        logger.info("全局错误拦截器已卸载")


# 控制台版本的错误拦截器（无需Qt）
class ConsoleErrorInterceptor:
    """控制台错误拦截器（非Qt版本）"""

    def __init__(self) -> None:
        self._installed = False

    def install(self) -> None:
        """安装全局异常钩子"""
        if self._installed:
            logger.warning("控制台错误拦截器已安装")
            return

        sys.excepthook = self._exception_hook
        self._installed = True
        logger.info("控制台错误拦截器已安装")

    def uninstall(self) -> None:
        """卸载全局异常钩子"""
        if not self._installed:
            return

        sys.excepthook = sys.__excepthook__
        self._installed = False
        logger.info("控制台错误拦截器已卸载")

    def _exception_hook(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        """Python异常钩子"""
        # 忽略KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 转换为应用异常
        if isinstance(exc_value, BaseAppException):
            app_exception = exc_value
        elif isinstance(exc_value, Exception):
            app_exception = from_standard_exception(exc_value, "全局未捕获异常")
        else:
            # 对于非Exception类型的异常，创建一个通用错误
            app_exception = BaseAppException(
                f"未知异常: {exc_type.__name__}: {exc_value}",
                error_code=ErrorCodeRegistry.UNKNOWN_ERROR,
                details={"exception_type": exc_type.__name__},
            )

        # 记录错误
        error_handler.handle_exception(app_exception, "全局未捕获异常")

        # 生成错误报告（使用控制台通知）
        error_reporter.report_error(
            app_exception,
            "全局未捕获异常",
            notify=True,
            notification_channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG],
        )

        # 打印到stderr
        traceback.print_exception(exc_type, exc_value, exc_traceback)


def install_console_error_interceptor() -> ConsoleErrorInterceptor:
    """
    安装控制台错误拦截器

    Returns:
        控制台错误拦截器实例
    """
    interceptor = ConsoleErrorInterceptor()
    interceptor.install()
    return interceptor
