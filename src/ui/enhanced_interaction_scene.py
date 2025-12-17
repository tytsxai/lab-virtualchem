"""
增强的交互式实验场景
添加更多交互反馈和视觉效果
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPointF, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QWidget,
)

from ..utils.logger import get_logger
from .interactive_scene import (
    ClickableItem,
    DraggableItem,
    InteractiveExperimentScene,
)

logger = get_logger(__name__)


class ParticleEffect(QGraphicsEllipseItem):
    """粒子效果"""

    def __init__(
        self, x: float, y: float, color: QColor, parent: QGraphicsItem | None = None
    ):
        super().__init__(-5, -5, 10, 10, parent)
        self.setPos(x, y)

        # 设置颜色和透明度
        self.setBrush(QBrush(color))
        self.setPen(Qt.PenStyle.NoPen)
        self.setOpacity(1.0)

        # 创建动画
        self.fade_animation = QPropertyAnimation(self, b"opacity")
        self.fade_animation.setDuration(800)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._on_finished)

        self.scale_animation = QPropertyAnimation(self, b"scale")
        self.scale_animation.setDuration(800)
        self.scale_animation.setStartValue(1.0)
        self.scale_animation.setEndValue(2.0)

        # 开始动画
        self.fade_animation.start()
        self.scale_animation.start()

    def _on_finished(self):
        """动画完成，移除自己"""
        if self.scene():
            self.scene().removeItem(self)


class GlowEffect(QGraphicsEllipseItem):
    """发光效果"""

    def __init__(self, item: QGraphicsItem, color: QColor):
        rect = item.boundingRect()
        radius = max(rect.width(), rect.height()) / 2 + 10

        super().__init__(-radius, -radius, radius * 2, radius * 2, item)

        # 创建径向渐变
        gradient = QRadialGradient(0, 0, radius)
        gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 0))
        gradient.setColorAt(0.7, QColor(color.red(), color.green(), color.blue(), 100))
        gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))

        self.setBrush(QBrush(gradient))
        self.setPen(Qt.PenStyle.NoPen)

        # 脉冲动画
        self.pulse_animation = QPropertyAnimation(self, b"scale")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(1.0)
        self.pulse_animation.setEndValue(1.2)
        self.pulse_animation.setLoopCount(-1)  # 无限循环
        self.pulse_animation.start()


class EnhancedDraggableItem(DraggableItem):
    """增强的可拖拽物品 - 添加更多反馈效果"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.glow_effect: GlowEffect | None = None
        self.is_highlighted = False
        # 启用悬停事件
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        """鼠标悬停进入"""
        if not self.is_locked:
            self.setScale(1.1)
            # 添加发光效果
            if not self.is_highlighted:
                self.glow_effect = GlowEffect(self, QColor(100, 200, 255))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """鼠标悬停离开"""
        if not self.is_locked:
            self.setScale(1.0)
            # 移除发光效果
            if self.glow_effect and not self.is_highlighted:
                if self.glow_effect.scene():
                    self.glow_effect.scene().removeItem(self.glow_effect)
                self.glow_effect = None
        super().hoverLeaveEvent(event)

    def highlight(self, color: QColor = QColor(255, 215, 0)):
        """高亮显示"""
        self.is_highlighted = True
        if not self.glow_effect:
            self.glow_effect = GlowEffect(self, color)

    def unhighlight(self):
        """取消高亮"""
        self.is_highlighted = False
        if self.glow_effect:
            if self.glow_effect.scene():
                self.glow_effect.scene().removeItem(self.glow_effect)
            self.glow_effect = None


