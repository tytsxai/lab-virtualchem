"""
主题管理器
提供主题切换和自定义功能
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ThemeType(Enum):
    """主题类型"""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # 跟随系统


class ThemeColorScheme:
    """主题颜色方案"""

    def __init__(self, name: str, colors: dict[str, str]):
        self.name = name
        self.colors = colors

    def get_color(self, key: str) -> QColor:
        """获取颜色"""
        color_str = self.colors.get(key, "#000000")
        return QColor(color_str)


class LightTheme(ThemeColorScheme):
    """浅色主题"""

    def __init__(self):
        colors = {
            "window": "#ffffff",
            "window_text": "#000000",
            "base": "#ffffff",
            "alternate_base": "#f7f7f7",
            "text": "#000000",
            "bright_text": "#ffffff",
            "button": "#f0f0f0",
            "button_text": "#000000",
            "highlight": "#0078d4",
            "highlighted_text": "#ffffff",
            "link": "#0078d4",
            "link_visited": "#800080",
        }
        super().__init__("light", colors)


class DarkTheme(ThemeColorScheme):
    """深色主题"""

    def __init__(self):
        colors = {
            "window": "#2d2d30",
            "window_text": "#ffffff",
            "base": "#252526",
            "alternate_base": "#2d2d30",
            "text": "#ffffff",
            "bright_text": "#000000",
            "button": "#3c3c3c",
            "button_text": "#ffffff",
            "highlight": "#007acc",
            "highlighted_text": "#ffffff",
            "link": "#4fc3f7",
            "link_visited": "#b19cd9",
        }
        super().__init__("dark", colors)


class ThemeManager:
    """主题管理器"""

    _instance: ThemeManager | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.current_theme = ThemeType.DARK
            self.themes = {
                ThemeType.LIGHT: LightTheme(),
                ThemeType.DARK: DarkTheme(),
            }
            self._load_user_preferences()

    def _load_user_preferences(self):
        """加载用户偏好"""
        try:
            # 这里可以从配置系统加载用户的主题偏好
            pass
        except Exception as e:
            logger.warning(f"加载主题偏好失败: {e}")

    def set_theme(self, theme: ThemeType) -> None:
        """设置主题"""
        if theme not in self.themes:
            logger.warning(f"不支持的主题: {theme}")
            return

        self.current_theme = theme
        self._apply_theme()

        logger.info(f"主题已切换到: {theme.value}")

    def get_current_theme(self) -> ThemeType:
        """获取当前主题"""
        return self.current_theme

    def _apply_theme(self) -> None:
        """应用主题"""
        try:
            app = QApplication.instance()
            if not app:
                return

            theme_scheme = self.themes[self.current_theme]
            self._apply_qt_theme(app, theme_scheme)

        except Exception as e:
            logger.error(f"应用主题失败: {e}")

    def _apply_qt_theme(self, app: QApplication, theme_scheme: ThemeColorScheme) -> None:
        """应用Qt主题"""
        palette = QPalette()

        # 设置基础颜色
        palette.setColor(QPalette.ColorRole.Window, theme_scheme.get_color("window"))
        palette.setColor(QPalette.ColorRole.WindowText, theme_scheme.get_color("window_text"))
        palette.setColor(QPalette.ColorRole.Base, theme_scheme.get_color("base"))
        palette.setColor(QPalette.ColorRole.AlternateBase, theme_scheme.get_color("alternate_base"))
        palette.setColor(QPalette.ColorRole.Text, theme_scheme.get_color("text"))
        palette.setColor(QPalette.ColorRole.BrightText, theme_scheme.get_color("bright_text"))
        palette.setColor(QPalette.ColorRole.Button, theme_scheme.get_color("button"))
        palette.setColor(QPalette.ColorRole.ButtonText, theme_scheme.get_color("button_text"))
        palette.setColor(QPalette.ColorRole.Highlight, theme_scheme.get_color("highlight"))
        palette.setColor(QPalette.ColorRole.HighlightedText, theme_scheme.get_color("highlighted_text"))

        app.setPalette(palette)

    def get_theme_colors(self) -> dict[str, str]:
        """获取当前主题颜色"""
        theme_scheme = self.themes[self.current_theme]
        return theme_scheme.colors.copy()

    def is_dark_theme(self) -> bool:
        """是否为深色主题"""
        return self.current_theme == ThemeType.DARK


def get_theme_manager() -> ThemeManager:
    """获取主题管理器实例"""
    return ThemeManager()
