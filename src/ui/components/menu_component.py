"""
菜单组件
提供主窗口菜单功能
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from .base_window import BaseWindowComponent
from ...core.common_exceptions import UIError

logger = logging.getLogger(__name__)


class MenuComponent(BaseWindowComponent):
    """菜单组件"""

    # 信号定义
    action_triggered = Signal(str)
    menu_ready = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._menubar: Optional[QMenuBar] = None
        self._menus: dict[str, QMenu] = {}
        self._actions: dict[str, QAction] = {}

    def _setup_ui(self) -> None:
        """设置UI"""
        # 创建菜单栏
        self._menubar = QMenuBar(self)

        # 添加默认菜单
        self._add_default_menus()

    def _add_default_menus(self) -> None:
        """添加默认菜单"""
        # 文件菜单
        file_menu = self._add_menu("file", "文件(&F)")

        # 新建实验
        new_action = QAction("新建实验(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(lambda: self.action_triggered.emit("new_experiment"))
        self._add_action("new_experiment", new_action, file_menu)

        # 打开实验
        open_action = QAction("打开实验(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(lambda: self.action_triggered.emit("open_experiment"))
        self._add_action("open_experiment", open_action, file_menu)

        # 保存实验
        save_action = QAction("保存实验(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: self.action_triggered.emit("save_experiment"))
        self._add_action("save_experiment", save_action, file_menu)

        # 分隔符
        file_menu.addSeparator()

        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(lambda: self.action_triggered.emit("exit"))
        self._add_action("exit", exit_action, file_menu)

        # 编辑菜单
        edit_menu = self._add_menu("edit", "编辑(&E)")

        # 撤销
        undo_action = QAction("撤销(&U)", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(lambda: self.action_triggered.emit("undo"))
        self._add_action("undo", undo_action, edit_menu)

        # 重做
        redo_action = QAction("重做(&R)", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(lambda: self.action_triggered.emit("redo"))
        self._add_action("redo", redo_action, edit_menu)

        # 分隔符
        edit_menu.addSeparator()

        # 复制
        copy_action = QAction("复制(&C)", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(lambda: self.action_triggered.emit("copy"))
        self._add_action("copy", copy_action, edit_menu)

        # 粘贴
        paste_action = QAction("粘贴(&V)", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(lambda: self.action_triggered.emit("paste"))
        self._add_action("paste", paste_action, edit_menu)

        # 实验菜单
        experiment_menu = self._add_menu("experiment", "实验(&X)")

        # 运行实验
        run_action = QAction("运行实验(&R)", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(lambda: self.action_triggered.emit("run_experiment"))
        self._add_action("run_experiment", run_action, experiment_menu)

        # 停止实验
        stop_action = QAction("停止实验(&S)", self)
        stop_action.setShortcut("F6")
        stop_action.triggered.connect(lambda: self.action_triggered.emit("stop_experiment"))
        self._add_action("stop_experiment", stop_action, experiment_menu)

        # 分隔符
        experiment_menu.addSeparator()

        # 实验设置
        settings_action = QAction("实验设置(&S)", self)
        settings_action.triggered.connect(lambda: self.action_triggered.emit("experiment_settings"))
        self._add_action("experiment_settings", settings_action, experiment_menu)

        # 工具菜单
        tools_menu = self._add_menu("tools", "工具(&T)")

        # 设置
        settings_action = QAction("设置(&S)", self)
        settings_action.triggered.connect(lambda: self.action_triggered.emit("settings"))
        self._add_action("settings", settings_action, tools_menu)

        # 分隔符
        tools_menu.addSeparator()

        # 开发者工具
        dev_tools_action = QAction("开发者工具(&D)", self)
        dev_tools_action.setShortcut("F12")
        dev_tools_action.triggered.connect(lambda: self.action_triggered.emit("dev_tools"))
        self._add_action("dev_tools", dev_tools_action, tools_menu)

        # 帮助菜单
        help_menu = self._add_menu("help", "帮助(&H)")

        # 帮助
        help_action = QAction("帮助(&H)", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(lambda: self.action_triggered.emit("help"))
        self._add_action("help", help_action, help_menu)

        # 分隔符
        help_menu.addSeparator()

        # 关于
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(lambda: self.action_triggered.emit("about"))
        self._add_action("about", about_action, help_menu)

    def _add_menu(self, name: str, title: str) -> QMenu:
        """添加菜单"""
        if self._menubar is None:
            raise UIError("MenuBar not initialized", widget="MenuComponent", action="add_menu")

        menu = QMenu(title, self)
        self._menus[name] = menu
        self._menubar.addMenu(menu)
        logger.debug(f"Menu {name} added")
        return menu

    def _add_action(self, name: str, action: QAction, menu: QMenu) -> None:
        """添加动作到菜单"""
        self._actions[name] = action
        menu.addAction(action)
        logger.debug(f"Action {name} added to menu")

    def add_menu(self, name: str, title: str) -> QMenu:
        """添加菜单"""
        return self._add_menu(name, title)

    def add_action(self, name: str, text: str, menu_name: str, shortcut: Optional[str] = None) -> None:
        """添加动作到指定菜单"""
        if menu_name not in self._menus:
            raise UIError(f"Menu {menu_name} not found", widget="MenuComponent", action="add_action")

        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda: self.action_triggered.emit(name))
        self._add_action(name, action, self._menus[menu_name])

    def remove_action(self, name: str) -> None:
        """移除动作"""
        if name in self._actions:
            action = self._actions.pop(name)
            # 从所有菜单中移除
            for menu in self._menus.values():
                menu.removeAction(action)
            logger.debug(f"Action {name} removed")

    def get_action(self, name: str) -> Optional[QAction]:
        """获取动作"""
        return self._actions.get(name)

    def set_action_enabled(self, name: str, enabled: bool) -> None:
        """设置动作启用状态"""
        if name in self._actions:
            self._actions[name].setEnabled(enabled)

    def get_menu(self, name: str) -> Optional[QMenu]:
        """获取菜单"""
        return self._menus.get(name)

    def get_menubar(self) -> Optional[QMenuBar]:
        """获取菜单栏"""
        return self._menubar

    def _cleanup_resources(self) -> None:
        """清理资源"""
        if self._menubar:
            self._menubar.clear()
        self._menus.clear()
        self._actions.clear()
