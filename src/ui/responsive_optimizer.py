"""
响应式优化器
优化界面在不同屏幕尺寸和DPI下的表现
"""

import logging
from typing import Any

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)


class ResponsiveOptimizer(QObject):
    """响应式优化器"""

    # 布局变化信号
    layout_changed = Signal(str)  # 布局类型
    dpi_changed = Signal(float)  # DPI值
    screen_changed = Signal(str)  # 屏幕信息

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._current_dpi = 96.0
        self._current_screen_size = QSize(1920, 1080)
        self._current_layout_type = "desktop"

        # 响应式断点
        self.breakpoints = {
            "mobile": 768,
            "tablet": 1024,
            "desktop": 1440,
            "large_desktop": 1920,
        }

        # DPI缩放因子
        self.dpi_scales = {
            "low": 0.75,  # 96 DPI
            "normal": 1.0,  # 120 DPI
            "high": 1.25,  # 144 DPI
            "very_high": 1.5,  # 192 DPI
        }

        # 字体大小映射
        self.font_sizes = {
            "mobile": {"small": 12, "medium": 14, "large": 16, "xlarge": 18},
            "tablet": {"small": 13, "medium": 15, "large": 17, "xlarge": 20},
            "desktop": {"small": 14, "medium": 16, "large": 18, "xlarge": 22},
            "large_desktop": {"small": 15, "medium": 17, "large": 20, "xlarge": 24},
        }

        # 间距映射
        self.spacings = {
            "mobile": {"small": 4, "medium": 8, "large": 12, "xlarge": 16},
            "tablet": {"small": 6, "medium": 10, "large": 14, "xlarge": 18},
            "desktop": {"small": 8, "medium": 12, "large": 16, "xlarge": 20},
            "large_desktop": {"small": 10, "medium": 14, "large": 18, "xlarge": 24},
        }

    def initialize(self) -> None:
        """初始化响应式优化器"""
        try:
            # 获取当前屏幕信息
            self._update_screen_info()

            # 设置初始布局类型
            self._update_layout_type()

            logger.info(
                f"响应式优化器初始化完成: {self._current_layout_type}, DPI: {self._current_dpi}"
            )

        except Exception as e:
            logger.error(f"响应式优化器初始化失败: {e}", exc_info=True)

    def _update_screen_info(self) -> None:
        """更新屏幕信息"""
        try:
            app = QApplication.instance()
            if not app:
                return

            screen = app.primaryScreen()  # type: ignore[attr-defined]
            if not screen:
                return

            # 获取屏幕尺寸
            self._current_screen_size = screen.size()

            # 获取DPI
            self._current_dpi = screen.logicalDotsPerInch()

            # 发出信号
            self.dpi_changed.emit(self._current_dpi)
            self.screen_changed.emit(
                f"{self._current_screen_size.width()}x{self._current_screen_size.height()}"
            )

        except Exception as e:
            logger.error(f"更新屏幕信息失败: {e}", exc_info=True)

    def _update_layout_type(self) -> None:
        """更新布局类型"""
        try:
            width = self._current_screen_size.width()

            if width < self.breakpoints["mobile"]:
                new_layout = "mobile"
            elif width < self.breakpoints["tablet"]:
                new_layout = "tablet"
            elif width < self.breakpoints["desktop"]:
                new_layout = "desktop"
            else:
                new_layout = "large_desktop"

            if new_layout != self._current_layout_type:
                self._current_layout_type = new_layout
                self.layout_changed.emit(new_layout)
                logger.info(f"布局类型已更新: {new_layout}")

        except Exception as e:
            logger.error(f"更新布局类型失败: {e}", exc_info=True)

    def get_layout_type(self) -> str:
        """获取当前布局类型"""
        return self._current_layout_type

    def get_dpi_scale(self) -> float:
        """获取DPI缩放因子"""
        try:
            if self._current_dpi <= 96:
                return self.dpi_scales["low"]
            elif self._current_dpi <= 120:
                return self.dpi_scales["normal"]
            elif self._current_dpi <= 144:
                return self.dpi_scales["high"]
            else:
                return self.dpi_scales["very_high"]

        except Exception as e:
            logger.error(f"获取DPI缩放因子失败: {e}", exc_info=True)
            return 1.0

    def get_font_size(self, size_type: str) -> int:
        """获取字体大小"""
        try:
            layout_type = self.get_layout_type()
            base_size = self.font_sizes.get(layout_type, {}).get(size_type, 16)

            # 应用DPI缩放
            dpi_scale = self.get_dpi_scale()
            scaled_size = int(base_size * dpi_scale)

            return max(8, min(32, scaled_size))  # 限制在8-32之间

        except Exception as e:
            logger.error(f"获取字体大小失败: {e}", exc_info=True)
            return 16

    def get_spacing(self, size_type: str) -> int:
        """获取间距大小"""
        try:
            layout_type = self.get_layout_type()
            base_spacing = self.spacings.get(layout_type, {}).get(size_type, 8)

            # 应用DPI缩放
            dpi_scale = self.get_dpi_scale()
            scaled_spacing = int(base_spacing * dpi_scale)

            return max(2, min(32, scaled_spacing))  # 限制在2-32之间

        except Exception as e:
            logger.error(f"获取间距大小失败: {e}", exc_info=True)
            return 8

    def get_scaled_size(self, base_size: int) -> int:
        """获取缩放后的大小"""
        try:
            dpi_scale = self.get_dpi_scale()
            scaled_size = int(base_size * dpi_scale)
            return max(1, scaled_size)

        except Exception as e:
            logger.error(f"获取缩放大小失败: {e}", exc_info=True)
            return base_size

    def optimize_widget(self, widget: QWidget) -> None:
        """优化组件"""
        try:
            layout_type = self.get_layout_type()

            # 根据布局类型调整组件
            if layout_type == "mobile":
                self._optimize_for_mobile(widget)
            elif layout_type == "tablet":
                self._optimize_for_tablet(widget)
            elif layout_type == "desktop":
                self._optimize_for_desktop(widget)
            else:
                self._optimize_for_large_desktop(widget)

        except Exception as e:
            logger.error(f"优化组件失败: {e}", exc_info=True)

    def _optimize_for_mobile(self, widget: QWidget) -> None:
        """移动端优化"""
        try:
            # 调整字体大小
            font = widget.font()
            font.setPointSize(self.get_font_size("medium"))
            widget.setFont(font)

            # 调整间距
            if hasattr(widget, "setSpacing"):
                widget.setSpacing(self.get_spacing("small"))

            # 调整边距
            if hasattr(widget, "setContentsMargins"):
                margin = self.get_spacing("small")
                widget.setContentsMargins(margin, margin, margin, margin)

        except Exception as e:
            logger.error(f"移动端优化失败: {e}", exc_info=True)

    def _optimize_for_tablet(self, widget: QWidget) -> None:
        """平板端优化"""
        try:
            # 调整字体大小
            font = widget.font()
            font.setPointSize(self.get_font_size("medium"))
            widget.setFont(font)

            # 调整间距
            if hasattr(widget, "setSpacing"):
                widget.setSpacing(self.get_spacing("medium"))

            # 调整边距
            if hasattr(widget, "setContentsMargins"):
                margin = self.get_spacing("medium")
                widget.setContentsMargins(margin, margin, margin, margin)

        except Exception as e:
            logger.error(f"平板端优化失败: {e}", exc_info=True)

    def _optimize_for_desktop(self, widget: QWidget) -> None:
        """桌面端优化"""
        try:
            # 调整字体大小
            font = widget.font()
            font.setPointSize(self.get_font_size("medium"))
            widget.setFont(font)

            # 调整间距
            if hasattr(widget, "setSpacing"):
                widget.setSpacing(self.get_spacing("medium"))

            # 调整边距
            if hasattr(widget, "setContentsMargins"):
                margin = self.get_spacing("medium")
                widget.setContentsMargins(margin, margin, margin, margin)

        except Exception as e:
            logger.error(f"桌面端优化失败: {e}", exc_info=True)

    def _optimize_for_large_desktop(self, widget: QWidget) -> None:
        """大屏桌面端优化"""
        try:
            # 调整字体大小
            font = widget.font()
            font.setPointSize(self.get_font_size("large"))
            widget.setFont(font)

            # 调整间距
            if hasattr(widget, "setSpacing"):
                widget.setSpacing(self.get_spacing("large"))

            # 调整边距
            if hasattr(widget, "setContentsMargins"):
                margin = self.get_spacing("large")
                widget.setContentsMargins(margin, margin, margin, margin)

        except Exception as e:
            logger.error(f"大屏桌面端优化失败: {e}", exc_info=True)

    def get_optimal_window_size(self) -> QSize:
        """获取最优窗口大小"""
        try:
            screen_size = self._current_screen_size
            layout_type = self.get_layout_type()

            if layout_type == "mobile":
                # 移动端：全屏
                return screen_size
            elif layout_type == "tablet":
                # 平板端：80%屏幕大小
                return QSize(
                    int(screen_size.width() * 0.8), int(screen_size.height() * 0.8)
                )
            elif layout_type == "desktop":
                # 桌面端：70%屏幕大小
                return QSize(
                    int(screen_size.width() * 0.7), int(screen_size.height() * 0.7)
                )
            else:
                # 大屏桌面端：60%屏幕大小
                return QSize(
                    int(screen_size.width() * 0.6), int(screen_size.height() * 0.6)
                )

        except Exception as e:
            logger.error(f"获取最优窗口大小失败: {e}", exc_info=True)
            return QSize(1200, 800)

    def get_optimal_layout(self) -> dict[str, Any]:
        """获取最优布局配置"""
        try:
            layout_type = self.get_layout_type()

            return {
                "type": layout_type,
                "font_sizes": self.font_sizes.get(layout_type, {}),
                "spacings": self.spacings.get(layout_type, {}),
                "dpi_scale": self.get_dpi_scale(),
                "window_size": self.get_optimal_window_size(),
            }

        except Exception as e:
            logger.error(f"获取最优布局配置失败: {e}", exc_info=True)
            return {}

    def update_screen_info(self) -> None:
        """更新屏幕信息"""
        self._update_screen_info()
        self._update_layout_type()


