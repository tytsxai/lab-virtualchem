"""
基础窗口组件
提供窗口组件的基础功能和通用接口
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from ...core.common_exceptions import UIError
from ...core.enhanced_event_bus import (
    Event,
    EventPriority,
    get_event_bus,
    publish_event,
    subscribe_event,
)
from ...core.error_handler import get_error_handler, safe_execute

logger = logging.getLogger(__name__)


class BaseWindowComponent(QWidget):
    """基础窗口组件"""

    # 信号定义
    component_ready = Signal()
    component_error = Signal(str)
    component_warning = Signal(str)
    component_info = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._initialized = False
        self._error_handler = get_error_handler()
        self._event_bus = get_event_bus()
        self._component_data: dict[str, Any] = {}
        self._subscriptions: list = []

    def initialize(self) -> None:
        """初始化组件"""
        if self._initialized:
            return

        try:
            self._setup_ui()
            self._connect_signals()
            self._load_data()
            self._initialized = True
            self.component_ready.emit()
            logger.debug(f"Component {self.__class__.__name__} initialized")
        except Exception as e:
            self._handle_initialization_error(e)

    @abstractmethod
    def _setup_ui(self) -> None:
        """设置UI - 子类必须实现"""
        pass

    def _connect_signals(self) -> None:
        """连接信号 - 子类可以重写"""
        pass

    def _load_data(self) -> None:
        """加载数据 - 子类可以重写"""
        pass

    def _handle_initialization_error(self, error: Exception) -> None:
        """处理初始化错误"""
        ui_error = UIError(
            message=f"Failed to initialize {self.__class__.__name__}: {str(error)}",
            widget=self.__class__.__name__,
            action="initialize",
            cause=error
        )
        self._error_handler.handle_error(ui_error)
        self.component_error.emit(str(error))

    def safe_execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """安全执行函数"""
        from ...core.common_exceptions import ErrorCategory, ErrorSeverity
        return safe_execute(
            func,
            *args,
            error_class=UIError,
            category=ErrorCategory.UI,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )

    def set_component_data(self, key: str, value: Any) -> None:
        """设置组件数据"""
        self._component_data[key] = value

    def get_component_data(self, key: str, default: Any = None) -> Any:
        """获取组件数据"""
        return self._component_data.get(key, default)

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def cleanup(self) -> None:
        """清理资源"""
        try:
            self._cleanup_resources()
            self._initialized = False
            logger.debug(f"Component {self.__class__.__name__} cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _cleanup_resources(self) -> None:
        """清理资源 - 子类可以重写"""
        # 取消所有事件订阅
        for subscription in self._subscriptions:
            self._event_bus.unsubscribe(subscription)
        self._subscriptions.clear()

    def subscribe_event(
        self,
        event_name: str,
        callback: Callable[[Event], None],
        priority: EventPriority = EventPriority.NORMAL,
        tags_filter: dict[str, str] | None = None,
        once: bool = False
    ) -> None:
        """订阅事件"""
        subscription = subscribe_event(
            event_name, callback, priority, tags_filter, once, self.__class__.__name__
        )
        self._subscriptions.append(subscription)

    def publish_event(
        self,
        event_name: str,
        data: Any = None,
        priority: EventPriority = EventPriority.NORMAL,
        tags: dict[str, str] | None = None
    ) -> None:
        """发布事件"""
        publish_event(event_name, data, self.__class__.__name__, priority, tags)


class WindowManager(QObject):
    """窗口管理器"""

    # 信号定义
    window_created = Signal(str)
    window_destroyed = Signal(str)
    window_error = Signal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._windows: dict[str, BaseWindowComponent] = {}
        self._error_handler = get_error_handler()

    def register_window(self, name: str, window: BaseWindowComponent) -> None:
        """注册窗口"""
        if name in self._windows:
            logger.warning(f"Window {name} already registered, replacing")

        self._windows[name] = window
        self.window_created.emit(name)
        logger.debug(f"Window {name} registered")

    def unregister_window(self, name: str) -> None:
        """注销窗口"""
        if name in self._windows:
            window = self._windows.pop(name)
            window.cleanup()
            self.window_destroyed.emit(name)
            logger.debug(f"Window {name} unregistered")

    def get_window(self, name: str) -> BaseWindowComponent | None:
        """获取窗口"""
        return self._windows.get(name)

    def get_all_windows(self) -> dict[str, BaseWindowComponent]:
        """获取所有窗口"""
        return self._windows.copy()

    def initialize_all_windows(self) -> None:
        """初始化所有窗口"""
        for name, window in self._windows.items():
            try:
                window.initialize()
            except Exception as e:
                self.window_error.emit(name, str(e))

    def cleanup_all_windows(self) -> None:
        """清理所有窗口"""
        for window in self._windows.values():
            window.cleanup()
        self._windows.clear()


class ComponentRegistry:
    """组件注册表"""

    def __init__(self):
        self._components: dict[str, type] = {}
        self._instances: dict[str, BaseWindowComponent] = {}

    def register_component(self, name: str, component_class: type) -> None:
        """注册组件类"""
        self._components[name] = component_class
        logger.debug(f"Component class {name} registered")

    def create_component(self, name: str, parent: QWidget | None = None) -> BaseWindowComponent | None:
        """创建组件实例"""
        if name not in self._components:
            logger.error(f"Component {name} not registered")
            return None

        try:
            component_class = self._components[name]
            instance = component_class(parent)
            self._instances[name] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to create component {name}: {e}")
            return None

    def get_component(self, name: str) -> BaseWindowComponent | None:
        """获取组件实例"""
        return self._instances.get(name)

    def remove_component(self, name: str) -> None:
        """移除组件实例"""
        if name in self._instances:
            instance = self._instances.pop(name)
            instance.cleanup()

    def get_registered_components(self) -> dict[str, type]:
        """获取已注册的组件"""
        return self._components.copy()


# 全局组件注册表
_global_registry = ComponentRegistry()


def get_component_registry() -> ComponentRegistry:
    """获取全局组件注册表"""
    return _global_registry


def register_component(name: str, component_class: type) -> None:
    """注册组件"""
    _global_registry.register_component(name, component_class)


def create_component(name: str, parent: QWidget | None = None) -> BaseWindowComponent | None:
    """创建组件"""
    return _global_registry.create_component(name, parent)
