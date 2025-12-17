"""
游戏化交互系统
提供类似平面游戏的交互体验，包括物理模拟、手势控制、动画效果等
"""

from __future__ import annotations

import math
import os
import random
import time
from enum import Enum
from typing import Any

from PySide6.QtCore import (
    QAnimationGroup,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PhysicsState(str, Enum):
    """物理状态"""

    STATIC = "static"
    MOVING = "moving"
    FALLING = "falling"
    BOUNCING = "bouncing"
    ROTATING = "rotating"


class InteractionType(str, Enum):
    """交互类型"""

    DRAG = "drag"
    CLICK = "click"
    SWIPE = "swipe"
    PINCH = "pinch"
    SHAKE = "shake"
    TILT = "tilt"


class _ItemSignal:
    """最简信号实现,用于在非QObject对象上转发事件"""

    def __init__(self) -> None:
        self._subscribers: list[Any] = []

    def connect(self, callback: Any) -> None:
        """注册回调"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def disconnect(self, callback: Any) -> None:
        """注销回调"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        """触发事件"""
        for callback in list(self._subscribers):
            try:
                callback(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - 记录但不影响主流程
                logger.warning("信号回调执行失败: %s", exc, exc_info=True)


class GamePhysicsItem(QGraphicsPixmapItem):
    """具有物理属性的游戏物品"""

    def __init__(
        self,
        item_id: str,
        item_type: str,
        pixmap: QPixmap | None = None,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(pixmap if pixmap else QPixmap(), parent)

        self.item_id = item_id
        self.item_type = item_type
        self.physics_state_changed: _ItemSignal = _ItemSignal()
        self.collision_detected: _ItemSignal = _ItemSignal()
        self.interaction_started: _ItemSignal = _ItemSignal()
        self.interaction_completed: _ItemSignal = _ItemSignal()

        # 物理属性
        self.mass = 1.0
        self.velocity = QPointF(0, 0)
        self.acceleration = QPointF(0, 0)
        self.friction = 0.95
        self.bounce_factor = 0.7
        self.gravity = QPointF(0, 0.5)
        self.physics_state = PhysicsState.STATIC

        # 交互属性
        self.is_interactive = True
        self.is_draggable = True
        self.is_clickable = True
        self.is_swipeable = True
        self.interaction_threshold = 10.0

        # 动画属性
        self.animation_group: QAnimationGroup | None = None
        self.current_animation: QPropertyAnimation | None = None

        # 碰撞检测
        self.collision_shape = "circle"  # circle, rectangle, polygon
        self.collision_radius = 50.0

        # 游戏化属性
        self.rarity = "common"  # common, uncommon, rare, epic, legendary
        self.glow_color = QColor(100, 200, 255, 100)
        self.particle_effect = None

        # 设置标志
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        # 接受鼠标事件
        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )

        # 工具提示
        self.setToolTip(f"{item_type}: {item_id}")

        logger.debug(f"创建游戏物理物品: {item_id} ({item_type})")

    def update_physics(self, delta_time: float = 0.016) -> None:
        """更新物理状态"""
        if self.physics_state == PhysicsState.STATIC:
            return

        # 应用重力
        if self.physics_state == PhysicsState.FALLING:
            self.velocity += self.gravity * delta_time

        # 更新位置
        new_pos = self.pos() + self.velocity * delta_time

        # 边界检测
        scene = self.scene()
        if scene:
            scene_rect = scene.sceneRect()
            if (
                new_pos.x() < 0
                or new_pos.x() > scene_rect.width() - self.boundingRect().width()
            ):
                self.velocity.setX(-self.velocity.x() * self.bounce_factor)
                new_pos.setX(
                    max(
                        0,
                        min(
                            new_pos.x(),
                            scene_rect.width() - self.boundingRect().width(),
                        ),
                    )
                )

            if (
                new_pos.y() < 0
                or new_pos.y() > scene_rect.height() - self.boundingRect().height()
            ):
                self.velocity.setY(-self.velocity.y() * self.bounce_factor)
                new_pos.setY(
                    max(
                        0,
                        min(
                            new_pos.y(),
                            scene_rect.height() - self.boundingRect().height(),
                        ),
                    )
                )

        # 应用摩擦力
        self.velocity *= self.friction

        # 停止条件
        if self.velocity.manhattanLength() < 0.1:
            self.set_physics_state(PhysicsState.STATIC)
            self.velocity = QPointF(0, 0)

        self.setPos(new_pos)

    def set_physics_state(self, state: PhysicsState) -> None:
        """设置物理状态"""
        if self.physics_state != state:
            old_state = self.physics_state
            self.physics_state = state
            self.physics_state_changed.emit(self.item_id, state)
            logger.debug(
                f"物品 {self.item_id} 物理状态: {old_state.value} -> {state.value}"
            )

    def apply_force(self, force: QPointF) -> None:
        """施加力"""
        self.acceleration += QPointF(force.x() / self.mass, force.y() / self.mass)
        if self.physics_state == PhysicsState.STATIC:
            self.set_physics_state(PhysicsState.MOVING)

    def apply_impulse(self, impulse: QPointF) -> None:
        """施加冲量"""
        self.velocity += QPointF(impulse.x() / self.mass, impulse.y() / self.mass)
        if self.physics_state == PhysicsState.STATIC:
            self.set_physics_state(PhysicsState.MOVING)

    def start_falling(self) -> None:
        """开始下落"""
        self.set_physics_state(PhysicsState.FALLING)

    def bounce(self, bounce_force: float = 1.0) -> None:
        """弹跳"""
        self.velocity.setY(-abs(self.velocity.y()) * self.bounce_factor * bounce_force)
        self.set_physics_state(PhysicsState.BOUNCING)

    def rotate_item(self, angle: float, duration: int = 500) -> None:
        """旋转物品"""
        if self.current_animation:
            self.current_animation.stop()

        self.current_animation = QPropertyAnimation(self, b"rotation")
        if self.current_animation:
            self.current_animation.setDuration(duration)
            self.current_animation.setStartValue(self.rotation())
            self.current_animation.setEndValue(self.rotation() + angle)
            self.current_animation.setEasingCurve(QEasingCurve.Type.OutBounce)
            self.current_animation.start()

    def shake_item(self, intensity: float = 10.0, duration: int = 200) -> None:
        """震动效果"""
        if self.current_animation:
            self.current_animation.stop()

        # 创建震动动画组
        shake_group = QSequentialAnimationGroup()

        for _ in range(5):
            anim = QPropertyAnimation(self, b"pos")  # type: ignore[arg-type]
            anim.setDuration(duration // 5)

            # 随机震动方向
            offset_x = random.uniform(-intensity, intensity)
            offset_y = random.uniform(-intensity, intensity)

            anim.setStartValue(self.pos())
            anim.setEndValue(self.pos() + QPointF(offset_x, offset_y))
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

            shake_group.addAnimation(anim)

        # 最后回到原位置
        final_anim = QPropertyAnimation(self, b"pos")  # type: ignore[arg-type]
        final_anim.setDuration(duration // 5)
        final_anim.setStartValue(self.pos())
        final_anim.setEndValue(self.pos())
        final_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        shake_group.addAnimation(final_anim)
        shake_group.start()

    def glow_effect(self, color: QColor | None = None, duration: int = 1000) -> None:
        """发光效果"""
        if color is None:
            color = self.glow_color

        # 创建发光动画
        glow_anim = QPropertyAnimation(self, b"opacity")  # type: ignore[arg-type]
        glow_anim.setDuration(duration)
        glow_anim.setStartValue(1.0)
        glow_anim.setEndValue(0.3)
        glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        # 反向动画
        reverse_anim = QPropertyAnimation(self, b"opacity")  # type: ignore[arg-type]
        reverse_anim.setDuration(duration)
        reverse_anim.setStartValue(0.3)
        reverse_anim.setEndValue(1.0)
        reverse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        # 组合动画
        glow_group = QSequentialAnimationGroup()
        glow_group.addAnimation(glow_anim)
        glow_group.addAnimation(reverse_anim)
        glow_group.start()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if not self.is_interactive:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_draggable:
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                self.setOpacity(0.8)
                self.interaction_started.emit(self.item_id, InteractionType.DRAG)

            elif self.is_clickable:
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                self.interaction_started.emit(self.item_id, InteractionType.CLICK)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if not self.is_interactive:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.setOpacity(1.0)

            # 检测交互类型
            if self.is_draggable:
                self.interaction_completed.emit(
                    self.item_id,
                    InteractionType.DRAG,
                    {
                        "final_position": (self.pos().x(), self.pos().y()),
                        "distance_moved": self.pos().manhattanLength(),
                    },
                )

            elif self.is_clickable:
                self.interaction_completed.emit(
                    self.item_id,
                    InteractionType.CLICK,
                    {"click_position": (event.pos().x(), event.pos().y())},
                )

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not self.is_interactive or not self.is_draggable:
            return

        # 检测滑动手势
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.pos() - event.lastPos()
            if delta.manhattanLength() > self.interaction_threshold:
                self.interaction_started.emit(self.item_id, InteractionType.SWIPE)

        super().mouseMoveEvent(event)

    def paint(self, painter: QPainter, option, widget):
        """自定义绘制"""
        super().paint(painter, option, widget)

        # 绘制发光效果
        if self.physics_state != PhysicsState.STATIC:
            painter.setPen(QPen(self.glow_color, 3))
            painter.setBrush(QBrush(self.glow_color))
            rect = self.boundingRect()
            painter.drawEllipse(
                rect.center(), self.collision_radius, self.collision_radius
            )

        # 绘制稀有度边框
        if self.rarity != "common":
            rarity_colors = {
                "uncommon": QColor(0, 255, 0, 150),
                "rare": QColor(0, 0, 255, 150),
                "epic": QColor(128, 0, 255, 150),
                "legendary": QColor(255, 215, 0, 150),
            }

            color = rarity_colors.get(self.rarity, QColor(100, 100, 100, 150))
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush())
            painter.drawRect(self.boundingRect())


class GamePhysicsScene(QGraphicsScene):
    """游戏化物理场景"""

    # 信号
    physics_updated = Signal()
    collision_detected = Signal(str, str)
    item_interacted = Signal(str, InteractionType, dict)

    def __init__(
        self, scene_config: dict[str, Any] | None = None, parent: QWidget | None = None
    ):
        super().__init__(parent)

        self.scene_config = scene_config or {}
        self.physics_items: dict[str, GamePhysicsItem] = {}

        # 物理循环参数（默认 60FPS，可通过 scene_config 或环境变量覆盖）
        # - scene_config["physics_fps"] 优先
        # - 环境变量 VCL_PHYSICS_FPS 其次
        physics_fps = 60
        try:
            if "physics_fps" in self.scene_config:
                physics_fps = int(self.scene_config["physics_fps"])
            else:
                env_fps = os.getenv("VCL_PHYSICS_FPS")
                if env_fps:
                    physics_fps = int(env_fps)
        except Exception:
            physics_fps = 60

        physics_fps = max(1, min(240, physics_fps))
        self._physics_interval_ms = max(1, int(1000 / physics_fps))
        self._last_physics_tick = time.perf_counter()

        # 物理设置
        self.gravity_enabled = True
        self.collision_enabled = True
        self.physics_speed = 1.0
        self.physics_timer = QTimer()
        self.physics_timer.timeout.connect(self.update_physics)
        self.physics_timer.setInterval(self._physics_interval_ms)
        # 注意：定时器采用“按需启动”，避免场景空闲时仍以 60FPS 空转发热
        # 任何物体进入非 STATIC 状态时会自动唤醒（见 _on_physics_state_changed）

        # 设置场景
        width = self.scene_config.get("width", 800)
        height = self.scene_config.get("height", 600)
        self.setSceneRect(0, 0, width, height)

        # 背景
        bg_color = self.scene_config.get("background_color", "#1a1a2e")
        self.setBackgroundBrush(QBrush(QColor(bg_color)))

        logger.info(f"创建游戏化物理场景: {width}x{height}")

    def _ensure_physics_timer_running(self) -> None:
        """确保物理定时器在运行（空闲时会停止）。"""
        if not self.physics_timer.isActive():
            self._last_physics_tick = time.perf_counter()
            self.physics_timer.start()

    def add_physics_item(
        self,
        item_id: str,
        item_type: str,
        pixmap: QPixmap | None = None,
        position: tuple[float, float] | None = None,
        physics_props: dict[str, Any] | None = None,
    ) -> GamePhysicsItem:
        """添加物理物品"""
        physics_props = physics_props or {}
        position = position or (0.0, 0.0)

        item = GamePhysicsItem(item_id, item_type, pixmap)
        item.setPos(float(position[0]), float(position[1]))

        # 设置物理属性
        if "mass" in physics_props:
            item.mass = physics_props["mass"]
        if "friction" in physics_props:
            item.friction = physics_props["friction"]
        if "bounce_factor" in physics_props:
            item.bounce_factor = physics_props["bounce_factor"]
        if "rarity" in physics_props:
            item.rarity = physics_props["rarity"]

        # 连接信号
        item.physics_state_changed.connect(self._on_physics_state_changed)
        item.collision_detected.connect(self._on_collision_detected)
        item.interaction_started.connect(self._on_interaction_started)
        item.interaction_completed.connect(self._on_interaction_completed)

        self.addItem(item)
        self.physics_items[item_id] = item

        logger.debug(f"添加物理物品: {item_id}")
        return item

    def update_physics(self):
        """更新物理状态"""
        # 根据真实 tick 计算 dt，避免固定 0.016 在低功耗/降帧场景下出现不一致
        now = time.perf_counter()
        delta_time = (now - self._last_physics_tick) * self.physics_speed
        # 防止窗口切后台/系统暂停导致 dt 过大引发穿透或抖动
        delta_time = max(0.0, min(0.05, delta_time))
        self._last_physics_tick = now

        items = list(self.physics_items.values())

        # 若没有任何活动物体，则停止定时器避免空转发热
        has_active = any(item.physics_state != PhysicsState.STATIC for item in items)
        if not has_active:
            if self.physics_timer.isActive():
                self.physics_timer.stop()
            return

        for item in items:
            item.update_physics(delta_time)

        # 碰撞检测
        if self.collision_enabled:
            self._check_collisions(items)

        self.physics_updated.emit()

    def _check_collisions(self, items: list[GamePhysicsItem] | None = None):
        """检测碰撞"""
        if items is None:
            items = list(self.physics_items.values())
        if len(items) < 2:
            return

        # 只检查“至少一方在运动”的 pair，避免大量静止物体时 O(n^2) 空转
        active_flags = [item.physics_state != PhysicsState.STATIC for item in items]

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item1, item2 = items[i], items[j]

                if not (active_flags[i] or active_flags[j]):
                    continue

                if self._items_collide(item1, item2):
                    self.collision_detected.emit(item1.item_id, item2.item_id)
                    self._handle_collision(item1, item2)

    def _items_collide(self, item1: GamePhysicsItem, item2: GamePhysicsItem) -> bool:
        """检测两个物品是否碰撞"""
        # 简单的圆形碰撞检测
        pos1 = item1.pos()
        pos2 = item2.pos()

        distance = math.sqrt((pos1.x() - pos2.x()) ** 2 + (pos1.y() - pos2.y()) ** 2)
        collision_distance = item1.collision_radius + item2.collision_radius

        return distance < collision_distance

    def _handle_collision(self, item1: GamePhysicsItem, item2: GamePhysicsItem):
        """处理碰撞"""
        # 计算碰撞响应
        pos1 = item1.pos()
        pos2 = item2.pos()

        # 碰撞方向
        dx = pos2.x() - pos1.x()
        dy = pos2.y() - pos1.y()
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 归一化方向
            dx /= distance
            dy /= distance

            # 计算相对速度
            relative_velocity = item2.velocity - item1.velocity

            # 碰撞冲量
            impulse = (
                -(1 + min(item1.bounce_factor, item2.bounce_factor))
                * relative_velocity.manhattanLength()
            )

            # 应用冲量
            item1.apply_impulse(QPointF(-dx * impulse, -dy * impulse))
            item2.apply_impulse(QPointF(dx * impulse, dy * impulse))

            # 触发碰撞效果
            item1.bounce()
            item2.bounce()

    def _on_physics_state_changed(self, item_id: str, state: PhysicsState) -> None:
        """物理状态改变处理"""
        logger.debug(f"物品 {item_id} 物理状态改变: {state.value}")
        if state != PhysicsState.STATIC:
            self._ensure_physics_timer_running()

    def _on_collision_detected(self, item_id: str, other_item_id: str) -> None:
        """碰撞检测处理"""
        logger.debug(f"碰撞检测: {item_id} <-> {other_item_id}")

    def _on_interaction_started(
        self, item_id: str, interaction_type: InteractionType
    ) -> None:
        """交互开始处理"""
        logger.debug(f"交互开始: {item_id} - {interaction_type.value}")

    def _on_interaction_completed(
        self, item_id: str, interaction_type: InteractionType, data: dict
    ) -> None:
        """交互完成处理"""
        self.item_interacted.emit(item_id, interaction_type, data)
        logger.debug(f"交互完成: {item_id} - {interaction_type.value} - {data}")

    def apply_global_force(self, force: QPointF):
        """对所有物品施加全局力"""
        for item in self.physics_items.values():
            item.apply_force(force)

    def shake_all_items(self, intensity: float = 5.0):
        """震动所有物品"""
        for item in self.physics_items.values():
            item.shake_item(intensity)

    def enable_gravity(self, enabled: bool = True):
        """启用/禁用重力"""
        self.gravity_enabled = enabled
        for item in self.physics_items.values():
            if enabled:
                item.start_falling()
            else:
                item.set_physics_state(PhysicsState.STATIC)

    def set_physics_speed(self, speed: float):
        """设置物理更新速度"""
        if speed <= 0:
            logger.warning("物理速度必须大于0")
            return

        self.physics_speed = speed
        # speed 影响 dt，不直接改变定时器频率；频率由 _physics_interval_ms / physics_fps 控制
        # 保留接口语义：提高 speed 会加快模拟推进
        self._ensure_physics_timer_running()


class GamePhysicsView(QGraphicsView):
    """游戏化物理视图"""

    RenderHint = QPainter.RenderHint
    ViewportUpdateMode = QGraphicsView.ViewportUpdateMode
    FullViewportUpdate = QGraphicsView.ViewportUpdateMode.FullViewportUpdate

    def __init__(
        self, scene: GamePhysicsScene | None = None, parent: QWidget | None = None
    ):
        super().__init__(parent)

        if scene is None:
            scene = GamePhysicsScene()

        self.setScene(scene)

        # 视图设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        # 默认为 FullViewportUpdate（与历史行为保持一致）
        # 如需降低整屏重绘开销，可设置环境变量 VCL_VIEWPORT_UPDATE_MODE=smart
        viewport_mode = os.getenv("VCL_VIEWPORT_UPDATE_MODE", "").strip().lower()
        if viewport_mode in {"smart", "smartviewportupdate"}:
            self.setViewportUpdateMode(
                QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
            )
        else:
            self.setViewportUpdateMode(
                QGraphicsView.ViewportUpdateMode.FullViewportUpdate
            )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 游戏化样式
        self.setStyleSheet(
            """
            QGraphicsView {
                border: 3px solid #4a90e2;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
            }
        """
        )

        logger.info("创建游戏化物理视图")

    def get_scene(self) -> GamePhysicsScene:
        """获取场景对象"""
        return self.scene()

    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        """键盘事件"""
        scene = self.get_scene()

        if event.key() == Qt.Key.Key_Space:
            # 空格键：震动所有物品
            scene.shake_all_items()
        elif event.key() == Qt.Key.Key_G:
            # G键：切换重力
            scene.enable_gravity(not scene.gravity_enabled)
        elif event.key() == Qt.Key.Key_R:
            # R键：重置所有物品
            for item in scene.physics_items.values():
                item.physics_state = PhysicsState.STATIC
                item.velocity = QPointF(0, 0)

        super().keyPressEvent(event)
