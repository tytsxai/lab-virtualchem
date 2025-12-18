"""
动画优化器
优化界面动画性能，提供流畅的用户体验
"""

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer, Signal
from PySide6.QtWidgets import QGraphicsItem, QWidget

logger = logging.getLogger(__name__)


class AnimationOptimizer(QObject):
    """动画优化器"""

    # 动画完成信号
    animation_finished = Signal(str)  # 动画名称
    animation_cancelled = Signal(str)  # 动画名称

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._active_animations: dict[str, QPropertyAnimation] = {}
        self._animation_queue: list[dict[str, Any]] = []
        self._processing_queue = False

        # 性能设置
        self.max_concurrent_animations = 3
        self.animation_duration_ms = 300
        self.fps_limit = 60

        # 统计信息
        self._animation_stats: dict[str, int] = {
            "total_animations": 0,
            "completed_animations": 0,
            "cancelled_animations": 0,
            "failed_animations": 0,
        }

    def create_fade_animation(
        self,
        target: QWidget | QGraphicsItem,
        duration_ms: int | None = None,
        start_opacity: float = 0.0,
        end_opacity: float = 1.0,
        easing: QEasingCurve.Type = QEasingCurve.Type.InOutQuad,
    ) -> QPropertyAnimation:
        """创建淡入淡出动画"""
        duration = duration_ms or self.animation_duration_ms

        animation = QPropertyAnimation(target, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(start_opacity)
        animation.setEndValue(end_opacity)
        animation.setEasingCurve(easing)

        return animation

    def create_scale_animation(
        self,
        target: QWidget | QGraphicsItem,
        duration_ms: int | None = None,
        start_scale: float = 0.0,
        end_scale: float = 1.0,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutBack,
    ) -> QPropertyAnimation:
        """创建缩放动画"""
        duration = duration_ms or self.animation_duration_ms

        animation = QPropertyAnimation(target, b"scale")
        animation.setDuration(duration)
        animation.setStartValue(start_scale)
        animation.setEndValue(end_scale)
        animation.setEasingCurve(easing)

        return animation

    def create_position_animation(
        self,
        target: QWidget | QGraphicsItem,
        duration_ms: int | None = None,
        start_pos: Any = None,
        end_pos: Any = None,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    ) -> QPropertyAnimation:
        """创建位置动画"""
        duration = duration_ms or self.animation_duration_ms

        animation = QPropertyAnimation(target, b"pos")
        animation.setDuration(duration)

        if start_pos is not None:
            animation.setStartValue(start_pos)
        if end_pos is not None:
            animation.setEndValue(end_pos)

        animation.setEasingCurve(easing)

        return animation

    def create_rotation_animation(
        self,
        target: QWidget | QGraphicsItem,
        duration_ms: int | None = None,
        start_angle: float = 0.0,
        end_angle: float = 360.0,
        easing: QEasingCurve.Type = QEasingCurve.Type.InOutQuad,
    ) -> QPropertyAnimation:
        """创建旋转动画"""
        duration = duration_ms or self.animation_duration_ms

        animation = QPropertyAnimation(target, b"rotation")
        animation.setDuration(duration)
        animation.setStartValue(start_angle)
        animation.setEndValue(end_angle)
        animation.setEasingCurve(easing)

        return animation

    def start_animation(
        self,
        name: str,
        animation: QPropertyAnimation,
        on_finished: Callable | None = None,
        on_cancelled: Callable | None = None,
    ) -> bool:
        """启动动画"""
        try:
            # 检查是否已有同名动画
            if name in self._active_animations:
                self.cancel_animation(name)

            # 检查并发动画数量限制
            if len(self._active_animations) >= self.max_concurrent_animations:
                # 添加到队列
                self._animation_queue.append(
                    {
                        "name": name,
                        "animation": animation,
                        "on_finished": on_finished,
                        "on_cancelled": on_cancelled,
                    }
                )
                logger.info(f"动画 {name} 已加入队列")
                return False

            # 连接信号
            animation.finished.connect(lambda: self._on_animation_finished(name))

            # 启动动画
            animation.start()
            self._active_animations[name] = animation

            # 设置回调
            if on_finished:
                self.animation_finished.connect(
                    lambda anim_name: on_finished() if anim_name == name else None
                )
            if on_cancelled:
                self.animation_cancelled.connect(
                    lambda anim_name: on_cancelled() if anim_name == name else None
                )

            self._animation_stats["total_animations"] += 1
            logger.info(f"动画 {name} 已启动")

            return True

        except Exception as e:
            logger.error(f"启动动画失败 {name}: {e}", exc_info=True)
            self._animation_stats["failed_animations"] += 1
            return False

    def cancel_animation(self, name: str) -> bool:
        """取消动画"""
        try:
            if name not in self._active_animations:
                return False

            animation = self._active_animations[name]
            animation.stop()
            animation.deleteLater()

            del self._active_animations[name]
            self._animation_stats["cancelled_animations"] += 1

            self.animation_cancelled.emit(name)
            logger.info(f"动画 {name} 已取消")

            # 处理队列中的下一个动画
            self._process_next_animation()

            return True

        except Exception as e:
            logger.error(f"取消动画失败 {name}: {e}", exc_info=True)
            return False

    def cancel_all_animations(self) -> int:
        """取消所有动画"""
        cancelled_count = 0
        animation_names = list(self._active_animations.keys())

        for name in animation_names:
            if self.cancel_animation(name):
                cancelled_count += 1

        # 清空队列
        self._animation_queue.clear()

        logger.info(f"已取消 {cancelled_count} 个动画")
        return cancelled_count

    def _on_animation_finished(self, name: str) -> None:
        """动画完成回调"""
        try:
            if name in self._active_animations:
                del self._active_animations[name]

            self._animation_stats["completed_animations"] += 1
            self.animation_finished.emit(name)

            logger.info(f"动画 {name} 已完成")

            # 处理队列中的下一个动画
            self._process_next_animation()

        except Exception as e:
            logger.error(f"动画完成回调失败 {name}: {e}", exc_info=True)

    def _process_next_animation(self) -> None:
        """处理队列中的下一个动画"""
        if (
            not self._animation_queue
            or len(self._active_animations) >= self.max_concurrent_animations
        ):
            return

        try:
            # 获取队列中的下一个动画
            animation_data = self._animation_queue.pop(0)

            # 延迟启动，避免阻塞
            QTimer.singleShot(
                50,
                lambda: self.start_animation(
                    animation_data["name"],
                    animation_data["animation"],
                    animation_data["on_finished"],
                    animation_data["on_cancelled"],
                ),
            )

        except Exception as e:
            logger.error(f"处理队列动画失败: {e}", exc_info=True)

    def get_animation_stats(self) -> dict[str, Any]:
        """获取动画统计信息"""
        return {
            "active_animations": len(self._active_animations),
            "queued_animations": len(self._animation_queue),
            "stats": self._animation_stats.copy(),
        }

    def optimize_for_performance(self) -> None:
        """优化动画性能"""
        try:
            # 减少并发动画数量
            if len(self._active_animations) > 2:
                self.max_concurrent_animations = 2

            # 缩短动画时长
            self.animation_duration_ms = min(self.animation_duration_ms, 200)

            # 取消低优先级动画
            low_priority_animations = []
            for name, animation in self._active_animations.items():
                if animation.duration() > 500:  # 超过500ms的动画
                    low_priority_animations.append(name)

            for name in low_priority_animations:
                self.cancel_animation(name)

            logger.info("动画性能优化完成")

        except Exception as e:
            logger.error(f"动画性能优化失败: {e}", exc_info=True)


class SmoothScroller:
    """平滑滚动器"""

    def __init__(self, target_widget: QWidget):
        self.target_widget = target_widget
        self._scroll_timer = QTimer(target_widget)
        self._scroll_timer.timeout.connect(self._scroll_step)
        self._scroll_timer.setSingleShot(False)

        self._target_position = 0
        self._current_position = 0
        self._scroll_speed = 0.1
        self._is_scrolling = False

    def scroll_to(self, position: int, duration_ms: int = 300) -> None:
        """滚动到指定位置"""
        self._target_position = position
        self._scroll_speed = abs(position - self._current_position) / (
            duration_ms / 16.67
        )  # 60 FPS

        if not self._is_scrolling:
            self._is_scrolling = True
            self._scroll_timer.start(16)  # 60 FPS

    def _scroll_step(self) -> None:
        """滚动步骤"""
        if abs(self._target_position - self._current_position) < 1:
            self._current_position = self._target_position
            self._is_scrolling = False
            self._scroll_timer.stop()
        else:
            diff = self._target_position - self._current_position
            self._current_position += diff * self._scroll_speed

        # 执行实际滚动
        if hasattr(self.target_widget, "scroll"):
            self.target_widget.scroll(0, int(self._current_position))
        elif hasattr(self.target_widget, "setValue"):
            self.target_widget.setValue(int(self._current_position))

    def stop(self) -> None:
        """停止滚动"""
        self._is_scrolling = False
        self._scroll_timer.stop()


class AnimationPresets:
    """动画预设"""

    @staticmethod
    def fade_in(
        target: QWidget | QGraphicsItem, duration_ms: int = 300
    ) -> QPropertyAnimation:
        """淡入动画"""
        optimizer = AnimationOptimizer()
        return optimizer.create_fade_animation(target, duration_ms, 0.0, 1.0)

    @staticmethod
    def fade_out(
        target: QWidget | QGraphicsItem, duration_ms: int = 300
    ) -> QPropertyAnimation:
        """淡出动画"""
        optimizer = AnimationOptimizer()
        return optimizer.create_fade_animation(target, duration_ms, 1.0, 0.0)

    @staticmethod
    def scale_in(
        target: QWidget | QGraphicsItem, duration_ms: int = 300
    ) -> QPropertyAnimation:
        """缩放进入动画"""
        optimizer = AnimationOptimizer()
        return optimizer.create_scale_animation(target, duration_ms, 0.0, 1.0)

    @staticmethod
    def scale_out(
        target: QWidget | QGraphicsItem, duration_ms: int = 300
    ) -> QPropertyAnimation:
        """缩放退出动画"""
        optimizer = AnimationOptimizer()
        return optimizer.create_scale_animation(target, duration_ms, 1.0, 0.0)

    @staticmethod
    def slide_in(
        target: QWidget | QGraphicsItem, duration_ms: int = 300
    ) -> QPropertyAnimation:
        """滑入动画"""
        optimizer = AnimationOptimizer()
        return optimizer.create_position_animation(target, duration_ms)

    @staticmethod
    def bounce_in(
        target: QWidget | QGraphicsItem, duration_ms: int = 500
    ) -> QPropertyAnimation:
        """弹跳进入动画"""
        optimizer = AnimationOptimizer()
        animation = optimizer.create_scale_animation(target, duration_ms, 0.0, 1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        return animation


# 全局动画优化器实例
_global_animation_optimizer: AnimationOptimizer | None = None


def get_animation_optimizer() -> AnimationOptimizer:
    """获取全局动画优化器实例"""
    global _global_animation_optimizer
    if _global_animation_optimizer is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        _global_animation_optimizer = (
            AnimationOptimizer(app) if app else AnimationOptimizer()
        )
    return _global_animation_optimizer


def start_animation(
    name: str,
    animation: QPropertyAnimation,
    on_finished: Callable | None = None,
    on_cancelled: Callable | None = None,
) -> bool:
    """启动动画"""
    optimizer = get_animation_optimizer()
    return optimizer.start_animation(name, animation, on_finished, on_cancelled)


def cancel_animation(name: str) -> bool:
    """取消动画"""
    optimizer = get_animation_optimizer()
    return optimizer.cancel_animation(name)


def cancel_all_animations() -> int:
    """取消所有动画"""
    optimizer = get_animation_optimizer()
    return optimizer.cancel_all_animations()
