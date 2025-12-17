"""
游戏化实验视图
集成游戏化交互系统的实验界面
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.experiment_controller import ExperimentController
from ..models.experiment import ExperimentTemplate
from ..utils.logger import get_logger
from .game_interaction import (
    GamePhysicsScene,
    GamePhysicsView,
    InteractionType,
    PhysicsState,
)
from .game_scene_builder import GameSceneBuilder
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class GameExperimentView(QWidget):
    """游戏化实验视图"""

    # 信号
    step_completed = Signal(str, dict)  # 步骤ID, 结果数据
    experiment_completed = Signal(dict)  # 实验结果
    interaction_logged = Signal(str, str, dict)  # 用户ID, 交互类型, 数据

    def __init__(
        self,
        template: ExperimentTemplate,
        controller: ExperimentController,
        user_id: str = "student_001",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.template = template
        self.controller = controller
        self.user_id = user_id

        # 游戏化属性
        self.game_scene: GamePhysicsScene | None = None
        self.game_view: GamePhysicsView | None = None
        self.interaction_log: list[dict[str, Any]] = []
        self.score_multiplier = 1.0
        self.combo_count = 0
        self.max_combo = 0

        # 游戏状态
        self.game_paused = False
        self.physics_enabled = True
        self.sound_enabled = True
        self.particle_effects_enabled = True

        # 主题管理器
        self.theme_manager = ThemeManager()

        self.init_ui()
        self.setup_game_scene()
        self.connect_signals()

        logger.info(f"游戏化实验视图初始化完成: {template.title}")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"游戏化实验 - {self.template.title}")
        self.setMinimumSize(1200, 800)

        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 左侧游戏区域
        self.game_area = self.create_game_area()
        main_layout.addWidget(self.game_area, 3)

        # 右侧控制面板
        self.control_panel = self.create_control_panel()
        main_layout.addWidget(self.control_panel, 1)

        # 应用主题
        self.apply_theme()

    def create_game_area(self) -> QWidget:
        """创建游戏区域"""
        game_widget = QWidget()
        game_layout = QVBoxLayout(game_widget)
        game_layout.setSpacing(5)
        game_layout.setContentsMargins(5, 5, 5, 5)

        # 游戏标题
        title_label = QLabel(f"🧪 {self.template.title}")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            QLabel {
                color: #4a90e2;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 2px solid #4a90e2;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """
        )
        game_layout.addWidget(title_label)

        # 游戏场景视图
        self.game_view = GamePhysicsView()
        self.game_view.setMinimumSize(800, 600)
        game_layout.addWidget(self.game_view)

        # 游戏状态栏
        self.status_bar = self.create_status_bar()
        game_layout.addWidget(self.status_bar)

        return game_widget

    def create_status_bar(self) -> QWidget:
        """创建状态栏"""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setSpacing(10)

        # 分数显示
        self.score_label = QLabel("分数: 0")
        self.score_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.score_label.setStyleSheet(
            """
            QLabel {
                color: #ffd700;
                background: #2d1b69;
                border: 1px solid #ffd700;
                border-radius: 4px;
                padding: 5px;
            }
        """
        )
        status_layout.addWidget(self.score_label)

        # 连击计数
        self.combo_label = QLabel("连击: 0")
        self.combo_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.combo_label.setStyleSheet(
            """
            QLabel {
                color: #ff6b6b;
                background: #2d1b69;
                border: 1px solid #ff6b6b;
                border-radius: 4px;
                padding: 5px;
            }
        """
        )
        status_layout.addWidget(self.combo_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #4a90e2;
                border-radius: 5px;
                text-align: center;
                background: #1a1a2e;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:1 #357abd);
                border-radius: 3px;
            }
        """
        )
        status_layout.addWidget(self.progress_bar)

        # 物理状态
        self.physics_status = QLabel("物理: 开启")
        self.physics_status.setFont(QFont("Arial", 10))
        self.physics_status.setStyleSheet(
            """
            QLabel {
                color: #4ecdc4;
                background: #2d1b69;
                border: 1px solid #4ecdc4;
                border-radius: 4px;
                padding: 5px;
            }
        """
        )
        status_layout.addWidget(self.physics_status)

        return status_widget

    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(300)
        panel.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 2px solid #4a90e2;
                border-radius: 8px;
            }
        """
        )

        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 游戏控制
        game_control_group = QGroupBox("🎮 游戏控制")
        game_control_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                color: #4a90e2;
                border: 2px solid #4a90e2;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        game_control_layout = QVBoxLayout(game_control_group)

        # 暂停/继续按钮
        self.pause_button = ModernButton("⏸️ 暂停")
        self.pause_button.clicked.connect(self.toggle_pause)
        game_control_layout.addWidget(self.pause_button)

        # 重置按钮
        self.reset_button = ModernButton("🔄 重置")
        self.reset_button.clicked.connect(self.reset_game)
        game_control_layout.addWidget(self.reset_button)

        # 物理开关
        self.physics_checkbox = QCheckBox("启用物理模拟")
        self.physics_checkbox.setChecked(True)
        self.physics_checkbox.toggled.connect(self.toggle_physics)
        game_control_layout.addWidget(self.physics_checkbox)

        # 音效开关
        self.sound_checkbox = QCheckBox("启用音效")
        self.sound_checkbox.setChecked(True)
        self.sound_checkbox.toggled.connect(self.toggle_sound)
        game_control_layout.addWidget(self.sound_checkbox)

        # 粒子效果开关
        self.particle_checkbox = QCheckBox("启用粒子效果")
        self.particle_checkbox.setChecked(True)
        self.particle_checkbox.toggled.connect(self.toggle_particles)
        game_control_layout.addWidget(self.particle_checkbox)

        layout.addWidget(game_control_group)

        # 物理设置
        physics_group = QGroupBox("⚙️ 物理设置")
        physics_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                color: #4a90e2;
                border: 2px solid #4a90e2;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        physics_layout = QVBoxLayout(physics_group)

        # 重力强度
        gravity_layout = QHBoxLayout()
        gravity_layout.addWidget(QLabel("重力:"))
        self.gravity_slider = QSlider(Qt.Orientation.Horizontal)
        self.gravity_slider.setRange(0, 100)
        self.gravity_slider.setValue(50)
        self.gravity_slider.valueChanged.connect(self.adjust_gravity)
        gravity_layout.addWidget(self.gravity_slider)
        physics_layout.addLayout(gravity_layout)

        # 摩擦力
        friction_layout = QHBoxLayout()
        friction_layout.addWidget(QLabel("摩擦力:"))
        self.friction_slider = QSlider(Qt.Orientation.Horizontal)
        self.friction_slider.setRange(0, 100)
        self.friction_slider.setValue(90)
        self.friction_slider.valueChanged.connect(self.adjust_friction)
        friction_layout.addWidget(self.friction_slider)
        physics_layout.addLayout(friction_layout)

        # 弹跳系数
        bounce_layout = QHBoxLayout()
        bounce_layout.addWidget(QLabel("弹跳:"))
        self.bounce_slider = QSlider(Qt.Orientation.Horizontal)
        self.bounce_slider.setRange(0, 100)
        self.bounce_slider.setValue(60)
        self.bounce_slider.valueChanged.connect(self.adjust_bounce)
        bounce_layout.addWidget(self.bounce_slider)
        physics_layout.addLayout(bounce_layout)

        layout.addWidget(physics_group)

        # 实验步骤
        steps_group = QGroupBox("📋 实验步骤")
        steps_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                color: #4a90e2;
                border: 2px solid #4a90e2;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        steps_layout = QVBoxLayout(steps_group)

        # 步骤列表
        self.steps_text = QTextEdit()
        self.steps_text.setMaximumHeight(200)
        self.steps_text.setReadOnly(True)
        self.steps_text.setStyleSheet(
            """
            QTextEdit {
                background: #1a1a2e;
                color: #ffffff;
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 5px;
            }
        """
        )
        steps_layout.addWidget(self.steps_text)

        layout.addWidget(steps_group)

        # 交互日志
        log_group = QGroupBox("📊 交互日志")
        log_group.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
                color: #4a90e2;
                border: 2px solid #4a90e2;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """
        )
        log_layout = QVBoxLayout(log_group)

        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background: #1a1a2e;
                color: #ffffff;
                border: 1px solid #4a90e2;
                border-radius: 4px;
                padding: 5px;
                font-family: monospace;
                font-size: 10px;
            }
        """
        )
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # 添加弹性空间
        layout.addStretch()

        return panel

    def setup_game_scene(self):
        """设置游戏场景"""
        try:
            # 获取场景配置
            scene_config = GameSceneBuilder.get_scene_by_experiment_type(
                getattr(self.template, "category", "general")
            )

            # 创建游戏场景
            self.game_scene = GamePhysicsScene(scene_config)

            # 添加物理物品
            for item_config in scene_config.get("physics_items", []):
                self.game_scene.add_physics_item(
                    item_id=item_config["id"],
                    item_type=item_config["type"],
                    position=tuple(item_config["position"]),
                    physics_props=item_config.get("physics_props", {}),
                )

            # 设置游戏视图
            self.game_view.setScene(self.game_scene)

            # 更新步骤显示
            self.update_steps_display()

            logger.info("游戏场景设置完成")

        except Exception as e:
            logger.error(f"设置游戏场景失败: {e}", exc_info=True)

    def connect_signals(self):
        """连接信号"""
        if self.game_scene:
            self.game_scene.item_interacted.connect(self.on_item_interacted)
            self.game_scene.collision_detected.connect(self.on_collision_detected)
            self.game_scene.physics_updated.connect(self.on_physics_updated)

    def on_item_interacted(
        self, item_id: str, interaction_type: InteractionType, data: dict
    ):
        """处理物品交互"""
        # 记录交互
        interaction_log = {
            "timestamp": self.controller.record.current_time,
            "item_id": item_id,
            "interaction_type": interaction_type.value,
            "data": data,
        }
        self.interaction_log.append(interaction_log)

        # 更新分数
        self.update_score(interaction_type, data)

        # 更新连击
        self.update_combo(interaction_type)

        # 更新日志显示
        self.update_log_display()

        # 发送信号
        self.interaction_logged.emit(self.user_id, interaction_type.value, data)

        logger.debug(f"物品交互: {item_id} - {interaction_type.value}")

    def on_collision_detected(self, item_id1: str, item_id2: str):
        """处理碰撞检测"""
        # 记录碰撞
        collision_log = {
            "timestamp": self.controller.record.current_time,
            "type": "collision",
            "item1": item_id1,
            "item2": item_id2,
        }
        self.interaction_log.append(collision_log)

        # 更新分数
        self.update_score(InteractionType.SWIPE, {"collision": True})

        # 更新日志显示
        self.update_log_display()

        logger.debug(f"碰撞检测: {item_id1} <-> {item_id2}")

    def on_physics_updated(self):
        """物理更新处理"""
        # 更新物理状态显示
        if self.game_scene:
            enabled = self.game_scene.gravity_enabled
            self.physics_status.setText(f"物理: {'开启' if enabled else '关闭'}")

    def update_score(self, interaction_type: InteractionType, _data: dict):
        """更新分数"""
        base_score = 10

        # 根据交互类型调整分数
        if interaction_type == InteractionType.DRAG:
            base_score = 5
        elif interaction_type == InteractionType.CLICK:
            base_score = 3
        elif interaction_type == InteractionType.SWIPE:
            base_score = 8

        # 应用连击倍数
        score = int(base_score * self.score_multiplier)

        # 更新分数显示
        current_score = int(self.score_label.text().split(": ")[1])
        new_score = current_score + score
        self.score_label.setText(f"分数: {new_score}")

        # 更新进度条
        max_score = len(self.template.steps) * 100
        progress = min(100, int((new_score / max_score) * 100))
        self.progress_bar.setValue(progress)

    def update_combo(self, _interaction_type: InteractionType):
        """更新连击计数"""
        self.combo_count += 1
        self.max_combo = max(self.max_combo, self.combo_count)

        # 更新连击显示
        self.combo_label.setText(f"连击: {self.combo_count}")

        # 更新分数倍数
        if self.combo_count >= 10:
            self.score_multiplier = 2.0
        elif self.combo_count >= 5:
            self.score_multiplier = 1.5
        else:
            self.score_multiplier = 1.0

    def update_steps_display(self):
        """更新步骤显示"""
        steps_text = "实验步骤:\n\n"
        for i, step in enumerate(self.template.steps, 1):
            steps_text += f"{i}. {step.text}\n"

        self.steps_text.setText(steps_text)

    def update_log_display(self):
        """更新日志显示"""
        log_text = "交互日志:\n\n"
        for log in self.interaction_log[-10:]:  # 显示最近10条
            timestamp = log.get("timestamp", "未知时间")
            log_type = log.get("type", "interaction")
            if log_type == "interaction":
                item_id = log.get("item_id", "未知物品")
                interaction_type = log.get("interaction_type", "未知类型")
                log_text += f"[{timestamp}] {item_id} - {interaction_type}\n"
            elif log_type == "collision":
                item1 = log.get("item1", "未知")
                item2 = log.get("item2", "未知")
                log_text += f"[{timestamp}] 碰撞: {item1} <-> {item2}\n"

        self.log_text.setText(log_text)

    def toggle_pause(self):
        """切换暂停状态"""
        self.game_paused = not self.game_paused

        if self.game_paused:
            self.pause_button.setText("▶️ 继续")
            if self.game_scene:
                self.game_scene.physics_timer.stop()
        else:
            self.pause_button.setText("⏸️ 暂停")
            if self.game_scene:
                self.game_scene.physics_timer.start(16)

        logger.info(f"游戏{'暂停' if self.game_paused else '继续'}")

    def reset_game(self):
        """重置游戏"""
        if self.game_scene:
            # 重置所有物品
            for item in self.game_scene.physics_items.values():
                item.physics_state = PhysicsState.STATIC
                item.velocity = QPointF(0, 0)

            # 重置分数和连击
            self.score_label.setText("分数: 0")
            self.combo_label.setText("连击: 0")
            self.progress_bar.setValue(0)
            self.score_multiplier = 1.0
            self.combo_count = 0

            # 清空日志
            self.interaction_log.clear()
            self.update_log_display()

            logger.info("游戏重置完成")

    def toggle_physics(self, enabled: bool):
        """切换物理模拟"""
        self.physics_enabled = enabled
        if self.game_scene:
            self.game_scene.enable_gravity(enabled)

        logger.info(f"物理模拟{'启用' if enabled else '禁用'}")

    def toggle_sound(self, enabled: bool):
        """切换音效"""
        self.sound_enabled = enabled
        logger.info(f"音效{'启用' if enabled else '禁用'}")

    def toggle_particles(self, enabled: bool):
        """切换粒子效果"""
        self.particle_effects_enabled = enabled
        logger.info(f"粒子效果{'启用' if enabled else '禁用'}")

    def adjust_gravity(self, value: int):
        """调整重力强度"""
        if self.game_scene:
            gravity_strength = value / 100.0
            for item in self.game_scene.physics_items.values():
                item.gravity = item.gravity.__class__(0, 0.5 * gravity_strength)

        logger.debug(f"重力强度调整为: {value}%")

    def adjust_friction(self, value: int):
        """调整摩擦力"""
        if self.game_scene:
            friction = value / 100.0
            for item in self.game_scene.physics_items.values():
                item.friction = friction

        logger.debug(f"摩擦力调整为: {value}%")

    def adjust_bounce(self, value: int):
        """调整弹跳系数"""
        if self.game_scene:
            bounce = value / 100.0
            for item in self.game_scene.physics_items.values():
                item.bounce_factor = bounce

        logger.debug(f"弹跳系数调整为: {value}%")

    def apply_theme(self):
        """应用主题"""
        try:
            app = self.theme_manager.get_application()
            if app:
                system_theme = self.theme_manager.get_system_theme()
                self.theme_manager.set_theme(app, system_theme)
        except Exception as e:
            logger.warning(f"应用主题失败: {e}")

    def get_interaction_summary(self) -> dict:
        """获取交互摘要"""
        return {
            "total_interactions": len(self.interaction_log),
            "max_combo": self.max_combo,
            "final_score": int(self.score_label.text().split(": ")[1]),
            "physics_enabled": self.physics_enabled,
            "sound_enabled": self.sound_enabled,
            "particle_effects_enabled": self.particle_effects_enabled,
            "interaction_log": self.interaction_log,
        }
