"""
插件系统
提供可扩展的插件管理、动态加载、生命周期管理和插件间通信
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import logging
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from .common_exceptions import SystemError
from .error_handler import get_error_handler
from .enhanced_event_bus import Event, EventPriority, publish_event, subscribe_event
from .enhanced_observability import get_observability, LogLevel, trace_span, TraceType

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class PluginType(Enum):
    """插件类型"""
    CORE = "core"
    FEATURE = "feature"
    UI = "ui"
    INTEGRATION = "integration"
    UTILITY = "utility"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    config_schema: Optional[Dict[str, Any]] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type.value,
            "dependencies": self.dependencies,
            "optional_dependencies": self.optional_dependencies,
            "entry_point": self.entry_point,
            "config_schema": self.config_schema,
            "tags": self.tags
        }


@dataclass
class PluginInstance:
    """插件实例"""
    info: PluginInfo
    module: Any
    instance: Any
    state: PluginState = PluginState.UNLOADED
    load_time: Optional[float] = None
    error: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "info": self.info.to_dict(),
            "state": self.state.value,
            "load_time": self.load_time,
            "error": self.error,
            "config": self.config
        }


class PluginInterface(ABC):
    """插件接口"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化插件"""
        pass

    @abstractmethod
    def start(self) -> None:
        """启动插件"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止插件"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """清理插件"""
        pass

    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.__class__.__name__,
            version="1.0.0",
            description="",
            author="",
            plugin_type=PluginType.UTILITY
        )

    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """获取配置模式"""
        return None

    def on_event(self, event: Event) -> None:
        """处理事件"""
        pass


class PluginManager:
    """插件管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._error_handler = get_error_handler()
        self._observability = get_observability()

        # 插件存储
        self._plugins: Dict[str, PluginInstance] = {}
        self._plugin_classes: Dict[str, Type[PluginInterface]] = {}
        self._plugin_directories: List[Path] = []

        # 插件状态
        self._state_lock = threading.RLock()
        self._initialized = False

        # 统计信息
        self._stats = {
            "total_plugins": 0,
            "loaded_plugins": 0,
            "started_plugins": 0,
            "failed_plugins": 0,
            "load_time": 0.0
        }

        # 事件订阅
        self._setup_event_subscriptions()

    def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        subscribe_event("plugin_load_request", self._handle_load_request)
        subscribe_event("plugin_unload_request", self._handle_unload_request)
        subscribe_event("plugin_start_request", self._handle_start_request)
        subscribe_event("plugin_stop_request", self._handle_stop_request)

    def initialize(self) -> None:
        """初始化插件管理器"""
        if self._initialized:
            return

        # 添加默认插件目录
        default_dirs = [
            Path("plugins"),
            Path("src/plugins"),
            Path("extensions")
        ]

        for dir_path in default_dirs:
            if dir_path.exists():
                self.add_plugin_directory(dir_path)

        self._initialized = True

        # 记录日志
        self._observability.log(
            LogLevel.INFO,
            "Plugin manager initialized",
            module="PluginManager",
            function="initialize"
        )

    def add_plugin_directory(self, directory: Path) -> None:
        """添加插件目录"""
        if directory.exists() and directory.is_dir():
            self._plugin_directories.append(directory)

            # 扫描目录中的插件
            self._scan_directory(directory)

            # 记录日志
            self._observability.log(
                LogLevel.INFO,
                f"Added plugin directory: {directory}",
                module="PluginManager",
                function="add_plugin_directory"
            )

    def _scan_directory(self, directory: Path) -> None:
        """扫描插件目录"""
        try:
            for file_path in directory.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue

                try:
                    self._load_plugin_from_file(file_path)
                except Exception as e:
                    logger.error(f"Failed to load plugin from {file_path}: {e}")

            # 扫描子目录
            for subdir in directory.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("__"):
                    self._scan_directory(subdir)
        except Exception as e:
            logger.error(f"Failed to scan directory {directory}: {e}")

    def _load_plugin_from_file(self, file_path: Path) -> None:
        """从文件加载插件"""
        try:
            # 构建模块名
            module_name = f"plugin_{file_path.stem}_{id(self)}"

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # 编译模块
            module = importlib.util.module_from_spec(
                importlib.util.spec_from_loader(module_name, loader=None)
            )

            # 执行代码
            exec(source_code, module.__dict__)

            # 查找插件类
            plugin_class = self._find_plugin_class(module)
            if plugin_class:
                self._register_plugin_class(plugin_class)

                # 记录日志
                self._observability.log(
                    LogLevel.INFO,
                    f"Loaded plugin class: {plugin_class.__name__}",
                    module="PluginManager",
                    function="_load_plugin_from_file"
                )
        except Exception as e:
            logger.error(f"Failed to load plugin from file {file_path}: {e}")

    def _find_plugin_class(self, module: Any) -> Optional[Type[PluginInterface]]:
        """查找插件类"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, PluginInterface) and
                obj != PluginInterface):
                return obj
        return None

    def _register_plugin_class(self, plugin_class: Type[PluginInterface]) -> None:
        """注册插件类"""
        plugin_name = plugin_class.__name__
        self._plugin_classes[plugin_name] = plugin_class

        # 记录日志
        self._observability.log(
            LogLevel.DEBUG,
            f"Registered plugin class: {plugin_name}",
            module="PluginManager",
            function="_register_plugin_class"
        )

    def load_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """加载插件"""
        if name not in self._plugin_classes:
            logger.error(f"Plugin class not found: {name}")
            return False

        if name in self._plugins:
            logger.warning(f"Plugin already loaded: {name}")
            return True

        with self._state_lock:
            try:
                # 创建插件实例
                plugin_class = self._plugin_classes[name]
                plugin_instance = plugin_class()

                # 获取插件信息
                plugin_info = plugin_instance.get_info()
                plugin_info.name = name

                # 创建插件实例
                instance = PluginInstance(
                    info=plugin_info,
                    module=plugin_class,
                    instance=plugin_instance,
                    state=PluginState.LOADING,
                    config=config or {}
                )

                self._plugins[name] = instance
                self._stats["total_plugins"] += 1

                # 记录日志
                self._observability.log(
                    LogLevel.INFO,
                    f"Plugin loaded: {name}",
                    module="PluginManager",
                    function="load_plugin"
                )

                return True
            except Exception as e:
                logger.error(f"Failed to load plugin {name}: {e}")
                self._stats["failed_plugins"] += 1
                return False

    def unload_plugin(self, name: str) -> bool:
        """卸载插件"""
        if name not in self._plugins:
            logger.warning(f"Plugin not loaded: {name}")
            return False

        with self._state_lock:
            try:
                plugin = self._plugins[name]

                # 停止插件
                if plugin.state == PluginState.STARTED:
                    self.stop_plugin(name)

                # 清理插件
                if plugin.state == PluginState.INITIALIZED:
                    plugin.instance.cleanup()

                # 移除插件
                del self._plugins[name]
                self._stats["loaded_plugins"] -= 1

                # 记录日志
                self._observability.log(
                    LogLevel.INFO,
                    f"Plugin unloaded: {name}",
                    module="PluginManager",
                    function="unload_plugin"
                )

                return True
            except Exception as e:
                logger.error(f"Failed to unload plugin {name}: {e}")
                return False

    def initialize_plugin(self, name: str) -> bool:
        """初始化插件"""
        if name not in self._plugins:
            logger.error(f"Plugin not loaded: {name}")
            return False

        with self._state_lock:
            try:
                plugin = self._plugins[name]

                if plugin.state != PluginState.LOADED:
                    logger.warning(f"Plugin not in loaded state: {name}")
                    return False

                plugin.state = PluginState.INITIALIZING

                # 初始化插件
                plugin.instance.initialize(plugin.config)

                plugin.state = PluginState.INITIALIZED
                plugin.load_time = time.time()

                # 记录日志
                self._observability.log(
                    LogLevel.INFO,
                    f"Plugin initialized: {name}",
                    module="PluginManager",
                    function="initialize_plugin"
                )

                return True
            except Exception as e:
                logger.error(f"Failed to initialize plugin {name}: {e}")
                plugin.state = PluginState.ERROR
                plugin.error = str(e)
                return False

    def start_plugin(self, name: str) -> bool:
        """启动插件"""
        if name not in self._plugins:
            logger.error(f"Plugin not loaded: {name}")
            return False

        with self._state_lock:
            try:
                plugin = self._plugins[name]

                if plugin.state != PluginState.INITIALIZED:
                    logger.warning(f"Plugin not initialized: {name}")
                    return False

                plugin.state = PluginState.STARTING

                # 启动插件
                plugin.instance.start()

                plugin.state = PluginState.STARTED
                self._stats["started_plugins"] += 1

                # 记录日志
                self._observability.log(
                    LogLevel.INFO,
                    f"Plugin started: {name}",
                    module="PluginManager",
                    function="start_plugin"
                )

                return True
            except Exception as e:
                logger.error(f"Failed to start plugin {name}: {e}")
                plugin.state = PluginState.ERROR
                plugin.error = str(e)
                return False

    def stop_plugin(self, name: str) -> bool:
        """停止插件"""
        if name not in self._plugins:
            logger.error(f"Plugin not loaded: {name}")
            return False

        with self._state_lock:
            try:
                plugin = self._plugins[name]

                if plugin.state != PluginState.STARTED:
                    logger.warning(f"Plugin not started: {name}")
                    return False

                plugin.state = PluginState.STOPPING

                # 停止插件
                plugin.instance.stop()

                plugin.state = PluginState.STOPPED
                self._stats["started_plugins"] -= 1

                # 记录日志
                self._observability.log(
                    LogLevel.INFO,
                    f"Plugin stopped: {name}",
                    module="PluginManager",
                    function="stop_plugin"
                )

                return True
            except Exception as e:
                logger.error(f"Failed to stop plugin {name}: {e}")
                plugin.state = PluginState.ERROR
                plugin.error = str(e)
                return False

    def get_plugin(self, name: str) -> Optional[PluginInstance]:
        """获取插件实例"""
        return self._plugins.get(name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInstance]:
        """按类型获取插件"""
        return [
            plugin for plugin in self._plugins.values()
            if plugin.info.plugin_type == plugin_type
        ]

    def get_plugin_list(self) -> List[PluginInstance]:
        """获取插件列表"""
        return list(self._plugins.values())

    def get_available_plugins(self) -> List[str]:
        """获取可用插件列表"""
        return list(self._plugin_classes.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def _handle_load_request(self, event: Event) -> None:
        """处理加载请求"""
        plugin_name = event.data.get("name")
        config = event.data.get("config", {})

        if plugin_name:
            success = self.load_plugin(plugin_name, config)
            if success:
                self.initialize_plugin(plugin_name)
                self.start_plugin(plugin_name)

    def _handle_unload_request(self, event: Event) -> None:
        """处理卸载请求"""
        plugin_name = event.data.get("name")

        if plugin_name:
            self.unload_plugin(plugin_name)

    def _handle_start_request(self, event: Event) -> None:
        """处理启动请求"""
        plugin_name = event.data.get("name")

        if plugin_name:
            self.start_plugin(plugin_name)

    def _handle_stop_request(self, event: Event) -> None:
        """处理停止请求"""
        plugin_name = event.data.get("name")

        if plugin_name:
            self.stop_plugin(plugin_name)

    def export_plugin_info(self, output_dir: Path) -> None:
        """导出插件信息"""
        output_dir.mkdir(exist_ok=True)

        # 导出插件列表
        plugins_file = output_dir / "plugins.json"
        plugins_data = {
            "plugins": [plugin.to_dict() for plugin in self._plugins.values()],
            "available_plugins": self.get_available_plugins(),
            "stats": self.get_stats()
        }

        with open(plugins_file, 'w', encoding='utf-8') as f:
            json.dump(plugins_data, f, indent=2, ensure_ascii=False)


# 全局插件管理器实例
_global_plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    return _global_plugin_manager


def load_plugin(name: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """加载插件"""
    return _global_plugin_manager.load_plugin(name, config)


def unload_plugin(name: str) -> bool:
    """卸载插件"""
    return _global_plugin_manager.unload_plugin(name)


def start_plugin(name: str) -> bool:
    """启动插件"""
    return _global_plugin_manager.start_plugin(name)


def stop_plugin(name: str) -> bool:
    """停止插件"""
    return _global_plugin_manager.stop_plugin(name)


def get_plugin(name: str) -> Optional[PluginInstance]:
    """获取插件实例"""
    return _global_plugin_manager.get_plugin(name)
