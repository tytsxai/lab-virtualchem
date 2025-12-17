"""
用户引导系统
提供新手教程、操作提示和交互式引导功能
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QPropertyAnimation, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class GuideStepType(Enum):
    """引导步骤类型"""

    HIGHLIGHT = "highlight"  # 高亮元素
    TOOLTIP = "tooltip"  # 工具提示
    OVERLAY = "overlay"  # 覆盖层
    MODAL = "modal"  # 模态对话框
    ANIMATION = "animation"  # 动画演示


class GuidePosition(Enum):
    """引导位置"""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    AUTO = "auto"


@dataclass
class GuideStep:
    """引导步骤"""

    id: str
    title: str
    content: str
    target_widget: str | None = None  # 目标控件名称
    step_type: GuideStepType = GuideStepType.TOOLTIP
    position: GuidePosition = GuidePosition.AUTO
    arrow_direction: str = "auto"
    highlight_color: str = "#4a90e2"
    auto_advance: bool = False
    auto_advance_delay: int = 3000
    required_action: str | None = None  # 需要的用户操作
    skip_enabled: bool = True
    back_enabled: bool = True
    next_enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuideTour:
    """引导旅程"""

    id: str
    title: str
    description: str
    steps: list[GuideStep]
    target_audience: str = "all"  # all, beginner, advanced
    prerequisites: list[str] = field(default_factory=list)
    estimated_duration: int = 0  # 预计时长（秒）
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)


class GuideOverlay(QWidget):
    """引导覆盖层"""

    step_changed = Signal(str)  # 步骤ID
    tour_completed = Signal(str)  # 旅程ID
    tour_skipped = Signal(str)  # 旅程ID

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.current_tour: GuideTour | None = None
        self.current_step_index = 0
        self.target_widget: QWidget | None = None
        self.theme_manager = ThemeManager()

        # 覆盖层设置
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # 动画
        self.fade_animation: QPropertyAnimation | None = None
        self.pulse_animation: QPropertyAnimation | None = None

        self.init_ui()
        self.apply_theme()

        logger.info("引导覆盖层初始化完成")

    def init_ui(self):
        """初始化UI"""
        # 创建提示框
        self.tooltip_widget = QWidget()
        self.tooltip_widget.setObjectName("guideTooltip")

        layout = QVBoxLayout(self.tooltip_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        self.title_label = QLabel()
        self.title_label.setObjectName("guideTitle")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        # 内容
        self.content_label = QLabel()
        self.content_label.setObjectName("guideContent")
        self.content_label.setWordWrap(True)
        self.content_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.content_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.back_button = ModernButton("⬅️ 上一步")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_button)

        self.skip_button = ModernButton("跳过")
        self.skip_button.clicked.connect(self.skip_tour)
        button_layout.addWidget(self.skip_button)

        button_layout.addStretch()

        self.next_button = ModernButton("下一步 ➡️")
        self.next_button.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_button)

        layout.addLayout(button_layout)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.tooltip_widget.setGraphicsEffect(shadow)

        # 初始隐藏
        self.tooltip_widget.hide()

    def apply_theme(self):
        """应用主题"""
        try:
            self.setStyleSheet(
                """
                QWidget#guideTooltip {
                    background-color: rgba(26, 26, 46, 0.95);
                    border: 2px solid #4a90e2;
                    border-radius: 10px;
                    color: #ffffff;
                }
                QLabel#guideTitle {
                    color: #4a90e2;
                    font-weight: bold;
                }
                QLabel#guideContent {
                    color: #ffffff;
                    line-height: 1.4;
                }
            """
            )

            logger.debug("引导主题应用成功")

        except Exception as e:
            logger.warning(f"应用引导主题失败: {e}")

    def start_tour(self, tour: GuideTour):
        """开始引导旅程"""
        self.current_tour = tour
        self.current_step_index = 0

        logger.info(f"开始引导旅程: {tour.title}")

        # 显示覆盖层
        self.show_overlay()

        # 显示第一步
        self.show_current_step()

    def show_current_step(self):
        """显示当前步骤"""
        if not self.current_tour or not self.current_tour.steps:
            return

        if self.current_step_index >= len(self.current_tour.steps):
            self.complete_tour()
            return

        step = self.current_tour.steps[self.current_step_index]

        # 更新内容
        self.title_label.setText(step.title)
        self.content_label.setText(step.content)

        # 更新按钮状态
        self.back_button.setEnabled(step.back_enabled and self.current_step_index > 0)
        self.next_button.setEnabled(step.next_enabled)
        self.skip_button.setEnabled(step.skip_enabled)

        # 更新按钮文本
        if self.current_step_index == len(self.current_tour.steps) - 1:
            self.next_button.setText("完成")
        else:
            self.next_button.setText("下一步 ➡️")

        # 定位提示框
        self.position_tooltip(step)

        # 显示提示框
        self.tooltip_widget.show()

        # 自动前进
        if step.auto_advance:
            QTimer.singleShot(step.auto_advance_delay, self.go_next)

        # 发送信号
        self.step_changed.emit(step.id)

        logger.info(f"显示引导步骤: {step.title}")

    def position_tooltip(self, step: GuideStep):
        """定位提示框"""
        if not step.target_widget:
            # 居中显示
            self.center_tooltip()
            return

        # 查找目标控件
        target = self.find_target_widget(step.target_widget)
        if not target:
            self.center_tooltip()
            return

        self.target_widget = target

        # 获取目标控件位置
        target_rect = target.geometry()
        target_global_pos = target.mapToGlobal(target_rect.topLeft())

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # 计算提示框位置
        tooltip_size = self.tooltip_widget.sizeHint()

        if step.position == GuidePosition.AUTO:
            # 自动选择最佳位置
            position = self.calculate_best_position(
                target_global_pos, tooltip_size, screen_geometry
            )
        else:
            position = self.calculate_position(
                step.position, target_global_pos, tooltip_size, screen_geometry
            )

        # 设置位置
        self.tooltip_widget.move(position)

        # 创建高亮效果
        self.create_highlight_effect(target_rect)

    def calculate_best_position(
        self, target_pos: QPoint, tooltip_size: QSize, screen_geometry: QRect
    ) -> QPoint:
        """计算最佳位置"""
        # 尝试不同位置，选择最合适的
        positions = [
            GuidePosition.BOTTOM,
            GuidePosition.RIGHT,
            GuidePosition.TOP,
            GuidePosition.LEFT,
        ]

        for pos in positions:
            position = self.calculate_position(
                pos, target_pos, tooltip_size, screen_geometry
            )
            if self.is_position_valid(position, tooltip_size, screen_geometry):
                return position

        # 如果都不合适，居中显示
        return self.center_tooltip()

    def calculate_position(
        self,
        position: GuidePosition,
        target_pos: QPoint,
        tooltip_size: QSize,
        _screen_geometry: QRect,
    ) -> QPoint:
        """计算指定位置"""
        margin = 20

        if position == GuidePosition.BOTTOM:
            return QPoint(
                target_pos.x() - tooltip_size.width() // 2, target_pos.y() + margin
            )
        elif position == GuidePosition.TOP:
            return QPoint(
                target_pos.x() - tooltip_size.width() // 2,
                target_pos.y() - tooltip_size.height() - margin,
            )
        elif position == GuidePosition.RIGHT:
            return QPoint(
                target_pos.x() + margin, target_pos.y() - tooltip_size.height() // 2
            )
        elif position == GuidePosition.LEFT:
            return QPoint(
                target_pos.x() - tooltip_size.width() - margin,
                target_pos.y() - tooltip_size.height() // 2,
            )
        else:  # CENTER
            return self.center_tooltip()

    def center_tooltip(self) -> QPoint:
        """居中显示提示框"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        tooltip_size = self.tooltip_widget.sizeHint()

        return QPoint(
            (screen_geometry.width() - tooltip_size.width()) // 2,
            (screen_geometry.height() - tooltip_size.height()) // 2,
        )

    def is_position_valid(
        self, position: QPoint, tooltip_size: QSize, screen_geometry: QRect
    ) -> bool:
        """检查位置是否有效"""
        return (
            position.x() >= 0
            and position.y() >= 0
            and position.x() + tooltip_size.width() <= screen_geometry.width()
            and position.y() + tooltip_size.height() <= screen_geometry.height()
        )

    def create_highlight_effect(self, target_rect: QRect):
        """创建高亮效果"""
        logger.debug(f"创建高亮效果: {target_rect}")

        # 创建高亮遮罩控件
        highlight_widget = QWidget(self)
        highlight_widget.setGeometry(target_rect)
        highlight_widget.setObjectName("highlightWidget")

        # 设置高亮样式
        highlight_color = (
            self.current_tour.steps[self.current_step_index].highlight_color
            if self.current_tour
            else "#4a90e2"
        )
        highlight_widget.setStyleSheet(
            f"""
            QWidget#highlightWidget {{
                background-color: transparent;
                border: 3px solid {highlight_color};
                border-radius: 8px;
            }}
        """
        )

        # 添加脉冲动画效果
        self.pulse_animation = QPropertyAnimation(highlight_widget, b"windowOpacity")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(1.0)
        self.pulse_animation.setEndValue(0.3)
        self.pulse_animation.setLoopCount(-1)  # 无限循环

        # 创建图形效果
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(20)
        glow_effect.setColor(QColor(highlight_color))
        glow_effect.setOffset(0, 0)
        highlight_widget.setGraphicsEffect(glow_effect)

        highlight_widget.show()
        self.pulse_animation.start()

        # 保存引用以便清理
        if not hasattr(self, "highlight_widgets"):
            self.highlight_widgets = []
        self.highlight_widgets.append(highlight_widget)

    def find_target_widget(self, widget_name: str) -> QWidget | None:
        """查找目标控件"""
        if not self.parent():
            return None

        # 递归查找控件
        def find_widget_recursive(parent: QWidget, name: str) -> QWidget | None:
            if parent.objectName() == name:
                return parent

            for child in parent.findChildren(QWidget):
                if child.objectName() == name:
                    return child

            return None

        return find_widget_recursive(self.parent(), widget_name)

    def show_overlay(self):
        """显示覆盖层"""
        if not self.parent():
            return

        # 设置覆盖层大小
        parent_rect = self.parent().geometry()
        self.setGeometry(parent_rect)

        # 淡入动画
        self.fade_in()

        self.show()

    def hide_overlay(self):
        """隐藏覆盖层"""
        self.fade_out()

    def fade_in(self):
        """淡入动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def fade_out(self):
        """淡出动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()

    def go_next(self):
        """下一步"""
        if not self.current_tour:
            return

        if self.current_step_index < len(self.current_tour.steps) - 1:
            self.current_step_index += 1
            self.show_current_step()
        else:
            self.complete_tour()

    def go_back(self):
        """上一步"""
        if not self.current_tour or self.current_step_index <= 0:
            return

        self.current_step_index -= 1
        self.show_current_step()

    def skip_tour(self):
        """跳过旅程"""
        if self.current_tour:
            self.tour_skipped.emit(self.current_tour.id)
            logger.info(f"跳过引导旅程: {self.current_tour.title}")

        self.hide_overlay()

    def complete_tour(self):
        """完成旅程"""
        if self.current_tour:
            self.tour_completed.emit(self.current_tour.id)
            logger.info(f"完成引导旅程: {self.current_tour.title}")

        self.hide_overlay()

    def paintEvent(self, _event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制半透明背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # 绘制高亮区域
        if self.target_widget:
            target_rect = self.target_widget.geometry()
            target_global_pos = self.target_widget.mapToGlobal(target_rect.topLeft())
            local_pos = self.mapFromGlobal(target_global_pos)

            # 创建高亮区域
            highlight_rect = QRect(local_pos, target_rect.size())

            # 绘制高亮边框
            pen = QPen(QColor(74, 144, 226), 3)
            painter.setPen(pen)
            painter.drawRect(highlight_rect)

            # 绘制高亮背景
            painter.fillRect(highlight_rect, QColor(74, 144, 226, 30))


class UserGuidanceManager:
    """用户引导管理器"""

    def __init__(self):
        self.tours: dict[str, GuideTour] = {}
        self.overlay: GuideOverlay | None = None
        self.completed_tours: set[str] = set()
        self.user_preferences: dict[str, Any] = {}

        # 加载引导数据
        self.load_guide_tours()
        self.load_user_preferences()

        logger.info("用户引导管理器初始化完成")

    def load_guide_tours(self):
        """加载引导旅程"""
        # 内置引导旅程
        self.add_tour(self.create_getting_started_tour())
        self.add_tour(self.create_experiment_tour())
        self.add_tour(self.create_game_mode_tour())
        self.add_tour(self.create_advanced_features_tour())

        logger.info(f"加载了 {len(self.tours)} 个引导旅程")

    def create_getting_started_tour(self) -> GuideTour:
        """创建快速开始引导"""
        return GuideTour(
            id="getting_started",
            title="快速开始",
            description="了解VirtualChemLab的基本功能",
            target_audience="beginner",
            estimated_duration=120,
            steps=[
                GuideStep(
                    id="welcome",
                    title="欢迎使用VirtualChemLab",
                    content="欢迎使用VirtualChemLab！这是一个强大的虚拟化学实验室。\n\n让我们开始探索吧！",
                    step_type=GuideStepType.MODAL,
                    auto_advance=True,
                    auto_advance_delay=3000,
                ),
                GuideStep(
                    id="main_window",
                    title="主界面介绍",
                    content="这是主界面，包含实验列表、控制面板和状态栏。\n\n左侧是实验模板列表，右侧是实验控制区域。",
                    target_widget="mainWindow",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.CENTER,
                ),
                GuideStep(
                    id="experiment_list",
                    title="实验列表",
                    content="这里显示所有可用的实验模板。\n\n点击任意实验可以查看详情并开始实验。",
                    target_widget="experimentList",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.RIGHT,
                ),
                GuideStep(
                    id="start_experiment",
                    title="开始实验",
                    content="选择实验后，点击'开始实验'按钮开始您的化学之旅！\n\n建议从简单的实验开始。",
                    target_widget="startButton",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.TOP,
                ),
            ],
        )

    def create_experiment_tour(self) -> GuideTour:
        """创建实验操作引导"""
        return GuideTour(
            id="experiment_guide",
            title="实验操作指南",
            description="学习如何进行化学实验",
            target_audience="beginner",
            estimated_duration=180,
            steps=[
                GuideStep(
                    id="experiment_view",
                    title="实验界面",
                    content="这是实验界面，包含实验步骤、控制按钮和反馈区域。",
                    target_widget="experimentView",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.CENTER,
                ),
                GuideStep(
                    id="step_instructions",
                    title="实验步骤",
                    content="这里显示当前实验步骤的详细说明。\n\n请仔细阅读并按照指示操作。",
                    target_widget="stepInstructions",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.RIGHT,
                ),
                GuideStep(
                    id="input_fields",
                    title="输入区域",
                    content="在这里输入实验数据，如温度、浓度等。\n\n系统会自动验证您的输入。",
                    target_widget="inputFields",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.LEFT,
                ),
                GuideStep(
                    id="submit_button",
                    title="提交结果",
                    content="完成当前步骤后，点击'提交'按钮。\n\n系统会验证您的答案并给出反馈。",
                    target_widget="submitButton",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.TOP,
                ),
            ],
        )

    def create_game_mode_tour(self) -> GuideTour:
        """创建游戏模式引导"""
        return GuideTour(
            id="game_mode_guide",
            title="游戏模式介绍",
            description="体验游戏化的化学实验",
            target_audience="all",
            estimated_duration=150,
            steps=[
                GuideStep(
                    id="game_mode_intro",
                    title="游戏模式",
                    content="游戏模式让化学实验变得更有趣！\n\n包含物理模拟、粒子效果和分数系统。",
                    step_type=GuideStepType.MODAL,
                    auto_advance=True,
                    auto_advance_delay=4000,
                ),
                GuideStep(
                    id="physics_simulation",
                    title="物理模拟",
                    content="在游戏模式中，实验器材具有真实的物理特性。\n\n您可以拖拽、旋转和碰撞物品。",
                    target_widget="gameScene",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.CENTER,
                ),
                GuideStep(
                    id="particle_effects",
                    title="粒子效果",
                    content="观察美丽的粒子效果，如气泡、烟雾和火焰。\n\n这些效果让实验更加生动。",
                    target_widget="particleSystem",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.BOTTOM,
                ),
                GuideStep(
                    id="score_system",
                    title="分数系统",
                    content="完成实验步骤可以获得分数和连击奖励。\n\n挑战自己获得更高分数！",
                    target_widget="scorePanel",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.TOP,
                ),
            ],
        )

    def create_advanced_features_tour(self) -> GuideTour:
        """创建高级功能引导"""
        return GuideTour(
            id="advanced_features",
            title="高级功能",
            description="探索VirtualChemLab的高级功能",
            target_audience="advanced",
            estimated_duration=200,
            steps=[
                GuideStep(
                    id="performance_monitor",
                    title="性能监控",
                    content="监控系统性能，包括CPU、内存使用率和帧率。\n\n帮助优化实验体验。",
                    target_widget="performanceDialog",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.LEFT,
                ),
                GuideStep(
                    id="settings_dialog",
                    title="设置面板",
                    content="自定义应用设置，包括主题、语言和实验参数。\n\n让VirtualChemLab更符合您的需求。",
                    target_widget="settingsDialog",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.RIGHT,
                ),
                GuideStep(
                    id="help_system",
                    title="帮助系统",
                    content="访问详细的帮助文档和故障排除指南。\n\n遇到问题时可以随时查看。",
                    target_widget="helpDialog",
                    step_type=GuideStepType.TOOLTIP,
                    position=GuidePosition.BOTTOM,
                ),
            ],
        )

    def add_tour(self, tour: GuideTour):
        """添加引导旅程"""
        self.tours[tour.id] = tour
        logger.info(f"添加引导旅程: {tour.title}")

    def get_tour(self, tour_id: str) -> GuideTour | None:
        """获取引导旅程"""
        return self.tours.get(tour_id)

    def get_available_tours(self, user_level: str = "beginner") -> list[GuideTour]:
        """获取可用的引导旅程"""
        available = []

        for tour in self.tours.values():
            if (
                tour.target_audience in ["all", user_level]
                and tour.id not in self.completed_tours
            ):
                available.append(tour)

        return available

    def start_tour(self, tour_id: str, parent: QWidget | None = None) -> bool:
        """开始引导旅程"""
        tour = self.get_tour(tour_id)
        if not tour:
            logger.warning(f"引导旅程不存在: {tour_id}")
            return False

        if not parent:
            logger.warning("需要指定父控件")
            return False

        # 创建覆盖层
        self.overlay = GuideOverlay(parent)

        # 连接信号
        self.overlay.tour_completed.connect(self.on_tour_completed)
        self.overlay.tour_skipped.connect(self.on_tour_skipped)

        # 开始旅程
        self.overlay.start_tour(tour)

        logger.info(f"开始引导旅程: {tour.title}")
        return True

    def on_tour_completed(self, tour_id: str):
        """旅程完成处理"""
        self.completed_tours.add(tour_id)
        self.save_user_preferences()

        logger.info(f"引导旅程完成: {tour_id}")

    def on_tour_skipped(self, tour_id: str):
        """旅程跳过处理"""
        logger.info(f"引导旅程跳过: {tour_id}")

    def is_tour_completed(self, tour_id: str) -> bool:
        """检查旅程是否已完成"""
        return tour_id in self.completed_tours

    def reset_tour_progress(self, tour_id: str | None = None):
        """重置旅程进度"""
        if tour_id:
            self.completed_tours.discard(tour_id)
        else:
            self.completed_tours.clear()

        self.save_user_preferences()
        logger.info(f"重置旅程进度: {tour_id or 'all'}")

    def load_user_preferences(self):
        """加载用户偏好"""
        try:
            prefs_file = Path("user_data/guidance_preferences.json")
            if prefs_file.exists():
                with open(prefs_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_tours = set(data.get("completed_tours", []))
                    self.user_preferences = data.get("preferences", {})

                logger.info("用户引导偏好加载成功")
        except Exception as e:
            logger.warning(f"加载用户引导偏好失败: {e}")

    def save_user_preferences(self):
        """保存用户偏好"""
        try:
            prefs_file = Path("user_data/guidance_preferences.json")
            prefs_file.parent.mkdir(exist_ok=True)

            data = {
                "completed_tours": list(self.completed_tours),
                "preferences": self.user_preferences,
            }

            with open(prefs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("用户引导偏好保存成功")
        except Exception as e:
            logger.warning(f"保存用户引导偏好失败: {e}")


# 全局引导管理器实例
_guidance_manager: UserGuidanceManager | None = None


def get_guidance_manager() -> UserGuidanceManager:
    """获取全局引导管理器"""
    global _guidance_manager
    if _guidance_manager is None:
        _guidance_manager = UserGuidanceManager()
    return _guidance_manager


def start_guide_tour(tour_id: str, parent: QWidget) -> bool:
    """开始引导旅程"""
    return get_guidance_manager().start_tour(tour_id, parent)


def show_guide_menu(parent: QWidget) -> bool:
    """显示引导菜单"""
    logger.info("显示引导菜单")

    try:
        from PySide6.QtWidgets import QDialog, QListWidget, QTextEdit

        # 创建引导菜单对话框
        dialog = QDialog(parent)
        dialog.setWindowTitle("🎓 用户引导菜单")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题说明
        title_label = QLabel("选择一个引导教程开始学习：")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 引导列表
        guide_list = QListWidget()
        guide_list.setObjectName("guideList")

        # 获取可用的引导
        manager = get_guidance_manager()
        tours = manager.get_all_tours()

        for tour in tours:
            duration_text = (
                f"{tour.estimated_duration}秒"
                if tour.estimated_duration > 0
                else "未知"
            )
            item_text = f"📚 {tour.title}\n   {tour.description}\n   预计时长: {duration_text} | 目标用户: {tour.target_audience}"
            guide_list.addItem(item_text)
            guide_list.item(guide_list.count() - 1).setData(
                Qt.ItemDataRole.UserRole, tour.id
            )

        guide_list.setMinimumHeight(300)
        layout.addWidget(guide_list)

        # 详细信息区域
        detail_label = QLabel("详细信息：")
        detail_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(detail_label)

        detail_text = QTextEdit()
        detail_text.setReadOnly(True)
        detail_text.setMaximumHeight(100)
        layout.addWidget(detail_text)

        # 更新详细信息
        def update_detail():
            current_item = guide_list.currentItem()
            if current_item:
                tour_id = current_item.data(Qt.ItemDataRole.UserRole)
                tour = manager.get_tour(tour_id)
                if tour:
                    detail_html = f"""
                    <h3>{tour.title}</h3>
                    <p><b>描述：</b>{tour.description}</p>
                    <p><b>步骤数：</b>{len(tour.steps)}</p>
                    <p><b>版本：</b>{tour.version}</p>
                    """
                    if tour.prerequisites:
                        detail_html += (
                            f"<p><b>前置要求：</b>{', '.join(tour.prerequisites)}</p>"
                        )
                    detail_text.setHtml(detail_html)

        guide_list.currentItemChanged.connect(lambda: update_detail())

        # 如果有引导，默认选择第一个
        if guide_list.count() > 0:
            guide_list.setCurrentRow(0)
            update_detail()

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        start_button = ModernButton("▶️ 开始引导")
        start_button.setMinimumWidth(120)

        def start_selected_tour():
            current_item = guide_list.currentItem()
            if current_item:
                tour_id = current_item.data(Qt.ItemDataRole.UserRole)
                manager.start_tour(tour_id, parent)
                dialog.accept()

        start_button.clicked.connect(start_selected_tour)
        button_layout.addWidget(start_button)

        cancel_button = ModernButton("❌ 取消")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 应用样式
        dialog.setStyleSheet(
            """
            QDialog {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QListWidget {
                background-color: #16213e;
                color: #ffffff;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                padding: 10px;
                font-size: 11pt;
            }
            QListWidget::item {
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
            }
            QListWidget::item:hover {
                background-color: #2a5a8a;
            }
            QTextEdit {
                background-color: #16213e;
                color: #ffffff;
                border: 2px solid #4a90e2;
                border-radius: 8px;
                padding: 10px;
            }
        """
        )

        # 显示对话框
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted

    except Exception as e:
        logger.error(f"显示引导菜单失败: {e}")
        return False
