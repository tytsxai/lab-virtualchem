"""
用户反馈系统
提供实时反馈、状态提示和交互响应
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class FeedbackType(Enum):
    """反馈类型"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    LOADING = "loading"
    PROGRESS = "progress"


class FeedbackPosition(Enum):
    """反馈位置"""

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    TOP_CENTER = "top_center"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_CENTER = "bottom_center"
    CENTER = "center"
    CUSTOM = "custom"


@dataclass
class FeedbackMessage:
    """反馈消息"""

    id: str
    type: FeedbackType
    title: str
    message: str
    duration: int = 3000  # 显示时长（毫秒）
    position: FeedbackPosition = FeedbackPosition.TOP_RIGHT
    custom_position: QPoint | None = None
    actions: list[dict[str, Any]] | None = None  # 操作按钮
    persistent: bool = False  # 是否持久显示
    closable: bool = True  # 是否可关闭
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.actions is None:
            self.actions = []
        if self.metadata is None:
            self.metadata = {}


class FeedbackToast(QWidget):
    """反馈提示框"""

    closed = Signal(str)  # 消息ID
    action_clicked = Signal(str, str)  # 消息ID, 操作ID

    def __init__(self, message: FeedbackMessage, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.message = message
        self.theme_manager = ThemeManager()  # type: ignore

        # 窗口设置
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # 动画
        self.slide_animation: QPropertyAnimation | None = None
        self.fade_animation: QPropertyAnimation | None = None

        # 定时器
        self.auto_close_timer: QTimer | None = None

        self.init_ui()
        self.apply_theme()
        self.setup_animations()

        logger.debug(f"创建反馈提示框: {message.title}")

    def init_ui(self) -> None:
        """初始化UI"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 内容区域
        content_widget = QWidget()
        content_widget.setObjectName("feedbackContent")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 标题和消息
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # 图标
        self.icon_label = QLabel()
        self.icon_label.setObjectName("feedbackIcon")
        self.icon_label.setFixedSize(24, 24)
        title_layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel()
        self.title_label.setObjectName("feedbackTitle")
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_layout.addWidget(self.title_label)

        # 关闭按钮
        if self.message.closable:
            self.close_button = QPushButton("×")
            self.close_button.setObjectName("feedbackClose")
            self.close_button.setFixedSize(20, 20)
            self.close_button.clicked.connect(self.close_toast)
            title_layout.addWidget(self.close_button)

        title_layout.addStretch()
        content_layout.addLayout(title_layout)

        # 消息内容
        self.message_label = QLabel()
        self.message_label.setObjectName("feedbackMessage")
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont("Arial", 9))
        content_layout.addWidget(self.message_label)

        # 操作按钮
        if self.message.actions:
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(6)

            for action in self.message.actions:
                button = ModernButton(action.get("text", "操作"))
                button.setObjectName("feedbackAction")
                button.clicked.connect(lambda _, a=action: self.on_action_clicked(a))
                actions_layout.addWidget(button)

            actions_layout.addStretch()
            content_layout.addLayout(actions_layout)

        layout.addWidget(content_widget)

        # 设置内容
        self.update_content()

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        content_widget.setGraphicsEffect(shadow)

    def update_content(self) -> None:
        """更新内容"""
        # 设置图标
        icon_map = {
            FeedbackType.SUCCESS: "✅",
            FeedbackType.ERROR: "❌",
            FeedbackType.WARNING: "⚠️",
            FeedbackType.INFO: "ℹ️",
            FeedbackType.LOADING: "⏳",
            FeedbackType.PROGRESS: "📊",
        }

        self.icon_label.setText(icon_map.get(self.message.type, "ℹ️"))

        # 设置文本
        self.title_label.setText(self.message.title)
        self.message_label.setText(self.message.message)

    def apply_theme(self) -> None:
        """应用主题"""
        # 根据反馈类型设置颜色
        color_map = {
            FeedbackType.SUCCESS: "#4CAF50",
            FeedbackType.ERROR: "#F44336",
            FeedbackType.WARNING: "#FF9800",
            FeedbackType.INFO: "#2196F3",
            FeedbackType.LOADING: "#9C27B0",
            FeedbackType.PROGRESS: "#607D8B",
        }

        primary_color = color_map.get(self.message.type, "#2196F3")

        try:
            self.setStyleSheet(
                f"""
                QWidget {{
                    background-color: rgba(26, 26, 46, 0.95);
                    border: 1px solid {primary_color};
                    border-radius: 8px;
                    color: #ffffff;
                }}
                QLabel#feedbackIcon {{
                    color: {primary_color};
                    font-size: 16px;
                }}
                QLabel#feedbackTitle {{
                    color: {primary_color};
                    font-weight: bold;
                }}
                QLabel#feedbackMessage {{
                    color: #ffffff;
                    line-height: 1.3;
                }}
                QPushButton#feedbackClose {{
                    background-color: transparent;
                    border: none;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton#feedbackClose:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }}
                QPushButton#feedbackAction {{
                    background-color: {primary_color};
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 4px 8px;
                    font-size: 9px;
                }}
                QPushButton#feedbackAction:hover {{
                    background-color: {self._darken_color(primary_color)};
                }}
            """
            )

            logger.debug(f"应用反馈主题: {self.message.type}")

        except Exception as e:
            logger.warning(f"应用反馈主题失败: {e}")

    def _darken_color(self, color: str) -> str:
        """加深颜色"""
        # 简单的颜色加深逻辑
        if color.startswith("#"):
            color = color[1:]

        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)

            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color

    def setup_animations(self) -> None:
        """设置动画"""
        # 自动关闭定时器
        if not self.message.persistent and self.message.duration > 0:
            self.auto_close_timer = QTimer(self)
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.close_toast)
            self.auto_close_timer.start(self.message.duration)

    def show_toast(self) -> None:
        """显示提示框"""
        # 计算位置
        position = self.calculate_position()
        self.move(position)

        # 显示动画
        self.show()
        self.slide_in()

    def calculate_position(self) -> QPoint:
        """计算位置"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # 获取提示框尺寸
        self.adjustSize()
        toast_size = self.size()

        margin = 20

        if self.message.position == FeedbackPosition.TOP_LEFT:
            return QPoint(margin, margin)
        elif self.message.position == FeedbackPosition.TOP_RIGHT:
            return QPoint(screen_geometry.width() - toast_size.width() - margin, margin)
        elif self.message.position == FeedbackPosition.TOP_CENTER:
            return QPoint((screen_geometry.width() - toast_size.width()) // 2, margin)
        elif self.message.position == FeedbackPosition.BOTTOM_LEFT:
            return QPoint(
                margin, screen_geometry.height() - toast_size.height() - margin
            )
        elif self.message.position == FeedbackPosition.BOTTOM_RIGHT:
            return QPoint(
                screen_geometry.width() - toast_size.width() - margin,
                screen_geometry.height() - toast_size.height() - margin,
            )
        elif self.message.position == FeedbackPosition.BOTTOM_CENTER:
            return QPoint(
                (screen_geometry.width() - toast_size.width()) // 2,
                screen_geometry.height() - toast_size.height() - margin,
            )
        elif self.message.position == FeedbackPosition.CENTER:
            return QPoint(
                (screen_geometry.width() - toast_size.width()) // 2,
                (screen_geometry.height() - toast_size.height()) // 2,
            )
        elif (
            self.message.position == FeedbackPosition.CUSTOM
            and self.message.custom_position
        ):
            return self.message.custom_position
        else:
            # 默认右上角
            return QPoint(screen_geometry.width() - toast_size.width() - margin, margin)

    def slide_in(self) -> None:
        """滑入动画"""
        if self.message.position in [
            FeedbackPosition.TOP_RIGHT,
            FeedbackPosition.BOTTOM_RIGHT,
        ]:
            # 从右侧滑入
            start_pos = QPoint(self.x() + self.width(), self.y())
            end_pos = QPoint(self.x(), self.y())
        elif self.message.position in [
            FeedbackPosition.TOP_LEFT,
            FeedbackPosition.BOTTOM_LEFT,
        ]:
            # 从左侧滑入
            start_pos = QPoint(self.x() - self.width(), self.y())
            end_pos = QPoint(self.x(), self.y())
        else:
            # 淡入
            self.fade_in()
            return

        self.move(start_pos)

        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setStartValue(start_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_animation.start()

    def slide_out(self) -> None:
        """滑出动画"""
        if self.message.position in [
            FeedbackPosition.TOP_RIGHT,
            FeedbackPosition.BOTTOM_RIGHT,
        ]:
            # 向右侧滑出
            end_pos = QPoint(self.x() + self.width(), self.y())
        elif self.message.position in [
            FeedbackPosition.TOP_LEFT,
            FeedbackPosition.BOTTOM_LEFT,
        ]:
            # 向左侧滑出
            end_pos = QPoint(self.x() - self.width(), self.y())
        else:
            # 淡出
            self.fade_out()
            return

        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setStartValue(self.pos())
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_animation.finished.connect(self.close)
        self.slide_animation.start()

    def fade_in(self) -> None:
        """淡入动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def fade_out(self) -> None:
        """淡出动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()

    def close_toast(self) -> None:
        """关闭提示框"""
        if self.auto_close_timer:
            self.auto_close_timer.stop()

        self.slide_out()
        self.closed.emit(self.message.id)

    def on_action_clicked(self, action: dict[str, Any]) -> None:
        """操作按钮点击"""
        action_id = action.get("id", "unknown")
        self.action_clicked.emit(self.message.id, action_id)

        # 执行回调
        callback = action.get("callback")
        if callback and callable(callback):
            try:
                callback()
            except Exception as e:
                logger.error(f"执行反馈操作回调失败: {e}")

        # 如果操作后应该关闭，则关闭提示框
        if action.get("close_after", True):
            self.close_toast()


class FeedbackManager:
    """反馈管理器"""

    def __init__(self) -> None:
        self.active_toasts: dict[str, FeedbackToast] = {}
        self.toast_counter = 0
        self.max_toasts = 5  # 最大同时显示数量

        logger.info("反馈管理器初始化完成")

    def show_message(
        self,
        type: FeedbackType,
        title: str,
        message: str,
        duration: int = 3000,
        position: FeedbackPosition = FeedbackPosition.TOP_RIGHT,
        custom_position: QPoint | None = None,
        actions: list[dict[str, Any]] | None = None,
        persistent: bool = False,
        closable: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """显示反馈消息"""
        # 生成消息ID
        self.toast_counter += 1
        message_id = f"toast_{self.toast_counter}"

        # 创建消息
        feedback_message = FeedbackMessage(
            id=message_id,
            type=type,
            title=title,
            message=message,
            duration=duration,
            position=position,
            custom_position=custom_position,
            actions=actions or [],
            persistent=persistent,
            closable=closable,
            metadata=metadata or {},
        )

        # 检查最大数量限制
        if len(self.active_toasts) >= self.max_toasts:
            # 关闭最旧的消息
            oldest_id = min(
                self.active_toasts.keys(), key=lambda k: int(k.split("_")[1])
            )
            self.close_message(oldest_id)

        # 创建提示框
        toast = FeedbackToast(feedback_message)

        # 连接信号
        toast.closed.connect(self.on_toast_closed)
        toast.action_clicked.connect(self.on_action_clicked)

        # 添加到活跃列表
        self.active_toasts[message_id] = toast

        # 显示提示框
        toast.show_toast()

        logger.info(f"显示反馈消息: {title} ({type.value})")
        return message_id

    def show_success(self, title: str, message: str, **kwargs: Any) -> str:
        """显示成功消息"""
        return self.show_message(FeedbackType.SUCCESS, title, message, **kwargs)

    def show_error(self, title: str, message: str, **kwargs: Any) -> str:
        """显示错误消息"""
        return self.show_message(FeedbackType.ERROR, title, message, **kwargs)

    def show_warning(self, title: str, message: str, **kwargs: Any) -> str:
        """显示警告消息"""
        return self.show_message(FeedbackType.WARNING, title, message, **kwargs)

    def show_info(self, title: str, message: str, **kwargs: Any) -> str:
        """显示信息消息"""
        return self.show_message(FeedbackType.INFO, title, message, **kwargs)

    def show_loading(self, title: str, message: str, **kwargs: Any) -> str:
        """显示加载消息"""
        return self.show_message(
            FeedbackType.LOADING, title, message, persistent=True, **kwargs
        )

    def show_progress(
        self, title: str, message: str, progress: float = 0.0, **kwargs: Any
    ) -> str:
        """显示进度消息"""
        progress_text = f"{message}\n进度: {progress:.1%}"
        return self.show_message(
            FeedbackType.PROGRESS, title, progress_text, persistent=True, **kwargs
        )

    def close_message(self, message_id: str) -> bool:
        """关闭消息"""
        if message_id in self.active_toasts:
            toast = self.active_toasts[message_id]
            toast.close_toast()
            return True
        return False

    def close_all_messages(self) -> None:
        """关闭所有消息"""
        for message_id in list(self.active_toasts.keys()):
            self.close_message(message_id)

    def on_toast_closed(self, message_id: str) -> None:
        """提示框关闭处理"""
        if message_id in self.active_toasts:
            del self.active_toasts[message_id]
            logger.debug(f"反馈消息已关闭: {message_id}")

    def on_action_clicked(self, message_id: str, action_id: str) -> None:
        """操作点击处理"""
        logger.debug(f"反馈操作点击: {message_id} - {action_id}")

    def get_active_count(self) -> int:
        """获取活跃消息数量"""
        return len(self.active_toasts)


class StatusBarFeedback:
    """状态栏反馈"""

    def __init__(self, status_bar: Any) -> None:
        self.status_bar = status_bar
        self.message_timer: QTimer | None = None

        logger.info("状态栏反馈初始化完成")

    def show_message(self, message: str, duration: int = 3000) -> None:
        """显示状态栏消息"""
        self.status_bar.showMessage(message)

        # 设置定时清除
        if self.message_timer:
            self.message_timer.stop()

        if duration > 0:
            self.message_timer = QTimer(self.status_bar)
            self.message_timer.setSingleShot(True)
            self.message_timer.timeout.connect(lambda: self.status_bar.clearMessage())
            self.message_timer.start(duration)

    def show_success(self, message: str, duration: int = 3000) -> None:
        """显示成功状态"""
        self.show_message(f"✅ {message}", duration)

    def show_error(self, message: str, duration: int = 5000) -> None:
        """显示错误状态"""
        self.show_message(f"❌ {message}", duration)

    def show_warning(self, message: str, duration: int = 4000) -> None:
        """显示警告状态"""
        self.show_message(f"⚠️ {message}", duration)

    def show_info(self, message: str, duration: int = 3000) -> None:
        """显示信息状态"""
        self.show_message(f"ℹ️ {message}", duration)

    def show_loading(self, message: str) -> None:
        """显示加载状态"""
        self.show_message(f"⏳ {message}", 0)  # 持久显示

    def clear(self) -> None:
        """清除状态栏消息"""
        self.status_bar.clearMessage()
        if self.message_timer:
            self.message_timer.stop()


# 全局反馈管理器实例
_feedback_manager: FeedbackManager | None = None


def get_feedback_manager() -> FeedbackManager:
    """获取全局反馈管理器"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager


# 便捷函数
def show_success(title: str, message: str, **kwargs: Any) -> str:
    """显示成功消息"""
    return get_feedback_manager().show_success(title, message, **kwargs)


def show_error(title: str, message: str, **kwargs: Any) -> str:
    """显示错误消息"""
    return get_feedback_manager().show_error(title, message, **kwargs)


def show_warning(title: str, message: str, **kwargs: Any) -> str:
    """显示警告消息"""
    return get_feedback_manager().show_warning(title, message, **kwargs)


def show_info(title: str, message: str, **kwargs: Any) -> str:
    """显示信息消息"""
    return get_feedback_manager().show_info(title, message, **kwargs)


def show_loading(title: str, message: str, **kwargs: Any) -> str:
    """显示加载消息"""
    return get_feedback_manager().show_loading(title, message, **kwargs)


def show_progress(
    title: str, message: str, progress: float = 0.0, **kwargs: Any
) -> str:
    """显示进度消息"""
    return get_feedback_manager().show_progress(title, message, progress, **kwargs)
