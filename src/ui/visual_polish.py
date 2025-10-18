"""
视觉优化工具
提供界面美化功能
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


def optimize_widget_theme(widget: QWidget) -> None:
    """优化控件主题

    Args:
        widget: 要优化的控件
    """
    try:
        # 设置抗锯齿
        widget.setAttribute(QWidget.WidgetAttribute.WA_OpaquePaintEvent, True)

        # 优化渲染
        widget.setAttribute(QWidget.WidgetAttribute.WA_PaintOnScreen, False)

        logger.debug(f"控件主题优化完成: {widget.__class__.__name__}")
    except Exception as e:
        logger.warning(f"控件主题优化失败: {e}")


def apply_modern_style(widget: QWidget) -> None:
    """应用现代样式

    Args:
        widget: 要应用样式的控件
    """
    try:
        # 设置现代样式
        style = """
        QWidget {
            background-color: #f5f5f5;
            color: #333333;
        }
            QPushButton {
            background-color: #0078d4;
                color: white;
                border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }
            QPushButton:hover {
            background-color: #106ebe;
        }
            QPushButton:pressed {
            background-color: #005a9e;
        }
        """
        widget.setStyleSheet(style)
        logger.debug(f"现代样式应用完成: {widget.__class__.__name__}")
    except Exception as e:
        logger.warning(f"现代样式应用失败: {e}")


def enhance_accessibility(widget: QWidget) -> None:
    """增强可访问性

        Args:
        widget: 要增强的控件
    """
    try:
        # 设置可访问性属性
        widget.setAccessibleName(widget.__class__.__name__)
        widget.setAccessibleDescription("VirtualChemLab界面控件")

        logger.debug(f"可访问性增强完成: {widget.__class__.__name__}")
    except Exception as e:
        logger.warning(f"可访问性增强失败: {e}")
