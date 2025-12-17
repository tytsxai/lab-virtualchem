"""
响应式设计模块
提供自适应布局和移动端优化
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, QSize, Signal
from PySide6.QtWidgets import QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Breakpoint(Enum):
    """断点枚举"""

    XS = "xs"  # 超小屏幕 (< 576px)
    SM = "sm"  # 小屏幕 (≥ 576px)
    MD = "md"  # 中等屏幕 (≥ 768px)
    LG = "lg"  # 大屏幕 (≥ 992px)
    XL = "xl"  # 超大屏幕 (≥ 1200px)
    XXL = "xxl"  # 超超大屏幕 (≥ 1400px)


class DeviceType(Enum):
    """设备类型"""

    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


class Orientation(Enum):
    """屏幕方向"""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class ResponsiveConfig:
    """响应式配置"""

    def __init__(self):
        # 断点配置
        self.breakpoints = {
            Breakpoint.XS: 0,
            Breakpoint.SM: 576,
            Breakpoint.MD: 768,
            Breakpoint.LG: 992,
            Breakpoint.XL: 1200,
            Breakpoint.XXL: 1400,
        }

        # 设备类型配置
        self.device_types = {
            DeviceType.MOBILE: (0, 767),
            DeviceType.TABLET: (768, 1023),
            DeviceType.DESKTOP: (1024, float("inf")),
        }

        # 布局配置
        self.layout_configs = {
            Breakpoint.XS: {
                "columns": 1,
                "spacing": 8,
                "font_size": 12,
                "button_height": 40,
                "padding": 8,
            },
            Breakpoint.SM: {
                "columns": 2,
                "spacing": 12,
                "font_size": 14,
                "button_height": 44,
                "padding": 12,
            },
            Breakpoint.MD: {
                "columns": 3,
                "spacing": 16,
                "font_size": 16,
                "button_height": 48,
                "padding": 16,
            },
            Breakpoint.LG: {
                "columns": 4,
                "spacing": 20,
                "font_size": 18,
                "button_height": 52,
                "padding": 20,
            },
            Breakpoint.XL: {
                "columns": 5,
                "spacing": 24,
                "font_size": 20,
                "button_height": 56,
                "padding": 24,
            },
            Breakpoint.XXL: {
                "columns": 6,
                "spacing": 28,
                "font_size": 22,
                "button_height": 60,
                "padding": 28,
            },
        }


class ResponsiveDesign(QObject):
    """响应式设计管理器"""

    # 信号
    breakpoint_changed = Signal(Breakpoint)
    device_type_changed = Signal(DeviceType)
    orientation_changed = Signal(Orientation)
    layout_updated = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        """初始化响应式设计管理器

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        self.config = ResponsiveConfig()
        self.current_breakpoint = Breakpoint.MD
        self.current_device_type = DeviceType.DESKTOP
        self.current_orientation = Orientation.LANDSCAPE
        self.current_size = QSize(1024, 768)

        # 响应式组件注册表
        self.responsive_widgets: list[QWidget] = []

        logger.info("响应式设计管理器已初始化")

    def register_widget(self, widget: QWidget) -> None:
        """注册响应式组件

        Args:
            widget: 要注册的组件
        """
        if widget not in self.responsive_widgets:
            self.responsive_widgets.append(widget)
            logger.debug(f"注册响应式组件: {widget.objectName()}")

    def unregister_widget(self, widget: QWidget) -> None:
        """取消注册响应式组件

        Args:
            widget: 要取消注册的组件
        """
        if widget in self.responsive_widgets:
            self.responsive_widgets.remove(widget)
            logger.debug(f"取消注册响应式组件: {widget.objectName()}")

    def update_layout(self, size: QSize) -> None:
        """更新布局

        Args:
            size: 当前窗口大小
        """
        self.current_size = size

        # 确定当前断点
        new_breakpoint = self._get_breakpoint(size.width())
        if new_breakpoint != self.current_breakpoint:
            self.current_breakpoint = new_breakpoint
            self.breakpoint_changed.emit(new_breakpoint)
            logger.info(f"断点变更: {new_breakpoint.value}")

        # 确定设备类型
        new_device_type = self._get_device_type(size.width())
        if new_device_type != self.current_device_type:
            self.current_device_type = new_device_type
            self.device_type_changed.emit(new_device_type)
            logger.info(f"设备类型变更: {new_device_type.value}")

        # 确定屏幕方向
        new_orientation = self._get_orientation(size)
        if new_orientation != self.current_orientation:
            self.current_orientation = new_orientation
            self.orientation_changed.emit(new_orientation)
            logger.info(f"屏幕方向变更: {new_orientation.value}")

        # 更新所有注册的组件
        self._update_responsive_widgets()

        # 发送布局更新信号
        layout_config = self.get_current_layout_config()
        self.layout_updated.emit(layout_config)

    def _get_breakpoint(self, width: int) -> Breakpoint:
        """根据宽度确定断点

        Args:
            width: 宽度

        Returns:
            断点
        """
        for breakpoint in reversed(list(Breakpoint)):
            if width >= self.config.breakpoints[breakpoint]:
                return breakpoint
        return Breakpoint.XS

    def _get_device_type(self, width: int) -> DeviceType:
        """根据宽度确定设备类型

        Args:
            width: 宽度

        Returns:
            设备类型
        """
        for device_type, (min_width, max_width) in self.config.device_types.items():
            if min_width <= width <= max_width:
                return device_type
        return DeviceType.DESKTOP

    def _get_orientation(self, size: QSize) -> Orientation:
        """根据尺寸确定屏幕方向

        Args:
            size: 尺寸

        Returns:
            屏幕方向
        """
        return (
            Orientation.LANDSCAPE
            if size.width() > size.height()
            else Orientation.PORTRAIT
        )

    def _update_responsive_widgets(self) -> None:
        """更新所有响应式组件"""
        layout_config = self.get_current_layout_config()

        for widget in self.responsive_widgets:
            try:
                # 调用组件的响应式更新方法
                if hasattr(widget, "update_responsive_layout"):
                    widget.update_responsive_layout(layout_config)
                elif hasattr(widget, "setStyleSheet"):
                    # 使用样式表更新
                    stylesheet = self._generate_stylesheet(layout_config)
                    widget.setStyleSheet(stylesheet)
            except Exception as e:
                logger.error(f"更新响应式组件失败: {e}")

    def _generate_stylesheet(self, config: dict[str, Any]) -> str:
        """生成样式表

        Args:
            config: 布局配置

        Returns:
            样式表字符串
        """
        return f"""
        QWidget {{
            font-size: {config["font_size"]}px;
            padding: {config["padding"]}px;
        }}
        QPushButton {{
            min-height: {config["button_height"]}px;
            padding: {config["padding"]}px;
        }}
        QLabel {{
            font-size: {config["font_size"]}px;
        }}
        """

    def get_current_layout_config(self) -> dict[str, Any]:
        """获取当前布局配置

        Returns:
            布局配置
        """
        return self.config.layout_configs[self.current_breakpoint].copy()

    def get_breakpoint_config(self, breakpoint: Breakpoint) -> dict[str, Any]:
        """获取指定断点的配置

        Args:
            breakpoint: 断点

        Returns:
            断点配置
        """
        return self.config.layout_configs[breakpoint].copy()

    def is_mobile(self) -> bool:
        """是否为移动设备

        Returns:
            是否为移动设备
        """
        return self.current_device_type == DeviceType.MOBILE

    def is_tablet(self) -> bool:
        """是否为平板设备

        Returns:
            是否为平板设备
        """
        return self.current_device_type == DeviceType.TABLET

    def is_desktop(self) -> bool:
        """是否为桌面设备

        Returns:
            是否为桌面设备
        """
        return self.current_device_type == DeviceType.DESKTOP

    def is_portrait(self) -> bool:
        """是否为竖屏

        Returns:
            是否为竖屏
        """
        return self.current_orientation == Orientation.PORTRAIT

    def is_landscape(self) -> bool:
        """是否为横屏

        Returns:
            是否为横屏
        """
        return self.current_orientation == Orientation.LANDSCAPE

    def get_optimal_columns(self, content_width: int) -> int:
        """获取最优列数

        Args:
            content_width: 内容宽度

        Returns:
            最优列数
        """
        config = self.get_current_layout_config()
        base_columns = config["columns"]

        # 根据内容宽度调整
        if content_width < 400:
            return max(1, base_columns - 2)
        elif content_width < 800:
            return max(1, base_columns - 1)
        elif content_width > 1600:
            return min(8, base_columns + 2)
        else:
            return base_columns

    def get_optimal_spacing(self) -> int:
        """获取最优间距

        Returns:
            最优间距
        """
        config = self.get_current_layout_config()
        return config["spacing"]

    def get_optimal_font_size(self, base_size: int = 16) -> int:
        """获取最优字体大小

        Args:
            base_size: 基础字体大小

        Returns:
            最优字体大小
        """
        config = self.get_current_layout_config()
        scale_factor = config["font_size"] / 16.0  # 以16px为基准
        return int(base_size * scale_factor)

    def get_optimal_button_size(self) -> tuple[int, int]:
        """获取最优按钮尺寸

        Returns:
            (宽度, 高度)
        """
        config = self.get_current_layout_config()
        height = config["button_height"]

        # 根据设备类型调整宽度
        if self.is_mobile():
            width = height * 2.5  # 移动端按钮更宽
        elif self.is_tablet():
            width = height * 2.0  # 平板按钮适中
        else:
            width = height * 1.8  # 桌面按钮较窄

        return (int(width), height)

    def get_responsive_margins(self) -> tuple[int, int, int, int]:
        """获取响应式边距

        Returns:
            (上, 右, 下, 左)
        """
        config = self.get_current_layout_config()
        margin = config["padding"]

        if self.is_mobile():
            return (margin, margin, margin, margin)
        elif self.is_tablet():
            return (margin * 2, margin * 2, margin * 2, margin * 2)
        else:
            return (margin * 3, margin * 3, margin * 3, margin * 3)

    def get_screen_info(self) -> dict[str, Any]:
        """获取屏幕信息

        Returns:
            屏幕信息
        """
        return {
            "width": self.current_size.width(),
            "height": self.current_size.height(),
            "breakpoint": self.current_breakpoint.value,
            "device_type": self.current_device_type.value,
            "orientation": self.current_orientation.value,
            "is_mobile": self.is_mobile(),
            "is_tablet": self.is_tablet(),
            "is_desktop": self.is_desktop(),
            "is_portrait": self.is_portrait(),
            "is_landscape": self.is_landscape(),
        }
