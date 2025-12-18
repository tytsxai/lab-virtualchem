"""
状态栏组件
提供主窗口状态栏功能
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QProgressBar, QStatusBar, QWidget

from ...core.common_exceptions import UIError
from .base_window import BaseWindowComponent

logger = logging.getLogger(__name__)


class StatusBarComponent(BaseWindowComponent):
    """状态栏组件"""

    # 信号定义
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._statusbar: QStatusBar | None = None
        self._status_label: QLabel | None = None
        self._progress_bar: QProgressBar | None = None
        self._timer: QTimer | None = None

    def _setup_ui(self) -> None:
        """设置UI"""
        # 创建状态栏
        self._statusbar = QStatusBar(self)

        # 创建状态标签
        self._status_label = QLabel("就绪")
        self._statusbar.addWidget(self._status_label)

        # 创建进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 100)
        self._statusbar.addPermanentWidget(self._progress_bar)

        # 创建定时器用于自动隐藏进度条
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._hide_progress)
        self._timer.setSingleShot(True)

    def set_status(self, message: str, timeout: int = 0) -> None:
        """设置状态消息"""
        if self._status_label is None:
            raise UIError(
                "Status label not initialized",
                widget="StatusBarComponent",
                action="set_status",
            )

        self._status_label.setText(message)
        self.status_changed.emit(message)
        logger.debug(f"Status updated: {message}")

        # 设置超时
        if timeout > 0:
            QTimer.singleShot(timeout, self, lambda: self.set_status("就绪"))

    def show_progress(self, value: int = 0, maximum: int = 100) -> None:
        """显示进度条"""
        if self._progress_bar is None:
            raise UIError(
                "Progress bar not initialized",
                widget="StatusBarComponent",
                action="show_progress",
            )

        self._progress_bar.setRange(0, maximum)
        self._progress_bar.setValue(value)
        self._progress_bar.setVisible(True)
        self.progress_changed.emit(value)

    def hide_progress(self) -> None:
        """隐藏进度条"""
        if self._progress_bar:
            self._progress_bar.setVisible(False)

    def _hide_progress(self) -> None:
        """自动隐藏进度条"""
        self.hide_progress()

    def set_progress(self, value: int) -> None:
        """设置进度值"""
        if self._progress_bar and self._progress_bar.isVisible():
            self._progress_bar.setValue(value)
            self.progress_changed.emit(value)

    def get_status(self) -> str:
        """获取当前状态"""
        if self._status_label:
            return self._status_label.text()
        return ""

    def get_progress(self) -> int:
        """获取当前进度"""
        if self._progress_bar:
            return self._progress_bar.value()
        return 0

    def is_progress_visible(self) -> bool:
        """检查进度条是否可见"""
        return self._progress_bar is not None and self._progress_bar.isVisible()

    def get_statusbar(self) -> QStatusBar | None:
        """获取状态栏"""
        return self._statusbar

    def _cleanup_resources(self) -> None:
        """清理资源"""
        if self._timer:
            self._timer.stop()
        if self._statusbar:
            self._statusbar.clearMessage()
