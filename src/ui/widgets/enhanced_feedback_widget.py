"""
增强反馈控件
提供视觉、动画和声音反馈的组合控件

功能:
1. 多种反馈类型（成功、失败、警告、信息）
2. 动画效果（淡入淡出、抖动、脉冲）
3. 自动隐藏
4. 操作建议
5. 帮助链接
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackType:
    """反馈类型"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    VALIDATING = "validating"


class EnhancedFeedbackWidget(QWidget):
    """增强反馈控件"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_type = FeedbackType.INFO
        self.auto_hide_timer: QTimer | None = None
        self.help_callback: Callable | None = None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 主反馈区域
        self.feedback_container = QWidget()
        self.feedback_container.setObjectName("feedbackContainer")

        feedback_layout = QHBoxLayout(self.feedback_container)
        feedback_layout.setContentsMargins(15, 12, 15, 12)
        feedback_layout.setSpacing(10)

        # 图标
        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("font-size: 20px;")
        feedback_layout.addWidget(self.icon_label)

        # 消息
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("font-size: 13px;")
        feedback_layout.addWidget(self.message_label, 1)

        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 12px;
            }
        """
        )
        self.close_btn.clicked.connect(self.hide_feedback)
        feedback_layout.addWidget(self.close_btn)

        layout.addWidget(self.feedback_container)

        # 帮助/建议区域（可选）
        self.help_widget = QWidget()
        self.help_widget.setObjectName("helpWidget")
        help_layout = QHBoxLayout(self.help_widget)
        help_layout.setContentsMargins(15, 10, 15, 10)

        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("font-size: 12px; color: #666;")
        help_layout.addWidget(self.help_label, 1)

        self.help_btn = QPushButton("💡 获取帮助")
        self.help_btn.clicked.connect(self.on_help_clicked)
        self.help_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e3f2fd;
                color: #1976d2;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
        """
        )
        help_layout.addWidget(self.help_btn)

        layout.addWidget(self.help_widget)
        self.help_widget.hide()

        # 初始隐藏
        self.hide()

    def show_feedback(
        self,
        message: str,
        feedback_type: str = FeedbackType.INFO,
        auto_hide: bool = True,
        duration: int = 3000,
        help_text: str | None = None,
        help_callback: Callable | None = None,
    ):
        """
        显示反馈

        Args:
            message: 反馈消息
            feedback_type: 反馈类型
            auto_hide: 是否自动隐藏
            duration: 显示时长（毫秒）
            help_text: 帮助文本
            help_callback: 帮助回调
        """
        self.current_type = feedback_type
        self.help_callback = help_callback

        # 更新内容
        self.message_label.setText(message)

        # 设置图标
        icons = {
            FeedbackType.SUCCESS: "✓",
            FeedbackType.ERROR: "✗",
            FeedbackType.WARNING: "⚠",
            FeedbackType.INFO: "ℹ",
            FeedbackType.VALIDATING: "⏳",
        }
        self.icon_label.setText(icons.get(feedback_type, "ℹ"))

        # 设置样式
        styles = {
            FeedbackType.SUCCESS: """
                QWidget#feedbackContainer {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-left: 4px solid #28a745;
                    border-radius: 5px;
                }
                QLabel { color: #155724; }
            """,
            FeedbackType.ERROR: """
                QWidget#feedbackContainer {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-left: 4px solid #dc3545;
                    border-radius: 5px;
                }
                QLabel { color: #721c24; }
            """,
            FeedbackType.WARNING: """
                QWidget#feedbackContainer {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-left: 4px solid #ffc107;
                    border-radius: 5px;
                }
                QLabel { color: #856404; }
            """,
            FeedbackType.INFO: """
                QWidget#feedbackContainer {
                    background-color: #d1ecf1;
                    border: 1px solid #bee5eb;
                    border-left: 4px solid #17a2b8;
                    border-radius: 5px;
                }
                QLabel { color: #0c5460; }
            """,
            FeedbackType.VALIDATING: """
                QWidget#feedbackContainer {
                    background-color: #e7f3ff;
                    border: 1px solid #b3d9ff;
                    border-left: 4px solid #2196F3;
                    border-radius: 5px;
                }
                QLabel { color: #004085; }
            """,
        }
        self.feedback_container.setStyleSheet(
            styles.get(feedback_type, styles[FeedbackType.INFO])
        )

        # 帮助区域
        if help_text and help_callback:
            self.help_label.setText(help_text)
            self.help_widget.show()
        else:
            self.help_widget.hide()

        # 显示动画
        self.show()
        self.fade_in()

        # 震动动画（错误时）
        if feedback_type == FeedbackType.ERROR:
            self.shake_animation()

        # 脉冲动画（成功时）
        elif feedback_type == FeedbackType.SUCCESS:
            self.pulse_animation()

        # 自动隐藏
        if auto_hide:
            if self.auto_hide_timer:
                self.auto_hide_timer.stop()

            self.auto_hide_timer = QTimer(self)
            self.auto_hide_timer.setSingleShot(True)
            self.auto_hide_timer.timeout.connect(self.hide_feedback)
            self.auto_hide_timer.start(duration)

        logger.debug(f"显示反馈: {feedback_type} - {message}")

    def hide_feedback(self):
        """隐藏反馈"""
        self.fade_out()

    def on_help_clicked(self):
        """帮助按钮点击"""
        if self.help_callback:
            self.help_callback()
            logger.info("用户请求帮助")

    def fade_in(self):
        """淡入动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_anim = QPropertyAnimation(effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.start()

    def fade_out(self):
        """淡出动画"""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_anim = QPropertyAnimation(effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_anim.finished.connect(self.hide)
        self.fade_anim.start()

    def shake_animation(self):
        """抖动动画"""
        # 保存原始位置
        original_pos = self.pos()

        # 创建动画组
        anim_group = QSequentialAnimationGroup(self)

        # 抖动序列
        shake_distance = 10
        shake_duration = 50

        for i in range(4):
            # 向左
            anim1 = QPropertyAnimation(self, b"pos")
            anim1.setDuration(shake_duration)
            anim1.setEndValue(
                QPoint(original_pos.x() - shake_distance, original_pos.y())
            )
            anim_group.addAnimation(anim1)

            # 向右
            anim2 = QPropertyAnimation(self, b"pos")
            anim2.setDuration(shake_duration)
            anim2.setEndValue(
                QPoint(original_pos.x() + shake_distance, original_pos.y())
            )
            anim_group.addAnimation(anim2)

        # 回到原位
        anim_final = QPropertyAnimation(self, b"pos")
        anim_final.setDuration(shake_duration)
        anim_final.setEndValue(original_pos)
        anim_group.addAnimation(anim_final)

        anim_group.start()

    def pulse_animation(self):
        """脉冲动画"""
        # 背景闪烁

        def flash():
            # 高亮
            highlight_style = (
                self.feedback_container.styleSheet()
                + """
                background-color: #b8e6b8;
            """
            )
            self.feedback_container.setStyleSheet(highlight_style)

            # 延迟恢复
            QTimer.singleShot(
                200,
                lambda: self.feedback_container.setStyleSheet(
                    self.feedback_container.styleSheet()
                ),
            )

        # 闪烁两次
        QTimer.singleShot(0, flash)
        QTimer.singleShot(300, flash)


class FeedbackOverlay(QWidget):
    """反馈浮层（用于全屏提示）"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 创建反馈控件
        self.feedback_widget = EnhancedFeedbackWidget(self)

        # 调整大小以匹配父控件
        self.resize(parent.size())

        # 初始隐藏
        self.hide()

    def show_toast(
        self,
        message: str,
        feedback_type: str = FeedbackType.INFO,
        duration: int = 2000,
        position: str = "top",
    ):
        """
        显示Toast提示

        Args:
            message: 提示消息
            feedback_type: 反馈类型
            duration: 显示时长
            position: 位置（top, center, bottom）
        """
        # 设置反馈内容
        self.feedback_widget.show_feedback(
            message, feedback_type, auto_hide=True, duration=duration
        )

        # 计算位置
        parent_rect = self.parent().rect()
        widget_size = self.feedback_widget.sizeHint()

        if position == "top":
            x = (parent_rect.width() - widget_size.width()) // 2
            y = 20
        elif position == "center":
            x = (parent_rect.width() - widget_size.width()) // 2
            y = (parent_rect.height() - widget_size.height()) // 2
        else:  # bottom
            x = (parent_rect.width() - widget_size.width()) // 2
            y = parent_rect.height() - widget_size.height() - 20

        self.feedback_widget.move(x, y)

        # 显示
        self.show()
        self.raise_()

        # 自动隐藏浮层
        QTimer.singleShot(duration + 500, self.hide)

    def resizeEvent(self, event):
        """调整大小事件"""
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())


# 便捷函数
def show_success_feedback(
    parent: QWidget,
    message: str,
    help_text: str | None = None,
    help_callback: Callable | None = None,
):
    """显示成功反馈"""
    feedback = EnhancedFeedbackWidget(parent)
    feedback.show_feedback(
        message, FeedbackType.SUCCESS, help_text=help_text, help_callback=help_callback
    )
    return feedback


def show_error_feedback(
    parent: QWidget,
    message: str,
    help_text: str | None = None,
    help_callback: Callable | None = None,
):
    """显示错误反馈"""
    feedback = EnhancedFeedbackWidget(parent)
    feedback.show_feedback(
        message, FeedbackType.ERROR, help_text=help_text, help_callback=help_callback
    )
    return feedback


def show_warning_feedback(parent: QWidget, message: str):
    """显示警告反馈"""
    feedback = EnhancedFeedbackWidget(parent)
    feedback.show_feedback(message, FeedbackType.WARNING)
    return feedback


def show_toast(
    parent: QWidget,
    message: str,
    feedback_type: str = FeedbackType.INFO,
    duration: int = 2000,
    position: str = "top",
):
    """显示Toast提示"""
    overlay = FeedbackOverlay(parent)
    overlay.show_toast(message, feedback_type, duration, position)
    return overlay
