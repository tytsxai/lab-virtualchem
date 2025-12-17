"""
现代化UI组件库
Material Design风格的自定义控件
支持Windows和Android平台
"""

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ModernButton(QPushButton):
    """现代化按钮（支持涟漪效果）"""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self._ripple_radius = 0
        self.ripple_x = 0
        self.ripple_y = 0
        self.ripple_animation = None

        # 设置最小高度
        self.setMinimumHeight(36)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标点击时触发涟漪效果"""
        super().mousePressEvent(event)

        # 记录点击位置
        self.ripple_x = event.pos().x()
        self.ripple_y = event.pos().y()

        # 创建涟漪动画
        if self.ripple_animation:
            self.ripple_animation.stop()

        self.ripple_animation = QPropertyAnimation(self, b"ripple_radius")
        self.ripple_animation.setDuration(400)
        self.ripple_animation.setStartValue(0)
        self.ripple_animation.setEndValue(max(self.width(), self.height()) * 1.5)
        self.ripple_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.ripple_animation.start()

    def paintEvent(self, event: QPaintEvent):
        """绘制涟漪效果"""
        super().paintEvent(event)

        if self.ripple_radius > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # 半透明白色涟漪
            color = QColor(255, 255, 255, 50)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)

            painter.drawEllipse(
                self.ripple_x - self.ripple_radius,
                self.ripple_y - self.ripple_radius,
                self.ripple_radius * 2,
                self.ripple_radius * 2,
            )

    def get_ripple_radius(self):
        return self._ripple_radius

    def set_ripple_radius(self, value):
        self._ripple_radius = value
        self.update()

    ripple_radius = Property(int, get_ripple_radius, set_ripple_radius)


class Card(QFrame):
    """卡片组件（Material Design风格）"""

    def __init__(self, parent: QWidget | None = None, elevation: int = 2):
        super().__init__(parent)
        self.elevation = elevation

        # 设置基本样式
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("card")

        # 添加阴影效果
        self.add_shadow(elevation)

        # 内边距
        self.setContentsMargins(16, 16, 16, 16)

    def add_shadow(self, elevation: int):
        """添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)

        if elevation == 1:
            shadow.setBlurRadius(4)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 30))
        elif elevation == 2:
            shadow.setBlurRadius(8)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 40))
        elif elevation == 3:
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 50))
        else:
            shadow.setBlurRadius(16)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(0, 0, 0, 60))

        self.setGraphicsEffect(shadow)

    def set_elevation(self, elevation: int):
        """设置阴影高度"""
        self.elevation = elevation
        self.add_shadow(elevation)


