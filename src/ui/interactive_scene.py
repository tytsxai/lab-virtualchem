"""
交互式实验场景系统
提供可视化、可交互的实验操作界面
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QPointF,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QWidget,
)

from ..utils.logger import get_logger
from .interaction_feedback import get_feedback_manager

logger = get_logger(__name__)


class DraggableItem(QGraphicsPixmapItem):
    """可拖拽的实验器材基类"""

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
        self.original_pos = QPointF(0, 0)
        self.is_locked = False
        self.properties: dict[str, Any] = {}
        self.feedback_manager = get_feedback_manager()

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

        logger.debug(f"创建可拖拽物品: {item_id} ({item_type})")

    def mousePressEvent(self, event: Any) -> None:
        """鼠标按下"""
        if not self.is_locked:
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

            # 增强视觉反馈：缩放和透明度
            self.setOpacity(0.8)
            self.setScale(1.05)  # 轻微放大

            # 添加阴影效果
            from PySide6.QtWidgets import QGraphicsDropShadowEffect

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 180))
            shadow.setOffset(3, 3)
            self.setGraphicsEffect(shadow)

            # 拾取反馈
            self.feedback_manager.on_item_picked(self)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """鼠标释放"""
        if not self.is_locked:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

            # 恢复视觉状态
            self.setOpacity(1.0)
            self.setScale(1.0)  # 恢复原始大小
            self.setGraphicsEffect(None)  # 移除阴影

            # 放下反馈
            self.feedback_manager.on_item_dropped(self)

            # 通知场景检查拖放动作
            scene = self.scene()
            if scene and isinstance(scene, InteractiveExperimentScene):
                dropped_in_zone = False
                # 检查是否放入任何区域
                for zone_id, zone in scene.drop_zones.items():
                    if zone.contains_item(self):
                        # 检查类型是否匹配
                        if (
                            not zone.accepted_types
                            or self.item_type in zone.accepted_types
                        ):
                            # 成功放入 - 添加成功动画
                            self.animate_drop_success()
                            scene.item_dropped.emit(self.item_id, zone_id)
                            logger.info(f"物品 {self.item_id} 放入区域 {zone_id}")
                            dropped_in_zone = True
                            break
                        else:
                            # 类型不匹配 - 添加错误动画
                            self.animate_drop_error()
                            logger.warning(
                                f"物品 {self.item_id} 类型不匹配区域 {zone_id}"
                            )
                            dropped_in_zone = True
                            break

                # 如果没有放入任何区域，可以选择返回原位
                if not dropped_in_zone and hasattr(self, "snap_back_on_invalid_drop"):
                    if self.snap_back_on_invalid_drop:
                        self.animate_snap_back()
        super().mouseReleaseEvent(event)

    def animate_drop_success(self):
        """成功放入动画"""
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation

        # 闪烁绿色边框效果
        animation = QPropertyAnimation(self, b"opacity")
        animation.setDuration(200)
        animation.setStartValue(1.0)
        animation.setKeyValueAt(0.5, 0.5)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

    def animate_drop_error(self):
        """放入错误动画 - 抖动效果"""
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation

        original_pos = self.pos()
        animation = QPropertyAnimation(self, b"pos")
        animation.setDuration(400)
        animation.setStartValue(original_pos)
        animation.setKeyValueAt(0.25, original_pos + QPointF(-5, 0))
        animation.setKeyValueAt(0.50, original_pos + QPointF(5, 0))
        animation.setKeyValueAt(0.75, original_pos + QPointF(-3, 0))
        animation.setEndValue(original_pos)
        animation.setEasingCurve(QEasingCurve.Type.InOutElastic)
        animation.start()

    def animate_snap_back(self):
        """弹回原位动画"""
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation

        animation = QPropertyAnimation(self, b"pos")
        animation.setDuration(300)
        animation.setStartValue(self.pos())
        animation.setEndValue(self.original_pos)
        animation.setEasingCurve(QEasingCurve.Type.OutBack)
        animation.start()

    def itemChange(self, change: Any, value: Any) -> Any:
        """物品状态改变"""
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self.scene()
        ):
            # 限制在场景范围内
            new_pos = value
            rect = self.scene().sceneRect()
            if not rect.contains(new_pos):
                new_pos.setX(min(rect.right(), max(new_pos.x(), rect.left())))
                new_pos.setY(min(rect.bottom(), max(new_pos.y(), rect.top())))
                return new_pos
        return super().itemChange(change, value)

    def lock(self) -> None:
        """锁定物品，禁止移动"""
        self.is_locked = True
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def unlock(self) -> None:
        """解锁物品"""
        self.is_locked = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))


class ClickableItem(QGraphicsPixmapItem):
    """可点击的实验器材（不可拖拽，但可以点击触发动作）"""

    def __init__(
        self,
        item_id: str,
        item_type: str,
        pixmap: QPixmap | None = None,
        callback: Callable[[str], None] | None = None,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(pixmap if pixmap else QPixmap(), parent)
        self.item_id = item_id
        self.item_type = item_type
        self.callback = callback
        self.properties: dict[str, Any] = {}
        self.feedback_manager = get_feedback_manager()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # 接受鼠标事件
        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )

        self.setToolTip(f"点击使用: {item_type}")

        logger.debug(f"创建可点击物品: {item_id} ({item_type})")

    def mousePressEvent(self, event: Any) -> None:
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 视觉反馈
            self.setOpacity(0.7)
            self.feedback_manager.on_item_clicked(self)

            # 通知场景
            scene = self.scene()
            if scene and isinstance(scene, InteractiveExperimentScene):
                scene.item_clicked.emit(self.item_id)
                logger.info(f"点击物品: {self.item_id}")

            if self.callback:
                self.callback(self.item_id)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """鼠标释放"""
        self.setOpacity(1.0)
        super().mouseReleaseEvent(event)


class DropZone(QGraphicsRectItem):
    """放置区域 - 用于接收拖放的物品"""

    def __init__(
        self,
        zone_id: str,
        rect: QRectF,
        accepted_types: list[str] | None = None,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(rect, parent)
        self.zone_id = zone_id
        self.accepted_types = accepted_types or []
        self.items_in_zone: list[DraggableItem] = []

        # 样式
        self.setPen(QPen(QColor(100, 150, 255, 100), 2, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(QColor(100, 150, 255, 30)))

        # 标签
        self.label = QGraphicsTextItem(zone_id, self)
        self.label.setDefaultTextColor(QColor(100, 150, 255))
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setPos(rect.topLeft() + QPointF(5, 5))

        logger.debug(f"创建放置区域: {zone_id}, 接受类型: {accepted_types}")

    def contains_item(self, item: DraggableItem) -> bool:
        """检查物品是否在区域内"""
        return self.contains(item.pos())

    def highlight(self, valid: bool = True) -> None:
        """高亮显示区域

        Args:
            valid: 是否为有效的放置（True=绿色，False=红色）
        """
        if valid:
            # 有效放置 - 绿色高亮
            self.setPen(QPen(QColor(46, 204, 113, 230), 4, Qt.PenStyle.SolidLine))
            self.setBrush(QBrush(QColor(46, 204, 113, 100)))
            self.label.setDefaultTextColor(QColor(39, 174, 96))
        else:
            # 无效放置 - 红色高亮
            self.setPen(QPen(QColor(231, 76, 60, 230), 4, Qt.PenStyle.SolidLine))
            self.setBrush(QBrush(QColor(231, 76, 60, 100)))
            self.label.setDefaultTextColor(QColor(192, 57, 43))

    def unhighlight(self) -> None:
        """取消高亮"""
        self.setPen(QPen(QColor(100, 150, 255, 100), 2, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(QColor(100, 150, 255, 30)))
        self.label.setDefaultTextColor(QColor(100, 150, 255))

    def pulse_animation(self):
        """脉冲动画效果"""
        from PySide6.QtCore import QEasingCurve, QVariantAnimation

        # 创建颜色动画
        animation = QVariantAnimation()
        animation.setDuration(1000)
        animation.setStartValue(30)
        animation.setEndValue(80)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        def update_alpha(value):
            color = QColor(100, 150, 255, int(value))
            self.setBrush(QBrush(color))

        animation.valueChanged.connect(update_alpha)
        animation.setLoopCount(-1)  # 无限循环
        animation.start()

        # 保存动画引用以防被垃圾回收
        if not hasattr(self, "_animations"):
            self._animations = []
        self._animations.append(animation)


class InteractiveExperimentScene(QGraphicsScene):
    """交互式实验场景"""

    # 信号
    item_dropped = Signal(str, str)  # 物品ID, 区域ID
    item_clicked = Signal(str)  # 物品ID
    action_completed = Signal(str, dict)  # 动作名称, 结果数据

    def __init__(
        self, scene_config: dict[str, Any] | None = None, parent: QWidget | None = None
    ):
        super().__init__(parent)

        self.scene_config = scene_config or {}
        self.draggable_items: dict[str, DraggableItem] = {}
        self.clickable_items: dict[str, ClickableItem] = {}
        self.drop_zones: dict[str, DropZone] = {}
        self.action_log: list[dict[str, Any]] = []

        # 设置场景大小
        width = self.scene_config.get("width", 800)
        height = self.scene_config.get("height", 600)
        self.setSceneRect(0, 0, width, height)

        # 背景色
        bg_color = self.scene_config.get("background_color", "#f5f5f5")
        self.setBackgroundBrush(QBrush(QColor(bg_color)))

        logger.info(f"创建交互式实验场景: {width}x{height}")

    def add_draggable_item(
        self,
        item_id: str,
        item_type: str,
        position: tuple[float, float],
        image_path: str | None = None,
        size: tuple[int, int] | None = None,
    ) -> DraggableItem:
        """添加可拖拽物品"""
        # 加载图片
        pixmap = self._load_pixmap(image_path, size)

        # 创建物品
        item = DraggableItem(item_id, item_type, pixmap)
        item.setPos(position[0], position[1])
        item.original_pos = QPointF(position[0], position[1])

        # 添加到场景
        self.addItem(item)
        self.draggable_items[item_id] = item

        logger.debug(f"添加可拖拽物品: {item_id} at {position}")
        return item

    def add_clickable_item(
        self,
        item_id: str,
        item_type: str,
        position: tuple[float, float],
        callback: Callable[[str], None] | None = None,
        image_path: str | None = None,
        size: tuple[int, int] | None = None,
    ) -> ClickableItem:
        """添加可点击物品"""
        pixmap = self._load_pixmap(image_path, size)

        item = ClickableItem(item_id, item_type, pixmap, callback)
        item.setPos(position[0], position[1])

        self.addItem(item)
        self.clickable_items[item_id] = item

        logger.debug(f"添加可点击物品: {item_id} at {position}")
        return item

    def add_drop_zone(
        self,
        zone_id: str,
        rect: tuple[float, float, float, float],
        accepted_types: list[str] | None = None,
    ) -> DropZone:
        """添加放置区域"""
        zone = DropZone(zone_id, QRectF(*rect), accepted_types)
        self.addItem(zone)
        self.drop_zones[zone_id] = zone

        logger.debug(f"添加放置区域: {zone_id}")
        return zone

    def check_drop_actions(self) -> list[dict[str, Any]]:
        """检查所有放置动作"""
        results = []

        for item_id, item in self.draggable_items.items():
            for zone_id, zone in self.drop_zones.items():
                if zone.contains_item(item):
                    # 检查类型是否匹配
                    if not zone.accepted_types or item.item_type in zone.accepted_types:
                        results.append(
                            {
                                "item_id": item_id,
                                "item_type": item.item_type,
                                "zone_id": zone_id,
                                "valid": True,
                            }
                        )
                        self.item_dropped.emit(item_id, zone_id)
                        logger.info(f"物品 {item_id} 放入区域 {zone_id}")
                    else:
                        results.append(
                            {
                                "item_id": item_id,
                                "item_type": item.item_type,
                                "zone_id": zone_id,
                                "valid": False,
                                "reason": "类型不匹配",
                            }
                        )

        return results

    def get_state(self) -> dict[str, Any]:
        """获取当前场景状态"""
        state = {
            "draggable_items": {
                item_id: {
                    "type": item.item_type,
                    "position": (item.pos().x(), item.pos().y()),
                    "locked": item.is_locked,
                    "properties": item.properties,
                }
                for item_id, item in self.draggable_items.items()
            },
            "drop_zones": {
                zone_id: {
                    "items_in_zone": [
                        item_id
                        for item_id, item in self.draggable_items.items()
                        if zone.contains_item(item)
                    ]
                }
                for zone_id, zone in self.drop_zones.items()
            },
            "action_log": self.action_log,
        }
        return state

    def reset_scene(self) -> None:
        """重置场景 - 将所有物品恢复到初始位置"""
        for item in self.draggable_items.values():
            item.setPos(item.original_pos)
            item.unlock()

        self.action_log.clear()
        logger.info("场景已重置")

    def load_state(self, state_data: dict[str, Any]) -> None:
        """
        加载场景状态

        Args:
            state_data: 状态数据，包含 item_positions 和 drop_actions
        """
        item_positions = state_data.get("item_positions", {})
        drop_actions = state_data.get("drop_actions", {})

        # 恢复物品位置
        for item_id, pos in item_positions.items():
            if item_id in self.draggable_items:
                item = self.draggable_items[item_id]
                item.setPos(pos[0], pos[1])

        # 恢复操作记录
        if drop_actions:
            self.action_log.clear()
            for item_id, zone_id in drop_actions.items():
                self.action_log.append({"item_id": item_id, "zone_id": zone_id})

        logger.info(
            f"场景状态已加载: {len(item_positions)} 个物品位置, {len(drop_actions)} 个放置动作"
        )

    def _load_pixmap(
        self, image_path: str | None, size: tuple[int, int] | None
    ) -> QPixmap:
        """加载并缩放图片"""
        if not image_path:
            # 创建默认占位符
            pixmap = QPixmap(size[0] if size else 50, size[1] if size else 50)
            pixmap.fill(QColor(200, 200, 200))
            return pixmap

        try:
            # 尝试加载图片
            path = Path(image_path)
            if not path.is_absolute():
                # 相对于项目根目录
                path = Path("assets/images/equipment") / image_path

            if not path.exists():
                logger.warning(f"图片不存在: {path}")
                # 返回占位符
                pixmap = QPixmap(size[0] if size else 50, size[1] if size else 50)
                pixmap.fill(QColor(200, 200, 200))
                return pixmap

            pixmap = QPixmap(str(path))

            # 缩放
            if size and not pixmap.isNull():
                pixmap = pixmap.scaled(
                    size[0],
                    size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            return pixmap

        except Exception as e:
            logger.error(f"加载图片失败: {e}")
            # 返回占位符
            pixmap = QPixmap(size[0] if size else 50, size[1] if size else 50)
            pixmap.fill(QColor(200, 200, 200))
            return pixmap


class InteractiveExperimentView(QGraphicsView):
    """交互式实验视图 - QGraphicsView的封装"""

    def __init__(
        self,
        scene: InteractiveExperimentScene | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        if scene is None:
            scene = InteractiveExperimentScene()

        self.setScene(scene)

        # 视图设置
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 启用交互
        self.setInteractive(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)  # 使用物品自己的拖动逻辑

        # 背景
        self.setBackgroundBrush(QBrush(QColor(245, 245, 245)))

        # 样式
        self.setStyleSheet(
            """
            QGraphicsView {
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                background-color: #f5f5f5;
            }
        """
        )

        logger.info("创建交互式实验视图")

    def get_scene(self) -> InteractiveExperimentScene:
        """获取场景对象"""
        scene = self.scene()
        assert isinstance(scene, InteractiveExperimentScene)
        return scene

    def fit_scene(self) -> None:
        """适应场景大小"""
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: Any) -> None:
        """鼠标滚轮缩放"""
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)


class ExperimentSceneBuilder:
    """实验场景构建器 - 从配置创建场景"""

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> InteractiveExperimentScene:
        """从配置字典创建场景"""
        scene = InteractiveExperimentScene(config)

        # 添加可拖拽物品
        for item_config in config.get("draggable_items", []):
            scene.add_draggable_item(
                item_id=item_config["id"],
                item_type=item_config["type"],
                position=tuple(item_config["position"]),
                image_path=item_config.get("image"),
                size=tuple(item_config["size"]) if "size" in item_config else None,
            )

        # 添加可点击物品
        for item_config in config.get("clickable_items", []):
            scene.add_clickable_item(
                item_id=item_config["id"],
                item_type=item_config["type"],
                position=tuple(item_config["position"]),
                image_path=item_config.get("image"),
                size=tuple(item_config["size"]) if "size" in item_config else None,
            )

        # 添加放置区域
        for zone_config in config.get("drop_zones", []):
            scene.add_drop_zone(
                zone_id=zone_config["id"],
                rect=tuple(zone_config["rect"]),
                accepted_types=zone_config.get("accepted_types"),
            )

        logger.info(
            f"从配置构建场景完成: {len(scene.draggable_items)} 个可拖拽物品, "
            f"{len(scene.clickable_items)} 个可点击物品, {len(scene.drop_zones)} 个放置区域"
        )

        return scene

    @staticmethod
    def build_from_file(config_path: str) -> InteractiveExperimentScene:
        """从JSON配置文件创建场景"""
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            return ExperimentSceneBuilder.build_from_config(config)
        except Exception as e:
            logger.error(f"从文件加载场景配置失败: {e}")
            raise


# 预设场景配置
PRESET_SCENES = {
    "titration": {
        "width": 800,
        "height": 600,
        "background_color": "#f9f9f9",
        "draggable_items": [
            {
                "id": "burette",
                "type": "burette",
                "position": [100, 100],
                "size": [60, 180],
                "image": "burette.png",
            },
            {
                "id": "beaker_100ml",
                "type": "beaker",
                "position": [100, 400],
                "size": [80, 100],
                "image": "beaker.png",
            },
            {
                "id": "erlenmeyer_flask",
                "type": "flask",
                "position": [300, 380],
                "size": [90, 120],
                "image": "flask.png",
            },
        ],
        "clickable_items": [
            {
                "id": "reagent_hcl",
                "type": "reagent",
                "position": [50, 50],
                "size": [60, 80],
                "image": "reagent_bottle.png",
            },
            {
                "id": "reagent_naoh",
                "type": "reagent",
                "position": [150, 50],
                "size": [60, 80],
                "image": "reagent_bottle.png",
            },
            {
                "id": "phenolphthalein",
                "type": "indicator",
                "position": [250, 50],
                "size": [50, 70],
                "image": "indicator_bottle.png",
            },
        ],
        "drop_zones": [
            {
                "id": "work_area",
                "rect": [250, 300, 300, 250],
                "accepted_types": ["beaker", "flask"],
            },
            {
                "id": "titration_stand",
                "rect": [80, 200, 100, 200],
                "accepted_types": ["burette"],
            },
        ],
    },
    "distillation": {
        "width": 800,
        "height": 600,
        "background_color": "#f9f9f9",
        "draggable_items": [
            {
                "id": "distilling_flask",
                "type": "flask",
                "position": [100, 400],
                "size": [100, 120],
                "image": "flask.png",
            },
            {
                "id": "condenser",
                "type": "equipment",
                "position": [250, 250],
                "size": [150, 60],
                "image": "condenser.png",
            },
            {
                "id": "receiving_flask",
                "type": "flask",
                "position": [450, 380],
                "size": [90, 110],
                "image": "flask.png",
            },
            {
                "id": "thermometer",
                "type": "instrument",
                "position": [100, 100],
                "size": [30, 120],
                "image": "thermometer.png",
            },
        ],
        "clickable_items": [
            {
                "id": "alcohol_lamp",
                "type": "heater",
                "position": [50, 50],
                "size": [60, 80],
                "image": "lamp.png",
            },
            {
                "id": "mixture_sample",
                "type": "reagent",
                "position": [150, 50],
                "size": [60, 80],
                "image": "reagent_bottle.png",
            },
        ],
        "drop_zones": [
            {
                "id": "heat_area",
                "rect": [80, 450, 140, 100],
                "accepted_types": ["flask"],
            },
            {
                "id": "condenser_area",
                "rect": [220, 220, 210, 120],
                "accepted_types": ["equipment"],
            },
            {
                "id": "collection_area",
                "rect": [420, 380, 140, 150],
                "accepted_types": ["flask"],
            },
        ],
    },
    "precipitation": {
        "width": 800,
        "height": 600,
        "background_color": "#f9f9f9",
        "draggable_items": [
            {
                "id": "beaker_250ml",
                "type": "beaker",
                "position": [100, 400],
                "size": [100, 120],
                "image": "beaker.png",
            },
            {
                "id": "test_tube",
                "type": "test_tube",
                "position": [250, 380],
                "size": [50, 150],
                "image": "test_tube.png",
            },
            {
                "id": "funnel",
                "type": "equipment",
                "position": [400, 300],
                "size": [80, 80],
                "image": "funnel.png",
            },
            {
                "id": "filter_paper",
                "type": "equipment",
                "position": [100, 100],
                "size": [60, 60],
                "image": "paper.png",
            },
        ],
        "clickable_items": [
            {
                "id": "reagent_agno3",
                "type": "reagent",
                "position": [50, 50],
                "size": [60, 80],
                "image": "reagent_bottle.png",
            },
            {
                "id": "reagent_nacl",
                "type": "reagent",
                "position": [150, 50],
                "size": [60, 80],
                "image": "reagent_bottle.png",
            },
            {
                "id": "stirring_rod",
                "type": "tool",
                "position": [250, 50],
                "size": [40, 100],
                "image": "rod.png",
            },
        ],
        "drop_zones": [
            {
                "id": "mixing_area",
                "rect": [70, 380, 160, 180],
                "accepted_types": ["beaker", "test_tube"],
            },
            {
                "id": "filtration_area",
                "rect": [370, 280, 140, 140],
                "accepted_types": ["funnel", "equipment"],
            },
        ],
    },
}