class DPIOptimizer:
    """DPI优化器"""

    def __init__(self) -> None:
        self._font_cache: dict[str, QFont] = {}

    def get_optimized_font(self, family: str, size: int, weight: int = 400) -> QFont:
        """获取优化的字体"""
        try:
            cache_key = f"{family}_{size}_{weight}"

            if cache_key in self._font_cache:
                return self._font_cache[cache_key]

            # 创建字体
            font = QFont(family, size, weight)

            # 优化字体渲染
            font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

            # 缓存字体
            self._font_cache[cache_key] = font

            return font

        except Exception as e:
            logger.error(f"获取优化字体失败: {e}", exc_info=True)
            return QFont()

    def clear_font_cache(self) -> None:
        """清理字体缓存"""
        self._font_cache.clear()

    def optimize_for_high_dpi(self, widget: QWidget) -> None:
        """高DPI优化"""
        try:
            # 启用高DPI缩放
            widget.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)

            # 优化字体渲染
            font = widget.font()
            font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            widget.setFont(font)

        except Exception as e:
            logger.error(f"高DPI优化失败: {e}", exc_info=True)


# 全局响应式优化器实例
_global_responsive_optimizer: ResponsiveOptimizer | None = None


def get_responsive_optimizer() -> ResponsiveOptimizer:
    """获取全局响应式优化器实例"""
    global _global_responsive_optimizer
    if _global_responsive_optimizer is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        _global_responsive_optimizer = (
            ResponsiveOptimizer(app) if app else ResponsiveOptimizer()
        )
        _global_responsive_optimizer.initialize()
    return _global_responsive_optimizer


def optimize_for_current_screen(widget: QWidget) -> None:
    """为当前屏幕优化组件"""
    optimizer = get_responsive_optimizer()
    optimizer.optimize_widget(widget)


def get_optimal_font_size(size_type: str) -> int:
    """获取最优字体大小"""
    optimizer = get_responsive_optimizer()
    return optimizer.get_font_size(size_type)


def get_optimal_spacing(size_type: str) -> int:
    """获取最优间距"""
    optimizer = get_responsive_optimizer()
    return optimizer.get_spacing(size_type)
