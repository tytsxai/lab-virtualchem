"""
UI组件模块
提供主窗口的各种组件
"""

from .base_window import (
    BaseWindowComponent,
    ComponentRegistry,
    WindowManager,
    create_component,
    get_component_registry,
    register_component,
)
from .menu_component import MenuComponent
from .statusbar_component import StatusBarComponent
from .toolbar_component import ToolbarComponent

__all__ = [
    "BaseWindowComponent",
    "ComponentRegistry",
    "WindowManager",
    "create_component",
    "get_component_registry",
    "register_component",
    "MenuComponent",
    "StatusBarComponent",
    "ToolbarComponent",
]
