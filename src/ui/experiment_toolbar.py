"""
交互式实验工具栏
提供实验操作的快捷工具和功能按钮
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExperimentToolbar(QFrame):
    """实验工具栏"""

    tool_selected = Signal(str)  # 工具ID
    action_triggered = Signal(str)  # 动作名称

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_tool: str | None = None
        self.tools: dict[str, QToolButton] = {}

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 10px;
            }
        """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 标题
        title_label = QLabel("实验工具")
        title_label.setStyleSheet(
            """
            QLabel {
                font-size: 13pt;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
            }
        """
        )
        main_layout.addWidget(title_label)

        # 工具按钮组（互斥选择）
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        # 工具部分
        tools_layout = QVBoxLayout()
        tools_layout.setSpacing(8)

        # 添加常用工具
        self._add_tool_section(
            tools_layout,
            "选择工具",
            [
                {"id": "select", "name": "选择", "icon": "➤", "tooltip": "选择和移动物品"},
                {"id": "hand", "name": "手", "icon": "✋", "tooltip": "拖拽和交互"},
            ],
        )

        self._add_tool_section(
            tools_layout,
            "测量工具",
            [
                {"id": "ruler", "name": "尺子", "icon": "📏", "tooltip": "测量长度"},
                {"id": "thermometer", "name": "温度计", "icon": "🌡️", "tooltip": "测量温度"},
                {"id": "ph_meter", "name": "pH计", "icon": "📊", "tooltip": "测量pH值"},
            ],
        )

        self._add_tool_section(
            tools_layout,
            "操作工具",
            [
                {"id": "dropper", "name": "滴管", "icon": "💧", "tooltip": "精确滴加液体"},
                {"id": "stirrer", "name": "搅拌棒", "icon": "🔄", "tooltip": "搅拌溶液"},
                {"id": "clamp", "name": "铁夹", "icon": "🔧", "tooltip": "固定器材"},
            ],
        )

        tools_layout.addStretch()
        main_layout.addLayout(tools_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #dee2e6; margin: 10px 0;")
        main_layout.addWidget(line)

        # 快捷操作
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        actions_label = QLabel("快捷操作")
        actions_label.setStyleSheet(
            """
            QLabel {
                font-size: 11pt;
                font-weight: bold;
                color: #495057;
                padding: 5px;
            }
        """
        )
        actions_layout.addWidget(actions_label)

        # 操作按钮
        action_buttons = [
            {"id": "reset_view", "name": "重置视图", "icon": "🔄"},
            {"id": "clear_all", "name": "清空场景", "icon": "🗑️"},
            {"id": "save_state", "name": "保存状态", "icon": "💾"},
            {"id": "load_state", "name": "加载状态", "icon": "📂"},
            {"id": "take_screenshot", "name": "截图", "icon": "📷"},
        ]

        for btn_data in action_buttons:
            btn = self._create_action_button(btn_data["id"], btn_data["name"], btn_data["icon"])
            actions_layout.addWidget(btn)

        main_layout.addLayout(actions_layout)

    def _add_tool_section(self, parent_layout: QVBoxLayout, section_name: str, tools: list[dict[str, str]]) -> None:
        """添加工具部分"""
        # 部分标题
        section_label = QLabel(section_name)
        section_label.setStyleSheet(
            """
            QLabel {
                font-size: 10pt;
                font-weight: bold;
                color: #6c757d;
                padding: 3px 5px;
                background-color: #e9ecef;
                border-radius: 4px;
            }
        """
        )
        parent_layout.addWidget(section_label)

        # 工具按钮
        for tool_data in tools:
            btn = self._create_tool_button(
                tool_data["id"], tool_data["name"], tool_data["icon"], tool_data.get("tooltip", "")
            )
            parent_layout.addWidget(btn)
            self.tools[tool_data["id"]] = btn

    def _create_tool_button(self, tool_id: str, name: str, icon: str, tooltip: str) -> QToolButton:
        """创建工具按钮"""
        btn = QToolButton()
        btn.setText(f"{icon}  {name}")
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setStyleSheet(
            """
            QToolButton {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-size: 10pt;
                color: #495057;
            }
            QToolButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QToolButton:checked {
                background-color: #0078d4;
                border-color: #0078d4;
                color: white;
                font-weight: bold;
            }
        """
        )

        btn.clicked.connect(lambda: self._on_tool_selected(tool_id))
        self.tool_group.addButton(btn)

        return btn

    def _create_action_button(self, action_id: str, name: str, icon: str) -> QPushButton:
        """创建操作按钮"""
        btn = QPushButton(f"{icon}  {name}")
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-size: 10pt;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """
        )

        btn.clicked.connect(lambda: self._on_action_triggered(action_id))

        return btn

    def _on_tool_selected(self, tool_id: str) -> None:
        """工具被选择"""
        self.current_tool = tool_id
        self.tool_selected.emit(tool_id)
        logger.info(f"选择工具: {tool_id}")

    def _on_action_triggered(self, action_id: str) -> None:
        """触发操作"""
        self.action_triggered.emit(action_id)
        logger.info(f"触发操作: {action_id}")

    def get_current_tool(self) -> str | None:
        """获取当前选中的工具"""
        return self.current_tool

    def set_tool(self, tool_id: str) -> None:
        """设置当前工具"""
        if tool_id in self.tools:
            self.tools[tool_id].setChecked(True)
            self.current_tool = tool_id


class CompactToolbar(QFrame):
    """紧凑型工具栏（适合水平布局）"""

    tool_selected = Signal(str)
    action_triggered = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tools: dict[str, QWidget] = {}

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 8px;
            }
        """
        )

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 8, 10, 8)

        # 工具按钮组
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        # 常用工具
        tools = [
            {"id": "select", "icon": "➤", "tooltip": "选择"},
            {"id": "hand", "icon": "✋", "tooltip": "拖拽"},
            {"id": "dropper", "icon": "💧", "tooltip": "滴管"},
            {"id": "thermometer", "icon": "🌡️", "tooltip": "温度计"},
            {"id": "ph_meter", "icon": "📊", "tooltip": "pH计"},
        ]

        for tool_data in tools:
            btn = self._create_compact_button(tool_data["id"], tool_data["icon"], tool_data["tooltip"])
            main_layout.addWidget(btn)
            self.tools[tool_data["id"]] = btn

        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("background-color: #dee2e6;")
        main_layout.addWidget(separator)

        # 快捷操作
        actions = [
            {"id": "reset_view", "icon": "🔄", "tooltip": "重置视图"},
            {"id": "save_state", "icon": "💾", "tooltip": "保存"},
            {"id": "take_screenshot", "icon": "📷", "tooltip": "截图"},
        ]

        for action_data in actions:
            btn = self._create_compact_action_button(action_data["id"], action_data["icon"], action_data["tooltip"])
            main_layout.addWidget(btn)

        main_layout.addStretch()

    def _create_compact_button(self, tool_id: str, icon: str, tooltip: str) -> QToolButton:
        """创建紧凑工具按钮"""
        btn = QToolButton()
        btn.setText(icon)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(40, 40)
        btn.setStyleSheet(
            """
            QToolButton {
                background-color: transparent;
                border: 2px solid transparent;
                border-radius: 6px;
                font-size: 16pt;
            }
            QToolButton:hover {
                background-color: #f8f9fa;
                border-color: #dee2e6;
            }
            QToolButton:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
        """
        )

        btn.clicked.connect(lambda: self.tool_selected.emit(tool_id))
        self.tool_group.addButton(btn)

        return btn

    def _create_compact_action_button(self, action_id: str, icon: str, tooltip: str) -> QPushButton:
        """创建紧凑操作按钮"""
        btn = QPushButton(icon)
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 2px solid transparent;
                border-radius: 6px;
                font-size: 16pt;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #dee2e6;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """
        )

        btn.clicked.connect(lambda: self.action_triggered.emit(action_id))

        return btn


