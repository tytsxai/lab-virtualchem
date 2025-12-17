"""
进度对话框组件
为耗时操作提供可视化进度反馈
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProgressWorker(QThread):
    """后台工作线程"""

    progress = Signal(int, str)  # 进度值, 状态消息
    finished = Signal(bool, str)  # 是否成功, 结果消息
    error = Signal(str)  # 错误消息

    def __init__(self, task: Callable, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False

    def run(self):
        """执行任务"""
        try:
            result = self.task(
                *self.args, **self.kwargs, progress_callback=self.report_progress
            )
            if not self._is_cancelled:
                self.finished.emit(True, str(result) if result else "操作完成")
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
                self.finished.emit(False, f"操作失败: {e}")

    def report_progress(self, value: int, message: str = ""):
        """报告进度"""
        if not self._is_cancelled:
            self.progress.emit(value, message)

    def cancel(self):
        """取消任务"""
        self._is_cancelled = True


class ProgressDialog(QDialog):
    """进度对话框"""

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "处理中",
        message: str = "正在处理，请稍候...",
        cancellable: bool = True,
        indeterminate: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )

        self.cancellable = cancellable
        self.cancelled = False
        self.worker: ProgressWorker | None = None

        self.init_ui(message, indeterminate)

    def init_ui(self, message: str, indeterminate: bool):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 消息标签
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                font-size: 12pt;
                color: #2c3e50;
                padding: 10px 0;
            }
        """)
        layout.addWidget(self.message_label)

        # 进度条
        self.progress_bar = QProgressBar()
        if indeterminate:
            self.progress_bar.setRange(0, 0)  # 不确定进度
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)

        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 11pt;
                background-color: #f8f9fa;
                height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 详细状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                color: #7f8c8d;
                padding: 5px 0;
            }
        """)
        layout.addWidget(self.status_label)

        # 取消按钮
        if self.cancellable:
            self.cancel_button = QPushButton("取消")
            self.cancel_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 30px;
                    font-size: 11pt;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
                QPushButton:disabled {
                    background-color: #bdc3c7;
                }
            """)
            self.cancel_button.clicked.connect(self.on_cancel)
            layout.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_message(self, message: str):
        """设置主消息"""
        self.message_label.setText(message)

    def set_status(self, status: str):
        """设置详细状态"""
        self.status_label.setText(status)

    def set_progress(self, value: int):
        """设置进度值"""
        self.progress_bar.setValue(value)

    def update_progress(self, value: int, message: str = ""):
        """更新进度和消息"""
        self.set_progress(value)
        if message:
            self.set_status(message)

    def on_cancel(self):
        """取消操作"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.set_status("正在取消...")
            if self.cancellable:
                self.cancel_button.setEnabled(False)
        self.cancelled = True

    def run_task(self, task: Callable, *args, **kwargs) -> bool:
        """在后台线程中运行任务

        Args:
            task: 要执行的函数，需要接受progress_callback参数
            *args: 任务参数
            **kwargs: 任务关键字参数

        Returns:
            bool: 任务是否成功完成
        """
        self.worker = ProgressWorker(task, *args, **kwargs)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.error.connect(self.on_task_error)

        self.worker.start()
        result = self.exec()

        return result == QDialog.DialogCode.Accepted

    def on_task_finished(self, success: bool, message: str):
        """任务完成"""
        if success:
            self.set_progress(100)
            self.set_status("完成！")
            QTimer.singleShot(500, lambda: self.accept())
        else:
            self.set_status(message)
            QTimer.singleShot(1000, lambda: self.reject())

    def on_task_error(self, error: str):
        """任务错误"""
        self.set_status(f"错误: {error}")


class SimpleProgressDialog:
    """简单的进度对话框（静态方法工具类）"""

    @staticmethod
    def run(
        task: Callable,
        *args,
        parent: QWidget | None = None,
        title: str = "处理中",
        message: str = "正在处理，请稍候...",
        cancellable: bool = True,
        **kwargs,
    ) -> tuple[bool, str]:
        """运行任务并显示进度对话框

        Args:
            task: 要执行的函数
            *args: 任务参数
            parent: 父窗口
            title: 对话框标题
            message: 对话框消息
            cancellable: 是否可取消
            **kwargs: 任务关键字参数

        Returns:
            tuple[bool, str]: (是否成功, 结果消息)
        """
        dialog = ProgressDialog(parent, title, message, cancellable)
        success = dialog.run_task(task, *args, **kwargs)

        return success, dialog.status_label.text()