class ProgressCard(Card):
    """进度卡片"""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent, elevation=1)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
            layout.addWidget(title_label)

        # 进度文本
        self.progress_label = QLabel("0%")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.progress_label)

        # 进度条
        self.progress_bar = CircularProgress(self)
        self.progress_bar.setFixedSize(120, 120)
        layout.addWidget(self.progress_bar, 0, Qt.AlignCenter)

    def set_progress(self, value: int):
        """设置进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")


class CircularProgress(QWidget):
    """环形进度条"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._value = 0
        self._max_value = 100
        self._color = QColor(0, 120, 212)  # 默认蓝色
        self._bg_color = QColor(230, 230, 230)
        self._thickness = 8

    def setValue(self, value: int):
        """设置当前值"""
        self._value = max(0, min(value, self._max_value))
        self.update()

    def value(self) -> int:
        """获取当前值"""
        return self._value

    def setMaximum(self, value: int):
        """设置最大值"""
        self._max_value = value
        self.update()

    def setColor(self, color: QColor):
        """设置颜色"""
        self._color = color
        self.update()

    def paintEvent(self, event: QPaintEvent):  # noqa: ARG002
        """绘制环形进度"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算绘制区域
        rect = self.rect()
        side = min(rect.width(), rect.height())
        painter.setViewport(
            (rect.width() - side) // 2, (rect.height() - side) // 2, side, side
        )
        painter.setWindow(0, 0, 120, 120)

        # 绘制背景圆环
        pen = QPen(self._bg_color)
        pen.setWidth(self._thickness)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            self._thickness,
            self._thickness,
            120 - 2 * self._thickness,
            120 - 2 * self._thickness,
            90 * 16,
            -360 * 16,
        )

        # 绘制进度圆环
        pen.setColor(self._color)
        painter.setPen(pen)
        progress_angle = int((self._value / self._max_value) * 360)
        painter.drawArc(
            self._thickness,
            self._thickness,
            120 - 2 * self._thickness,
            120 - 2 * self._thickness,
            90 * 16,
            -progress_angle * 16,
        )


class FloatingActionButton(QPushButton):
    """悬浮操作按钮（FAB）"""

    def __init__(self, icon_text: str = "+", parent: QWidget | None = None):
        super().__init__(icon_text, parent)

        # 设置圆形
        self.setFixedSize(56, 56)
        self.setStyleSheet(
            """
            QPushButton {
                border-radius: 28px;
                background-color: #0078D4;
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """
        )

        # 添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)


class Chip(QPushButton):
    """标签芯片"""

    def __init__(
        self, text: str, closable: bool = False, parent: QWidget | None = None
    ):
        super().__init__(text, parent)
        self.closable = closable

        self.setStyleSheet(
            """
            QPushButton {
                background-color: #E1E1E1;
                color: #333;
                border: none;
                border-radius: 16px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #D1D1D1;
            }
        """
        )

        # 如果可关闭，添加关闭按钮
        if closable:
            self.setText(text + " ×")


class InfoBanner(QFrame):
    """信息横幅"""

    closed = Signal()

    def __init__(
        self,
        message: str,
        banner_type: str = "info",
        closable: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        # 设置颜色
        colors = {
            "info": ("#E3F2FD", "#0078D4"),
            "success": ("#E8F5E9", "#10893E"),
            "warning": ("#FFF3E0", "#FFB900"),
            "error": ("#FFEBEE", "#D83B01"),
        }
        bg_color, text_color = colors.get(banner_type, colors["info"])

        self.setStyleSheet(
            """
            QFrame {{
                background-color: {bg_color};
                border-left: 4px solid {text_color};
                border-radius: 4px;
                padding: 12px;
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # 图标（可选）
        icon_label = QLabel(
            "ℹ️"
            if banner_type == "info"
            else "✓"
            if banner_type == "success"
            else "⚠"
            if banner_type == "warning"
            else "✗"
        )
        icon_label.setStyleSheet(f"color: {text_color}; font-size: 16px;")
        layout.addWidget(icon_label)

        # 消息
        message_label = QLabel(message)
        message_label.setStyleSheet(f"color: {text_color};")
        message_label.setWordWrap(True)
        layout.addWidget(message_label, 1)

        # 关闭按钮
        if closable:
            close_btn = QPushButton("×")
            close_btn.setFixedSize(24, 24)
            close_btn.setStyleSheet(
                """
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {text_color};
                    font-size: 18px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: rgba(0, 0, 0, 0.1);
                    border-radius: 12px;
                }}
            """
            )
            close_btn.clicked.connect(self._on_close)
            layout.addWidget(close_btn)

    def _on_close(self):
        """关闭横幅"""
        self.closed.emit()
        self.hide()


class BottomSheet(QFrame):
    """底部面板（适合移动端）"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 拖动手柄
        handle = QFrame()
        handle.setFixedHeight(32)
        handle.setStyleSheet(
            """
            QFrame {
                background-color: transparent;
            }
        """
        )
        handle_layout = QHBoxLayout(handle)

        handle_bar = QFrame()
        handle_bar.setFixedSize(40, 4)
        handle_bar.setStyleSheet(
            """
            QFrame {
                background-color: #999;
                border-radius: 2px;
            }
        """
        )
        handle_layout.addWidget(handle_bar, 0, Qt.AlignCenter)

        main_layout.addWidget(handle)

        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 0, 16, 16)

        main_layout.addWidget(self.content_widget)

        # 设置样式
        self.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """
        )

    def add_widget(self, widget: QWidget):
        """添加内容控件"""
        self.content_layout.addWidget(widget)

    def show_at_bottom(self, parent: QWidget):
        """在底部显示"""
        parent_rect = parent.geometry()
        sheet_height = min(parent_rect.height() * 0.7, 500)

        self.setGeometry(
            parent_rect.x(),
            parent_rect.y() + parent_rect.height() - int(sheet_height),
            parent_rect.width(),
            int(sheet_height),
        )
        self.show()


class StepIndicator(QWidget):
    """步骤指示器"""

    def __init__(self, steps: int = 3, parent: QWidget | None = None):
        super().__init__(parent)
        self._steps = steps
        self._current_step = 0
        self._completed_color = QColor(0, 120, 212)
        self._pending_color = QColor(200, 200, 200)

        self.setMinimumHeight(60)

    def set_current_step(self, step: int):
        """设置当前步骤"""
        self._current_step = max(0, min(step, self._steps - 1))
        self.update()

    def paintEvent(self, event: QPaintEvent):  # noqa: ARG002
        """绘制步骤指示器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        circle_radius = 12
        line_y = height // 2

        # 计算步骤间距
        step_width = (width - 40) / (self._steps - 1) if self._steps > 1 else 0

        # 绘制连接线和圆圈
        for i in range(self._steps):
            x = 20 + i * step_width

            # 绘制连接线（除了最后一个）
            if i < self._steps - 1:
                next_x = 20 + (i + 1) * step_width
                color = (
                    self._completed_color
                    if i < self._current_step
                    else self._pending_color
                )
                pen = QPen(color, 2)
                painter.setPen(pen)
                painter.drawLine(
                    int(x + circle_radius), line_y, int(next_x - circle_radius), line_y
                )

            # 绘制圆圈
            color = (
                self._completed_color
                if i <= self._current_step
                else self._pending_color
            )
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(x - circle_radius),
                line_y - circle_radius,
                circle_radius * 2,
                circle_radius * 2,
            )

            # 绘制步骤数字
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(
                QRect(
                    int(x - circle_radius),
                    line_y - circle_radius,
                    circle_radius * 2,
                    circle_radius * 2,
                ),
                Qt.AlignCenter,
                str(i + 1),
            )


class EmptyState(QWidget):
    """空状态提示"""

    def __init__(
        self, message: str = "暂无数据", icon: str = "📭", parent: QWidget | None = None
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 消息
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #666; font-size: 14px;")
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)


class SearchBar(QWidget):
    """搜索栏"""

    search_triggered = Signal(str)

    def __init__(self, placeholder: str = "搜索...", parent: QWidget | None = None):
        super().__init__(parent)

        from PySide6.QtWidgets import QLineEdit

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.returnPressed.connect(self._on_search)
        layout.addWidget(self.search_input)

        search_btn = QPushButton("🔍")
        search_btn.setFixedSize(36, 36)
        search_btn.clicked.connect(self._on_search)
        layout.addWidget(search_btn)

    def _on_search(self):
        """触发搜索"""
        text = self.search_input.text().strip()
        self.search_triggered.emit(text)
