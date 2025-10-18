"""
上下文感知的智能帮助系统
根据用户当前操作提供相关的帮助和提示
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class HelpLevel(Enum):
    """帮助级别"""

    BEGINNER = "beginner"  # 初学者
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级


class HelpTrigger(Enum):
    """帮助触发方式"""

    HOVER = "hover"  # 悬停
    CLICK = "click"  # 点击
    FOCUS = "focus"  # 获得焦点
    ERROR = "error"  # 错误发生
    IDLE = "idle"  # 空闲状态


@dataclass
class HelpTopic:
    """帮助主题"""

    id: str
    title: str
    content: str
    level: HelpLevel
    keywords: list[str]
    related_topics: list[str] | None = None
    examples: list[str] | None = None
    tips: list[str] | None = None


class ContextHelpTooltip(QWidget):
    """上下文帮助提示框"""

    closed = Signal()
    topic_clicked = Signal(str)

    def __init__(self, help_topic: HelpTopic, parent: QWidget | None = None):
        super().__init__(parent)
        self.help_topic = help_topic

        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMaximumWidth(400)

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 主容器
        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: rgba(50, 50, 50, 240);
                border-radius: 10px;
            }
        """
        )

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)

        # 标题
        title = QLabel(f"💡 {self.help_topic.title}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        title.setWordWrap(True)
        container_layout.addWidget(title)

        # 内容
        content = QLabel(self.help_topic.content)
        content.setStyleSheet("color: #ddd; line-height: 1.5;")
        content.setWordWrap(True)
        container_layout.addWidget(content)

        # 示例
        if self.help_topic.examples:
            examples_label = QLabel("📝 示例：")
            examples_label.setStyleSheet("color: #88c0d0; font-weight: bold; margin-top: 5px;")
            container_layout.addWidget(examples_label)

            for example in self.help_topic.examples[:2]:  # 最多显示2个示例
                example_label = QLabel(f"• {example}")
                example_label.setStyleSheet("color: #d8dee9; padding-left: 10px;")
                example_label.setWordWrap(True)
                container_layout.addWidget(example_label)

        # 提示
        if self.help_topic.tips:
            tips_label = QLabel("💡 提示：")
            tips_label.setStyleSheet("color: #ebcb8b; font-weight: bold; margin-top: 5px;")
            container_layout.addWidget(tips_label)

            for tip in self.help_topic.tips[:2]:  # 最多显示2个提示
                tip_label = QLabel(f"• {tip}")
                tip_label.setStyleSheet("color: #d8dee9; padding-left: 10px;")
                tip_label.setWordWrap(True)
                container_layout.addWidget(tip_label)

        # 查看更多按钮
        more_btn = QPushButton("查看详细帮助 →")
        more_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(74, 144, 226, 180);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(74, 144, 226, 220);
            }
        """
        )
        more_btn.clicked.connect(lambda: self.topic_clicked.emit(self.help_topic.id))
        more_btn.clicked.connect(self.close)
        container_layout.addWidget(more_btn)

        layout.addWidget(container)

    def show_at_cursor(self):
        """在光标位置显示"""
        cursor_pos = QCursor.pos()
        self.move(cursor_pos.x() + 15, cursor_pos.y() + 15)
        self.show()

    def show_at_widget(self, widget: QWidget):
        """在控件附近显示"""
        global_pos = widget.mapToGlobal(QPoint(0, widget.height()))
        self.move(global_pos.x(), global_pos.y() + 5)
        self.show()


class InlineHelpWidget(QWidget):
    """内联帮助控件"""

    def __init__(self, message: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.message = message

        self.setFixedHeight(40)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                border-radius: 4px;
            }
        """
        )

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 8, 10, 8)

        label = QLabel(f"💡 {self.message}")
        label.setStyleSheet("color: #1565c0; font-size: 10pt;")
        label.setWordWrap(True)
        container_layout.addWidget(label)

        layout.addWidget(container)