class EnhancedClickableItem(ClickableItem):
    """增强的可点击物品"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 启用悬停事件
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        """鼠标悬停进入"""
        self.setScale(1.1)
        # 添加边框高亮
        from PySide6.QtWidgets import QGraphicsRectItem

        rect = self.boundingRect()
        self.highlight_rect = QGraphicsRectItem(rect, self)
        self.highlight_rect.setPen(QPen(QColor(100, 200, 255), 3))
        self.highlight_rect.setBrush(Qt.BrushStyle.NoBrush)

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """鼠标悬停离开"""
        self.setScale(1.0)
        # 移除高亮
        if hasattr(self, "highlight_rect") and self.highlight_rect:
            if self.highlight_rect.scene():
                self.highlight_rect.scene().removeItem(self.highlight_rect)
            self.highlight_rect = None

        super().hoverLeaveEvent(event)


class EnhancedInteractiveScene(InteractiveExperimentScene):
    """增强的交互式实验场景"""

    # 额外信号
    item_hovered = Signal(str)  # 物品ID
    zone_activated = Signal(str)  # 区域ID
    interaction_hint = Signal(str)  # 交互提示文本

    def __init__(
        self, scene_config: dict[str, Any] | None = None, parent: QWidget | None = None
    ):
        super().__init__(scene_config, parent)

        # 反馈系统
        self.show_particles = True
        self.show_hints = True

        # 创建提示文本项（待实现）
        self.hint_timer = QTimer()
        self.hint_timer.setSingleShot(True)
        self.hint_timer.timeout.connect(self._hide_hint)

        logger.info("创建增强的交互式场景")

    def add_draggable_item(
        self,
        item_id: str,
        item_type: str,
        position: tuple[float, float],
        image_path: str | None = None,
        size: tuple[int, int] | None = None,
    ) -> EnhancedDraggableItem:
        """添加增强的可拖拽物品"""
        # 加载图片
        pixmap = self._load_pixmap(image_path, size)

        # 创建增强的物品
        item = EnhancedDraggableItem(item_id, item_type, pixmap)
        item.setPos(position[0], position[1])
        item.original_pos = QPointF(position[0], position[1])

        # 启用悬停事件
        item.setAcceptHoverEvents(True)

        # 添加到场景
        self.addItem(item)
        self.draggable_items[item_id] = item

        logger.debug(f"添加增强的可拖拽物品: {item_id} at {position}")
        return item

    def add_clickable_item(
        self,
        item_id: str,
        item_type: str,
        position: tuple[float, float],
        callback: Any = None,
        image_path: str | None = None,
        size: tuple[int, int] | None = None,
    ) -> EnhancedClickableItem:
        """添加增强的可点击物品"""
        pixmap = self._load_pixmap(image_path, size)

        item = EnhancedClickableItem(item_id, item_type, pixmap, callback)
        item.setPos(position[0], position[1])

        # 启用悬停事件
        item.setAcceptHoverEvents(True)

        self.addItem(item)
        self.clickable_items[item_id] = item

        logger.debug(f"添加增强的可点击物品: {item_id} at {position}")
        return item

    def show_success_feedback(self, position: QPointF):
        """显示成功反馈"""
        if self.show_particles:
            # 创建绿色粒子效果
            for i in range(8):
                import math
                import random

                angle = (i * 45 + random.randint(-10, 10)) * math.pi / 180
                distance = random.randint(20, 40)
                x = position.x() + distance * math.cos(angle)
                y = position.y() + distance * math.sin(angle)

                particle = ParticleEffect(x, y, QColor(46, 204, 113))
                self.addItem(particle)

        logger.info(f"显示成功反馈: {position}")

    def show_error_feedback(self, position: QPointF):
        """显示错误反馈"""
        if self.show_particles:
            # 创建红色粒子效果
            for i in range(6):
                import math
                import random

                angle = (i * 60 + random.randint(-15, 15)) * math.pi / 180
                distance = random.randint(15, 30)
                x = position.x() + distance * math.cos(angle)
                y = position.y() + distance * math.sin(angle)

                particle = ParticleEffect(x, y, QColor(231, 76, 60))
                self.addItem(particle)

        logger.info(f"显示错误反馈: {position}")

    def show_hint(self, hint_text: str, duration: int = 3000):
        """显示提示文本"""
        if self.show_hints:
            self.interaction_hint.emit(hint_text)
            self.hint_timer.start(duration)

        logger.info(f"显示提示: {hint_text}")

    def _hide_hint(self):
        """隐藏提示"""
        self.interaction_hint.emit("")

    def highlight_compatible_zones(self, item: DraggableItem):
        """高亮兼容的放置区域"""
        for zone in self.drop_zones.values():
            if not zone.accepted_types or item.item_type in zone.accepted_types:
                zone.highlight()

    def unhighlight_all_zones(self):
        """取消所有区域高亮"""
        for zone in self.drop_zones.values():
            zone.unhighlight()

    def validate_drop(self, item_id: str) -> bool:
        """验证物品放置是否正确"""
        if item_id not in self.draggable_items:
            return False

        item = self.draggable_items[item_id]

        # 检查是否在任何区域内
        for zone_id, zone in self.drop_zones.items():
            if zone.contains_item(item):
                # 检查类型是否匹配
                if not zone.accepted_types or item.item_type in zone.accepted_types:
                    # 成功
                    self.show_success_feedback(item.pos())
                    self.show_hint(f"✓ {item_id} 正确放置到 {zone_id}")
                    self.item_dropped.emit(item_id, zone_id)
                    return True
                else:
                    # 类型不匹配
                    self.show_error_feedback(item.pos())
                    self.show_hint(f"✗ {item_id} 不能放置在 {zone_id}")
                    # 恢复到原位
                    item.setPos(item.original_pos)
                    return False

        return False

    def add_connection_line(
        self, item1_id: str, item2_id: str, color: QColor = QColor(100, 150, 255)
    ):
        """在两个物品之间添加连接线"""
        if item1_id not in self.draggable_items or item2_id not in self.draggable_items:
            return

        item1 = self.draggable_items[item1_id]
        item2 = self.draggable_items[item2_id]

        from PySide6.QtWidgets import QGraphicsLineItem

        line = QGraphicsLineItem(
            item1.pos().x(), item1.pos().y(), item2.pos().x(), item2.pos().y()
        )
        line.setPen(QPen(color, 3, Qt.PenStyle.DashLine))
        self.addItem(line)

        logger.info(f"添加连接线: {item1_id} -> {item2_id}")

    def shake_item(self, item_id: str):
        """震动物品（表示错误）"""
        if item_id not in self.draggable_items:
            return

        item = self.draggable_items[item_id]
        original_pos = item.pos()

        # 创建震动动画
        animation = QPropertyAnimation(item, b"pos")
        animation.setDuration(400)

        # 震动序列
        animation.setKeyValueAt(0, original_pos)
        animation.setKeyValueAt(0.1, QPointF(original_pos.x() - 5, original_pos.y()))
        animation.setKeyValueAt(0.2, QPointF(original_pos.x() + 5, original_pos.y()))
        animation.setKeyValueAt(0.3, QPointF(original_pos.x() - 5, original_pos.y()))
        animation.setKeyValueAt(0.4, QPointF(original_pos.x() + 5, original_pos.y()))
        animation.setKeyValueAt(0.5, QPointF(original_pos.x() - 3, original_pos.y()))
        animation.setKeyValueAt(0.6, QPointF(original_pos.x() + 3, original_pos.y()))
        animation.setKeyValueAt(1, original_pos)

        animation.start()

        logger.info(f"震动物品: {item_id}")

    def bounce_item(self, item_id: str):
        """弹跳物品（表示成功）"""
        if item_id not in self.draggable_items:
            return

        item = self.draggable_items[item_id]
        original_pos = item.pos()

        # 创建弹跳动画
        animation = QPropertyAnimation(item, b"pos")
        animation.setDuration(600)

        animation.setKeyValueAt(0, original_pos)
        animation.setKeyValueAt(0.3, QPointF(original_pos.x(), original_pos.y() - 20))
        animation.setKeyValueAt(0.6, original_pos)
        animation.setKeyValueAt(0.8, QPointF(original_pos.x(), original_pos.y() - 10))
        animation.setKeyValueAt(1, original_pos)

        animation.start()

        logger.info(f"弹跳物品: {item_id}")

    def pulse_zone(self, zone_id: str):
        """脉冲区域（吸引注意力）"""
        if zone_id not in self.drop_zones:
            return

        zone = self.drop_zones[zone_id]

        # 创建脉冲动画
        animation = QPropertyAnimation(zone, b"opacity")
        animation.setDuration(800)
        animation.setKeyValueAt(0, 1.0)
        animation.setKeyValueAt(0.5, 0.3)
        animation.setKeyValueAt(1, 1.0)
        animation.setLoopCount(3)

        animation.start()

        logger.info(f"脉冲区域: {zone_id}")


# 预设增强场景配置
ENHANCED_PRESET_SCENES = {
    "acid_base_titration": {
        "width": 900,
        "height": 700,
        "background_color": "#f9f9f9",
        "draggable_items": [
            {
                "id": "burette",
                "type": "burette",
                "position": [150, 120],
                "size": [60, 200],
                "image": "burette.png",
            },
            {
                "id": "erlenmeyer_flask",
                "type": "flask",
                "position": [350, 400],
                "size": [100, 130],
                "image": "flask.png",
            },
            {
                "id": "phenolphthalein",
                "type": "indicator",
                "position": [50, 50],
                "size": [50, 70],
                "image": "indicator_bottle.png",
            },
        ],
        "clickable_items": [
            {
                "id": "hcl_bottle",
                "type": "reagent",
                "position": [600, 100],
                "size": [70, 90],
                "image": "reagent_bottle.png",
            },
            {
                "id": "naoh_bottle",
                "type": "reagent",
                "position": [700, 100],
                "size": [70, 90],
                "image": "reagent_bottle.png",
            },
        ],
        "drop_zones": [
            {
                "id": "titration_stand",
                "rect": [120, 200, 120, 280],
                "accepted_types": ["burette"],
            },
            {
                "id": "workspace",
                "rect": [300, 380, 180, 200],
                "accepted_types": ["flask"],
            },
        ],
    },
}
