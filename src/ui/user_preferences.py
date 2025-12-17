"""
用户偏好设置
提供个性化定制选项和偏好管理
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AnimationSpeed(Enum):
    """动画速度"""

    NONE = "none"  # 无动画
    SLOW = "slow"  # 慢速
    NORMAL = "normal"  # 正常
    FAST = "fast"  # 快速


class Theme(Enum):
    """主题"""

    SYSTEM = "system"  # 跟随系统
    LIGHT = "light"  # 浅色
    DARK = "dark"  # 深色


class Language(Enum):
    """语言"""

    SYSTEM = "system"  # 跟随系统
    ZH_CN = "zh_CN"  # 简体中文
    EN_US = "en_US"  # English
    JA_JP = "ja_JP"  # 日本語


@dataclass
class UserPreferences:
    """用户偏好设置"""

    # 外观设置
    theme: Theme = Theme.SYSTEM
    animation_speed: AnimationSpeed = AnimationSpeed.NORMAL
    font_size: int = 11
    show_animations: bool = True
    reduce_motion: bool = False

    # 语言设置
    language: Language = Language.SYSTEM

    # 行为设置
    auto_save: bool = True
    auto_save_interval: int = 300  # 秒
    confirm_on_exit: bool = True
    remember_window_size: bool = True
    remember_last_experiment: bool = True

    # 实验设置
    show_hints: bool = True
    auto_advance_steps: bool = False
    show_safety_warnings: bool = True
    enable_achievements: bool = True

    # 性能设置
    enable_hardware_acceleration: bool = True
    max_fps: int = 60
    enable_vsync: bool = True
    render_quality: str = "high"

    # 反馈设置
    enable_sound: bool = False
    enable_visual_feedback: bool = True
    enable_haptic_feedback: bool = False
    feedback_intensity: float = 1.0

    # 辅助功能
    high_contrast: bool = False
    large_cursor: bool = False
    screen_reader_support: bool = False
    keyboard_only_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "theme": self.theme.value,
            "animation_speed": self.animation_speed.value,
            "font_size": self.font_size,
            "show_animations": self.show_animations,
            "reduce_motion": self.reduce_motion,
            "language": self.language.value,
            "auto_save": self.auto_save,
            "auto_save_interval": self.auto_save_interval,
            "confirm_on_exit": self.confirm_on_exit,
            "remember_window_size": self.remember_window_size,
            "remember_last_experiment": self.remember_last_experiment,
            "show_hints": self.show_hints,
            "auto_advance_steps": self.auto_advance_steps,
            "show_safety_warnings": self.show_safety_warnings,
            "enable_achievements": self.enable_achievements,
            "enable_hardware_acceleration": self.enable_hardware_acceleration,
            "max_fps": self.max_fps,
            "enable_vsync": self.enable_vsync,
            "render_quality": self.render_quality,
            "enable_sound": self.enable_sound,
            "enable_visual_feedback": self.enable_visual_feedback,
            "enable_haptic_feedback": self.enable_haptic_feedback,
            "feedback_intensity": self.feedback_intensity,
            "high_contrast": self.high_contrast,
            "large_cursor": self.large_cursor,
            "screen_reader_support": self.screen_reader_support,
            "keyboard_only_mode": self.keyboard_only_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserPreferences:
        """从字典创建"""
        prefs = cls()

        if "theme" in data:
            prefs.theme = Theme(data["theme"])
        if "animation_speed" in data:
            prefs.animation_speed = AnimationSpeed(data["animation_speed"])
        if "language" in data:
            prefs.language = Language(data["language"])

        # 其他属性
        for key, value in data.items():
            if hasattr(prefs, key) and key not in [
                "theme",
                "animation_speed",
                "language",
            ]:
                setattr(prefs, key, value)

        return prefs


class PreferencesDialog(QDialog):
    """偏好设置对话框"""

    preferences_changed = Signal(UserPreferences)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.preferences = UserPreferences()
        self.load_preferences()

        self.setWindowTitle("偏好设置")
        self.setModal(True)
        self.setMinimumSize(700, 600)

        self.init_ui()
        self.load_values_to_ui()

        logger.info("偏好设置对话框已创建")

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("⚙️ 偏好设置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 选项卡
        tabs = QTabWidget()
        tabs.addTab(self.create_appearance_tab(), "🎨 外观")
        tabs.addTab(self.create_behavior_tab(), "🔧 行为")
        tabs.addTab(self.create_experiment_tab(), "🧪 实验")
        tabs.addTab(self.create_performance_tab(), "⚡ 性能")
        tabs.addTab(self.create_feedback_tab(), "💬 反馈")
        tabs.addTab(self.create_accessibility_tab(), "♿ 辅助功能")
        layout.addWidget(tabs)

        # 按钮
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_preferences)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def create_appearance_tab(self) -> QWidget:
        """创建外观选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 主题
        theme_group = QGroupBox("主题")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["跟随系统", "浅色", "深色"])
        theme_layout.addRow("主题:", self.theme_combo)

        layout.addWidget(theme_group)

        # 动画
        animation_group = QGroupBox("动画")
        animation_layout = QFormLayout(animation_group)

        self.animation_speed_combo = QComboBox()
        self.animation_speed_combo.addItems(["无动画", "慢速", "正常", "快速"])
        animation_layout.addRow("动画速度:", self.animation_speed_combo)

        self.show_animations_check = QCheckBox("显示动画效果")
        animation_layout.addRow(self.show_animations_check)

        self.reduce_motion_check = QCheckBox("减少动画（辅助功能）")
        animation_layout.addRow(self.reduce_motion_check)

        layout.addWidget(animation_group)

        # 字体
        font_group = QGroupBox("字体")
        font_layout = QFormLayout(font_group)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setSuffix(" pt")
        font_layout.addRow("字体大小:", self.font_size_spin)

        layout.addWidget(font_group)

        # 语言
        language_group = QGroupBox("语言")
        language_layout = QFormLayout(language_group)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["跟随系统", "简体中文", "English", "日本語"])
        language_layout.addRow("界面语言:", self.language_combo)

        note = QLabel("注意：更改语言需要重启应用")
        note.setStyleSheet("color: #666; font-size: 10px;")
        language_layout.addRow(note)

        layout.addWidget(language_group)

        layout.addStretch()
        return widget

    def create_behavior_tab(self) -> QWidget:
        """创建行为选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 自动保存
        save_group = QGroupBox("保存")
        save_layout = QFormLayout(save_group)

        self.auto_save_check = QCheckBox("自动保存实验进度")
        save_layout.addRow(self.auto_save_check)

        self.auto_save_interval_spin = QSpinBox()
        self.auto_save_interval_spin.setRange(60, 3600)
        self.auto_save_interval_spin.setSuffix(" 秒")
        save_layout.addRow("自动保存间隔:", self.auto_save_interval_spin)

        layout.addWidget(save_group)

        # 窗口行为
        window_group = QGroupBox("窗口")
        window_layout = QFormLayout(window_group)

        self.confirm_exit_check = QCheckBox("退出时确认")
        window_layout.addRow(self.confirm_exit_check)

        self.remember_window_check = QCheckBox("记住窗口大小和位置")
        window_layout.addRow(self.remember_window_check)

        self.remember_experiment_check = QCheckBox("启动时打开上次的实验")
        window_layout.addRow(self.remember_experiment_check)

        layout.addWidget(window_group)

        layout.addStretch()
        return widget

    def create_experiment_tab(self) -> QWidget:
        """创建实验选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 提示
        hint_group = QGroupBox("提示和帮助")
        hint_layout = QFormLayout(hint_group)

        self.show_hints_check = QCheckBox("显示操作提示")
        hint_layout.addRow(self.show_hints_check)

        self.show_safety_check = QCheckBox("显示安全警告")
        hint_layout.addRow(self.show_safety_check)

        layout.addWidget(hint_group)

        # 步骤
        step_group = QGroupBox("实验步骤")
        step_layout = QFormLayout(step_group)

        self.auto_advance_check = QCheckBox("完成后自动进入下一步")
        step_layout.addRow(self.auto_advance_check)

        layout.addWidget(step_group)

        # 游戏化
        game_group = QGroupBox("游戏化")
        game_layout = QFormLayout(game_group)

        self.enable_achievements_check = QCheckBox("启用成就系统")
        game_layout.addRow(self.enable_achievements_check)

        layout.addWidget(game_group)

        layout.addStretch()
        return widget

    def create_performance_tab(self) -> QWidget:
        """创建性能选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 硬件加速
        hw_group = QGroupBox("硬件加速")
        hw_layout = QFormLayout(hw_group)

        self.hw_accel_check = QCheckBox("启用硬件加速")
        hw_layout.addRow(self.hw_accel_check)

        layout.addWidget(hw_group)

        # 渲染
        render_group = QGroupBox("渲染设置")
        render_layout = QFormLayout(render_group)

        self.max_fps_spin = QSpinBox()
        self.max_fps_spin.setRange(30, 144)
        self.max_fps_spin.setSuffix(" FPS")
        render_layout.addRow("最大帧率:", self.max_fps_spin)

        self.vsync_check = QCheckBox("启用垂直同步")
        render_layout.addRow(self.vsync_check)

        self.render_quality_combo = QComboBox()
        self.render_quality_combo.addItems(["低", "中", "高", "极高"])
        render_layout.addRow("渲染质量:", self.render_quality_combo)

        layout.addWidget(render_group)

        layout.addStretch()
        return widget

    def create_feedback_tab(self) -> QWidget:
        """创建反馈选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 反馈类型
        type_group = QGroupBox("反馈类型")
        type_layout = QFormLayout(type_group)

        self.sound_check = QCheckBox("启用声音反馈")
        type_layout.addRow(self.sound_check)

        self.visual_feedback_check = QCheckBox("启用视觉反馈")
        type_layout.addRow(self.visual_feedback_check)

        self.haptic_check = QCheckBox("启用触觉反馈（需要硬件支持）")
        type_layout.addRow(self.haptic_check)

        layout.addWidget(type_group)

        # 强度
        intensity_group = QGroupBox("反馈强度")
        intensity_layout = QFormLayout(intensity_group)

        self.feedback_intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.feedback_intensity_slider.setRange(0, 100)
        self.feedback_intensity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.feedback_intensity_slider.setTickInterval(25)
        intensity_layout.addRow("强度:", self.feedback_intensity_slider)

        layout.addWidget(intensity_group)

        layout.addStretch()
        return widget

    def create_accessibility_tab(self) -> QWidget:
        """创建辅助功能选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 视觉辅助
        visual_group = QGroupBox("视觉辅助")
        visual_layout = QFormLayout(visual_group)

        self.high_contrast_check = QCheckBox("高对比度模式")
        visual_layout.addRow(self.high_contrast_check)

        self.large_cursor_check = QCheckBox("大光标")
        visual_layout.addRow(self.large_cursor_check)

        layout.addWidget(visual_group)

        # 输入辅助
        input_group = QGroupBox("输入辅助")
        input_layout = QFormLayout(input_group)

        self.screen_reader_check = QCheckBox("屏幕阅读器支持")
        input_layout.addRow(self.screen_reader_check)

        self.keyboard_only_check = QCheckBox("仅键盘模式")
        input_layout.addRow(self.keyboard_only_check)

        layout.addWidget(input_group)

        # 说明
        note = QLabel(
            "辅助功能设置可以帮助有特殊需求的用户更好地使用应用程序。\n某些功能可能需要重启应用才能生效。"
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #666; padding: 10px; background-color: #f0f0f0; border-radius: 6px;"
        )
        layout.addWidget(note)

        layout.addStretch()
        return widget

    def load_values_to_ui(self):
        """将值加载到UI"""
        # 外观
        theme_map = {Theme.SYSTEM: 0, Theme.LIGHT: 1, Theme.DARK: 2}
        self.theme_combo.setCurrentIndex(theme_map[self.preferences.theme])

        speed_map = {
            AnimationSpeed.NONE: 0,
            AnimationSpeed.SLOW: 1,
            AnimationSpeed.NORMAL: 2,
            AnimationSpeed.FAST: 3,
        }
        self.animation_speed_combo.setCurrentIndex(
            speed_map[self.preferences.animation_speed]
        )

        self.show_animations_check.setChecked(self.preferences.show_animations)
        self.reduce_motion_check.setChecked(self.preferences.reduce_motion)
        self.font_size_spin.setValue(self.preferences.font_size)

        lang_map = {
            Language.SYSTEM: 0,
            Language.ZH_CN: 1,
            Language.EN_US: 2,
            Language.JA_JP: 3,
        }
        self.language_combo.setCurrentIndex(lang_map[self.preferences.language])

        # 行为
        self.auto_save_check.setChecked(self.preferences.auto_save)
        self.auto_save_interval_spin.setValue(self.preferences.auto_save_interval)
        self.confirm_exit_check.setChecked(self.preferences.confirm_on_exit)
        self.remember_window_check.setChecked(self.preferences.remember_window_size)
        self.remember_experiment_check.setChecked(
            self.preferences.remember_last_experiment
        )

        # 实验
        self.show_hints_check.setChecked(self.preferences.show_hints)
        self.auto_advance_check.setChecked(self.preferences.auto_advance_steps)
        self.show_safety_check.setChecked(self.preferences.show_safety_warnings)
        self.enable_achievements_check.setChecked(self.preferences.enable_achievements)

        # 性能
        self.hw_accel_check.setChecked(self.preferences.enable_hardware_acceleration)
        self.max_fps_spin.setValue(self.preferences.max_fps)
        self.vsync_check.setChecked(self.preferences.enable_vsync)

        quality_map = {"low": 0, "medium": 1, "high": 2, "ultra": 3}
        self.render_quality_combo.setCurrentIndex(
            quality_map.get(self.preferences.render_quality, 2)
        )

        # 反馈
        self.sound_check.setChecked(self.preferences.enable_sound)
        self.visual_feedback_check.setChecked(self.preferences.enable_visual_feedback)
        self.haptic_check.setChecked(self.preferences.enable_haptic_feedback)
        self.feedback_intensity_slider.setValue(
            int(self.preferences.feedback_intensity * 100)
        )

        # 辅助功能
        self.high_contrast_check.setChecked(self.preferences.high_contrast)
        self.large_cursor_check.setChecked(self.preferences.large_cursor)
        self.screen_reader_check.setChecked(self.preferences.screen_reader_support)
        self.keyboard_only_check.setChecked(self.preferences.keyboard_only_mode)

    def save_values_from_ui(self):
        """从UI保存值"""
        # 外观
        theme_map = [Theme.SYSTEM, Theme.LIGHT, Theme.DARK]
        self.preferences.theme = theme_map[self.theme_combo.currentIndex()]

        speed_map = [
            AnimationSpeed.NONE,
            AnimationSpeed.SLOW,
            AnimationSpeed.NORMAL,
            AnimationSpeed.FAST,
        ]
        self.preferences.animation_speed = speed_map[
            self.animation_speed_combo.currentIndex()
        ]

        self.preferences.show_animations = self.show_animations_check.isChecked()
        self.preferences.reduce_motion = self.reduce_motion_check.isChecked()
        self.preferences.font_size = self.font_size_spin.value()

        lang_map = [Language.SYSTEM, Language.ZH_CN, Language.EN_US, Language.JA_JP]
        self.preferences.language = lang_map[self.language_combo.currentIndex()]

        # 行为
        self.preferences.auto_save = self.auto_save_check.isChecked()
        self.preferences.auto_save_interval = self.auto_save_interval_spin.value()
        self.preferences.confirm_on_exit = self.confirm_exit_check.isChecked()
        self.preferences.remember_window_size = self.remember_window_check.isChecked()
        self.preferences.remember_last_experiment = (
            self.remember_experiment_check.isChecked()
        )

        # 实验
        self.preferences.show_hints = self.show_hints_check.isChecked()
        self.preferences.auto_advance_steps = self.auto_advance_check.isChecked()
        self.preferences.show_safety_warnings = self.show_safety_check.isChecked()
        self.preferences.enable_achievements = (
            self.enable_achievements_check.isChecked()
        )

        # 性能
        self.preferences.enable_hardware_acceleration = self.hw_accel_check.isChecked()
        self.preferences.max_fps = self.max_fps_spin.value()
        self.preferences.enable_vsync = self.vsync_check.isChecked()

        quality_map = ["low", "medium", "high", "ultra"]
        self.preferences.render_quality = quality_map[
            self.render_quality_combo.currentIndex()
        ]

        # 反馈
        self.preferences.enable_sound = self.sound_check.isChecked()
        self.preferences.enable_visual_feedback = self.visual_feedback_check.isChecked()
        self.preferences.enable_haptic_feedback = self.haptic_check.isChecked()
        self.preferences.feedback_intensity = (
            self.feedback_intensity_slider.value() / 100.0
        )

        # 辅助功能
        self.preferences.high_contrast = self.high_contrast_check.isChecked()
        self.preferences.large_cursor = self.large_cursor_check.isChecked()
        self.preferences.screen_reader_support = self.screen_reader_check.isChecked()
        self.preferences.keyboard_only_mode = self.keyboard_only_check.isChecked()

    def save_preferences(self):
        """保存偏好设置"""
        self.save_values_from_ui()

        # 保存到文件
        try:
            prefs_file = Path("data/user_preferences.json")
            prefs_file.parent.mkdir(parents=True, exist_ok=True)

            import json

            with open(prefs_file, "w", encoding="utf-8") as f:
                json.dump(self.preferences.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info("用户偏好设置已保存")

            # 发送信号
            self.preferences_changed.emit(self.preferences)

            self.accept()

        except Exception as e:
            logger.error(f"保存偏好设置失败: {e}")
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "保存失败", f"无法保存偏好设置：{e}")

    def load_preferences(self):
        """加载偏好设置"""
        try:
            prefs_file = Path("data/user_preferences.json")
            if prefs_file.exists():
                import json

                with open(prefs_file, encoding="utf-8") as f:
                    data = json.load(f)
                self.preferences = UserPreferences.from_dict(data)
                logger.info("已加载用户偏好设置")
        except Exception as e:
            logger.warning(f"加载偏好设置失败: {e}")
            self.preferences = UserPreferences()

    def reset_to_defaults(self):
        """重置为默认值"""
        from PySide6.QtWidgets import QMessageBox

        result = QMessageBox.question(
            self,
            "重置确认",
            "确定要将所有设置重置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            self.preferences = UserPreferences()
            self.load_values_to_ui()
            logger.info("偏好设置已重置为默认值")


def get_user_preferences() -> UserPreferences:
    """获取用户偏好设置"""
    try:
        prefs_file = Path("data/user_preferences.json")
        if prefs_file.exists():
            import json

            with open(prefs_file, encoding="utf-8") as f:
                data = json.load(f)
            return UserPreferences.from_dict(data)
    except Exception as e:
        logger.warning(f"加载偏好设置失败: {e}")

    return UserPreferences()
