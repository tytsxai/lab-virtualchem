"""
UI主题系统
支持浅色、深色、高对比度主题，为Windows和Android优化
"""

from enum import Enum
from typing import Any

from PySide6.QtGui import QColor, QPalette


class ThemeType(Enum):
    """主题类型"""

    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    AUTO = "auto"


class ModernTheme:
    """现代化主题系统"""

    # 浅色主题配色
    LIGHT_THEME = {
        # 主色调
        "primary": "#0078D4",
        "primary_hover": "#106EBE",
        "primary_pressed": "#005A9E",
        "primary_text": "#FFFFFF",
        # 次要色
        "secondary": "#5C2D91",
        "accent": "#00BCF2",
        "success": "#10893E",
        "warning": "#FFB900",
        "danger": "#D83B01",
        "info": "#0078D4",
        # 背景色
        "background": "#F3F3F3",
        "surface": "#FFFFFF",
        "card": "#FFFFFF",
        "dialog": "#FFFFFF",
        # 文本色
        "text_primary": "#1F1F1F",
        "text_secondary": "#605E5C",
        "text_disabled": "#A19F9D",
        "text_hint": "#8A8886",
        # 边框和分割线
        "border": "#E1DFDD",
        "divider": "#EDEBE9",
        # 状态色
        "hover": "#F3F2F1",
        "selected": "#E3F2FD",
        "focus": "#0078D4",
        "disabled": "#F3F2F1",
        # 阴影
        "shadow_light": "rgba(0, 0, 0, 0.05)",
        "shadow_medium": "rgba(0, 0, 0, 0.10)",
        "shadow_strong": "rgba(0, 0, 0, 0.15)",
    }

    # 深色主题配色
    DARK_THEME = {
        # 主色调
        "primary": "#60CDFF",
        "primary_hover": "#80D6FF",
        "primary_pressed": "#40BFFF",
        "primary_text": "#000000",
        # 次要色
        "secondary": "#B4A0FF",
        "accent": "#00D7FF",
        "success": "#6CCB5F",
        "warning": "#FCE100",
        "danger": "#FF6B6B",
        "info": "#60CDFF",
        # 背景色
        "background": "#1F1F1F",
        "surface": "#2D2D2D",
        "card": "#3A3A3A",
        "dialog": "#2D2D2D",
        # 文本色
        "text_primary": "#FFFFFF",
        "text_secondary": "#D0D0D0",
        "text_disabled": "#858585",
        "text_hint": "#A0A0A0",
        # 边框和分割线
        "border": "#454545",
        "divider": "#3A3A3A",
        # 状态色
        "hover": "#3A3A3A",
        "selected": "#1E3A5F",
        "focus": "#60CDFF",
        "disabled": "#3A3A3A",
        # 阴影
        "shadow_light": "rgba(0, 0, 0, 0.20)",
        "shadow_medium": "rgba(0, 0, 0, 0.30)",
        "shadow_strong": "rgba(0, 0, 0, 0.40)",
    }

    # 高对比度主题
    HIGH_CONTRAST_THEME = {
        # 主色调
        "primary": "#FFFF00",
        "primary_hover": "#FFFF66",
        "primary_pressed": "#CCCC00",
        "primary_text": "#000000",
        # 次要色
        "secondary": "#00FFFF",
        "accent": "#FF00FF",
        "success": "#00FF00",
        "warning": "#FFFF00",
        "danger": "#FF0000",
        "info": "#00FFFF",
        # 背景色
        "background": "#000000",
        "surface": "#000000",
        "card": "#000000",
        "dialog": "#000000",
        # 文本色
        "text_primary": "#FFFFFF",
        "text_secondary": "#FFFFFF",
        "text_disabled": "#808080",
        "text_hint": "#FFFFFF",
        # 边框和分割线
        "border": "#FFFFFF",
        "divider": "#FFFFFF",
        # 状态色
        "hover": "#333333",
        "selected": "#0000FF",
        "focus": "#FFFF00",
        "disabled": "#808080",
        # 阴影
        "shadow_light": "rgba(255, 255, 255, 0.20)",
        "shadow_medium": "rgba(255, 255, 255, 0.30)",
        "shadow_strong": "rgba(255, 255, 255, 0.40)",
    }

    @staticmethod
    def get_theme_colors(theme_type: ThemeType) -> dict[str, str]:
        """获取主题配色方案"""
        if theme_type == ThemeType.DARK:
            return ModernTheme.DARK_THEME
        elif theme_type == ThemeType.HIGH_CONTRAST:
            return ModernTheme.HIGH_CONTRAST_THEME
        else:
            return ModernTheme.LIGHT_THEME

    @staticmethod
    def get_stylesheet(theme_type: ThemeType) -> str:
        """生成Qt样式表"""
        ModernTheme.get_theme_colors(theme_type)

        return """
        /* ========== 全局样式 ========== */
        QWidget {{
            font-family: "Segoe UI", "Microsoft YaHei UI", "微软雅黑", sans-serif;
            font-size: 10pt;
            color: {colors['text_primary']};
            background-color: {colors['background']};
        }}

        /* ========== 主窗口 ========== */
        QMainWindow {{
            background-color: {colors['background']};
        }}

        /* ========== 按钮样式 ========== */
        QPushButton {{
            background-color: {colors['primary']};
            color: {colors['primary_text']};
            border: none;
            border-radius: 6px;
            /* 增大触控面积，提升易点性 */
            padding: 10px 20px;
            min-width: 100px;
            min-height: 40px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }}

        QPushButton:hover {{
            background-color: {colors['primary_hover']};
        }}

        QPushButton:pressed {{
            background-color: {colors['primary_pressed']};
        }}

        QPushButton:disabled {{
            background-color: {colors['disabled']};
            color: {colors['text_disabled']};
        }}

        QPushButton:focus {{
            outline: 2px solid {colors['focus']};
            outline-offset: 2px;
            /* 明显的聚焦态，利于键盘无障碍 */
            box-shadow: 0 0 0 3px rgba(0, 120, 212, 0.25);
        }}

        /* 次要按钮 */
        QPushButton[class="secondary"] {{
            background-color: transparent;
            border: 1.5px solid {colors['border']};
            color: {colors['text_primary']};
            border-radius: 6px;
            padding: 10px 20px;
            min-height: 40px;
        }}

        QPushButton[class="secondary"]:hover {{
            background-color: {colors['hover']};
        }}

        /* ========== 输入框 ========== */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 8px;
            color: {colors['text_primary']};
            selection-background-color: {colors['selected']};
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {colors['focus']};
            padding: 7px;
        }}

        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {colors['disabled']};
            color: {colors['text_disabled']};
        }}

        /* ========== 下拉框 ========== */
        QComboBox {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 8px;
            min-height: 32px;
            color: {colors['text_primary']};
        }}

        QComboBox:hover {{
            border-color: {colors['primary']};
        }}

        QComboBox:focus {{
            border: 2px solid {colors['focus']};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {colors['text_secondary']};
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            selection-background-color: {colors['selected']};
            outline: none;
        }}

        /* ========== 列表 ========== */
        QListWidget, QListView {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px;
            outline: none;
        }}

        QListWidget::item, QListView::item {{
            padding: 10px;
            border-radius: 4px;
            color: {colors['text_primary']};
        }}

        QListWidget::item:hover, QListView::item:hover {{
            background-color: {colors['hover']};
        }}

        QListWidget::item:selected, QListView::item:selected {{
            background-color: {colors['selected']};
            color: {colors['text_primary']};
        }}

        /* ========== 分组框 ========== */
        QGroupBox {{
            background-color: {colors['card']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 8px;
            color: {colors['text_primary']};
            background-color: {colors['card']};
        }}

        /* ========== 进度条 ========== */
        QProgressBar {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            text-align: center;
            height: 28px;
            color: {colors['text_primary']};
            font-weight: 600;
        }}

        QProgressBar::chunk {{
            background-color: {colors['primary']};
            border-radius: 5px;
        }}

        /* ========== 标签页 ========== */
        QTabWidget::pane {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            top: -1px;
        }}

        QTabBar::tab {{
            background-color: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 10px 20px;
            margin-right: 4px;
            color: {colors['text_secondary']};
        }}

        QTabBar::tab:hover {{
            color: {colors['text_primary']};
            border-bottom-color: {colors['border']};
        }}

        QTabBar::tab:selected {{
            color: {colors['primary']};
            border-bottom-color: {colors['primary']};
            font-weight: 600;
        }}

        /* ========== 滚动条 ========== */
        QScrollBar:vertical {{
            background-color: {colors['background']};
            width: 14px;
            border-radius: 7px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colors['border']};
            border-radius: 7px;
            min-height: 36px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colors['text_hint']};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {colors['background']};
            height: 14px;
            border-radius: 7px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {colors['border']};
            border-radius: 7px;
            min-width: 36px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['text_hint']};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* ========== 菜单栏 ========== */
        QMenuBar {{
            background-color: {colors['surface']};
            border-bottom: 1px solid {colors['border']};
            padding: 4px;
        }}

        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
        }}

        QMenuBar::item:selected {{
            background-color: {colors['hover']};
        }}

        QMenu {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: 8px 24px 8px 12px;
            border-radius: 4px;
        }}

        QMenu::item:selected {{
            background-color: {colors['selected']};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {colors['divider']};
            margin: 4px 8px;
        }}

        /* ========== 状态栏 ========== */
        QStatusBar {{
            background-color: {colors['surface']};
            border-top: 1px solid {colors['border']};
            color: {colors['text_secondary']};
            padding: 4px;
        }}

        /* ========== 对话框 ========== */
        QDialog {{
            background-color: {colors['dialog']};
        }}

        /* ========== 复选框和单选框 ========== */
        QCheckBox, QRadioButton {{
            spacing: 8px;
            color: {colors['text_primary']};
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {colors['border']};
            background-color: {colors['surface']};
        }}

        QCheckBox::indicator {{
            border-radius: 3px;
        }}

        QRadioButton::indicator {{
            border-radius: 9px;
        }}

        QCheckBox::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
            image: url(none);
        }}

        QRadioButton::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
        }}

        /* ========== 提示框 ========== */
        QToolTip {{
            background-color: {colors['card']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 6px;
        }}

        /* ========== 分割线 ========== */
        QSplitter::handle {{
            background-color: {colors['border']};
        }}

        QSplitter::handle:horizontal {{
            width: 1px;
        }}

        QSplitter::handle:vertical {{
            height: 1px;
        }}

        /* ========== 滑块 ========== */
        QSlider::groove:horizontal {{
            background-color: {colors['border']};
            height: 4px;
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            background-color: {colors['primary']};
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -6px 0;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {colors['primary_hover']};
        }}

        /* ========== 微调框 ========== */
        QSpinBox, QDoubleSpinBox {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 6px;
            min-height: 28px;
        }}

        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {colors['focus']};
            padding: 5px;
        }}

        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: transparent;
            border: none;
            width: 20px;
        }}

        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {colors['hover']};
        }}
        """

    @staticmethod
    def get_qpalette(theme_type: ThemeType) -> QPalette:
        """生成Qt调色板"""
        colors = ModernTheme.get_theme_colors(theme_type)
        palette = QPalette()

        # 窗口背景
        palette.setColor(QPalette.ColorRole.Window, QColor(colors["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text_primary"]))

        # 控件背景
        palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["card"]))

        # 文本
        palette.setColor(QPalette.ColorRole.Text, QColor(colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text_primary"]))
        palette.setColor(
            QPalette.ColorRole.PlaceholderText, QColor(colors["text_hint"])
        )

        # 高亮
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["selected"]))
        palette.setColor(
            QPalette.ColorRole.HighlightedText, QColor(colors["text_primary"])
        )

        # 按钮
        palette.setColor(QPalette.ColorRole.Button, QColor(colors["surface"]))

        # 链接
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["primary"]))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors["secondary"]))

        return palette


class ThemeManager:
    """主题管理器"""

    def __init__(self) -> None:
        self.current_theme = ThemeType.LIGHT

    def set_theme(self, app: Any, theme_type: ThemeType) -> None:
        """应用主题"""
        self.current_theme = theme_type

        # 应用样式表
        stylesheet = ModernTheme.get_stylesheet(theme_type)
        app.setStyleSheet(stylesheet)

        # 应用调色板
        palette = ModernTheme.get_qpalette(theme_type)
        app.setPalette(palette)

    def get_current_theme(self) -> ThemeType:
        """获取当前主题"""
        return self.current_theme

    def toggle_theme(self, app: Any) -> None:
        """切换主题"""
        if self.current_theme == ThemeType.LIGHT:
            self.set_theme(app, ThemeType.DARK)
        else:
            self.set_theme(app, ThemeType.LIGHT)

    @staticmethod
    def get_system_theme() -> ThemeType:
        """获取系统主题（Windows 10/11）"""
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)

            return ThemeType.LIGHT if value == 1 else ThemeType.DARK
        except Exception:
            return ThemeType.LIGHT
