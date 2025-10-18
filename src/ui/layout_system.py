"""
响应式布局系统
基于8px网格系统和黄金比例的现代化布局方案
"""

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class LayoutSpacing(Enum):
    """布局间距规范（8px网格系统）"""

    NONE = 0
    TINY = 4  # 极小间距
    SMALL = 8  # 小间距
    MEDIUM = 16  # 中等间距
    LARGE = 24  # 大间距
    XLARGE = 32  # 超大间距
    XXLARGE = 48  # 特大间距


class LayoutMargin(Enum):
    """布局边距规范"""

    NONE = (0, 0, 0, 0)
    COMPACT = (8, 8, 8, 8)  # 紧凑边距
    NORMAL = (16, 16, 16, 16)  # 标准边距
    COMFORTABLE = (24, 24, 24, 24)  # 舒适边距
    SPACIOUS = (32, 32, 32, 32)  # 宽松边距


class ContentWidth(Enum):
    """内容宽度规范"""

    NARROW = 600  # 窄内容（表单、对话框）
    MEDIUM = 900  # 中等内容
    WIDE = 1200  # 宽内容
    FULL = -1  # 全宽


class AspectRatio(Enum):
    """常用宽高比"""

    SQUARE = (1, 1)  # 1:1
    VIDEO = (16, 9)  # 16:9
    PHOTO = (4, 3)  # 4:3
    GOLDEN = (1.618, 1)  # 黄金比例
    CARD = (3, 2)  # 卡片比例


class FlexLayout(QHBoxLayout):
    """
    Flexbox风格的布局
    提供更直观的布局控制
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        spacing: LayoutSpacing = LayoutSpacing.MEDIUM,
        margins: LayoutMargin = LayoutMargin.NORMAL,
        direction: Qt.Orientation = Qt.Orientation.Horizontal,
    ):
        (
            super().__init__(parent)
            if direction == Qt.Orientation.Horizontal
            else QVBoxLayout.__init__(self, parent if parent else None)
        )

        self.flex_direction = direction

        # 设置间距和边距
        self.setSpacing(spacing.value)
        margins_tuple = margins.value
        self.setContentsMargins(*margins_tuple)

    def add_item(
        self,
        widget: QWidget,
        stretch: int = 0,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
    ) -> None:
        """
        添加项目到布局

        Args:
            widget: 要添加的组件
            stretch: 拉伸因子（0表示不拉伸）
            alignment: 对齐方式
        """
        self.addWidget(widget, stretch, alignment)

    def add_stretch(self, stretch: int = 1) -> None:
        """添加弹性空间"""
        self.addStretch(stretch)

    def add_spacing(self, size: int) -> None:
        """添加固定间距"""
        self.addSpacing(size)


class GridLayout(QGridLayout):
    """
    增强的网格布局
    支持响应式网格和自动换行
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        columns: int = 12,
        spacing: LayoutSpacing = LayoutSpacing.MEDIUM,
        margins: LayoutMargin = LayoutMargin.NORMAL,
    ):
        super().__init__(parent)

        self.columns = columns
        self._current_row = 0
        self._current_col = 0

        # 设置间距和边距
        self.setSpacing(spacing.value)
        margins_tuple = margins.value
        self.setContentsMargins(*margins_tuple)

    def add_item(
        self,
        widget: QWidget,
        col_span: int = 1,
        row_span: int = 1,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
    ) -> None:
        """
        添加项目到网格

        Args:
            widget: 要添加的组件
            col_span: 跨越的列数
            row_span: 跨越的行数
            alignment: 对齐方式
        """
        # 检查是否需要换行
        if self._current_col + col_span > self.columns:
            self._current_row += 1
            self._current_col = 0

        self.addWidget(widget, self._current_row, self._current_col, row_span, col_span, alignment)

        # 更新当前位置
        self._current_col += col_span

    def next_row(self) -> None:
        """移动到下一行"""
        self._current_row += 1
        self._current_col = 0


