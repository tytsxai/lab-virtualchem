"""
移动端适配模块
提供响应式设计、触摸优化、移动端UI等功能
"""

from .adaptive_layout import AdaptiveLayout, LayoutMode
from .mobile_ui import MobileLayout, MobileUI
from .responsive_design import Breakpoint, ResponsiveDesign
from .touch_optimization import GestureRecognizer, TouchOptimization

__all__ = [
    # 响应式设计
    "ResponsiveDesign",
    "Breakpoint",
    # 触摸优化
    "TouchOptimization",
    "GestureRecognizer",
    # 移动端UI
    "MobileUI",
    "MobileLayout",
    # 自适应布局
    "AdaptiveLayout",
    "LayoutMode",
]
