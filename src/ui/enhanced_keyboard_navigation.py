"""
增强的键盘导航系统
提供完善的键盘操作支持
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class NavigationMode(Enum):
    """导航模式"""

    NORMAL = "normal"  # 正常模式
    SPATIAL = "spatial"  # 空间导航（方向键）
    LINEAR = "linear"  # 线性导航（Tab键）
    CUSTOM = "custom"  # 自定义导航


class KeyboardNavigationManager(QObject):
    """键盘导航管理器"""

    # 信号
    focus_changed = Signal(QWidget, QWidget)  # 焦点变更: (旧控件, 新控件)
    shortcut_triggered = Signal(str)  # 快捷键触发
    navigation_mode_changed = Signal(NavigationMode)  # 导航模式变更

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 导航模式
        self.mode = NavigationMode.NORMAL

        # 快捷键映射
        self.shortcuts: dict[QKeySequence, tuple[str, callable]] = {}

        # 焦点历史
        self.focus_history: list[QWidget] = []
        self.max_history = 10

        # 空间导航网格
        self.spatial_grid: dict[tuple[int, int], QWidget] = {}

        # 是否启用
        self.enabled = True

        # 是否显示焦点指示
        self.show_focus_indicator = True

        logger.info("键盘导航管理器初始化完成")

    def enable(self):
        """启用键盘导航"""
        self.enabled = True
        logger.info("键盘导航已启用")

    def disable(self):
        """禁用键盘导航"""
        self.enabled = False
        logger.info("键盘导航已禁用")

    def set_mode(self, mode: NavigationMode):
        """设置导航模式"""
        self.mode = mode
        self.navigation_mode_changed.emit(mode)
        logger.info(f"导航模式已设置: {mode.value}")

    def register_shortcut(self, key_sequence: str | QKeySequence, name: str, callback: callable):
        """注册快捷键

        Args:
            key_sequence: 按键序列（如 "Ctrl+S"）
            name: 快捷键名称
            callback: 回调函数
        """
        if isinstance(key_sequence, str):
            key_sequence = QKeySequence(key_sequence)

        self.shortcuts[key_sequence] = (name, callback)
        logger.info(f"注册快捷键: {key_sequence.toString()} -> {name}")

    def unregister_shortcut(self, key_sequence: str | QKeySequence):
        """注销快捷键"""
        if isinstance(key_sequence, str):
            key_sequence = QKeySequence(key_sequence)

        if key_sequence in self.shortcuts:
            name, _ = self.shortcuts.pop(key_sequence)
            logger.info(f"注销快捷键: {key_sequence.toString()} ({name})")

    def handle_key_event(self, event: QKeyEvent) -> bool:
        """处理按键事件

        Args:
            event: 按键事件

        Returns:
            是否处理了该事件
        """
        if not self.enabled:
            return False

        # 检查快捷键
        key_seq = QKeySequence(event.keyCombination())

        for shortcut, (name, callback) in self.shortcuts.items():
            if key_seq.matches(shortcut) == QKeySequence.SequenceMatch.ExactMatch:
                logger.debug(f"触发快捷键: {shortcut.toString()} ({name})")
                callback()
                self.shortcut_triggered.emit(name)
                return True

        # 空间导航
        if self.mode == NavigationMode.SPATIAL:
            return self._handle_spatial_navigation(event)

        # 线性导航
        elif self.mode == NavigationMode.LINEAR:
            return self._handle_linear_navigation(event)

        return False

    def _handle_spatial_navigation(self, event: QKeyEvent) -> bool:
        """处理空间导航"""
        current_widget = QApplication.focusWidget()

        if not current_widget:
            return False

        # 获取当前位置
        current_pos = self._get_grid_position(current_widget)

        if not current_pos:
            return False

        # 确定目标位置
        row, col = current_pos
        target_pos = None

        if event.key() == Qt.Key.Key_Up:
            target_pos = (row - 1, col)
        elif event.key() == Qt.Key.Key_Down:
            target_pos = (row + 1, col)
        elif event.key() == Qt.Key.Key_Left:
            target_pos = (row, col - 1)
        elif event.key() == Qt.Key.Key_Right:
            target_pos = (row, col + 1)

        if target_pos and target_pos in self.spatial_grid:
            target_widget = self.spatial_grid[target_pos]
            target_widget.setFocus()
            return True

        return False

    def _handle_linear_navigation(self, event: QKeyEvent) -> bool:
        """处理线性导航"""
        if event.key() == Qt.Key.Key_Tab:
            # Tab键：下一个控件
            QApplication.focusNextChild()
            return True
        elif event.key() == Qt.Key.Key_Backtab:
            # Shift+Tab：上一个控件
            QApplication.focusPreviousChild()
            return True

        return False

    def setup_tab_order(self, widgets: list[QWidget]):
        """设置Tab顺序

        Args:
            widgets: 控件列表（按Tab顺序）
        """
        for i in range(len(widgets) - 1):
            QWidget.setTabOrder(widgets[i], widgets[i + 1])

        logger.info(f"Tab顺序已设置: {len(widgets)} 个控件")

    def setup_spatial_grid(self, grid: dict[tuple[int, int], QWidget]):
        """设置空间导航网格

        Args:
            grid: {(行, 列): 控件}
        """
        self.spatial_grid = grid
        logger.info(f"空间导航网格已设置: {len(grid)} 个位置")

    def _get_grid_position(self, widget: QWidget) -> tuple[int, int] | None:
        """获取控件在网格中的位置"""
        for pos, w in self.spatial_grid.items():
            if w == widget:
                return pos
        return None

    def add_to_focus_history(self, widget: QWidget):
        """添加到焦点历史"""
        # 避免重复
        if self.focus_history and self.focus_history[-1] == widget:
            return

        self.focus_history.append(widget)

        # 限制历史大小
        if len(self.focus_history) > self.max_history:
            self.focus_history.pop(0)

    def go_back(self):
        """返回上一个焦点"""
        if len(self.focus_history) >= 2:
            # 移除当前焦点
            self.focus_history.pop()

            # 获取上一个焦点
            previous = self.focus_history[-1]
            previous.setFocus()

            logger.debug("返回上一个焦点")

    def get_focusable_widgets(self, parent: QWidget) -> list[QWidget]:
        """获取所有可聚焦的控件

        Args:
            parent: 父控件

        Returns:
            可聚焦控件列表
        """
        focusable = []

        for child in parent.findChildren(QWidget):
            if child.focusPolicy() != Qt.FocusPolicy.NoFocus and child.isVisible() and child.isEnabled():
                focusable.append(child)

        return focusable

    def auto_setup_tab_order(self, parent: QWidget):
        """自动设置Tab顺序（基于位置）

        Args:
            parent: 父控件
        """
        focusable = self.get_focusable_widgets(parent)

        # 按位置排序（从左到右，从上到下）
        focusable.sort(key=lambda w: (w.pos().y(), w.pos().x()))

        self.setup_tab_order(focusable)

    def add_focus_indicator(self, widget: QWidget, color: str = "#0066CC", thickness: int = 2):
        """添加焦点指示器

        Args:
            widget: 控件
            color: 焦点颜色
            thickness: 边框厚度
        """
        if not self.show_focus_indicator:
            return

        # 设置焦点样式
        focus_style = f"""
            QWidget:focus {{
                border: {thickness}px solid {color};
                border-radius: 4px;
                outline: none;
            }}
        """

        current_style = widget.styleSheet()
        widget.setStyleSheet(current_style + "\n" + focus_style)

    def install_event_filter(self, app: QApplication):
        """安装事件过滤器

        Args:
            app: 应用实例
        """
        app.installEventFilter(self)
        logger.info("键盘导航事件过滤器已安装")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """事件过滤器"""
        # 处理焦点变更
        if event.type() == QEvent.Type.FocusIn:
            if isinstance(obj, QWidget):
                old_widget = self.focus_history[-1] if self.focus_history else None
                self.add_to_focus_history(obj)
                self.focus_changed.emit(old_widget, obj)

        # 处理按键
        elif event.type() == QEvent.Type.KeyPress:
            if isinstance(event, QKeyEvent):
                if self.handle_key_event(event):
                    return True  # 事件已处理

        return super().eventFilter(obj, event)


class ShortcutHint:
    """快捷键提示"""

    # 常用快捷键
    COMMON_SHORTCUTS = {
        "保存": "Ctrl+S",
        "打开": "Ctrl+O",
        "撤销": "Ctrl+Z",
        "重做": "Ctrl+Y / Ctrl+Shift+Z",
        "复制": "Ctrl+C",
        "粘贴": "Ctrl+V",
        "剪切": "Ctrl+X",
        "查找": "Ctrl+F",
        "全选": "Ctrl+A",
        "帮助": "F1",
        "全屏": "F11",
        "刷新": "F5",
        "命令面板": "Ctrl+P",
        "设置": "Ctrl+,",
        "关闭": "Ctrl+W / Ctrl+Q",
    }

    @staticmethod
    def get_hint_text(shortcuts: dict[str, str] | None = None) -> str:
        """获取快捷键提示文本

        Args:
            shortcuts: 自定义快捷键字典

        Returns:
            提示文本
        """
        all_shortcuts = ShortcutHint.COMMON_SHORTCUTS.copy()

        if shortcuts:
            all_shortcuts.update(shortcuts)

        lines = ["# 键盘快捷键\n"]

        for name, keys in all_shortcuts.items():
            lines.append(f"**{name}**: `{keys}`")

        return "\n".join(lines)

    @staticmethod
    def create_hint_widget(parent: QWidget | None = None) -> QWidget:
        """创建快捷键提示控件"""
        from PySide6.QtWidgets import QLabel, QVBoxLayout

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)

        # 标题
        title = QLabel("<h3>键盘快捷键</h3>")
        layout.addWidget(title)

        # 快捷键列表
        for name, keys in ShortcutHint.COMMON_SHORTCUTS.items():
            label = QLabel(f"<b>{name}:</b> <code>{keys}</code>")
            layout.addWidget(label)

        widget.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 16px;
            }
            QLabel {
                padding: 4px;
            }
        """
        )

        return widget


# 全局单例
_keyboard_navigation: KeyboardNavigationManager | None = None


def get_keyboard_navigation() -> KeyboardNavigationManager:
    """获取键盘导航管理器单例"""
    global _keyboard_navigation
    if _keyboard_navigation is None:
        _keyboard_navigation = KeyboardNavigationManager()
    return _keyboard_navigation
