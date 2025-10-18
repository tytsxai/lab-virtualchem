"""
快速访问和搜索功能
提供命令面板、最近使用、收藏夹等功能
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ActionType(Enum):
    """动作类型"""

    EXPERIMENT = "experiment"  # 实验
    COMMAND = "command"  # 命令
    FILE = "file"  # 文件
    SETTING = "setting"  # 设置
    HELP = "help"  # 帮助


@dataclass
class QuickAction:
    """快速动作"""

    id: str
    title: str
    description: str
    type: ActionType
    icon: str
    callback: Callable | None = None
    keywords: list[str] | None = None
    shortcut: str | None = None
    last_used: datetime | None = None
    use_count: int = 0


class CommandPalette(QDialog):
    """命令面板"""

    action_selected = Signal(str)  # 动作ID

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.actions: dict[str, QuickAction] = {}
        self.filtered_actions: list[QuickAction] = []

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self.init_ui()
        self.load_default_actions()

        logger.info("命令面板已创建")

    def init_ui(self):
        """初始化UI"""
        self.setMinimumSize(600, 400)
        self.setMaximumSize(800, 600)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主容器
        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: white;
                border-radius: 12px;
            }
        """
        )

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(15)

        # 标题
        title = QLabel("⚡ 快速访问")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        container_layout.addWidget(title)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索实验、命令或帮助...")
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f5f5f5;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: white;
            }
        """
        )
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.on_enter_pressed)
        container_layout.addWidget(self.search_input)

        # 结果列表
        self.results_list = QListWidget()
        self.results_list.setStyleSheet(
            """
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """
        )
        self.results_list.itemDoubleClicked.connect(self.on_item_activated)
        container_layout.addWidget(self.results_list)

        # 提示信息
        hint_layout = QHBoxLayout()

        hints = [
            ("↵", "选择"),
            ("↑↓", "导航"),
            ("Esc", "关闭"),
        ]

        for key, desc in hints:
            hint_widget = self.create_hint_widget(key, desc)
            hint_layout.addWidget(hint_widget)

        hint_layout.addStretch()
        container_layout.addLayout(hint_layout)

        layout.addWidget(container)

        # 阴影效果
        container.setGraphicsEffect(self.create_shadow_effect())

    def create_hint_widget(self, key: str, description: str) -> QWidget:
        """创建提示控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(5)

        # 按键
        key_label = QLabel(key)
        key_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-family: monospace;
            }
        """
        )
        layout.addWidget(key_label)

        # 描述
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(desc_label)

        return widget

    def create_shadow_effect(self):
        """创建阴影效果"""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 4)
        return shadow

    def load_default_actions(self):
        """加载默认动作"""
        # 实验相关
        self.add_action(
            QuickAction(
                id="exp_new",
                title="新建实验",
                description="创建一个新的实验",
                type=ActionType.EXPERIMENT,
                icon="🧪",
                keywords=["new", "create", "实验", "新建"],
                shortcut="Ctrl+N",
            )
        )

        self.add_action(
            QuickAction(
                id="exp_open",
                title="打开实验记录",
                description="查看历史实验记录",
                type=ActionType.EXPERIMENT,
                icon="📂",
                keywords=["open", "history", "记录", "打开"],
                shortcut="Ctrl+O",
            )
        )

        self.add_action(
            QuickAction(
                id="exp_save",
                title="保存实验进度",
                description="保存当前实验的进度",
                type=ActionType.EXPERIMENT,
                icon="💾",
                keywords=["save", "保存", "进度"],
                shortcut="Ctrl+S",
            )
        )

        # 命令相关
        self.add_action(
            QuickAction(
                id="cmd_settings",
                title="打开设置",
                description="配置应用程序设置",
                type=ActionType.COMMAND,
                icon="⚙️",
                keywords=["settings", "preferences", "设置", "配置"],
                shortcut="Ctrl+,",
            )
        )

        self.add_action(
            QuickAction(
                id="cmd_theme",
                title="切换主题",
                description="在深色和浅色主题之间切换",
                type=ActionType.COMMAND,
                icon="🎨",
                keywords=["theme", "dark", "light", "主题", "暗色", "亮色"],
                shortcut="Ctrl+T",
            )
        )

        self.add_action(
            QuickAction(
                id="cmd_performance",
                title="性能监控",
                description="查看应用性能统计",
                type=ActionType.COMMAND,
                icon="📊",
                keywords=["performance", "monitor", "性能", "监控"],
                shortcut="Ctrl+Shift+P",
            )
        )

        # 帮助相关
        self.add_action(
            QuickAction(
                id="help_docs",
                title="帮助文档",
                description="查看用户手册和帮助文档",
                type=ActionType.HELP,
                icon="📚",
                keywords=["help", "docs", "manual", "帮助", "文档"],
                shortcut="F1",
            )
        )

        self.add_action(
            QuickAction(
                id="help_tutorial",
                title="交互式教程",
                description="学习如何使用VirtualChemLab",
                type=ActionType.HELP,
                icon="🎓",
                keywords=["tutorial", "guide", "教程", "引导"],
            )
        )

        self.add_action(
            QuickAction(
                id="help_shortcuts",
                title="快捷键列表",
                description="查看所有可用的快捷键",
                type=ActionType.HELP,
                icon="⌨️",
                keywords=["shortcuts", "keyboard", "快捷键", "键盘"],
                shortcut="Ctrl+Shift+K",
            )
        )

        # 初始显示所有动作
        self.update_results()

    def add_action(self, action: QuickAction):
        """添加动作"""
        self.actions[action.id] = action

    def remove_action(self, action_id: str):
        """移除动作"""
        if action_id in self.actions:
            del self.actions[action_id]

    def on_search_changed(self, text: str):
        """搜索文本改变"""
        self.filter_actions(text)
        self.update_results()

    def filter_actions(self, query: str):
        """过滤动作"""
        query = query.lower().strip()

        if not query:
            # 显示最近使用的动作
            self.filtered_actions = sorted(
                self.actions.values(), key=lambda a: (a.use_count, a.last_used or datetime.min), reverse=True
            )
        else:
            # 搜索匹配
            matches = []
            for action in self.actions.values():
                score = self.calculate_match_score(action, query)
                if score > 0:
                    matches.append((score, action))

            # 按分数排序
            matches.sort(key=lambda x: x[0], reverse=True)
            self.filtered_actions = [action for _, action in matches]

    def calculate_match_score(self, action: QuickAction, query: str) -> int:
        """计算匹配分数"""
        score = 0
        query = query.lower()

        # 标题匹配
        if query in action.title.lower():
            score += 100
            if action.title.lower().startswith(query):
                score += 50

        # 描述匹配
        if query in action.description.lower():
            score += 50

        # 关键词匹配
        if action.keywords:
            for keyword in action.keywords:
                if query in keyword.lower():
                    score += 30
                    if keyword.lower().startswith(query):
                        score += 20

        # 使用频率加成
        score += action.use_count

        return score

    def update_results(self):
        """更新结果列表"""
        self.results_list.clear()

        for action in self.filtered_actions[:20]:  # 最多显示20个结果
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, action.id)

            # 创建项目控件
            widget = self.create_action_widget(action)
            item.setSizeHint(widget.sizeHint())

            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

        # 选择第一项
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def create_action_widget(self, action: QuickAction) -> QWidget:
        """创建动作控件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # 图标
        icon_label = QLabel(action.icon)
        icon_label.setStyleSheet("font-size: 20px;")
        icon_label.setFixedWidth(30)
        layout.addWidget(icon_label)

        # 文本
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # 标题
        title = QLabel(action.title)
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        text_layout.addWidget(title)

        # 描述
        desc = QLabel(action.description)
        desc.setStyleSheet("color: #666; font-size: 10px;")
        text_layout.addWidget(desc)

        layout.addLayout(text_layout)
        layout.addStretch()

        # 快捷键
        if action.shortcut:
            shortcut_label = QLabel(action.shortcut)
            shortcut_label.setStyleSheet(
                """
                QLabel {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 10px;
                    font-family: monospace;
                }
            """
            )
            layout.addWidget(shortcut_label)

        return widget

    def on_item_activated(self, item: QListWidgetItem):
        """项目被激活"""
        action_id = item.data(Qt.ItemDataRole.UserRole)
        self.execute_action(action_id)

    def on_enter_pressed(self):
        """回车键按下"""
        current_item = self.results_list.currentItem()
        if current_item:
            self.on_item_activated(current_item)

    def execute_action(self, action_id: str):
        """执行动作"""
        if action_id not in self.actions:
            return

        action = self.actions[action_id]

        # 更新使用统计
        action.use_count += 1
        action.last_used = datetime.now()

        # 发送信号
        self.action_selected.emit(action_id)

        # 执行回调
        if action.callback:
            try:
                action.callback()
            except Exception as e:
                logger.error(f"执行动作失败 {action_id}: {e}")

        # 关闭面板
        self.close_palette()

        logger.info(f"执行动作: {action.title}")

    def keyPressEvent(self, event: QKeyEvent):
        """按键事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.close_palette()
        elif event.key() == Qt.Key.Key_Down:
            # 下一项
            current_row = self.results_list.currentRow()
            if current_row < self.results_list.count() - 1:
                self.results_list.setCurrentRow(current_row + 1)
        elif event.key() == Qt.Key.Key_Up:
            # 上一项
            current_row = self.results_list.currentRow()
            if current_row > 0:
                self.results_list.setCurrentRow(current_row - 1)
        else:
            super().keyPressEvent(event)

    def show_palette(self):
        """显示命令面板"""
        # 居中显示
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() // 4
            self.move(x, y)

        self.show()
        self.search_input.setFocus()
        self.search_input.clear()

        # 淡入动画
        self.setWindowOpacity(0)

        opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        opacity_anim.setDuration(200)
        opacity_anim.setStartValue(0)
        opacity_anim.setEndValue(1)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        opacity_anim.start()

        logger.info("命令面板已显示")

    def close_palette(self):
        """关闭命令面板"""
        # 淡出动画
        opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        opacity_anim.setDuration(150)
        opacity_anim.setStartValue(1)
        opacity_anim.setEndValue(0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        opacity_anim.finished.connect(self.close)
        opacity_anim.start()

        logger.info("命令面板已关闭")


class RecentItemsManager:
    """最近使用项管理器"""

    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.items: list[dict[str, Any]] = []
        self.save_file = Path("data/recent_items.json")
        self.load_items()

        logger.info(f"最近使用项管理器初始化完成 (最多{max_items}项)")

    def add_item(self, item: dict[str, Any]):
        """添加项目"""
        # 移除已存在的相同项
        self.items = [i for i in self.items if i.get("id") != item.get("id")]

        # 添加到开头
        item["timestamp"] = datetime.now().isoformat()
        self.items.insert(0, item)

        # 限制数量
        self.items = self.items[: self.max_items]

        # 保存
        self.save_items()

    def get_items(self) -> list[dict[str, Any]]:
        """获取项目列表"""
        return self.items.copy()

    def clear_items(self):
        """清除所有项目"""
        self.items.clear()
        self.save_items()

    def load_items(self):
        """加载项目"""
        try:
            if self.save_file.exists():
                import json

                with open(self.save_file, encoding="utf-8") as f:
                    self.items = json.load(f)
                logger.info(f"加载了 {len(self.items)} 个最近使用项")
        except Exception as e:
            logger.error(f"加载最近使用项失败: {e}")
            self.items = []

    def save_items(self):
        """保存项目"""
        try:
            self.save_file.parent.mkdir(parents=True, exist_ok=True)
            import json

            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存最近使用项失败: {e}")
