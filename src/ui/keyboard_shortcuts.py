"""键盘快捷键支持"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ShortcutAction:
    """快捷键动作"""

    # 导航
    NEXT_STEP = "next_step"
    PREV_STEP = "prev_step"
    FIRST_STEP = "first_step"
    LAST_STEP = "last_step"

    # 操作
    SUBMIT = "submit"
    RESET = "reset"
    UNDO = "undo"
    REDO = "redo"

    # 保存/加载
    SAVE = "save"
    LOAD = "load"
    QUICK_SAVE = "quick_save"

    # 视图
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    ZOOM_RESET = "zoom_reset"
    TOGGLE_FULLSCREEN = "toggle_fullscreen"

    # 帮助
    SHOW_HELP = "show_help"
    SHOW_HINTS = "show_hints"


class KeyboardShortcutManager(QObject):
    """键盘快捷键管理器"""

    # 信号
    shortcut_triggered = Signal(str)  # 快捷键触发，参数为动作名称

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.parent_widget = parent
        self.shortcuts: dict[str, QShortcut] = {}
        self.enabled = True

        # 默认快捷键映射
        self.default_shortcuts = {
            # 导航 (方向键)
            ShortcutAction.NEXT_STEP: [Qt.Key.Key_Right, Qt.Key.Key_N],
            ShortcutAction.PREV_STEP: [Qt.Key.Key_Left, Qt.Key.Key_P],
            ShortcutAction.FIRST_STEP: [Qt.Key.Key_Home],
            ShortcutAction.LAST_STEP: [Qt.Key.Key_End],
            # 操作 (Enter/Escape)
            ShortcutAction.SUBMIT: [Qt.Key.Key_Return, Qt.Key.Key_Enter],
            ShortcutAction.RESET: [Qt.Key.Key_Escape],
            ShortcutAction.UNDO: [QKeySequence.StandardKey.Undo],  # Ctrl+Z
            ShortcutAction.REDO: [QKeySequence.StandardKey.Redo],  # Ctrl+Y
            # 保存/加载
            ShortcutAction.SAVE: [QKeySequence.StandardKey.Save],  # Ctrl+S
            ShortcutAction.LOAD: [QKeySequence.StandardKey.Open],  # Ctrl+O
            ShortcutAction.QUICK_SAVE: [Qt.Key.Key_F5],
            # 视图
            ShortcutAction.ZOOM_IN: [QKeySequence.StandardKey.ZoomIn],  # Ctrl++
            ShortcutAction.ZOOM_OUT: [QKeySequence.StandardKey.ZoomOut],  # Ctrl+-
            ShortcutAction.ZOOM_RESET: [QKeySequence.StandardKey.ZoomIn],  # Ctrl+0
            ShortcutAction.TOGGLE_FULLSCREEN: [Qt.Key.Key_F11],
            # 帮助
            ShortcutAction.SHOW_HELP: [Qt.Key.Key_F1],
            ShortcutAction.SHOW_HINTS: [Qt.Key.Key_H],
        }

    def register_shortcuts(self, parent: QWidget | None = None) -> None:
        """注册所有快捷键"""
        parent = parent or self.parent_widget

        if not parent:
            logger.warning("没有指定父窗口，无法注册快捷键")
            return

        for action, keys in self.default_shortcuts.items():
            if isinstance(keys, list):
                for key in keys:
                    self.add_shortcut(action, key, parent)

        logger.info(f"已注册 {len(self.shortcuts)} 个快捷键")

    def add_shortcut(
        self,
        action: str,
        key: Qt.Key | QKeySequence.StandardKey | int,
        parent: QWidget | None = None,
    ) -> None:
        """
        添加快捷键

        Args:
            action: 动作名称
            key: 快捷键
            parent: 父窗口
        """
        parent = parent or self.parent_widget

        if not parent:
            logger.warning(f"无法添加快捷键 {action}: 没有父窗口")
            return

        shortcut_id = f"{action}_{id(key)}"

        if shortcut_id in self.shortcuts:
            logger.debug(f"快捷键已存在: {shortcut_id}")
            return

        try:
            # 创建快捷键
            if isinstance(key, QKeySequence.StandardKey):
                shortcut = QShortcut(QKeySequence(key), parent)
            else:
                shortcut = QShortcut(QKeySequence(key), parent)

            # 连接信号
            shortcut.activated.connect(lambda a=action: self._on_shortcut_activated(a))

            self.shortcuts[shortcut_id] = shortcut
            logger.debug(f"添加快捷键: {action} -> {key}")

        except Exception as e:
            logger.error(f"添加快捷键失败 {action}: {e}")

    def remove_shortcut(self, action: str) -> None:
        """移除快捷键"""
        removed = []

        for shortcut_id in list(self.shortcuts.keys()):
            if shortcut_id.startswith(action):
                shortcut = self.shortcuts.pop(shortcut_id)
                shortcut.setEnabled(False)
                shortcut.deleteLater()
                removed.append(shortcut_id)

        logger.debug(f"移除快捷键: {removed}")

    def _on_shortcut_activated(self, action: str) -> None:
        """快捷键被触发"""
        if not self.enabled:
            logger.debug(f"快捷键已禁用: {action}")
            return

        logger.info(f"快捷键触发: {action}")
        self.shortcut_triggered.emit(action)

    def enable(self) -> None:
        """启用快捷键"""
        self.enabled = True
        for shortcut in self.shortcuts.values():
            shortcut.setEnabled(True)
        logger.info("快捷键已启用")

    def disable(self) -> None:
        """禁用快捷键"""
        self.enabled = False
        for shortcut in self.shortcuts.values():
            shortcut.setEnabled(False)
        logger.info("快捷键已禁用")

    def get_shortcut_list(self) -> list[dict[str, str]]:
        """获取快捷键列表（用于显示帮助）"""
        shortcuts_info = []

        action_names = {
            ShortcutAction.NEXT_STEP: "下一步",
            ShortcutAction.PREV_STEP: "上一步",
            ShortcutAction.FIRST_STEP: "第一步",
            ShortcutAction.LAST_STEP: "最后一步",
            ShortcutAction.SUBMIT: "提交",
            ShortcutAction.RESET: "重置",
            ShortcutAction.UNDO: "撤销",
            ShortcutAction.REDO: "重做",
            ShortcutAction.SAVE: "保存",
            ShortcutAction.LOAD: "加载",
            ShortcutAction.QUICK_SAVE: "快速保存",
            ShortcutAction.ZOOM_IN: "放大",
            ShortcutAction.ZOOM_OUT: "缩小",
            ShortcutAction.ZOOM_RESET: "重置缩放",
            ShortcutAction.TOGGLE_FULLSCREEN: "全屏",
            ShortcutAction.SHOW_HELP: "帮助",
            ShortcutAction.SHOW_HINTS: "显示提示",
        }

        for action, keys in self.default_shortcuts.items():
            key_strings: list[str] = []
            if isinstance(keys, list):
                for key in keys:
                    if isinstance(key, QKeySequence.StandardKey):
                        key_strings.append(QKeySequence(key).toString())
                    else:
                        key_strings.append(QKeySequence(key).toString())

            shortcuts_info.append(
                {
                    "action": action,
                    "name": action_names.get(action, action),
                    "keys": ", ".join(key_strings),
                }
            )

        return shortcuts_info


class ShortcutHelpDialog:
    """快捷键帮助对话框（静态方法）"""

    @staticmethod
    def show_help(parent: QWidget | None, shortcuts: list[dict[str, str]]) -> None:
        """显示快捷键帮助"""
        from PySide6.QtWidgets import (
            QDialog,
            QLabel,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
        )

        dialog = QDialog(parent)
        dialog.setWindowTitle("⌨️ 键盘快捷键")
        dialog.setMinimumSize(400, 500)

        layout = QVBoxLayout(dialog)

        # 标题
        title = QLabel("快捷键列表")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # 表格
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["功能", "快捷键"])
        table.setRowCount(len(shortcuts))

        for i, shortcut in enumerate(shortcuts):
            table.setItem(i, 0, QTableWidgetItem(shortcut["name"]))
            table.setItem(i, 1, QTableWidgetItem(shortcut["keys"]))

        table.resizeColumnsToContents()
        layout.addWidget(table)

        # 说明
        note = QLabel("提示：按 F1 随时查看此帮助")
        note.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(note)

        dialog.exec()
