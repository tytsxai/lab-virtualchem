"""
响应式设计工具
提供自适应界面功能
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AdaptiveSize:
    """自适应尺寸工具"""

    @staticmethod
    def window_size() -> QSize:
        """获取适合的窗口大小"""
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_size = screen.availableSize()
            # 使用屏幕的80%作为默认窗口大小
            width = int(screen_size.width() * 0.8)
            height = int(screen_size.height() * 0.8)
            return QSize(width, height)
        else:
            # 默认大小
            return QSize(1200, 800)

    @staticmethod
    def dialog_size() -> QSize:
        """获取适合的对话框大小"""
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_size = screen.availableSize()
            # 使用屏幕的50%作为对话框大小
            width = int(screen_size.width() * 0.5)
            height = int(screen_size.height() * 0.5)
            return QSize(width, height)
        else:
            # 默认大小
            return QSize(600, 400)


class ResponsiveHelper:
    """响应式助手"""

    @staticmethod
    def get_screen_info() -> dict[str, Any]:
        """获取屏幕信息"""
        screen = QGuiApplication.primaryScreen()
        if screen:
            return {
                'screen': screen,
                'size': screen.size(),
                'available_size': screen.availableSize(),
                'geometry': screen.geometry(),
                'available_geometry': screen.availableGeometry(),
                'dpi': screen.logicalDotsPerInch(),
                'device_pixel_ratio': screen.devicePixelRatio()
            }
        else:
            return {'screen': None}

    @staticmethod
    def is_mobile_screen() -> bool:
        """判断是否为移动设备屏幕"""
        screen_info = ResponsiveHelper.get_screen_info()
        if screen_info.get('screen'):
            size = screen_info['size']
            # 如果宽度小于800像素，认为是移动设备
            return size.width() < 800
        return False

    @staticmethod
    def get_optimal_font_size(base_size: int = 12) -> int:
        """获取最佳字体大小"""
        screen_info = ResponsiveHelper.get_screen_info()
        if screen_info.get('screen'):
            dpi = screen_info['dpi']
            # 根据DPI调整字体大小
            if dpi > 120:
                return int(base_size * 1.2)
            elif dpi < 96:
                return int(base_size * 0.9)
        return base_size

    @staticmethod
    def get_optimal_spacing(base_spacing: int = 8) -> int:
        """获取最佳间距"""
        screen_info = ResponsiveHelper.get_screen_info()
        if screen_info.get('screen'):
            size = screen_info['size']
            # 根据屏幕大小调整间距
            if size.width() > 1920:
                return int(base_spacing * 1.5)
            elif size.width() < 1024:
                return int(base_spacing * 0.8)
        return base_spacing