class ContextHelpManager:
    """上下文帮助管理器"""

    _instance = None

    def __init__(self):
        self.help_topics: dict[str, HelpTopic] = {}
        self.widget_help_map: dict[QWidget, str] = {}  # 控件到帮助主题的映射
        self.current_tooltip: ContextHelpTooltip | None = None
        self.user_level = HelpLevel.BEGINNER
        self.show_tooltips = True
        self.idle_help_enabled = True
        self.idle_timer: QTimer | None = None
        self.last_activity_time = 0.0

        self.load_default_topics()

        logger.info("上下文帮助管理器初始化完成")

    @classmethod
    def instance(cls) -> ContextHelpManager:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_default_topics(self):
        """加载默认帮助主题"""
        # 实验相关
        self.add_topic(
            HelpTopic(
                id="exp_start",
                title="开始实验",
                content="选择一个实验模板，然后点击'开始实验'按钮。系统会引导你完成实验的各个步骤。",
                level=HelpLevel.BEGINNER,
                keywords=["实验", "开始", "模板", "选择"],
                examples=["从左侧列表中选择'酸碱滴定'实验", "点击'开始'按钮进入实验界面"],
                tips=["首次使用建议从简单实验开始", "实验会自动保存进度，可随时继续"],
            )
        )

        self.add_topic(
            HelpTopic(
                id="exp_steps",
                title="实验步骤",
                content="每个实验分为多个步骤。按照提示完成当前步骤后，点击'下一步'继续。",
                level=HelpLevel.BEGINNER,
                keywords=["步骤", "操作", "提示", "下一步"],
                examples=["阅读当前步骤的说明", "按照要求进行操作", "确认无误后点击'下一步'"],
                tips=["每步都有详细的操作提示", "不确定时可以查看帮助"],
            )
        )

        self.add_topic(
            HelpTopic(
                id="exp_data_entry",
                title="数据输入",
                content="在实验中需要输入观察到的数据。请注意单位和有效数字的要求。",
                level=HelpLevel.BEGINNER,
                keywords=["数据", "输入", "单位", "有效数字"],
                examples=["输入滴定体积：25.00 mL", "记录溶液颜色：无色→粉红色"],
                tips=["注意数据的有效位数", "确认单位是否正确"],
            )
        )

        # 界面相关
        self.add_topic(
            HelpTopic(
                id="ui_navigation",
                title="界面导航",
                content="使用左侧菜单切换不同功能，顶部工具栏提供快速操作。",
                level=HelpLevel.BEGINNER,
                keywords=["界面", "导航", "菜单", "工具栏"],
                examples=["点击左侧'实验'查看实验列表", "使用顶部搜索框快速查找"],
                tips=["按F1随时打开帮助", "使用Ctrl+P打开命令面板"],
            )
        )

        self.add_topic(
            HelpTopic(
                id="shortcuts",
                title="快捷键",
                content="使用快捷键可以提高操作效率。常用快捷键：F1帮助、Ctrl+S保存、Ctrl+Z撤销。",
                level=HelpLevel.INTERMEDIATE,
                keywords=["快捷键", "键盘", "效率"],
                examples=["Ctrl+N - 新建实验", "Ctrl+P - 命令面板", "F1 - 帮助文档"],
                tips=["按Ctrl+Shift+K查看所有快捷键", "可以在设置中自定义快捷键"],
            )
        )

        # 高级功能
        self.add_topic(
            HelpTopic(
                id="advanced_features",
                title="高级功能",
                content="探索游戏模式、数据分析、报告生成等高级功能。",
                level=HelpLevel.ADVANCED,
                keywords=["高级", "游戏", "分析", "报告"],
                examples=["启用游戏模式进行趣味实验", "使用数据分析工具查看趋势", "一键生成实验报告"],
                tips=["游戏模式下有成就系统", "可以导出数据进行深入分析"],
            )
        )

    def add_topic(self, topic: HelpTopic):
        """添加帮助主题"""
        self.help_topics[topic.id] = topic

    def get_topic(self, topic_id: str) -> HelpTopic | None:
        """获取帮助主题"""
        return self.help_topics.get(topic_id)

    def register_widget_help(self, widget: QWidget, topic_id: str, trigger: HelpTrigger = HelpTrigger.HOVER):
        """注册控件帮助

        Args:
            widget: 控件
            topic_id: 帮助主题ID
            trigger: 触发方式
        """
        self.widget_help_map[widget] = topic_id

        # 根据触发方式添加事件处理
        if trigger == HelpTrigger.HOVER:
            original_enter = widget.enterEvent if hasattr(widget, "enterEvent") else None

            def enter_event(event):
                if original_enter:
                    original_enter(event)
                self.show_tooltip_for_widget(widget)

            widget.enterEvent = enter_event

        elif trigger == HelpTrigger.FOCUS:
            original_focus_in = widget.focusInEvent if hasattr(widget, "focusInEvent") else None

            def focus_in_event(event):
                if original_focus_in:
                    original_focus_in(event)
                self.show_tooltip_for_widget(widget)

            widget.focusInEvent = focus_in_event

    def show_tooltip_for_widget(self, widget: QWidget):
        """为控件显示帮助提示"""
        if not self.show_tooltips:
            return

        topic_id = self.widget_help_map.get(widget)
        if not topic_id:
            return

        topic = self.get_topic(topic_id)
        if not topic:
            return

        # 关闭之前的提示
        if self.current_tooltip:
            self.current_tooltip.close()

        # 创建新提示
        self.current_tooltip = ContextHelpTooltip(topic)
        self.current_tooltip.closed.connect(self.on_tooltip_closed)
        self.current_tooltip.show_at_widget(widget)

        logger.debug(f"显示帮助提示: {topic.title}")

    def show_help_for_context(self, context: str):
        """根据上下文显示帮助"""
        # 搜索相关主题
        matching_topics = []
        context_lower = context.lower()

        for topic in self.help_topics.values():
            # 根据用户级别过滤
            if topic.level.value != self.user_level.value:
                continue

            # 关键词匹配
            score = 0
            for keyword in topic.keywords:
                if keyword in context_lower:
                    score += 1

            if score > 0:
                matching_topics.append((score, topic))

        # 按分数排序
        matching_topics.sort(key=lambda x: x[0], reverse=True)

        if matching_topics:
            # 显示最相关的主题
            topic = matching_topics[0][1]
            self.show_tooltip(topic)

    def show_tooltip(self, topic: HelpTopic):
        """显示帮助提示"""
        if not self.show_tooltips:
            return

        # 关闭之前的提示
        if self.current_tooltip:
            self.current_tooltip.close()

        # 创建新提示
        self.current_tooltip = ContextHelpTooltip(topic)
        self.current_tooltip.closed.connect(self.on_tooltip_closed)
        self.current_tooltip.show_at_cursor()

        logger.debug(f"显示帮助提示: {topic.title}")

    def hide_tooltip(self):
        """隐藏帮助提示"""
        if self.current_tooltip:
            self.current_tooltip.close()

    def on_tooltip_closed(self):
        """提示关闭处理"""
        self.current_tooltip = None

    def set_user_level(self, level: HelpLevel):
        """设置用户级别"""
        self.user_level = level
        logger.info(f"用户级别设置为: {level.value}")

    def set_show_tooltips(self, show: bool):
        """设置是否显示提示"""
        self.show_tooltips = show

    def start_idle_help(self):
        """启动空闲帮助"""
        if not self.idle_help_enabled:
            return

        if not self.idle_timer:
            self.idle_timer = QTimer()
            self.idle_timer.timeout.connect(self.check_idle_state)

        self.idle_timer.start(5000)  # 每5秒检查一次

    def stop_idle_help(self):
        """停止空闲帮助"""
        if self.idle_timer:
            self.idle_timer.stop()

    def check_idle_state(self):
        """检查空闲状态"""
        # 这里可以检测用户是否长时间没有操作
        # 并提供相关帮助建议
        import time

        current_time = time.time()

        if current_time - self.last_activity_time > 30:  # 30秒无操作
            # 显示一些有用的提示
            self.show_help_for_context("idle")

    def record_activity(self):
        """记录用户活动"""
        import time

        self.last_activity_time = time.time()


def show_inline_help(message: str, parent: QWidget) -> InlineHelpWidget:
    """显示内联帮助

    Args:
        message: 帮助消息
        parent: 父控件

    Returns:
        内联帮助控件
    """
    help_widget = InlineHelpWidget(message, parent)
    return help_widget