class ResponsiveContainer(QWidget):
    """
    响应式容器
    根据窗口大小自动调整布局
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        max_width: ContentWidth = ContentWidth.MEDIUM,
        center: bool = True,
    ):
        super().__init__(parent)

        self.max_width = max_width.value
        self.center = center

        # 设置尺寸策略
        if max_width == ContentWidth.FULL:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
            if self.max_width > 0:
                self.setMaximumWidth(self.max_width)

    def resizeEvent(self, event) -> None:
        """窗口大小改变时"""
        super().resizeEvent(event)

        # 如果需要居中，调整位置
        if self.center and self.parent() and hasattr(self.parent(), "width"):
            parent_widget = self.parent()
            if isinstance(parent_widget, QWidget):
                parent_width = parent_widget.width()
                if self.max_width > 0 and parent_width > self.max_width:
                    x = (parent_width - self.max_width) // 2
                    self.move(x, self.y())


class StackLayout(QVBoxLayout):
    """
    堆叠布局
    垂直堆叠多个组件，自动添加分隔符
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        spacing: LayoutSpacing = LayoutSpacing.MEDIUM,
        add_dividers: bool = False,
    ):
        super().__init__(parent)

        self.add_dividers = add_dividers
        self.setSpacing(spacing.value)
        self.setContentsMargins(0, 0, 0, 0)

    def add_section(self, widget: QWidget) -> None:
        """添加一个区块"""
        if self.add_dividers and self.count() > 0:
            # 添加分隔线
            from PySide6.QtWidgets import QFrame

            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setStyleSheet("background-color: #DEE2E6; max-height: 1px;")
            self.addWidget(divider)

        self.addWidget(widget)


