"""
手势控制器
支持多点触控、自定义手势识别等高级交互
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, QPointF, Qt, Signal
from PySide6.QtGui import QTouchEvent

from ..utils.logger import get_logger

logger = get_logger(__name__)


class GestureType(Enum):
    """手势类型"""

    TAP = "tap"  # 单击
    DOUBLE_TAP = "double_tap"  # 双击
    LONG_PRESS = "long_press"  # 长按
    SWIPE = "swipe"  # 滑动
    PINCH = "pinch"  # 捏合/缩放
    ROTATE = "rotate"  # 旋转
    PAN = "pan"  # 平移
    THREE_FINGER_SWIPE = "three_finger_swipe"  # 三指滑动
    CUSTOM = "custom"  # 自定义手势


class SwipeDirection(Enum):
    """滑动方向"""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass
class GestureEvent:
    """手势事件数据"""

    gesture_type: GestureType
    position: QPointF
    delta: QPointF = QPointF(0, 0)
    scale: float = 1.0
    rotation: float = 0.0
    direction: SwipeDirection | None = None
    velocity: float = 0.0
    timestamp: float = 0.0
    custom_data: dict[str, Any] | None = None


@dataclass
class TouchPoint:
    """触摸点数据"""

    id: int
    position: QPointF
    last_position: QPointF
    timestamp: float
    pressed: bool = True


class GestureRecognizer(QObject):
    """手势识别器"""

    # 信号
    gesture_recognized = Signal(GestureEvent)
    tap_detected = Signal(QPointF)
    double_tap_detected = Signal(QPointF)
    long_press_detected = Signal(QPointF)
    swipe_detected = Signal(SwipeDirection, float)  # 方向, 速度
    pinch_detected = Signal(float, QPointF)  # 缩放比例, 中心点
    rotate_detected = Signal(float, QPointF)  # 旋转角度, 中心点
    pan_detected = Signal(QPointF)  # 位移

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 触摸点跟踪
        self.touch_points: dict[int, TouchPoint] = {}

        # 手势参数
        self.tap_threshold = 200  # 毫秒
        self.double_tap_threshold = 300  # 毫秒
        self.long_press_threshold = 500  # 毫秒
        self.swipe_threshold = 50  # 像素
        self.swipe_velocity_threshold = 100  # 像素/秒
        self.pinch_threshold = 10  # 像素
        self.rotation_threshold = 5  # 度

        # 状态跟踪
        self.last_tap_time = 0.0
        self.last_tap_pos = QPointF()
        self.press_start_time = 0.0
        self.press_start_pos = QPointF()
        self.initial_distance = 0.0
        self.initial_rotation = 0.0

        # 自定义手势
        self.custom_gestures: dict[str, Callable[[list[QPointF]], bool]] = {}

        logger.info("手势识别器初始化完成")

    def process_touch_event(self, event: QTouchEvent) -> None:
        """处理触摸事件"""
        current_time = time.time()

        # 更新触摸点
        touch_points = event.points()
        active_points: list[QPointF] = []

        for point in touch_points:
            point_id = point.id()
            position = point.position()

            if point.state() == Qt.TouchPointState.TouchPointPressed:  # type: ignore
                # 新触摸点
                self.touch_points[point_id] = TouchPoint(
                    id=point_id, position=position, last_position=position, timestamp=current_time, pressed=True
                )

                # 记录按压开始
                if len(self.touch_points) == 1:
                    self.press_start_time = current_time
                    self.press_start_pos = position

            elif point.state() == Qt.TouchPointState.TouchPointMoved:  # type: ignore
                # 触摸点移动
                if point_id in self.touch_points:
                    touch = self.touch_points[point_id]
                    touch.last_position = touch.position
                    touch.position = position
                    active_points.append(position)

            elif point.state() == Qt.TouchPointState.TouchPointReleased:  # type: ignore
                # 触摸点释放
                if point_id in self.touch_points:
                    touch = self.touch_points[point_id]
                    touch.pressed = False

                    # 检测手势
                    self._detect_gesture(touch, current_time)

                    # 清理触摸点
                    del self.touch_points[point_id]

        # 多点触控手势检测
        if len(active_points) >= 2:
            self._detect_multi_touch_gesture(active_points, current_time)

    def _detect_gesture(self, touch: TouchPoint, current_time: float) -> None:
        """检测单点手势"""
        duration = current_time - touch.timestamp
        delta = touch.position - touch.last_position
        distance = math.sqrt(delta.x() ** 2 + delta.y() ** 2)

        # 检测长按
        if duration >= self.long_press_threshold / 1000 and distance < 10:
            event = GestureEvent(gesture_type=GestureType.LONG_PRESS, position=touch.position, timestamp=current_time)
            self.gesture_recognized.emit(event)
            self.long_press_detected.emit(touch.position)
            logger.debug(f"检测到长按手势: {touch.position}")
            return

        # 检测滑动
        if distance >= self.swipe_threshold:
            velocity = distance / max(duration, 0.001)
            if velocity >= self.swipe_velocity_threshold:
                direction = self._get_swipe_direction(delta)
                event = GestureEvent(
                    gesture_type=GestureType.SWIPE,
                    position=touch.position,
                    delta=delta,
                    direction=direction,
                    velocity=velocity,
                    timestamp=current_time,
                )
                self.gesture_recognized.emit(event)
                self.swipe_detected.emit(direction, velocity)
                logger.debug(f"检测到滑动手势: {direction.value}, 速度: {velocity:.2f}")
                return

        # 检测点击
        if duration < self.tap_threshold / 1000 and distance < 10:
            # 检测双击
            time_since_last_tap = current_time - self.last_tap_time
            distance_from_last_tap = math.sqrt(
                (touch.position.x() - self.last_tap_pos.x()) ** 2 + (touch.position.y() - self.last_tap_pos.y()) ** 2
            )

            if time_since_last_tap < self.double_tap_threshold / 1000 and distance_from_last_tap < 50:
                event = GestureEvent(
                    gesture_type=GestureType.DOUBLE_TAP, position=touch.position, timestamp=current_time
                )
                self.gesture_recognized.emit(event)
                self.double_tap_detected.emit(touch.position)
                logger.debug(f"检测到双击手势: {touch.position}")
                self.last_tap_time = 0  # 重置以避免三连击
            else:
                event = GestureEvent(gesture_type=GestureType.TAP, position=touch.position, timestamp=current_time)
                self.gesture_recognized.emit(event)
                self.tap_detected.emit(touch.position)
                logger.debug(f"检测到点击手势: {touch.position}")
                self.last_tap_time = current_time
                self.last_tap_pos = touch.position

    def _detect_multi_touch_gesture(self, points: list[QPointF], current_time: float) -> None:
        """检测多点触控手势"""
        if len(points) < 2:
            return

        # 计算中心点
        center = QPointF(sum(p.x() for p in points) / len(points), sum(p.y() for p in points) / len(points))

        # 双指捏合/缩放
        if len(points) == 2:
            current_distance = self._calculate_distance(points[0], points[1])

            if self.initial_distance == 0:
                self.initial_distance = current_distance
            else:
                scale = current_distance / self.initial_distance
                if abs(scale - 1.0) > 0.1:  # 10% 变化阈值
                    event = GestureEvent(
                        gesture_type=GestureType.PINCH, position=center, scale=scale, timestamp=current_time
                    )
                    self.gesture_recognized.emit(event)
                    self.pinch_detected.emit(scale, center)
                    logger.debug(f"检测到缩放手势: {scale:.2f}x")

            # 旋转检测
            current_angle = self._calculate_angle(points[0], points[1])
            if self.initial_rotation == 0:
                self.initial_rotation = current_angle
            else:
                rotation = current_angle - self.initial_rotation
                if abs(rotation) > self.rotation_threshold:
                    event = GestureEvent(
                        gesture_type=GestureType.ROTATE, position=center, rotation=rotation, timestamp=current_time
                    )
                    self.gesture_recognized.emit(event)
                    self.rotate_detected.emit(rotation, center)
                    logger.debug(f"检测到旋转手势: {rotation:.2f}度")

        # 三指滑动
        elif len(points) == 3:
            # 计算平均移动
            total_delta_x = 0.0
            total_delta_y = 0.0
            for _point_id, touch in self.touch_points.items():
                if touch.pressed:
                    delta = touch.position - touch.last_position
                    total_delta_x += delta.x()
                    total_delta_y += delta.y()

            avg_delta = QPointF(total_delta_x / len(points), total_delta_y / len(points))
            distance = math.sqrt(avg_delta.x() ** 2 + avg_delta.y() ** 2)

            if distance >= self.swipe_threshold:
                direction = self._get_swipe_direction(avg_delta)
                event = GestureEvent(
                    gesture_type=GestureType.THREE_FINGER_SWIPE,
                    position=center,
                    delta=avg_delta,
                    direction=direction,
                    timestamp=current_time,
                )
                self.gesture_recognized.emit(event)
                logger.debug(f"检测到三指滑动: {direction.value}")

    def _get_swipe_direction(self, delta: QPointF) -> SwipeDirection:
        """获取滑动方向"""
        abs_x = abs(delta.x())
        abs_y = abs(delta.y())

        if abs_x > abs_y:
            return SwipeDirection.RIGHT if delta.x() > 0 else SwipeDirection.LEFT
        else:
            return SwipeDirection.DOWN if delta.y() > 0 else SwipeDirection.UP

    def _calculate_distance(self, p1: QPointF, p2: QPointF) -> float:
        """计算两点间距离"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.sqrt(dx * dx + dy * dy)

    def _calculate_angle(self, p1: QPointF, p2: QPointF) -> float:
        """计算两点间角度（度）"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.degrees(math.atan2(dy, dx))

    def register_custom_gesture(self, name: str, recognizer: Callable[[list[QPointF]], bool]) -> None:
        """注册自定义手势识别器"""
        self.custom_gestures[name] = recognizer
        logger.info(f"注册自定义手势: {name}")

    def reset(self) -> None:
        """重置手势状态"""
        self.touch_points.clear()
        self.initial_distance = 0.0
        self.initial_rotation = 0.0
        logger.debug("手势识别器状态已重置")


class GestureController(QObject):
    """手势控制器 - 管理手势与动作的绑定"""

    # 信号
    action_triggered = Signal(str, GestureEvent)  # 动作名称, 手势事件

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.recognizer = GestureRecognizer(self)
        self.gesture_bindings: dict[GestureType, list[str]] = {}
        self.action_handlers: dict[str, Callable[[GestureEvent], None]] = {}

        # 连接信号
        self.recognizer.gesture_recognized.connect(self._on_gesture_recognized)

        # 默认绑定
        self._setup_default_bindings()

        logger.info("手势控制器初始化完成")

    def _setup_default_bindings(self) -> None:
        """设置默认手势绑定"""
        # 单击 - 选择
        self.bind_gesture(GestureType.TAP, "select_item")

        # 双击 - 确认/放大
        self.bind_gesture(GestureType.DOUBLE_TAP, "confirm_action")
        self.bind_gesture(GestureType.DOUBLE_TAP, "zoom_in")

        # 长按 - 上下文菜单
        self.bind_gesture(GestureType.LONG_PRESS, "show_context_menu")

        # 滑动 - 切换/滚动
        self.bind_gesture(GestureType.SWIPE, "navigate")

        # 捏合 - 缩放
        self.bind_gesture(GestureType.PINCH, "zoom")

        # 旋转 - 旋转物体
        self.bind_gesture(GestureType.ROTATE, "rotate_object")

        # 三指滑动 - 切换实验步骤
        self.bind_gesture(GestureType.THREE_FINGER_SWIPE, "switch_step")

    def bind_gesture(self, gesture_type: GestureType, action_name: str) -> None:
        """绑定手势到动作"""
        if gesture_type not in self.gesture_bindings:
            self.gesture_bindings[gesture_type] = []

        if action_name not in self.gesture_bindings[gesture_type]:
            self.gesture_bindings[gesture_type].append(action_name)
            logger.info(f"绑定手势 {gesture_type.value} 到动作 {action_name}")

    def unbind_gesture(self, gesture_type: GestureType, action_name: str) -> None:
        """解绑手势"""
        if gesture_type in self.gesture_bindings:
            if action_name in self.gesture_bindings[gesture_type]:
                self.gesture_bindings[gesture_type].remove(action_name)
                logger.info(f"解绑手势 {gesture_type.value} 从动作 {action_name}")

    def register_action(self, action_name: str, handler: Callable[[GestureEvent], None]) -> None:
        """注册动作处理器"""
        self.action_handlers[action_name] = handler
        logger.info(f"注册动作处理器: {action_name}")

    def _on_gesture_recognized(self, event: GestureEvent) -> None:
        """处理识别到的手势"""
        if event.gesture_type in self.gesture_bindings:
            actions = self.gesture_bindings[event.gesture_type]
            for action_name in actions:
                # 触发信号
                self.action_triggered.emit(action_name, event)

                # 执行处理器
                if action_name in self.action_handlers:
                    try:
                        self.action_handlers[action_name](event)
                        logger.debug(f"执行动作: {action_name}")
                    except Exception as e:
                        logger.error(f"执行动作 {action_name} 失败: {e}", exc_info=True)

    def process_touch_event(self, event: QTouchEvent) -> None:
        """处理触摸事件"""
        self.recognizer.process_touch_event(event)

    def get_bindings(self) -> dict[str, list[str]]:
        """获取当前手势绑定"""
        return {gesture_type.value: actions for gesture_type, actions in self.gesture_bindings.items()}

    def save_bindings(self, filepath: str) -> None:
        """保存手势绑定配置"""
        import json

        bindings_data = {gesture_type.value: actions for gesture_type, actions in self.gesture_bindings.items()}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(bindings_data, f, indent=2, ensure_ascii=False)

        logger.info(f"手势绑定已保存到: {filepath}")

    def load_bindings(self, filepath: str) -> None:
        """加载手势绑定配置"""
        import json

        with open(filepath, encoding="utf-8") as f:
            bindings_data = json.load(f)

        self.gesture_bindings.clear()
        for gesture_str, actions in bindings_data.items():
            gesture_type = GestureType(gesture_str)
            self.gesture_bindings[gesture_type] = actions

        logger.info(f"手势绑定已从 {filepath} 加载")
