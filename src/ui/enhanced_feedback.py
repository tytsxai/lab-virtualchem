"""
增强反馈系统
提供视觉、音效和触觉反馈的综合体验
"""

from __future__ import annotations

import random
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPointF,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect
from PySide6.QtWidgets import (
    QGraphicsColorizeEffect,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsOpacityEffect,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackType(Enum):
    """反馈类型"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PICKUP = "pickup"
    DROP = "drop"
    COLLISION = "collision"
    ACHIEVEMENT = "achievement"
    LEVEL_UP = "level_up"


class AnimationType(Enum):
    """动画类型"""

    SCALE = "scale"
    FADE = "fade"
    SHAKE = "shake"
    BOUNCE = "bounce"
    GLOW = "glow"
    PULSE = "pulse"
    PARTICLE = "particle"


class FeedbackManager(QObject):
    """反馈管理器 - 单例模式"""

    _instance: FeedbackManager | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True
            self.feedback_system = EnhancedFeedbackSystem()

    @classmethod
    def instance(cls) -> FeedbackManager:
        """获取实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def show_feedback(self, widget, feedback_type, animation_type=None, **kwargs):
        """显示反馈"""
        return self.feedback_system.show_feedback(widget, feedback_type, animation_type, **kwargs)

    def play_sound(self, feedback_type):
        """播放音效"""
        return self.feedback_system.play_sound(feedback_type)

    def animate_widget(self, widget, animation_type, **kwargs):
        """动画化控件"""
        return self.feedback_system.animate_widget(widget, animation_type, **kwargs)

    def create_particle_effect(self, scene, center, color, **kwargs):
        """创建粒子效果"""
        return self.feedback_system.create_particle_effect(scene, center, color, **kwargs)

    def cleanup(self):
        """清理资源"""
        return self.feedback_system.cleanup()


class EnhancedFeedbackSystem(QObject):
    """增强反馈系统"""

    # 信号
    feedback_started = Signal(str)  # 反馈类型
    feedback_completed = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 音效系统
        self.sound_enabled = True
        self.sound_volume = 0.7
        self.sound_effects: dict[str, QSoundEffect] = {}

        # 音乐播放器
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(self.sound_volume)
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)

        # 动画组
        self.active_animations: list[QPropertyAnimation] = []

        # 粒子效果缓存
        self.particle_cache: list[QGraphicsItem] = []

        # 加载音效
        self._load_sound_effects()

        logger.info("增强反馈系统初始化完成")

    def _load_sound_effects(self) -> None:
        """加载音效文件"""
        sound_dir = Path("assets/sounds")

        # 默认音效映射
        sound_files = {
            FeedbackType.SUCCESS: "success.wav",
            FeedbackType.ERROR: "error.wav",
            FeedbackType.WARNING: "warning.wav",
            FeedbackType.INFO: "info.wav",
            FeedbackType.PICKUP: "pickup.wav",
            FeedbackType.DROP: "drop.wav",
            FeedbackType.COLLISION: "collision.wav",
            FeedbackType.ACHIEVEMENT: "achievement.wav",
            FeedbackType.LEVEL_UP: "levelup.wav",
        }

        for feedback_type, filename in sound_files.items():
            filepath = sound_dir / filename
            if filepath.exists():
                effect = QSoundEffect()
                effect.setSource(filepath.as_uri())
                effect.setVolume(self.sound_volume)
                self.sound_effects[feedback_type.value] = effect
                logger.debug(f"加载音效: {filename}")

    def play_sound(self, feedback_type: FeedbackType) -> None:
        """播放音效"""
        if not self.sound_enabled:
            return

        if feedback_type.value in self.sound_effects:
            self.sound_effects[feedback_type.value].play()
            logger.debug(f"播放音效: {feedback_type.value}")

    def set_sound_enabled(self, enabled: bool) -> None:
        """设置音效开关"""
        self.sound_enabled = enabled
        logger.info(f"音效已{'启用' if enabled else '禁用'}")

    def set_sound_volume(self, volume: float) -> None:
        """设置音量 (0.0-1.0)"""
        self.sound_volume = max(0.0, min(1.0, volume))
        self.audio_output.setVolume(self.sound_volume)

        for effect in self.sound_effects.values():
            effect.setVolume(self.sound_volume)

        logger.info(f"音量已设置为: {self.sound_volume:.1%}")

    def animate_widget(self, widget: QWidget, animation_type: AnimationType, duration: int = 300) -> None:
        """为组件添加动画效果"""
        if animation_type == AnimationType.SCALE:
            self._animate_scale(widget, duration)
        elif animation_type == AnimationType.FADE:
            self._animate_fade(widget, duration)
        elif animation_type == AnimationType.SHAKE:
            self._animate_shake(widget, duration)
        elif animation_type == AnimationType.BOUNCE:
            self._animate_bounce(widget, duration)
        elif animation_type == AnimationType.GLOW:
            self._animate_glow(widget, duration)
        elif animation_type == AnimationType.PULSE:
            self._animate_pulse(widget, duration)

    def _animate_scale(self, widget: QWidget, duration: int) -> None:
        """缩放动画"""
        # 创建缩放效果的动画组
        anim_group = QSequentialAnimationGroup()

        # 放大
        scale_up = QPropertyAnimation(widget, b"maximumSize")
        scale_up.setDuration(duration // 2)
        scale_up.setStartValue(widget.size())
        scale_up.setEndValue(widget.size() * 1.1)
        scale_up.setEasingCurve(QEasingCurve.Type.OutQuad)

        # 恢复
        scale_down = QPropertyAnimation(widget, b"maximumSize")
        scale_down.setDuration(duration // 2)
        scale_down.setStartValue(widget.size() * 1.1)
        scale_down.setEndValue(widget.size())
        scale_down.setEasingCurve(QEasingCurve.Type.InQuad)

        anim_group.addAnimation(scale_up)
        anim_group.addAnimation(scale_down)
        anim_group.start()

        # Note: 存储动画以防止被垃圾回收
        self.active_animations.append(scale_up)

    def _animate_fade(self, widget: QWidget, duration: int) -> None:
        """淡入淡出动画"""
        effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 动画结束后恢复
        def clear_effect() -> None:
            if widget:
                widget.setGraphicsEffect(None)  # type: ignore

        anim.finished.connect(clear_effect)
        anim.start()

        self.active_animations.append(anim)

    def _animate_shake(self, widget: QWidget, duration: int) -> None:
        """抖动动画"""
        from PySide6.QtCore import QPoint

        original_pos = widget.pos()
        shake_distance = 10

        anim_group = QSequentialAnimationGroup()

        # 左右抖动
        for _ in range(4):
            offset = shake_distance if _ % 2 == 0 else -shake_distance

            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(duration // 4)
            anim.setStartValue(widget.pos())
            anim.setEndValue(original_pos + QPoint(offset, 0))
            anim.setEasingCurve(QEasingCurve.Type.OutInQuad)

            anim_group.addAnimation(anim)

        # 恢复原位
        restore = QPropertyAnimation(widget, b"pos")
        restore.setDuration(duration // 4)
        restore.setEndValue(original_pos)
        anim_group.addAnimation(restore)

        anim_group.start()
        self.active_animations.append(restore)

    def _animate_bounce(self, widget: QWidget, duration: int) -> None:
        """弹跳动画"""
        from PySide6.QtCore import QPoint

        original_pos = widget.pos()
        bounce_height = 20

        anim_group = QSequentialAnimationGroup()

        # 上升
        rise = QPropertyAnimation(widget, b"pos")
        rise.setDuration(duration // 2)
        rise.setStartValue(original_pos)
        rise.setEndValue(original_pos - QPoint(0, bounce_height))
        rise.setEasingCurve(QEasingCurve.Type.OutQuad)

        # 下落
        fall = QPropertyAnimation(widget, b"pos")
        fall.setDuration(duration // 2)
        fall.setStartValue(original_pos - QPoint(0, bounce_height))
        fall.setEndValue(original_pos)
        fall.setEasingCurve(QEasingCurve.Type.OutBounce)

        anim_group.addAnimation(rise)
        anim_group.addAnimation(fall)
        anim_group.start()

        self.active_animations.append(fall)

    def _animate_glow(self, widget: QWidget, duration: int) -> None:
        """发光动画"""
        # 创建阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(52, 152, 219, 200))
        shadow.setOffset(0, 0)
        widget.setGraphicsEffect(shadow)

        # 动画改变模糊半径
        anim = QPropertyAnimation(shadow, b"blurRadius")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(30)
        anim.setLoopCount(2)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 动画结束后移除效果
        def clear_effect() -> None:
            if widget:
                widget.setGraphicsEffect(None)  # type: ignore

        anim.finished.connect(clear_effect)
        anim.start()

        self.active_animations.append(anim)

    def _animate_pulse(self, widget: QWidget, duration: int) -> None:
        """脉冲动画"""
        colorize = QGraphicsColorizeEffect()
        colorize.setColor(QColor(52, 152, 219))
        widget.setGraphicsEffect(colorize)

        anim = QPropertyAnimation(colorize, b"strength")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(0.8)
        anim.setLoopCount(2)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def clear_effect() -> None:
            if widget:
                widget.setGraphicsEffect(None)  # type: ignore

        anim.finished.connect(clear_effect)
        anim.start()

        self.active_animations.append(anim)

    def show_feedback(
        self,
        widget: QWidget,
        feedback_type: FeedbackType,
        animation_type: AnimationType = AnimationType.PULSE,
        duration: int = 300,
        with_sound: bool = True,
    ) -> None:
        """显示综合反馈"""
        # 发送开始信号
        self.feedback_started.emit(feedback_type.value)

        # 播放音效
        if with_sound:
            self.play_sound(feedback_type)

        # 显示动画
        self.animate_widget(widget, animation_type, duration)

        # 延迟发送完成信号
        QTimer.singleShot(duration, lambda: self.feedback_completed.emit(feedback_type.value))

        logger.debug(f"显示反馈: {feedback_type.value} - {animation_type.value}")

    def create_particle_effect(
        self,
        scene: Any,  # QGraphicsScene
        position: QPointF,
        color: QColor,
        count: int = 20,
        duration: int = 1000,
    ) -> None:
        """创建粒子效果"""
        from PySide6.QtWidgets import QGraphicsEllipseItem

        for _ in range(count):
            # 创建粒子
            size = random.randint(3, 8)
            particle = QGraphicsEllipseItem(0, 0, size, size)
            particle.setBrush(color)
            particle.setPen(Qt.PenStyle.NoPen)
            particle.setPos(position)

            # 随机方向和距离
            angle = random.uniform(0, 360)
            distance = random.uniform(30, 100)

            import math

            end_x = position.x() + distance * math.cos(math.radians(angle))
            end_y = position.y() + distance * math.sin(math.radians(angle))

            # 创建动画组
            anim_group = QParallelAnimationGroup()

            # 位置动画 - 简化处理
            pos_anim = QPropertyAnimation(anim_group)
            pos_anim.setDuration(duration)
            pos_anim.setStartValue(position)
            pos_anim.setEndValue(QPointF(end_x, end_y))
            pos_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

            # 透明度动画
            opacity_effect = QGraphicsOpacityEffect()
            particle.setGraphicsEffect(opacity_effect)
            opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
            opacity_anim.setDuration(duration)
            opacity_anim.setStartValue(1.0)
            opacity_anim.setEndValue(0.0)

            anim_group.addAnimation(opacity_anim)

            # 动画结束后移除粒子
            def remove_particle(p: Any = particle, s: Any = scene) -> None:
                if s and p:
                    s.removeItem(p)

            anim_group.finished.connect(remove_particle)

            # 添加到场景
            scene.addItem(particle)
            anim_group.start()

            self.active_animations.append(opacity_anim)

        logger.debug(f"创建粒子效果: {count}个粒子")

    def show_success_effect(self, widget: QWidget, message: str = "成功！") -> None:
        """显示成功效果"""
        self.show_feedback(widget, FeedbackType.SUCCESS, AnimationType.BOUNCE, duration=400, with_sound=True)

        # 可以添加一个临时标签显示消息
        from PySide6.QtWidgets import QLabel

        label = QLabel(message, widget)
        label.setStyleSheet(
            """
                QLabel {
                background-color: #27ae60;
                    color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12pt;
                font-weight: bold;
                }
            """
        )
        label.adjustSize()
        label.move((widget.width() - label.width()) // 2, (widget.height() - label.height()) // 2)
        label.show()

        # 淡出并移除
        QTimer.singleShot(1500, label.deleteLater)

    def show_error_effect(self, widget: QWidget, message: str = "错误！") -> None:
        """显示错误效果"""
        self.show_feedback(widget, FeedbackType.ERROR, AnimationType.SHAKE, duration=400, with_sound=True)

        from PySide6.QtWidgets import QLabel

        label = QLabel(message, widget)
        label.setStyleSheet(
            """
            QLabel {
                background-color: #e74c3c;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12pt;
                font-weight: bold;
            }
        """
        )
        label.adjustSize()
        label.move((widget.width() - label.width()) // 2, (widget.height() - label.height()) // 2)
        label.show()

        QTimer.singleShot(1500, label.deleteLater)

    def show_achievement_effect(self, widget: QWidget, achievement_name: str, scene: Any | None = None) -> None:
        """显示成就解锁效果"""
        self.play_sound(FeedbackType.ACHIEVEMENT)

        # 发光动画
        self.animate_widget(widget, AnimationType.GLOW, duration=1000)

        # 粒子效果
        if scene:
            center = QPointF(widget.width() / 2, widget.height() / 2)
            self.create_particle_effect(
                scene,
                center,
                QColor(255, 215, 0),  # 金色
                count=30,
                duration=1500,
            )

        logger.info(f"显示成就效果: {achievement_name}")

    def cleanup(self) -> None:
        """清理资源"""
        # 停止所有动画
        for anim in self.active_animations:
            if anim.state() == QPropertyAnimation.State.Running:
                anim.stop()

        self.active_animations.clear()

        # 停止音效
        self.media_player.stop()

        logger.info("反馈系统已清理")
