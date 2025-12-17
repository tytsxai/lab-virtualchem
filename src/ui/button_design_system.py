"""
现代化按钮设计系统
基于 Microsoft Fluent Design 和 Material Design 3 的最佳实践
提供统一的按钮样式、尺寸和交互规范
"""

from enum import Enum

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class ButtonSize(Enum):
    """按钮尺寸规范（基于8px网格系统）"""

    SMALL = ("small", 32, 8, 16, "9pt")  # 紧凑型按钮
    MEDIUM = ("medium", 40, 12, 24, "10pt")  # 标准按钮
    LARGE = ("large", 48, 16, 32, "11pt")  # 大号按钮
    XLARGE = ("xlarge", 56, 20, 40, "12pt")  # 超大按钮（触屏优化）

    def __init__(
        self, name: str, height: int, padding_v: int, padding_h: int, font_size: str
    ):
        self.display_name = name
        self.height = height
        self.padding_v = padding_v
        self.padding_h = padding_h
        self.font_size = font_size


class ButtonVariant(Enum):
    """按钮变体"""

    PRIMARY = "primary"  # 主要按钮
    SECONDARY = "secondary"  # 次要按钮
    OUTLINE = "outline"  # 轮廓按钮
    GHOST = "ghost"  # 幽灵按钮（透明背景）
    TEXT = "text"  # 文本按钮
    DANGER = "danger"  # 危险操作按钮
    SUCCESS = "success"  # 成功按钮


class ButtonState(Enum):
    """按钮状态"""

    NORMAL = "normal"
    HOVER = "hover"
    PRESSED = "pressed"
    DISABLED = "disabled"
    FOCUSED = "focused"


class DesignTokens:
    """设计令牌 - 统一的设计变量"""

    # 颜色系统
    PRIMARY = "#0078D4"
    PRIMARY_HOVER = "#106EBE"
    PRIMARY_PRESSED = "#005A9E"

    SECONDARY = "#6C757D"
    SECONDARY_HOVER = "#5A6268"
    SECONDARY_PRESSED = "#545B62"

    SUCCESS = "#28A745"
    SUCCESS_HOVER = "#218838"
    SUCCESS_PRESSED = "#1E7E34"

    DANGER = "#DC3545"
    DANGER_HOVER = "#C82333"
    DANGER_PRESSED = "#BD2130"

    SURFACE = "#FFFFFF"
    SURFACE_VARIANT = "#F8F9FA"
    BORDER = "#DEE2E6"
    TEXT_PRIMARY = "#212529"
    TEXT_SECONDARY = "#6C757D"
    TEXT_ON_PRIMARY = "#FFFFFF"

    # 阴影
    SHADOW_1 = "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)"
    SHADOW_2 = "0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23)"
    SHADOW_3 = "0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23)"

    # 圆角
    RADIUS_SM = 4
    RADIUS_MD = 6
    RADIUS_LG = 8
    RADIUS_XL = 12
    RADIUS_FULL = 999

    # 间距（8px网格系统）
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 16
    SPACE_LG = 24
    SPACE_XL = 32

    # 动画时长
    DURATION_INSTANT = 100
    DURATION_FAST = 200
    DURATION_NORMAL = 300
    DURATION_SLOW = 500


