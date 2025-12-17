"""
工具栏组件
提供主窗口工具栏功能
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QToolBar, QWidget

from ...core.common_exceptions import UIError
from .base_window import BaseWindowComponent

logger = logging.getLogger(__name__)


class ToolbarComponent(BaseWindowComponent):
    """工具栏组件"""

    # 信号定义
    action_triggered = Signal(str)
    toolbar_ready = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._toolbar: QToolBar | None = None
        self._actions: dict[str, QAction] = {}

    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建工具栏
        self._toolbar = QToolBar("主工具栏", self)
        self._toolbar.setMovable(True)
        self._toolbar.setFloatable(True)

        layout.addWidget(self._toolbar)

        # 添加默认动作
        self._add_default_actions()

    def _add_default_actions(self) -> None:
        """添加默认动作"""
        # 新建实验
        new_action = QAction("新建实验", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(
            lambda: self.action_triggered.emit("new_experiment")
        )
        self._add_action("new_experiment", new_action)

        # 打开实验
        open_action = QAction("打开实验", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(
            lambda: self.action_triggered.emit("open_experiment")
        )
        self._add_action("open_experiment", open_action)

        # 保存实验
        save_action = QAction("保存实验", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(
            lambda: self.action_triggered.emit("save_experiment")
        )
        self._add_action("save_experiment", save_action)

        # 分隔符
        self._toolbar.addSeparator()

        # 运行实验
        run_action = QAction("运行实验", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(
            lambda: self.action_triggered.emit("run_experiment")
        )
        self._add_action("run_experiment", run_action)

        # 停止实验
        stop_action = QAction("停止实验", self)
        stop_action.setShortcut("F6")
        stop_action.triggered.connect(
            lambda: self.action_triggered.emit("stop_experiment")
        )
        self._add_action("stop_experiment", stop_action)

        # 分隔符
        self._toolbar.addSeparator()

        # 设置
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(
            lambda: self.action_triggered.emit("settings")
        )
        self._add_action("settings", settings_action)

        # 帮助
        help_action = QAction("帮助", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(lambda: self.action_triggered.emit("help"))
        self._add_action("help", help_action)

    def _add_action(self, name: str, action: QAction) -> None:
        """添加动作"""
        if self._toolbar is None:
            raise UIError(
                "Toolbar not initialized",
                widget="ToolbarComponent",
                action="add_action",
            )

        self._actions[name] = action
        self._toolbar.addAction(action)
        logger.debug(f"Action {name} added to toolbar")

    def add_action(self, name: str, text: str, shortcut: str | None = None) -> None:
        """添加动作"""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda: self.action_triggered.emit(name))
        self._add_action(name, action)

    def remove_action(self, name: str) -> None:
        """移除动作"""
        if name in self._actions:
            action = self._actions.pop(name)
            self._toolbar.removeAction(action)
            logger.debug(f"Action {name} removed from toolbar")

    def get_action(self, name: str) -> QAction | None:
        """获取动作"""
        return self._actions.get(name)

    def set_action_enabled(self, name: str, enabled: bool) -> None:
        """设置动作启用状态"""
        if name in self._actions:
            self._actions[name].setEnabled(enabled)

    def get_toolbar(self) -> QToolBar | None:
        """获取工具栏"""
        return self._toolbar

    def _cleanup_resources(self) -> None:
        """清理资源"""
        if self._toolbar:
            self._toolbar.clear()
        self._actions.clear()