class FloatingToolPalette(QFrame):
    """浮动工具面板（可拖动）"""

    tool_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._dragging = False
        self._drag_position = None

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255, 255, 255, 240);
                border: 2px solid #0078d4;
                border-radius: 12px;
            }
        """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 标题栏（可拖动）
        title_bar = QFrame()
        title_bar.setStyleSheet(
            """
            QFrame {
                background-color: #0078d4;
                border-radius: 8px;
                padding: 5px;
            }
        """
        )
        title_bar.setCursor(Qt.CursorShape.SizeAllCursor)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)

        title_label = QLabel("🧪 工具")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 10pt;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16pt;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
                border-radius: 10px;
            }
        """
        )
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)

        main_layout.addWidget(title_bar)

        # 工具按钮网格
        tools = [
            {"id": "select", "icon": "➤"},
            {"id": "hand", "icon": "✋"},
            {"id": "dropper", "icon": "💧"},
            {"id": "thermometer", "icon": "🌡️"},
            {"id": "ph_meter", "icon": "📊"},
            {"id": "stirrer", "icon": "🔄"},
        ]

        from PySide6.QtWidgets import QGridLayout

        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)

        for i, tool_data in enumerate(tools):
            btn = QPushButton(tool_data["icon"])
            btn.setFixedSize(45, 45)
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: white;
                    border: 2px solid #dee2e6;
                    border-radius: 8px;
                    font-size: 18pt;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                    border-color: #0078d4;
                }
                QPushButton:pressed {
                    background-color: #0078d4;
                    color: white;
                }
            """
            )
            btn.clicked.connect(lambda checked, tid=tool_data["id"]: self.tool_selected.emit(tid))

            row = i // 2
            col = i % 2
            grid_layout.addWidget(btn, row, col)

        main_layout.addLayout(grid_layout)

    def mousePressEvent(self, event: Qt.MouseButton) -> None:
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: Qt.MouseMoveEvent) -> None:
        """鼠标移动"""
        if self._dragging and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: Qt.MouseReleaseEvent) -> None:
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