class CardLayout(QWidget):
    """
    卡片布局容器
    带有边框、圆角和阴影的内容容器
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        padding: LayoutMargin = LayoutMargin.NORMAL,
        elevation: int = 1,
    ):
        super().__init__(parent)

        self.card_padding = padding
        self.card_elevation = elevation

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        # 设置样式
        self.setStyleSheet(
            """
            CardLayout {
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
            }
        """
        )

        # 添加阴影
        if self.card_elevation > 0:
            from PySide6.QtGui import QColor
            from PySide6.QtWidgets import QGraphicsDropShadowEffect

            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(8 * self.card_elevation)
            shadow.setOffset(0, 2 * self.card_elevation)
            shadow.setColor(QColor(0, 0, 0, 30 + 10 * self.card_elevation))
            self.setGraphicsEffect(shadow)

        # 创建内部布局
        self.content_layout = QVBoxLayout(self)
        margins_tuple = self.card_padding.value
        self.content_layout.setContentsMargins(*margins_tuple)
        self.content_layout.setSpacing(LayoutSpacing.MEDIUM.value)

    def set_content(self, widget: QWidget) -> None:
        """设置卡片内容"""
        # 清除现有内容
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.content_layout.addWidget(widget)


class TwoColumnLayout(QWidget):
    """
    两列布局
    左右两列，支持响应式调整
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        left_ratio: float = 0.5,
        spacing: LayoutSpacing = LayoutSpacing.LARGE,
        responsive: bool = True,
    ):
        super().__init__(parent)

        self.left_ratio = left_ratio
        self.right_ratio = 1 - left_ratio
        self.responsive = responsive
        self._is_stacked = False

        self._init_ui(spacing)

    def _init_ui(self, spacing: LayoutSpacing) -> None:
        """初始化UI"""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(spacing.value)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧容器
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)

        # 右侧容器
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # 添加到主布局
        self.main_layout.addWidget(self.left_container, int(self.left_ratio * 100))
        self.main_layout.addWidget(self.right_container, int(self.right_ratio * 100))

    def set_left_content(self, widget: QWidget) -> None:
        """设置左侧内容"""
        self._clear_layout(self.left_layout)
        self.left_layout.addWidget(widget)

    def set_right_content(self, widget: QWidget) -> None:
        """设置右侧内容"""
        self._clear_layout(self.right_layout)
        self.right_layout.addWidget(widget)

    def _clear_layout(self, layout: QLayout) -> None:
        """清空布局"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def resizeEvent(self, event) -> None:
        """响应式调整"""
        super().resizeEvent(event)

        if not self.responsive:
            return

        # 窗口宽度小于600px时堆叠显示
        if self.width() < 600 and not self._is_stacked:
            self._switch_to_stacked()
        elif self.width() >= 600 and self._is_stacked:
            self._switch_to_columns()

    def _switch_to_stacked(self) -> None:
        """切换到堆叠布局"""
        self._is_stacked = True

        # 移除现有布局
        self.main_layout.removeWidget(self.left_container)
        self.main_layout.removeWidget(self.right_container)

        # 改为垂直布局
        if isinstance(self.main_layout, QHBoxLayout):
            # 删除旧布局
            QWidget().setLayout(self.main_layout)

            # 创建新的垂直布局
            new_layout: QVBoxLayout = QVBoxLayout(self)
            new_layout.setContentsMargins(0, 0, 0, 0)
            new_layout.setSpacing(LayoutSpacing.MEDIUM.value)
            self.main_layout = new_layout  # type: ignore

        self.main_layout.addWidget(self.left_container)
        self.main_layout.addWidget(self.right_container)

    def _switch_to_columns(self) -> None:
        """切换到两列布局"""
        self._is_stacked = False

        # 移除现有布局
        self.main_layout.removeWidget(self.left_container)
        self.main_layout.removeWidget(self.right_container)

        # 改为水平布局
        if isinstance(self.main_layout, QVBoxLayout):
            # 删除旧布局
            QWidget().setLayout(self.main_layout)

            # 创建新的水平布局
            self.main_layout = QHBoxLayout(self)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(LayoutSpacing.LARGE.value)

        self.main_layout.addWidget(self.left_container, int(self.left_ratio * 100))
        self.main_layout.addWidget(self.right_container, int(self.right_ratio * 100))


class Spacer:
    """空间工具类"""

    @staticmethod
    def vertical(size: LayoutSpacing = LayoutSpacing.MEDIUM) -> QSpacerItem:
        """创建垂直空间"""
        return QSpacerItem(0, size.value, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    @staticmethod
    def horizontal(size: LayoutSpacing = LayoutSpacing.MEDIUM) -> QSpacerItem:
        """创建水平空间"""
        return QSpacerItem(size.value, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

    @staticmethod
    def expanding_vertical() -> QSpacerItem:
        """创建可扩展的垂直空间"""
        return QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

    @staticmethod
    def expanding_horizontal() -> QSpacerItem:
        """创建可扩展的水平空间"""
        return QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)


# 便捷函数
def create_flex_row(
    spacing: LayoutSpacing = LayoutSpacing.MEDIUM,
    margins: LayoutMargin = LayoutMargin.NONE,
) -> FlexLayout:
    """创建水平Flex布局"""
    return FlexLayout(spacing=spacing, margins=margins, direction=Qt.Orientation.Horizontal)


def create_flex_column(
    spacing: LayoutSpacing = LayoutSpacing.MEDIUM,
    margins: LayoutMargin = LayoutMargin.NONE,
) -> FlexLayout:
    """创建垂直Flex布局"""
    return FlexLayout(spacing=spacing, margins=margins, direction=Qt.Orientation.Vertical)


def create_card(
    content: QWidget | None = None,
    padding: LayoutMargin = LayoutMargin.NORMAL,
    elevation: int = 1,
) -> CardLayout:
    """创建卡片容器"""
    card = CardLayout(padding=padding, elevation=elevation)
    if content:
        card.set_content(content)
    return card


def create_responsive_grid(
    columns: int = 12,
    spacing: LayoutSpacing = LayoutSpacing.MEDIUM,
) -> GridLayout:
    """创建响应式网格"""
    return GridLayout(columns=columns, spacing=spacing)
