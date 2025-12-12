"""
智能引导系统
提供实时操作提示、上下文感知帮助和自适应学习引导
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class GuideType(Enum):
    """引导类型"""

    TOOLTIP = "tooltip"  # 工具提示
    HINT = "hint"  # 提示
    TUTORIAL = "tutorial"  # 教程
    WARNING = "warning"  # 警告
    SUCCESS = "success"  # 成功提示
    ERROR = "error"  # 错误提示
    INFO = "info"  # 信息


class GuidePriority(Enum):
    """引导优先级"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class GuideContext:
    """引导上下文"""

    experiment_id: str
    step_index: int
    step_type: str
    user_level: str = "beginner"  # beginner, intermediate, advanced
    user_mistakes: int = 0
    time_spent: float = 0.0
    current_action: str = ""
    previous_actions: list[str] = field(default_factory=list)
    user_preferences: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuideMessage:
    """引导消息"""

    id: str
    guide_type: GuideType
    priority: GuidePriority
    title: str
    content: str
    target_widget: QWidget | None = None
    target_position: QPoint | None = None
    duration: int = 5000  # 毫秒
    show_arrow: bool = True
    actions: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class GuideOverlay(QWidget):
    """引导浮层组件"""

    # 信号
    action_clicked = Signal(str)  # 动作ID
    closed = Signal()

    def __init__(self, message: GuideMessage, parent: QWidget | None = None):
        super().__init__(parent)
        self.message = message

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()
        self._apply_style()

        # 自动隐藏计时器
        if message.duration > 0:
            QTimer.singleShot(message.duration, self.close)

    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(self.message.title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 内容
        content_label = QLabel(self.message.content)
        content_label.setWordWrap(True)
        content_label.setFont(QFont("Arial", 10))
        layout.addWidget(content_label)

        # 动作按钮
        if self.message.actions:
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(5)

            for action in self.message.actions:
                btn = QPushButton(action.get("label", "确定"))
                btn.clicked.connect(lambda _checked=False, aid=action.get("id", ""): self._on_action(aid))
                actions_layout.addWidget(btn)

            layout.addLayout(actions_layout)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 2)
        shadow.setColor(Qt.GlobalColor.black)
        self.setGraphicsEffect(shadow)

    def _apply_style(self) -> None:
        """应用样式"""
        color_map = {
            GuideType.TOOLTIP: "#2c3e50",
            GuideType.HINT: "#3498db",
            GuideType.TUTORIAL: "#9b59b6",
            GuideType.WARNING: "#f39c12",
            GuideType.SUCCESS: "#27ae60",
            GuideType.ERROR: "#e74c3c",
            GuideType.INFO: "#34495e",
        }

        bg_color = color_map.get(self.message.guide_type, "#2c3e50")

        self.setStyleSheet(
            f"""
            GuideOverlay {{
                background-color: {bg_color};
                border-radius: 8px;
                color: white;
            }}
            QLabel {{
                color: white;
                background: transparent;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 4px;
                color: white;
                padding: 5px 15px;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """
        )

    def _on_action(self, action_id: str) -> None:
        """处理动作点击"""
        self.action_clicked.emit(action_id)
        self.close()

    def closeEvent(self, event: Any) -> None:
        """关闭事件"""
        self.closed.emit()
        super().closeEvent(event)


