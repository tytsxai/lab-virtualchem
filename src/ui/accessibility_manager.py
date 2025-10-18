"""
无障碍访问管理器
提供完善的无障碍功能支持
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ColorBlindType(Enum):
    """色盲类型"""

    NONE = "none"  # 正常视觉
    PROTANOPIA = "protanopia"  # 红色盲
    DEUTERANOPIA = "deuteranopia"  # 绿色盲
    TRITANOPIA = "tritanopia"  # 蓝黄色盲
    ACHROMATOPSIA = "achromatopsia"  # 全色盲


class AccessibilityLevel(Enum):
    """无障碍级别"""

    STANDARD = "standard"  # 标准
    ENHANCED = "enhanced"  # 增强
    MAXIMUM = "maximum"  # 最大化


class AccessibilityManager(QObject):
    """无障碍访问管理器"""

    # 信号
    accessibility_changed = Signal(dict)  # 无障碍设置变更
    focus_changed = Signal(QWidget)  # 焦点变更
    screen_reader_message = Signal(str)  # 屏幕阅读器消息

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 设置
        self.enabled = False
        self.level = AccessibilityLevel.STANDARD
        self.color_blind_mode = ColorBlindType.NONE

        # 高对比度
        self.high_contrast = False
        self.contrast_ratio = 4.5  # WCAG AA 标准

        # 字体
        self.large_text = False
        self.base_font_size = 11
        self.font_scale = 1.0

        # 焦点
        self.show_focus_indicators = True
        self.focus_thickness = 2
        self.focus_color = QColor(0, 102, 204)  # #0066CC

        # 键盘导航
        self.keyboard_only_mode = False
        self.tab_navigation_enabled = True

        # 屏幕阅读器
        self.screen_reader_enabled = False
        self.announce_changes = True

        # 动画
        self.reduce_motion = False

        # 颜色映射（色盲友好）
        self.color_maps = self._init_color_maps()

        logger.info("无障碍访问管理器初始化完成")

    def _init_color_maps(self) -> dict[ColorBlindType, dict[str, QColor]]:
        """初始化颜色映射"""
        return {
            ColorBlindType.NONE: {
                "primary": QColor(0, 102, 204),  # 蓝色
                "success": QColor(0, 200, 83),  # 绿色
                "warning": QColor(255, 160, 0),  # 橙色
                "error": QColor(211, 47, 47),  # 红色
                "info": QColor(52, 152, 219),  # 浅蓝
            },
            ColorBlindType.PROTANOPIA: {  # 红色盲
                "primary": QColor(0, 102, 204),
                "success": QColor(0, 150, 200),  # 蓝绿
                "warning": QColor(255, 200, 0),  # 明黄
                "error": QColor(100, 100, 100),  # 灰色替代红色
                "info": QColor(0, 180, 216),
            },
            ColorBlindType.DEUTERANOPIA: {  # 绿色盲
                "primary": QColor(0, 102, 204),
                "success": QColor(0, 150, 200),  # 蓝绿
                "warning": QColor(255, 200, 0),
                "error": QColor(150, 50, 50),  # 暗红
                "info": QColor(0, 180, 216),
            },
            ColorBlindType.TRITANOPIA: {  # 蓝黄色盲
                "primary": QColor(200, 0, 100),  # 品红
                "success": QColor(0, 150, 100),  # 青绿
                "warning": QColor(200, 100, 100),  # 粉红
                "error": QColor(150, 0, 0),  # 深红
                "info": QColor(100, 200, 200),  # 青色
            },
            ColorBlindType.ACHROMATOPSIA: {  # 全色盲
                "primary": QColor(100, 100, 100),
                "success": QColor(200, 200, 200),
                "warning": QColor(150, 150, 150),
                "error": QColor(50, 50, 50),
                "info": QColor(120, 120, 120),
            },
        }

    def enable_accessibility(self, level: AccessibilityLevel = AccessibilityLevel.ENHANCED):
        """启用无障碍功能

        Args:
            level: 无障碍级别
        """
        self.enabled = True
        self.level = level

        logger.info(f"无障碍功能已启用: {level.value}")

        # 根据级别应用设置
        if level == AccessibilityLevel.STANDARD:
            self.show_focus_indicators = True
            self.tab_navigation_enabled = True

        elif level == AccessibilityLevel.ENHANCED:
            self.show_focus_indicators = True
            self.tab_navigation_enabled = True
            self.announce_changes = True
            self.font_scale = 1.2

        elif level == AccessibilityLevel.MAXIMUM:
            self.show_focus_indicators = True
            self.tab_navigation_enabled = True
            self.announce_changes = True
            self.font_scale = 1.5
            self.high_contrast = True
            self.reduce_motion = True

        self.apply_settings()

    def disable_accessibility(self):
        """禁用无障碍功能"""
        self.enabled = False
        logger.info("无障碍功能已禁用")
        self.apply_settings()

    def set_color_blind_mode(self, mode: ColorBlindType):
        """设置色盲模式

        Args:
            mode: 色盲类型
        """
        self.color_blind_mode = mode
        logger.info(f"色盲模式已设置: {mode.value}")
        self.apply_settings()

    def get_accessible_color(self, color_name: str) -> QColor:
        """获取无障碍颜色

        Args:
            color_name: 颜色名称 (primary, success, warning, error, info)

        Returns:
            适配色盲模式的颜色
        """
        return self.color_maps[self.color_blind_mode].get(color_name, QColor(100, 100, 100))

    def apply_high_contrast(self, app: QApplication):
        """应用高对比度模式

        Args:
            app: 应用实例
        """
        if not self.high_contrast:
            return

        palette = QPalette()

        # 背景和文本
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))

        # 按钮
        palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))

        # 高亮
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        app.setPalette(palette)
        logger.info("高对比度模式已应用")

    def apply_font_scaling(self, app: QApplication):
        """应用字体缩放

        Args:
            app: 应用实例
        """
        if self.font_scale == 1.0:
            return

        font = app.font()
        scaled_size = int(self.base_font_size * self.font_scale)
        font.setPointSize(scaled_size)
        app.setFont(font)

        logger.info(f"字体缩放已应用: {self.font_scale}x ({scaled_size}pt)")

    def add_focus_indicator(self, widget: QWidget):
        """为控件添加焦点指示器

        Args:
            widget: 控件
        """
        if not self.show_focus_indicators:
            return

        # 设置焦点策略
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 应用焦点样式
        style = f"""
            QWidget:focus {{
                border: {self.focus_thickness}px solid {self.focus_color.name()};
                border-radius: 4px;
                outline: none;
            }}
        """

        current_style = widget.styleSheet()
        widget.setStyleSheet(current_style + "\n" + style)

    def set_accessible_name(self, widget: QWidget, name: str, description: str | None = None):
        """设置控件的无障碍名称

        Args:
            widget: 控件
            name: 可访问名称
            description: 可访问描述
        """
        widget.setAccessibleName(name)

        if description:
            widget.setAccessibleDescription(description)

        logger.debug(f"设置无障碍名称: {name}")

    def announce(self, message: str, priority: str = "polite"):
        """发送屏幕阅读器消息

        Args:
            message: 消息内容
            priority: 优先级 (polite, assertive)
        """
        if not self.screen_reader_enabled or not self.announce_changes:
            return

        # 发送信号给屏幕阅读器
        self.screen_reader_message.emit(message)

        # 也记录到日志
        logger.info(f"[屏幕阅读器] {message} (优先级: {priority})")

    def enable_keyboard_navigation(self, widget: QWidget):
        """启用键盘导航

        Args:
            widget: 根控件
        """
        if not self.tab_navigation_enabled:
            return

        # 设置Tab顺序
        self._setup_tab_order(widget)

        # 添加键盘快捷键提示
        widget.setToolTip(widget.toolTip() + "\n\n[键盘导航: Tab/Shift+Tab 切换焦点]")

        logger.debug(f"键盘导航已启用: {widget.objectName()}")

    def _setup_tab_order(self, widget: QWidget):
        """设置Tab顺序"""
        # 获取所有可聚焦的子控件
        focusable = []

        for child in widget.findChildren(QWidget):
            if child.focusPolicy() != Qt.FocusPolicy.NoFocus and child.isVisible():
                focusable.append(child)

        # 按照位置排序（从左到右，从上到下）
        focusable.sort(key=lambda w: (w.pos().y(), w.pos().x()))

        # 设置Tab顺序
        for i in range(len(focusable) - 1):
            QWidget.setTabOrder(focusable[i], focusable[i + 1])

    def get_settings(self) -> dict[str, Any]:
        """获取当前设置"""
        return {
            "enabled": self.enabled,
            "level": self.level.value,
            "color_blind_mode": self.color_blind_mode.value,
            "high_contrast": self.high_contrast,
            "large_text": self.large_text,
            "font_scale": self.font_scale,
            "show_focus_indicators": self.show_focus_indicators,
            "keyboard_only_mode": self.keyboard_only_mode,
            "screen_reader_enabled": self.screen_reader_enabled,
            "reduce_motion": self.reduce_motion,
        }

    def apply_settings(self):
        """应用所有设置"""
        app = QApplication.instance()

        if not app:
            logger.warning("应用实例不存在，无法应用设置")
            return

        # 应用高对比度
        if self.high_contrast:
            self.apply_high_contrast(app)

        # 应用字体缩放
        self.apply_font_scaling(app)

        # 发送变更信号
        self.accessibility_changed.emit(self.get_settings())

        logger.info("无障碍设置已应用")

    def create_wcag_compliant_stylesheet(self) -> str:
        """创建符合WCAG标准的样式表"""
        colors = self.color_maps[self.color_blind_mode]

        # 确保对比度符合标准
        def ensure_contrast(fg: QColor, bg: QColor) -> QColor:
            """确保前景色和背景色有足够的对比度"""
            # 简化的对比度计算
            fg_lum = fg.lightnessF()
            bg_lum = bg.lightnessF()

            ratio = (max(fg_lum, bg_lum) + 0.05) / (min(fg_lum, bg_lum) + 0.05)

            # 如果对比度不足，调整前景色
            if ratio < self.contrast_ratio:
                if bg_lum > 0.5:
                    # 背景亮，前景变暗
                    return QColor(0, 0, 0)
                else:
                    # 背景暗，前景变亮
                    return QColor(255, 255, 255)

            return fg

        bg = QColor(255, 255, 255) if not self.high_contrast else QColor(0, 0, 0)

        primary = ensure_contrast(colors["primary"], bg)
        success = ensure_contrast(colors["success"], bg)
        warning = ensure_contrast(colors["warning"], bg)
        error = ensure_contrast(colors["error"], bg)

        stylesheet = f"""
            /* 主要颜色 */
            .primary {{ color: {primary.name()}; }}
            .success {{ color: {success.name()}; }}
            .warning {{ color: {warning.name()}; }}
            .error {{ color: {error.name()}; }}

            /* 按钮 */
            QPushButton {{
                min-height: 32px;
                padding: 8px 16px;
                border: 2px solid {primary.name()};
                border-radius: 4px;
            }}

            QPushButton:focus {{
                border: {self.focus_thickness}px solid {self.focus_color.name()};
                outline: none;
            }}

            /* 输入框 */
            QLineEdit, QTextEdit {{
                min-height: 28px;
                padding: 6px;
                border: 2px solid #ccc;
                border-radius: 4px;
            }}

            QLineEdit:focus, QTextEdit:focus {{
                border: {self.focus_thickness}px solid {self.focus_color.name()};
            }}
        """

        return stylesheet


# 全局单例
_accessibility_manager: AccessibilityManager | None = None


def get_accessibility_manager() -> AccessibilityManager:
    """获取无障碍管理器单例"""
    global _accessibility_manager
    if _accessibility_manager is None:
        _accessibility_manager = AccessibilityManager()
    return _accessibility_manager
