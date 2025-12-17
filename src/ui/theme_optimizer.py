"""
主题优化器
优化主题切换性能和高DPI显示效果
"""

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from .themes import ThemeManager, ThemeType

logger = logging.getLogger(__name__)


class ThemeOptimizer(QObject):
    """主题优化器"""

    # 主题切换信号
    theme_changed = Signal(ThemeType)
    theme_optimization_completed = Signal(ThemeType)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self._current_theme = ThemeType.LIGHT
        self._is_switching = False

        # 主题切换性能优化
        self._switch_delay_ms = 100
        self._optimization_timer = QTimer(self)
        self._optimization_timer.timeout.connect(self._complete_theme_switch)
        self._optimization_timer.setSingleShot(True)

        # 高DPI优化设置
        self._dpi_scale_factor = 1.0
        self._font_scale_factor = 1.0

        # 主题缓存
        self._theme_cache: dict[ThemeType, dict[str, Any]] = {}

    def initialize(self) -> None:
        """初始化主题优化器"""
        try:
            # 获取当前主题
            self._current_theme = self.theme_manager.get_current_theme()

            # 检测DPI缩放
            self._detect_dpi_scaling()

            # 预加载主题
            self._preload_themes()

            logger.info(f"主题优化器初始化完成: {self._current_theme.value}")

        except Exception as e:
            logger.error(f"主题优化器初始化失败: {e}", exc_info=True)

    def _detect_dpi_scaling(self) -> None:
        """检测DPI缩放"""
        try:
            app = QApplication.instance()
            if not app:
                return

            screen = app.primaryScreen()
            if not screen:
                return

            # 获取DPI信息
            dpi = screen.logicalDotsPerInch()
            self._dpi_scale_factor = dpi / 96.0

            # 计算字体缩放因子
            if self._dpi_scale_factor <= 1.0:
                self._font_scale_factor = 1.0
            elif self._dpi_scale_factor <= 1.25:
                self._font_scale_factor = 1.1
            elif self._dpi_scale_factor <= 1.5:
                self._font_scale_factor = 1.2
            else:
                self._font_scale_factor = 1.3

            logger.info(
                f"DPI缩放检测完成: DPI={dpi}, 缩放因子={self._dpi_scale_factor:.2f}"
            )

        except Exception as e:
            logger.error(f"DPI缩放检测失败: {e}", exc_info=True)

    def _preload_themes(self) -> None:
        """预加载主题"""
        try:
            for theme_type in ThemeType:
                self._theme_cache[theme_type] = self._generate_theme_config(theme_type)

            logger.info("主题预加载完成")

        except Exception as e:
            logger.error(f"主题预加载失败: {e}", exc_info=True)

    def _generate_theme_config(self, theme_type: ThemeType) -> dict[str, Any]:
        """生成主题配置"""
        try:
            if theme_type == ThemeType.LIGHT:
                return {
                    "background_color": "#ffffff",
                    "text_color": "#000000",
                    "accent_color": "#0078d4",
                    "border_color": "#e1e1e1",
                    "hover_color": "#f5f5f5",
                    "font_family": "Segoe UI",
                    "font_size": int(14 * self._font_scale_factor),
                }
            elif theme_type == ThemeType.DARK:
                return {
                    "background_color": "#2b2b2b",
                    "text_color": "#ffffff",
                    "accent_color": "#0078d4",
                    "border_color": "#404040",
                    "hover_color": "#404040",
                    "font_family": "Segoe UI",
                    "font_size": int(14 * self._font_scale_factor),
                }
            elif theme_type == ThemeType.HIGH_CONTRAST:
                return {
                    "background_color": "#000000",
                    "text_color": "#ffffff",
                    "accent_color": "#ffff00",
                    "border_color": "#ffffff",
                    "hover_color": "#333333",
                    "font_family": "Segoe UI",
                    "font_size": int(16 * self._font_scale_factor),
                }
            else:
                return self._theme_cache.get(ThemeType.LIGHT, {})

        except Exception as e:
            logger.error(f"生成主题配置失败: {e}", exc_info=True)
            return {}

    def switch_theme(self, theme_type: ThemeType) -> bool:
        """切换主题"""
        try:
            if self._is_switching:
                logger.warning("主题正在切换中，请稍候")
                return False

            if theme_type == self._current_theme:
                logger.info("主题无需切换")
                return True

            self._is_switching = True
            logger.info(
                f"开始切换主题: {self._current_theme.value} -> {theme_type.value}"
            )

            # 获取主题配置
            theme_config = self._theme_cache.get(theme_type)
            if not theme_config:
                theme_config = self._generate_theme_config(theme_type)
                self._theme_cache[theme_type] = theme_config

            # 应用主题
            self._apply_theme_config(theme_config)

            # 延迟完成切换
            self._optimization_timer.start(self._switch_delay_ms)

            return True

        except Exception as e:
            logger.error(f"切换主题失败: {e}", exc_info=True)
            self._is_switching = False
            return False

    def _apply_theme_config(self, config: dict[str, Any]) -> None:
        """应用主题配置"""
        try:
            app = QApplication.instance()
            if not app:
                return

            # 创建调色板
            palette = QPalette()

            # 设置背景色
            from PySide6.QtGui import QColor

            bg_color = QColor(config["background_color"])
            text_color = QColor(config["text_color"])
            accent_color = QColor(config["accent_color"])

            palette.setColor(QPalette.ColorRole.Window, bg_color)
            palette.setColor(QPalette.ColorRole.WindowText, text_color)
            palette.setColor(QPalette.ColorRole.Base, bg_color)
            palette.setColor(QPalette.ColorRole.AlternateBase, bg_color)
            palette.setColor(QPalette.ColorRole.Text, text_color)
            palette.setColor(QPalette.ColorRole.Highlight, accent_color)
            palette.setColor(QPalette.ColorRole.HighlightedText, text_color)

            # 应用调色板
            app.setPalette(palette)

            # 设置字体
            font = QFont(config["font_family"], config["font_size"])
            app.setFont(font)

        except Exception as e:
            logger.error(f"应用主题配置失败: {e}", exc_info=True)

    def _complete_theme_switch(self) -> None:
        """完成主题切换"""
        try:
            self._is_switching = False
            self.theme_changed.emit(self._current_theme)
            self.theme_optimization_completed.emit(self._current_theme)

            logger.info(f"主题切换完成: {self._current_theme.value}")

        except Exception as e:
            logger.error(f"完成主题切换失败: {e}", exc_info=True)

    def optimize_widget_for_theme(self, widget: QWidget) -> None:
        """为组件优化主题"""
        try:
            theme_config = self._theme_cache.get(self._current_theme)
            if not theme_config:
                return

            # 优化字体
            font = widget.font()
            font.setFamily(theme_config["font_family"])
            font.setPointSize(theme_config["font_size"])
            widget.setFont(font)

            # 优化样式
            style_sheet = f"""
                QWidget {{
                    background-color: {theme_config["background_color"]};
                    color: {theme_config["text_color"]};
                    border: 1px solid {theme_config["border_color"]};
                }}
                QWidget:hover {{
                    background-color: {theme_config["hover_color"]};
                }}
            """
            widget.setStyleSheet(style_sheet)

        except Exception as e:
            logger.error(f"优化组件主题失败: {e}", exc_info=True)

    def get_current_theme(self) -> ThemeType:
        """获取当前主题"""
        return self._current_theme

    def get_theme_config(self, theme_type: ThemeType | None = None) -> dict[str, Any]:
        """获取主题配置"""
        if theme_type is None:
            theme_type = self._current_theme

        return self._theme_cache.get(theme_type, {})

    def clear_theme_cache(self) -> None:
        """清理主题缓存"""
        self._theme_cache.clear()
        self._preload_themes()

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

            # 应用DPI缩放
            if self._dpi_scale_factor > 1.0:
                # 调整组件大小
                size = widget.size()
                scaled_size = size * self._dpi_scale_factor
                widget.resize(scaled_size)

        except Exception as e:
            logger.error(f"高DPI优化失败: {e}", exc_info=True)

    def get_dpi_scale_factor(self) -> float:
        """获取DPI缩放因子"""
        return self._dpi_scale_factor

    def get_font_scale_factor(self) -> float:
        """获取字体缩放因子"""
        return self._font_scale_factor