class ModernButton(QPushButton):
    """
    现代化按钮组件

    特性：
    - 支持多种尺寸和变体
    - 涟漪动画效果
    - 悬浮提升效果
    - 加载状态
    - 图标支持
    - 完整的可访问性支持
    """

    clicked_with_feedback = Signal()  # 带反馈的点击信号

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        size: ButtonSize = ButtonSize.MEDIUM,
        variant: ButtonVariant = ButtonVariant.PRIMARY,
        icon: QIcon | None = None,
        full_width: bool = False,
    ):
        super().__init__(text, parent)

        self.button_size = size
        self.button_variant = variant
        self.button_icon = icon
        self._is_loading = False

        # 涟漪效果属性
        self._ripple_radius = 0
        self._ripple_opacity = 0
        self._ripple_x = 0
        self._ripple_y = 0
        self._ripple_animation: QPropertyAnimation | None = None

        # 提升效果属性
        self._elevation = 0
        self._shadow_effect: QGraphicsDropShadowEffect | None = None

        self._init_ui(full_width)
        self._apply_styles()

    def _init_ui(self, full_width: bool) -> None:
        """初始化UI"""
        # 设置尺寸
        self.setMinimumHeight(self.button_size.height)
        self.setContentsMargins(
            self.button_size.padding_h,
            self.button_size.padding_v,
            self.button_size.padding_h,
            self.button_size.padding_v,
        )

        # 设置字体
        font = QFont()
        font.setPointSize(int(self.button_size.font_size.replace("pt", "")))
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)

        # 设置尺寸策略
        if full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            self.setMinimumWidth(80)

        # 设置图标
        if self.button_icon:
            self.setIcon(self.button_icon)
            icon_size = self.button_size.height - self.button_size.padding_v * 2
            self.setIconSize(QRect(0, 0, icon_size, icon_size).size())

        # 添加阴影效果（仅用于primary按钮）
        if self.button_variant in [
            ButtonVariant.PRIMARY,
            ButtonVariant.DANGER,
            ButtonVariant.SUCCESS,
        ]:
            self._shadow_effect = QGraphicsDropShadowEffect(self)
            self._shadow_effect.setBlurRadius(8)
            self._shadow_effect.setOffset(0, 2)
            self._shadow_effect.setColor(QColor(0, 0, 0, 40))
            self.setGraphicsEffect(self._shadow_effect)

    def _apply_styles(self) -> None:
        """应用样式"""
        styles = self._get_styles()
        self.setStyleSheet(styles)

    def _get_styles(self) -> str:
        """获取样式表"""
        # 根据变体选择颜色
        if self.button_variant == ButtonVariant.PRIMARY:
            bg_color = DesignTokens.PRIMARY
            bg_hover = DesignTokens.PRIMARY_HOVER
            bg_pressed = DesignTokens.PRIMARY_PRESSED
            text_color = DesignTokens.TEXT_ON_PRIMARY
            border_color = DesignTokens.PRIMARY
        elif self.button_variant == ButtonVariant.SECONDARY:
            bg_color = DesignTokens.SECONDARY
            bg_hover = DesignTokens.SECONDARY_HOVER
            bg_pressed = DesignTokens.SECONDARY_PRESSED
            text_color = DesignTokens.TEXT_ON_PRIMARY
            border_color = DesignTokens.SECONDARY
        elif self.button_variant == ButtonVariant.DANGER:
            bg_color = DesignTokens.DANGER
            bg_hover = DesignTokens.DANGER_HOVER
            bg_pressed = DesignTokens.DANGER_PRESSED
            text_color = DesignTokens.TEXT_ON_PRIMARY
            border_color = DesignTokens.DANGER
        elif self.button_variant == ButtonVariant.SUCCESS:
            bg_color = DesignTokens.SUCCESS
            bg_hover = DesignTokens.SUCCESS_HOVER
            bg_pressed = DesignTokens.SUCCESS_PRESSED
            text_color = DesignTokens.TEXT_ON_PRIMARY
            border_color = DesignTokens.SUCCESS
        elif self.button_variant == ButtonVariant.OUTLINE:
            bg_color = "transparent"
            bg_hover = DesignTokens.SURFACE_VARIANT
            bg_pressed = DesignTokens.BORDER
            text_color = DesignTokens.PRIMARY
            border_color = DesignTokens.PRIMARY
        elif self.button_variant == ButtonVariant.GHOST:
            bg_color = "transparent"
            bg_hover = DesignTokens.SURFACE_VARIANT
            bg_pressed = DesignTokens.BORDER
            text_color = DesignTokens.TEXT_PRIMARY
            border_color = "transparent"
        elif self.button_variant == ButtonVariant.TEXT:
            bg_color = "transparent"
            bg_hover = DesignTokens.SURFACE_VARIANT
            bg_pressed = DesignTokens.BORDER
            text_color = DesignTokens.PRIMARY
            border_color = "transparent"
        else:
            bg_color = DesignTokens.PRIMARY
            bg_hover = DesignTokens.PRIMARY_HOVER
            bg_pressed = DesignTokens.PRIMARY_PRESSED
            text_color = DesignTokens.TEXT_ON_PRIMARY
            border_color = DesignTokens.PRIMARY

        # 构建样式表
        border_width = 2 if self.button_variant == ButtonVariant.OUTLINE else 0

        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: {border_width}px solid {border_color};
                border-radius: {DesignTokens.RADIUS_MD}px;
                padding: {self.button_size.padding_v}px {self.button_size.padding_h}px;
                font-weight: 500;
                text-align: center;
            }}

            QPushButton:hover {{
                background-color: {bg_hover};
            }}

            QPushButton:pressed {{
                background-color: {bg_pressed};
            }}

            QPushButton:disabled {{
                background-color: {DesignTokens.BORDER};
                color: {DesignTokens.TEXT_SECONDARY};
                border-color: {DesignTokens.BORDER};
            }}

            QPushButton:focus {{
                outline: 2px solid {DesignTokens.PRIMARY};
                outline-offset: 2px;
            }}
        """

    def mousePressEvent(self, event) -> None:  # type: ignore
        """鼠标按下 - 触发涟漪效果"""
        super().mousePressEvent(event)

        # 记录涟漪位置
        self._ripple_x = event.pos().x()
        self._ripple_y = event.pos().y()

        # 创建涟漪动画
        self._start_ripple_animation()

    def _start_ripple_animation(self) -> None:
        """开始涟漪动画"""
        if self._ripple_animation:
            self._ripple_animation.stop()

        # 半径动画
        radius_anim = QPropertyAnimation(self, b"ripple_radius")
        radius_anim.setDuration(DesignTokens.DURATION_SLOW)
        radius_anim.setStartValue(0)
        max_radius = max(self.width(), self.height()) * 1.5
        radius_anim.setEndValue(max_radius)
        radius_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 透明度动画
        opacity_anim = QPropertyAnimation(self, b"ripple_opacity")
        opacity_anim.setDuration(DesignTokens.DURATION_SLOW)
        opacity_anim.setStartValue(80)
        opacity_anim.setEndValue(0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 并行执行
        group_anim = QParallelAnimationGroup(self)
        group_anim.addAnimation(radius_anim)
        group_anim.addAnimation(opacity_anim)
        group_anim.start()
        self._ripple_animation = radius_anim

    def enterEvent(self, event) -> None:  # type: ignore
        """鼠标进入 - 提升效果"""
        super().enterEvent(event)

        if self._shadow_effect and self.variant in [
            ButtonVariant.PRIMARY,
            ButtonVariant.DANGER,
            ButtonVariant.SUCCESS,
        ]:
            anim = QPropertyAnimation(self._shadow_effect, b"blurRadius")
            anim.setDuration(DesignTokens.DURATION_FAST)
            anim.setStartValue(8)
            anim.setEndValue(16)
            anim.start()

    def leaveEvent(self, event) -> None:  # type: ignore
        """鼠标离开 - 恢复高度"""
        super().leaveEvent(event)

        if self._shadow_effect and self.button_variant in [
            ButtonVariant.PRIMARY,
            ButtonVariant.DANGER,
            ButtonVariant.SUCCESS,
        ]:
            anim = QPropertyAnimation(self._shadow_effect, b"blurRadius")
            anim.setDuration(DesignTokens.DURATION_FAST)
            anim.setStartValue(16)
            anim.setEndValue(8)
            anim.start()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制 - 添加涟漪效果"""
        super().paintEvent(event)

        if self._ripple_radius > 0 and self._ripple_opacity > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 涟漪颜色（白色或黑色，取决于按钮背景）
            ripple_color = QColor(255, 255, 255, self._ripple_opacity)
            if self.button_variant in [
                ButtonVariant.OUTLINE,
                ButtonVariant.GHOST,
                ButtonVariant.TEXT,
            ]:
                ripple_color = QColor(0, 0, 0, self._ripple_opacity // 3)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ripple_color)

            painter.drawEllipse(
                self._ripple_x - self._ripple_radius,
                self._ripple_y - self._ripple_radius,
                self._ripple_radius * 2,
                self._ripple_radius * 2,
            )

    def set_loading(self, loading: bool) -> None:
        """设置加载状态"""
        self._is_loading = loading
        self.setEnabled(not loading)

        if loading:
            self.setText("⏳ 加载中...")
        else:
            # 恢复原文本（需要在外部保存原文本）
            pass

    @property
    def is_loading(self) -> bool:
        return self._is_loading

    # Qt属性定义
    def get_ripple_radius(self) -> int:
        return self._ripple_radius

    def set_ripple_radius(self, value: int) -> None:
        self._ripple_radius = value
        self.update()

    def get_ripple_opacity(self) -> int:
        return self._ripple_opacity

    def set_ripple_opacity(self, value: int) -> None:
        self._ripple_opacity = value
        self.update()

    ripple_radius = Property(int, get_ripple_radius, set_ripple_radius)
    ripple_opacity = Property(int, get_ripple_opacity, set_ripple_opacity)


class ButtonGroup(QWidget):
    """
    按钮组组件
    用于展示多个相关按钮，支持水平和垂直布局
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        spacing: int = DesignTokens.SPACE_SM,
    ):
        super().__init__(parent)
        self.button_group_orientation = orientation
        self.group_spacing = spacing
        self.buttons: list[ModernButton] = []

        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

        if orientation == Qt.Orientation.Horizontal:
            self.group_layout = QHBoxLayout(self)
        else:
            self.group_layout = QVBoxLayout(self)

        self.group_layout.setSpacing(spacing)
        self.group_layout.setContentsMargins(0, 0, 0, 0)

    def add_button(self, button: ModernButton) -> None:
        """添加按钮"""
        self.buttons.append(button)
        self.group_layout.addWidget(button)

    def add_stretch(self) -> None:
        """添加弹性空间"""
        self.group_layout.addStretch()


class IconButton(ModernButton):
    """
    图标按钮
    只显示图标的圆形按钮
    """

    def __init__(
        self,
        icon: QIcon,
        parent: QWidget | None = None,
        size: ButtonSize = ButtonSize.MEDIUM,
        variant: ButtonVariant = ButtonVariant.GHOST,
    ):
        super().__init__("", parent, size, variant, icon)

        # 设置为正方形
        btn_size = size.height
        self.setFixedSize(btn_size, btn_size)

        # 圆形样式
        self.setStyleSheet(
            self.styleSheet()
            + f"""
            QPushButton {{
                border-radius: {btn_size // 2}px;
            }}
        """
        )


class ToggleButton(ModernButton):
    """
    切换按钮
    可在两种状态间切换的按钮
    """

    toggled = Signal(bool)

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        size: ButtonSize = ButtonSize.MEDIUM,
    ):
        super().__init__(text, parent, size, ButtonVariant.OUTLINE)

        self.setCheckable(True)
        self.clicked.connect(self._on_toggled)

        # 选中状态的样式
        self.setStyleSheet(
            self.styleSheet()
            + f"""
            QPushButton:checked {{
                background-color: {DesignTokens.PRIMARY};
                color: {DesignTokens.TEXT_ON_PRIMARY};
                border-color: {DesignTokens.PRIMARY};
            }}
        """
        )

    def _on_toggled(self) -> None:
        """切换事件"""
        self.toggled.emit(self.isChecked())


# 便捷创建函数
def create_primary_button(
    text: str, size: ButtonSize = ButtonSize.MEDIUM
) -> ModernButton:
    """创建主要按钮"""
    return ModernButton(text, size=size, variant=ButtonVariant.PRIMARY)


def create_secondary_button(
    text: str, size: ButtonSize = ButtonSize.MEDIUM
) -> ModernButton:
    """创建次要按钮"""
    return ModernButton(text, size=size, variant=ButtonVariant.SECONDARY)


def create_outline_button(
    text: str, size: ButtonSize = ButtonSize.MEDIUM
) -> ModernButton:
    """创建轮廓按钮"""
    return ModernButton(text, size=size, variant=ButtonVariant.OUTLINE)


def create_text_button(text: str, size: ButtonSize = ButtonSize.MEDIUM) -> ModernButton:
    """创建文本按钮"""
    return ModernButton(text, size=size, variant=ButtonVariant.TEXT)


def create_danger_button(
    text: str, size: ButtonSize = ButtonSize.MEDIUM
) -> ModernButton:
    """创建危险按钮"""
    return ModernButton(text, size=size, variant=ButtonVariant.DANGER)


def create_success_button(
    text: str, size: ButtonSize = ButtonSize.MEDIUM
) -> ModernButton:
    """创建成功按钮"""
    return ModernButton(text, size=size, variant=ButtonVariant.SUCCESS)
