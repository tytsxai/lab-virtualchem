"""
交互反馈系统
提供动画、音效、视觉反馈等增强用户体验的功能
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QTimer,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsColorizeEffect,
    QGraphicsItem,
    QGraphicsOpacityEffect,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AnimationHelper:
    """动画辅助类"""

    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300) -> None:
        """淡入动画"""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, QByteArray(b"opacity"))
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

        # 保持动画对象引用，防止被垃圾回收
        widget.setProperty("_fade_animation", animation)

        logger.debug(f"淡入动画: {widget}")

    @staticmethod
    def fade_out(
        widget: QWidget, duration: int = 300, callback: Callable[[], None] | None = None
    ) -> None:
        """淡出动画"""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, QByteArray(b"opacity"))
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        if callback:
            animation.finished.connect(callback)

        animation.start()
        widget.setProperty("_fade_animation", animation)

        logger.debug(f"淡出动画: {widget}")

    @staticmethod
    def shake(widget: QWidget, intensity: int = 10, duration: int = 500) -> None:
        """抖动动画（错误提示）"""
        original_pos = widget.pos()

        # 创建序列动画组
        sequence = QSequentialAnimationGroup(widget)

        # 左右抖动5次
        for _ in range(5):
            # 向右
            anim1 = QPropertyAnimation(widget, QByteArray(b"pos"))
            anim1.setDuration(duration // 10)
            anim1.setEndValue(QPoint(original_pos.x() + intensity, original_pos.y()))
            sequence.addAnimation(anim1)

            # 向左
            anim2 = QPropertyAnimation(widget, QByteArray(b"pos"))
            anim2.setDuration(duration // 10)
            anim2.setEndValue(QPoint(original_pos.x() - intensity, original_pos.y()))
            sequence.addAnimation(anim2)

        # 回到原位
        anim_back = QPropertyAnimation(widget, QByteArray(b"pos"))
        anim_back.setDuration(duration // 10)
        anim_back.setEndValue(original_pos)
        sequence.addAnimation(anim_back)

        sequence.start()
        widget.setProperty("_shake_animation", sequence)

        logger.debug(f"抖动动画: {widget}")

    @staticmethod
    def bounce(widget: QWidget, height: int = 20, duration: int = 600) -> None:
        """弹跳动画（成功提示）"""
        original_pos = widget.pos()

        sequence = QSequentialAnimationGroup(widget)

        # 上升
        anim1 = QPropertyAnimation(widget, QByteArray(b"pos"))
        anim1.setDuration(duration // 3)
        anim1.setEndValue(QPoint(original_pos.x(), original_pos.y() - height))
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)
        sequence.addAnimation(anim1)

        # 下降
        anim2 = QPropertyAnimation(widget, QByteArray(b"pos"))
        anim2.setDuration(duration // 3)
        anim2.setEndValue(original_pos)
        anim2.setEasingCurve(QEasingCurve.Type.InQuad)
        sequence.addAnimation(anim2)

        # 小幅反弹
        anim3 = QPropertyAnimation(widget, QByteArray(b"pos"))
        anim3.setDuration(duration // 6)
        anim3.setEndValue(QPoint(original_pos.x(), original_pos.y() - height // 3))
        sequence.addAnimation(anim3)

        # 最终落地
        anim4 = QPropertyAnimation(widget, QByteArray(b"pos"))
        anim4.setDuration(duration // 6)
        anim4.setEndValue(original_pos)
        sequence.addAnimation(anim4)

        sequence.start()
        widget.setProperty("_bounce_animation", sequence)

        logger.debug(f"弹跳动画: {widget}")

    @staticmethod
    def pulse(widget: QWidget, scale_factor: float = 1.1, duration: int = 300) -> None:
        """脉冲动画（强调）"""
        # 使用样式表实现简单的缩放效果
        original_size = widget.size()

        # 放大
        anim1 = QPropertyAnimation(widget, QByteArray(b"minimumSize"))
        anim1.setDuration(duration // 2)
        anim1.setStartValue(original_size)
        anim1.setEndValue(original_size * scale_factor)
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)

        # 缩小
        anim2 = QPropertyAnimation(widget, QByteArray(b"minimumSize"))
        anim2.setDuration(duration // 2)
        anim2.setStartValue(original_size * scale_factor)
        anim2.setEndValue(original_size)
        anim2.setEasingCurve(QEasingCurve.Type.InQuad)

        sequence = QSequentialAnimationGroup(widget)
        sequence.addAnimation(anim1)
        sequence.addAnimation(anim2)
        sequence.start()

        widget.setProperty("_pulse_animation", sequence)

        logger.debug(f"脉冲动画: {widget}")

    @staticmethod
    def highlight_flash(
        widget: QWidget, color: QColor = QColor(255, 255, 0), duration: int = 600
    ) -> None:
        """高亮闪烁效果"""
        effect = QGraphicsColorizeEffect(widget)
        widget.setGraphicsEffect(effect)

        # 颜色强度动画
        animation = QPropertyAnimation(effect, QByteArray(b"strength"))
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setKeyValueAt(0.5, 0.8)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        effect.setColor(color)
        animation.start()

        widget.setProperty("_highlight_animation", animation)

        logger.debug(f"高亮闪烁: {widget}")


class GraphicsItemAnimator:
    """QGraphicsItem动画器"""

    @staticmethod
    def move_to(
        item: QGraphicsItem, target_pos: tuple[float, float], duration: int = 500
    ) -> None:
        """移动到指定位置"""
        from PySide6.QtCore import QPointF

        animation = QPropertyAnimation(item, QByteArray(b"pos"))  # type: ignore[arg-type]
        animation.setDuration(duration)
        animation.setEndValue(QPointF(*target_pos))
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.start()

        # 保持引用
        item.setData(0, animation)

        logger.debug(f"物品移动动画: {item}")

    @staticmethod
    def scale_to(item: QGraphicsItem, scale: float, duration: int = 300) -> None:
        """缩放到指定比例"""
        # 使用scale属性
        animation = QPropertyAnimation(item, QByteArray(b"scale"))  # type: ignore[arg-type]
        animation.setDuration(duration)
        animation.setEndValue(scale)
        animation.setEasingCurve(QEasingCurve.Type.OutElastic)
        animation.start()

        item.setData(1, animation)

        logger.debug(f"物品缩放动画: {item}")

    @staticmethod
    def rotate_to(item: QGraphicsItem, angle: float, duration: int = 400) -> None:
        """旋转到指定角度"""
        animation = QPropertyAnimation(item, QByteArray(b"rotation"))  # type: ignore[arg-type]
        animation.setDuration(duration)
        animation.setEndValue(angle)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

        item.setData(2, animation)

        logger.debug(f"物品旋转动画: {item}")


class FeedbackManager:
    """反馈管理器 - 统一管理各种反馈效果"""

    def __init__(self) -> None:
        self.sound_enabled = True
        self.animation_enabled = True
        self.vibration_enabled = False

    def on_success(self, widget: QWidget) -> None:
        """成功反馈"""
        if self.animation_enabled:
            AnimationHelper.bounce(widget)
            AnimationHelper.highlight_flash(widget, QColor(0, 255, 0))

        # 播放成功音效（如果启用）
        if self.sound_enabled:
            self._play_sound("success")

        logger.info("成功反馈")

    def on_error(self, widget: QWidget) -> None:
        """错误反馈"""
        if self.animation_enabled:
            AnimationHelper.shake(widget)
            AnimationHelper.highlight_flash(widget, QColor(255, 0, 0))

        if self.sound_enabled:
            self._play_sound("error")

        logger.info("错误反馈")

    def on_warning(self, widget: QWidget) -> None:
        """警告反馈"""
        if self.animation_enabled:
            AnimationHelper.pulse(widget)
            AnimationHelper.highlight_flash(widget, QColor(255, 165, 0))

        if self.sound_enabled:
            self._play_sound("warning")

        logger.info("警告反馈")

    def on_info(self, widget: QWidget) -> None:
        """信息反馈"""
        if self.animation_enabled:
            AnimationHelper.fade_in(widget)

        logger.info("信息反馈")

    def on_item_picked(self, item: QGraphicsItem) -> None:
        """拾取物品反馈"""
        if self.animation_enabled:
            GraphicsItemAnimator.scale_to(item, 1.2)
            QTimer.singleShot(150, lambda: GraphicsItemAnimator.scale_to(item, 1.0))

        if self.sound_enabled:
            self._play_sound("pick")

        logger.debug("拾取物品反馈")

    def on_item_dropped(self, item: QGraphicsItem) -> None:
        """放下物品反馈"""
        if self.animation_enabled:
            GraphicsItemAnimator.scale_to(item, 0.9)
            QTimer.singleShot(100, lambda: GraphicsItemAnimator.scale_to(item, 1.0))

        if self.sound_enabled:
            self._play_sound("drop")

        logger.debug("放下物品反馈")

    def on_item_clicked(self, item: QGraphicsItem) -> None:
        """点击物品反馈"""
        if self.animation_enabled:
            GraphicsItemAnimator.scale_to(item, 1.1)
            QTimer.singleShot(100, lambda: GraphicsItemAnimator.scale_to(item, 1.0))

        if self.sound_enabled:
            self._play_sound("click")

        logger.debug("点击物品反馈")

    def _play_sound(self, sound_type: str) -> None:
        """播放音效"""
        try:
            # 尝试使用 QSoundEffect
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QSoundEffect

            # 音效文件映射
            sound_files = {
                "click": "assets/sounds/click.wav",
                "success": "assets/sounds/success.wav",
                "error": "assets/sounds/error.wav",
                "hover": "assets/sounds/hover.wav",
                "drop": "assets/sounds/drop.wav",
            }

            sound_file = sound_files.get(sound_type, "assets/sounds/click.wav")
            sound_path = Path(sound_file)

            if sound_path.exists():
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(sound_path.absolute())))
                effect.setVolume(0.5)
                effect.play()
                logger.debug(f"播放音效: {sound_type}")
            else:
                # 如果文件不存在，使用系统提示音
                self._play_system_sound(sound_type)

        except ImportError:
            # QSoundEffect 不可用时使用系统提示音
            self._play_system_sound(sound_type)
        except Exception as e:
            logger.error(f"播放音效失败: {e}")
            self._play_system_sound(sound_type)

    def _play_system_sound(self, sound_type: str) -> None:
        """播放系统提示音"""
        try:
            import platform
            import subprocess

            system = platform.system()

            if system == "Windows":
                # Windows 系统音效
                sound_map = {
                    "click": "SystemAsterisk",
                    "success": "SystemExclamation",
                    "error": "SystemHand",
                    "hover": "SystemQuestion",
                    "drop": "SystemDefault",
                }
                sound_map.get(sound_type, "SystemDefault")
                subprocess.run(
                    ["powershell", "-c", "[console]::beep(800, 100)"],
                    capture_output=True,
                )
            elif system == "Darwin":  # macOS
                subprocess.run(
                    ["afplay", "/System/Library/Sounds/Glass.aiff"], capture_output=True
                )
            else:  # Linux
                subprocess.run(
                    ["paplay", "/usr/share/sounds/alsa/Front_Left.wav"],
                    capture_output=True,
                )

            logger.debug(f"播放系统音效: {sound_type}")

        except Exception as e:
            logger.error(f"播放系统音效失败: {e}")


class VisualEffects:
    """视觉效果工具类"""

    @staticmethod
    def create_particle_effect(widget: QWidget, particle_count: int = 20) -> None:
        """创建粒子效果"""
        try:
            import random

            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QBrush, QColor
            from PySide6.QtWidgets import (
                QGraphicsEllipseItem,
                QGraphicsScene,
                QGraphicsView,
            )

            # 创建粒子场景
            scene = QGraphicsScene()
            view = QGraphicsView(scene)
            view.setParent(widget)
            view.setGeometry(widget.rect())
            view.setStyleSheet("background: transparent; border: none;")

            particles = []

            # 创建粒子
            for _i in range(particle_count):
                # 随机位置
                x = random.randint(0, widget.width())
                y = random.randint(0, widget.height())

                # 随机大小
                size = random.randint(3, 8)

                # 创建粒子
                particle = QGraphicsEllipseItem(0, 0, size, size)
                particle.setPos(x, y)

                # 随机颜色
                color = QColor(
                    random.randint(100, 255),
                    random.randint(100, 255),
                    random.randint(100, 255),
                    150,
                )
                particle.setBrush(QBrush(color))

                scene.addItem(particle)
                particles.append(particle)

            # 动画效果
            def animate_particles() -> None:
                for particle in particles:
                    # 随机移动
                    dx = random.randint(-5, 5)
                    dy = random.randint(-5, 5)

                    current_pos = particle.pos()
                    new_x = max(0, min(widget.width(), current_pos.x() + dx))
                    new_y = max(0, min(widget.height(), current_pos.y() + dy))

                    particle.setPos(new_x, new_y)

                    # 透明度变化
                    current_brush = particle.brush()
                    current_color = current_brush.color()
                    alpha = max(0, current_color.alpha() - 2)
                    current_color.setAlpha(alpha)
                    particle.setBrush(QBrush(current_color))

            # 定时器：绑定 parent，避免视图提前销毁后仍触发 timeout
            timer = QTimer(view)
            timer.timeout.connect(animate_particles)
            timer.start(50)  # 20 FPS

            # 自动清理
            def cleanup() -> None:
                timer.stop()
                view.deleteLater()
                scene.deleteLater()

            # 绑定 receiver，若 view 已销毁则不会再回调 cleanup
            QTimer.singleShot(2000, view, cleanup)  # 2秒后清理

            logger.debug(f"创建粒子效果: {particle_count} 个粒子")

        except Exception as e:
            logger.error(f"创建粒子效果失败: {e}")
            # 降级到简单的视觉效果
            VisualEffects.create_glow_effect(widget)

    @staticmethod
    def create_trail_effect(item: QGraphicsItem, trail_length: int = 5) -> None:
        """创建拖尾效果"""
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QBrush, QColor, QPen
            from PySide6.QtWidgets import QGraphicsEllipseItem

            # 获取场景
            scene = item.scene()
            if not scene:
                return

            # 创建拖尾粒子
            trail_particles = []

            for i in range(trail_length):
                # 创建拖尾粒子
                particle = QGraphicsEllipseItem(0, 0, 4, 4)
                particle.setPos(item.pos())

                # 设置颜色（逐渐变淡）
                alpha = int(255 * (1 - i / trail_length))
                color = QColor(100, 150, 255, alpha)
                particle.setBrush(QBrush(color))
                particle.setPen(QPen(QColor(100, 150, 255, alpha)))

                scene.addItem(particle)
                trail_particles.append(particle)

            # 动画效果
            def update_trail() -> None:
                # 更新拖尾位置
                for i, particle in enumerate(trail_particles):
                    if i == 0:
                        # 第一个粒子跟随主物体
                        particle.setPos(item.pos())
                    else:
                        # 其他粒子跟随前一个粒子
                        prev_particle = trail_particles[i - 1]
                        particle.setPos(prev_particle.pos())

                    # 更新透明度
                    current_brush = particle.brush()
                    current_color = current_brush.color()
                    alpha = max(0, current_color.alpha() - 5)
                    current_color.setAlpha(alpha)
                    particle.setBrush(QBrush(current_color))
                    particle.setPen(QPen(QColor(100, 150, 255, alpha)))

            # 定时器：绑定 parent，避免 scene 生命周期结束后仍触发 timeout
            timer = QTimer(scene)
            timer.timeout.connect(update_trail)
            timer.start(30)  # 30ms 更新一次

            # 自动清理
            def cleanup() -> None:
                timer.stop()
                for particle in trail_particles:
                    scene.removeItem(particle)

            # 绑定 receiver，若 scene 已销毁则不会再回调 cleanup
            QTimer.singleShot(1000, scene, cleanup)  # 1秒后清理

            logger.debug(f"创建拖尾效果: 长度 {trail_length}")

        except Exception as e:
            logger.error(f"创建拖尾效果失败: {e}")

    @staticmethod
    def create_glow_effect(
        widget: QWidget, color: QColor = QColor(0, 255, 255)
    ) -> None:
        """创建发光效果"""
        # 使用阴影效果模拟发光
        from PySide6.QtWidgets import QGraphicsDropShadowEffect

        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(20)
        effect.setColor(color)
        effect.setOffset(0, 0)
        widget.setGraphicsEffect(effect)

        logger.debug(f"创建发光效果: {color.name()}")


# 全局反馈管理器实例
_feedback_manager: FeedbackManager | None = None


def get_feedback_manager() -> FeedbackManager:
    """获取全局反馈管理器"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager
