"""
化学反应动画效果
实现颜色变化、气泡、烟雾等视觉效果
"""

from __future__ import annotations

import math
import random
from typing import Any

from PySide6.QtCore import QObject, QRectF, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsScene

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Particle:
    """粒子类"""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        life: float = 1.0,
        color: QColor = QColor(255, 255, 255),
        size: float = 2.0,
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt: float) -> bool:
        """更新粒子状态"""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

        # 重力效果
        self.vy += 50.0 * dt

        # 空气阻力
        self.vx *= 0.99
        self.vy *= 0.99

        return self.life > 0

    def get_alpha(self) -> int:
        """获取透明度"""
        return int(255 * (self.life / self.max_life))


class BubbleParticle(Particle):
    """气泡粒子"""

    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            vx=(random.random() - 0.5) * 20.0,
            vy=-50.0 - random.random() * 30.0,
            life=2.0 + random.random(),
            color=QColor(200, 230, 255, 150),
            size=3.0 + random.random() * 3.0,
        )


class SmokeParticle(Particle):
    """烟雾粒子"""

    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            vx=(random.random() - 0.5) * 10.0,
            vy=-20.0 - random.random() * 10.0,
            life=3.0 + random.random() * 2.0,
            color=QColor(200, 200, 200, 100),
            size=2.0 + random.random() * 2.0,
        )


class ColorTransition:
    """颜色过渡效果"""

    def __init__(self, start_color: QColor, end_color: QColor, duration: float = 1.0):
        self.start_color = start_color
        self.end_color = end_color
        self.duration = duration
        self.elapsed = 0.0
        self.active = True

    def update(self, dt: float) -> QColor:
        """更新颜色过渡"""
        if not self.active:
            return self.end_color

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        if progress >= 1.0:
            self.active = False
            return self.end_color

        # 线性插值
        r = int(
            self.start_color.red()
            + (self.end_color.red() - self.start_color.red()) * progress
        )
        g = int(
            self.start_color.green()
            + (self.end_color.green() - self.start_color.green()) * progress
        )
        b = int(
            self.start_color.blue()
            + (self.end_color.blue() - self.start_color.blue()) * progress
        )
        a = int(
            self.start_color.alpha()
            + (self.end_color.alpha() - self.start_color.alpha()) * progress
        )

        return QColor(r, g, b, a)


class ReactionAnimation(QObject):
    """化学反应动画效果"""

    # 信号
    animation_completed = Signal(str)  # 动画ID
    color_updated = Signal(str, QColor)  # 动画ID, 当前颜色

    def __init__(self) -> None:
        super().__init__()

        # 粒子系统
        self.particles: list[Particle] = []

        # 颜色过渡
        self.color_transitions: dict[str, ColorTransition] = {}

        # 动画计时器
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animations)
        self.animation_timer.setInterval(16)  # 60 FPS

        # 场景引用
        self.scene: QGraphicsScene | None = None

        logger.info("反应动画系统初始化完成")

    def set_scene(self, scene: QGraphicsScene) -> None:
        """设置场景"""
        self.scene = scene

    def start_color_transition(
        self,
        animation_id: str,
        start_color: QColor,
        end_color: QColor,
        duration: float = 1.0,
    ) -> None:
        """开始颜色过渡动画"""
        self.color_transitions[animation_id] = ColorTransition(
            start_color, end_color, duration
        )
        logger.info(f"开始颜色过渡动画: {animation_id}")

    def create_bubble_effect(self, x: float, y: float, count: int = 10) -> None:
        """创建气泡效果"""
        for _ in range(count):
            bubble = BubbleParticle(x, y)
            self.particles.append(bubble)
        logger.info(f"创建气泡效果: {count} 个气泡")

    def create_smoke_effect(self, x: float, y: float, count: int = 15) -> None:
        """创建烟雾效果"""
        for _ in range(count):
            smoke = SmokeParticle(x, y)
            self.particles.append(smoke)
        logger.info(f"创建烟雾效果: {count} 个烟雾粒子")

    def create_explosion_effect(self, x: float, y: float, count: int = 20) -> None:
        """创建爆炸效果"""
        for _ in range(count):
            # 随机方向
            angle = random.random() * 2 * math.pi
            speed = 50.0 + random.random() * 50.0

            particle = Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=1.0 + random.random(),
                color=QColor(255, 100, 0, 200),
                size=2.0 + random.random() * 3.0,
            )
            self.particles.append(particle)
        logger.info(f"创建爆炸效果: {count} 个粒子")

    def start_animation(self) -> None:
        """开始动画"""
        self.animation_timer.start()
        logger.info("开始动画")

    def stop_animation(self) -> None:
        """停止动画"""
        self.animation_timer.stop()
        logger.info("停止动画")

    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停止定时器
            if self.animation_timer.isActive():
                self.animation_timer.stop()

            # 清理粒子
            self.particles.clear()

            # 清理颜色过渡
            self.color_transitions.clear()

            # 断开场景引用
            self.scene = None

            logger.info("反应动画资源已清理")
        except Exception as e:
            logger.error(f"清理反应动画资源失败: {e}", exc_info=True)

    def _update_animations(self) -> None:
        """更新动画"""
        dt = 0.016  # 16ms = 1/60秒

        # 更新粒子
        self.particles = [p for p in self.particles if p.update(dt)]

        # 更新颜色过渡
        completed_transitions = []
        for animation_id, transition in self.color_transitions.items():
            if not transition.active:
                completed_transitions.append(animation_id)
            else:
                # 更新颜色并发送信号
                current_color = transition.update(dt)
                self.color_updated.emit(animation_id, current_color)

        # 清理完成的过渡
        for animation_id in completed_transitions:
            del self.color_transitions[animation_id]
            self.animation_completed.emit(animation_id)

        # 重绘场景
        if self.scene:
            self.scene.update()

    def draw_particles(self, painter: QPainter) -> None:
        """绘制粒子"""
        for particle in self.particles:
            alpha = particle.get_alpha()
            color = QColor(particle.color)
            color.setAlpha(alpha)

            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(
                int(particle.x - particle.size),
                int(particle.y - particle.size),
                int(particle.size * 2),
                int(particle.size * 2),
            )

    def get_current_color(self, animation_id: str) -> QColor | None:
        """获取当前颜色"""
        transition = self.color_transitions.get(animation_id)
        if transition:
            return transition.update(0.016)  # 假设16ms更新
        return None

    def clear_all_effects(self) -> None:
        """清除所有效果"""
        self.particles.clear()
        self.color_transitions.clear()
        logger.info("清除所有动画效果")


class AnimatedContainer(QGraphicsPixmapItem):
    """带动画效果的容器"""

    def __init__(
        self,
        container_id: str,
        pixmap: Any | None = None,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(pixmap, parent)
        self.container_id = container_id
        self.current_color = QColor(255, 255, 255)
        self.target_color = QColor(255, 255, 255)
        self.animation_speed = 0.05

        # 动画效果
        self.bubble_timer = QTimer()
        self.bubble_timer.timeout.connect(self._create_bubbles)
        self.bubble_timer.setInterval(200)  # 每200ms创建气泡

        self.showing_bubbles = False

    def set_target_color(self, color: QColor) -> None:
        """设置目标颜色"""
        self.target_color = color

    def start_bubble_effect(self) -> None:
        """开始气泡效果"""
        self.showing_bubbles = True
        # QGraphicsItem 不是 QObject，无法作为 parent；尽量绑定到所属 scene，避免无主定时器长期存活。
        if self.bubble_timer.parent() is None and self.scene() is not None:
            self.bubble_timer.setParent(self.scene())
        self.bubble_timer.start()

    def stop_bubble_effect(self) -> None:
        """停止气泡效果"""
        self.showing_bubbles = False
        self.bubble_timer.stop()

    def _create_bubbles(self) -> None:
        """创建气泡"""
        scene = self.scene()
        if not scene:
            # 物体已不在场景中，停止定时器避免空转与潜在回调风险
            self.bubble_timer.stop()
            self.showing_bubbles = False
            return

        if self.showing_bubbles:
            # 在容器底部创建气泡
            rect = self.boundingRect()
            x = rect.center().x()
            y = rect.bottom() - 10

            # 获取动画系统
            if hasattr(self.scene(), "reaction_animation"):
                self.scene().reaction_animation.create_bubble_effect(x, y, 3)

    def paint(self, painter: QPainter, option: Any, widget: Any = None) -> None:
        """绘制容器"""
        # 更新颜色
        self.current_color = self._interpolate_color(
            self.current_color, self.target_color, self.animation_speed
        )

        # 绘制容器
        super().paint(painter, option, widget)

        # 绘制液体
        if self.current_color.alpha() > 0:
            rect = self.boundingRect()
            liquid_rect = QRectF(
                rect.x() + 5,
                rect.y() + rect.height() * 0.3,
                rect.width() - 10,
                rect.height() * 0.4,
            )

            painter.setBrush(QBrush(self.current_color))
            painter.setPen(QPen(self.current_color))
            painter.drawRect(liquid_rect)

    def _interpolate_color(self, start: QColor, end: QColor, speed: float) -> QColor:
        """颜色插值"""
        r = int(start.red() + (end.red() - start.red()) * speed)
        g = int(start.green() + (end.green() - start.green()) * speed)
        b = int(start.blue() + (end.blue() - start.blue()) * speed)
        a = int(start.alpha() + (end.alpha() - start.alpha()) * speed)

        return QColor(r, g, b, a)