class SmartGuideSystem(QObject):
    """智能引导系统"""

    # 信号
    guide_shown = Signal(str)  # 引导ID
    guide_dismissed = Signal(str)
    guide_action_taken = Signal(str, str)  # 引导ID, 动作ID

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.context = GuideContext(experiment_id="", step_index=0, step_type="")

        # 引导规则库
        self.guide_rules: dict[str, dict[str, Any]] = {}

        # 显示的引导
        self.active_guides: dict[str, GuideOverlay] = {}

        # 已显示的引导记录
        self.shown_guides: set[str] = set()

        # 用户交互历史
        self.interaction_history: list[dict[str, Any]] = []

        # 加载默认规则
        self._load_default_rules()

        logger.info("智能引导系统初始化完成")

    def _load_default_rules(self) -> None:
        """加载默认引导规则"""
        # 新手引导
        self.add_rule(
            rule_id="beginner_welcome",
            conditions={
                "user_level": "beginner",
                "step_index": 0,
            },
            guide=GuideMessage(
                id="beginner_welcome",
                guide_type=GuideType.TUTORIAL,
                priority=GuidePriority.HIGH,
                title="欢迎使用虚拟化学实验室",
                content="这是您的第一个实验。我们将引导您完成每个步骤。点击'开始'继续。",
                actions=[{"id": "start", "label": "开始"}, {"id": "skip", "label": "跳过引导"}],
            ),
        )

        # 错误过多提示
        self.add_rule(
            rule_id="too_many_mistakes",
            conditions={
                "user_mistakes": lambda x: x >= 3,
            },
            guide=GuideMessage(
                id="too_many_mistakes",
                guide_type=GuideType.HINT,
                priority=GuidePriority.NORMAL,
                title="需要帮助吗？",
                content="看起来您遇到了一些困难。要查看详细提示吗？",
                actions=[{"id": "show_hint", "label": "查看提示"}, {"id": "continue", "label": "继续尝试"}],
            ),
        )

        # 操作超时提示
        self.add_rule(
            rule_id="operation_timeout",
            conditions={
                "time_spent": lambda x: x > 120,  # 2分钟
            },
            guide=GuideMessage(
                id="operation_timeout",
                guide_type=GuideType.INFO,
                priority=GuidePriority.NORMAL,
                title="提示",
                content="如果您不确定如何操作，可以点击帮助按钮查看详细说明。",
                duration=8000,
            ),
        )

        # 步骤类型特定引导
        step_guides = {
            "confirm": {
                "id": "confirm_guide",
                "title": "确认步骤",
                "content": "请仔细阅读安全注意事项，然后勾选确认框。",
            },
            "input": {
                "id": "input_guide",
                "title": "数值输入",
                "content": "请输入准确的数值。系统会检查您的输入是否在允许范围内。",
            },
            "select": {
                "id": "select_guide",
                "title": "选择步骤",
                "content": "从下拉列表中选择正确的选项。如果不确定，可以查看知识库。",
            },
            "sequence": {
                "id": "sequence_guide",
                "title": "排序步骤",
                "content": "拖动项目以调整顺序。正确的顺序对实验成功很重要。",
            },
        }

        for step_type, guide_data in step_guides.items():
            self.add_rule(
                rule_id=f"step_{step_type}",
                conditions={
                    "step_type": step_type,
                    "user_level": "beginner",
                },
                guide=GuideMessage(
                    id=guide_data["id"],
                    guide_type=GuideType.HINT,
                    priority=GuidePriority.NORMAL,
                    title=guide_data["title"],
                    content=guide_data["content"],
                    duration=6000,
                ),
            )

    def add_rule(self, rule_id: str, conditions: dict[str, Any], guide: GuideMessage) -> None:
        """添加引导规则"""
        self.guide_rules[rule_id] = {"conditions": conditions, "guide": guide}
        logger.debug(f"添加引导规则: {rule_id}")

    def update_context(self, **kwargs: Any) -> None:
        """更新引导上下文"""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

        # 检查并显示符合条件的引导
        self._check_and_show_guides()

    def _check_and_show_guides(self) -> None:
        """检查并显示符合条件的引导"""
        for _rule_id, rule in self.guide_rules.items():
            # 已显示过的引导不再显示（除非是高优先级）
            guide = rule["guide"]
            if guide.id in self.shown_guides and guide.priority != GuidePriority.CRITICAL:
                continue

            # 检查条件
            if self._check_conditions(rule["conditions"]):
                self.show_guide(guide)

    def _check_conditions(self, conditions: dict[str, Any]) -> bool:
        """检查条件是否满足"""
        for key, expected in conditions.items():
            if not hasattr(self.context, key):
                continue

            actual = getattr(self.context, key)

            # 如果期望值是函数，调用它
            if callable(expected):
                if not expected(actual):
                    return False
            # 否则直接比较
            elif actual != expected:
                return False

        return True

    def show_guide(self, guide: GuideMessage, parent_widget: QWidget | None = None) -> None:
        """显示引导"""
        # 如果已经显示，先关闭
        if guide.id in self.active_guides:
            self.active_guides[guide.id].close()

        # 确定父窗口
        if parent_widget is None:
            parent_widget = QApplication.activeWindow()

        if parent_widget is None:
            logger.warning("无法显示引导：没有活动窗口")
            return

        # 创建引导浮层
        overlay = GuideOverlay(guide, parent_widget)

        # 确定位置
        if guide.target_position:
            overlay.move(guide.target_position)
        elif guide.target_widget:
            # 定位到目标组件附近
            target_rect = guide.target_widget.geometry()
            pos = parent_widget.mapToGlobal(QPoint(target_rect.x(), target_rect.y() + target_rect.height() + 5))
            overlay.move(pos)
        else:
            # 默认居中显示
            overlay.move(parent_widget.x() + (parent_widget.width() - overlay.width()) // 2, parent_widget.y() + 100)

        # 连接信号
        overlay.action_clicked.connect(lambda aid: self._on_guide_action(guide.id, aid))
        overlay.closed.connect(lambda: self._on_guide_closed(guide.id))

        # 显示
        overlay.show()
        self.active_guides[guide.id] = overlay
        self.shown_guides.add(guide.id)

        # 发送信号
        self.guide_shown.emit(guide.id)

        logger.info(f"显示引导: {guide.id} - {guide.title}")

    def _on_guide_action(self, guide_id: str, action_id: str) -> None:
        """处理引导动作"""
        self.guide_action_taken.emit(guide_id, action_id)

        # 记录到历史
        self.interaction_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "guide_id": guide_id,
                "action_id": action_id,
                "context": self.context.__dict__.copy(),
            }
        )

        logger.info(f"引导动作: {guide_id} -> {action_id}")

    def _on_guide_closed(self, guide_id: str) -> None:
        """处理引导关闭"""
        if guide_id in self.active_guides:
            del self.active_guides[guide_id]

        self.guide_dismissed.emit(guide_id)
        logger.debug(f"引导已关闭: {guide_id}")

    def dismiss_guide(self, guide_id: str) -> None:
        """关闭指定引导"""
        if guide_id in self.active_guides:
            self.active_guides[guide_id].close()

    def dismiss_all_guides(self) -> None:
        """关闭所有引导"""
        for guide_id in list(self.active_guides.keys()):
            self.active_guides[guide_id].close()

    def record_user_action(self, action: str) -> None:
        """记录用户操作"""
        self.context.current_action = action
        self.context.previous_actions.append(action)

        # 限制历史记录长度
        if len(self.context.previous_actions) > 20:
            self.context.previous_actions = self.context.previous_actions[-20:]

    def show_context_help(self, context_key: str, target_widget: QWidget | None = None) -> None:
        """显示上下文帮助"""
        help_messages = {
            "equipment_selection": GuideMessage(
                id="help_equipment",
                guide_type=GuideType.INFO,
                priority=GuidePriority.NORMAL,
                title="器材选择",
                content="从器材库中选择实验所需的器材。可以使用搜索功能快速定位。",
                target_widget=target_widget,
            ),
            "drag_drop": GuideMessage(
                id="help_drag_drop",
                guide_type=GuideType.INFO,
                priority=GuidePriority.NORMAL,
                title="拖放操作",
                content="点击并拖动器材到工作台。将器材放到正确的位置以继续实验。",
                target_widget=target_widget,
            ),
            "measurement": GuideMessage(
                id="help_measurement",
                guide_type=GuideType.INFO,
                priority=GuidePriority.NORMAL,
                title="数据测量",
                content="点击测量工具进行数据读取。确保读数准确，这会影响实验结果。",
                target_widget=target_widget,
            ),
        }

        if context_key in help_messages:
            self.show_guide(help_messages[context_key])

    def get_suggestion(self, _current_state: dict[str, Any]) -> str | None:
        """根据当前状态获取建议"""
        # 基于用户历史和当前状态提供智能建议
        if self.context.user_mistakes > 2:
            return "建议查看实验步骤详解或观看演示视频"

        if self.context.time_spent > 180:  # 3分钟
            return "操作时间较长，如需帮助请点击帮助按钮"

        # 根据用户水平提供不同建议
        if self.context.user_level == "beginner":
            if self.context.step_type == "input":
                return "提示：输入数值时要注意单位和精度"

        return None

    def save_interaction_history(self, filepath: str) -> None:
        """保存交互历史"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.interaction_history, f, indent=2, ensure_ascii=False)
        logger.info(f"交互历史已保存到: {filepath}")

    def analyze_user_behavior(self) -> dict[str, Any]:
        """分析用户行为"""
        total_actions = len(self.interaction_history)

        if total_actions == 0:
            return {"total_actions": 0}

        # 统计动作类型
        action_types: dict[str, int] = {}
        for record in self.interaction_history:
            action_id = record.get("action_id", "unknown")
            action_types[action_id] = action_types.get(action_id, 0) + 1

        # 计算平均响应时间
        response_times = []
        for i in range(1, len(self.interaction_history)):
            prev_time = datetime.fromisoformat(self.interaction_history[i - 1]["timestamp"])
            curr_time = datetime.fromisoformat(self.interaction_history[i]["timestamp"])
            response_times.append((curr_time - prev_time).total_seconds())

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_actions": total_actions,
            "action_types": action_types,
            "avg_response_time": avg_response_time,
            "mistakes": self.context.user_mistakes,
            "user_level": self.context.user_level,
        }