class ThemeTransitionManager:
    """主题过渡管理器"""

    def __init__(self):
        self._transition_duration_ms = 300
        self._transition_timer = QTimer()
        self._transition_timer.timeout.connect(self._update_transition)
        self._transition_timer.setSingleShot(False)

        self._is_transitioning = False
        self._start_time = 0
        self._start_config: dict[str, Any] = {}
        self._end_config: dict[str, Any] = {}
        self._current_config: dict[str, Any] = {}

    def start_transition(
        self, start_config: dict[str, Any], end_config: dict[str, Any]
    ) -> None:
        """开始主题过渡"""
        try:
            if self._is_transitioning:
                return

            self._is_transitioning = True
            self._start_time = time.time()
            self._start_config = start_config.copy()
            self._end_config = end_config.copy()
            self._current_config = start_config.copy()

            # 启动过渡定时器
            self._transition_timer.start(16)  # 60 FPS

            logger.info("主题过渡开始")

        except Exception as e:
            logger.error(f"开始主题过渡失败: {e}", exc_info=True)

    def _update_transition(self) -> None:
        """更新过渡"""
        try:
            current_time = time.time()
            elapsed = current_time - self._start_time
            progress = min(elapsed / (self._transition_duration_ms / 1000.0), 1.0)

            # 计算当前配置
            self._current_config = self._interpolate_config(
                self._start_config, self._end_config, progress
            )

            # 应用当前配置
            self._apply_current_config()

            # 检查是否完成
            if progress >= 1.0:
                self._complete_transition()

        except Exception as e:
            logger.error(f"更新过渡失败: {e}", exc_info=True)

    def _interpolate_config(
        self, start: dict[str, Any], end: dict[str, Any], progress: float
    ) -> dict[str, Any]:
        """插值配置"""
        try:
            result = {}

            for key in start:
                if key in end:
                    if isinstance(start[key], str) and start[key].startswith("#"):
                        # 颜色插值
                        result[key] = self._interpolate_color(
                            start[key], end[key], progress
                        )
                    elif isinstance(start[key], (int, float)):
                        # 数值插值
                        result[key] = start[key] + (end[key] - start[key]) * progress
                    else:
                        # 其他类型直接使用结束值
                        result[key] = end[key]
                else:
                    result[key] = start[key]

            return result

        except Exception as e:
            logger.error(f"插值配置失败: {e}", exc_info=True)
            return start

    def _interpolate_color(
        self, start_color: str, end_color: str, progress: float
    ) -> str:
        """插值颜色"""
        try:
            # 简单的颜色插值实现
            # 这里可以使用更复杂的颜色空间插值
            return end_color if progress > 0.5 else start_color

        except Exception as e:
            logger.error(f"插值颜色失败: {e}", exc_info=True)
            return start_color

    def _apply_current_config(self) -> None:
        """应用当前配置"""
        try:
            app = QApplication.instance()
            if not app:
                return

            # 应用配置到应用程序
            # 这里可以实现具体的配置应用逻辑

        except Exception as e:
            logger.error(f"应用当前配置失败: {e}", exc_info=True)

    def _complete_transition(self) -> None:
        """完成过渡"""
        try:
            self._is_transitioning = False
            self._transition_timer.stop()

            logger.info("主题过渡完成")

        except Exception as e:
            logger.error(f"完成过渡失败: {e}", exc_info=True)

    def is_transitioning(self) -> bool:
        """是否正在过渡"""
        return self._is_transitioning


# 全局主题优化器实例
_global_theme_optimizer: ThemeOptimizer | None = None


def get_theme_optimizer() -> ThemeOptimizer:
    """获取全局主题优化器实例"""
    global _global_theme_optimizer
    if _global_theme_optimizer is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        _global_theme_optimizer = ThemeOptimizer(app) if app else ThemeOptimizer()
        _global_theme_optimizer.initialize()
    return _global_theme_optimizer


def switch_theme_optimized(theme_type: ThemeType) -> bool:
    """优化主题切换"""
    optimizer = get_theme_optimizer()
    return optimizer.switch_theme(theme_type)


def optimize_widget_theme(widget: QWidget) -> None:
    """优化组件主题"""
    optimizer = get_theme_optimizer()
    optimizer.optimize_widget_for_theme(widget)


def optimize_for_high_dpi(widget: QWidget) -> None:
    """高DPI优化"""
    optimizer = get_theme_optimizer()
    optimizer.optimize_for_high_dpi(widget)
