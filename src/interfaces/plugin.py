"""插件相关接口定义与轻量实现"""

from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable


class PluginType(str, Enum):
    """插件类型"""

    RENDERER = "renderer"  # 渲染器
    CALCULATOR = "calculator"  # 计算器
    EXPORTER = "exporter"  # 导出器
    ANALYZER = "analyzer"  # 分析器
    VISUALIZER = "visualizer"  # 可视化
    INTEGRATION = "integration"  # 集成


class PluginPriority(int, Enum):
    """插件优先级"""

    CRITICAL = 100  # 关键
    HIGH = 75  # 高
    NORMAL = 50  # 正常
    LOW = 25  # 低
    OPTIONAL = 0  # 可选


class IPlugin(ABC):
    """插件接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> PluginType:
        """插件类型"""
        pass

    @property
    @abstractmethod
    def priority(self) -> PluginPriority:
        """插件优先级"""
        pass

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> bool:
        """初始化插件

        Args:
            config: 配置字典(可选)

        Returns:
            是否初始化成功
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查插件是否可用

        Returns:
            是否可用
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """获取插件能力

        Returns:
            能力列表
        """
        pass

    @abstractmethod
    def execute(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """执行插件动作

        Args:
            action: 动作名称
            params: 参数字典(可选)

        Returns:
            执行结果
        """
        pass


class IPluginLoader(ABC):
    """插件加载器接口"""

    @abstractmethod
    def load_plugin(self, plugin_path: str) -> IPlugin | None:
        """加载插件

        Args:
            plugin_path: 插件路径

        Returns:
            插件实例,失败返回None
        """
        pass

    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否卸载成功
        """
        pass

    @abstractmethod
    def get_plugin(self, plugin_name: str) -> IPlugin | None:
        """获取插件

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例,不存在返回None
        """
        pass

    @abstractmethod
    def list_plugins(self, plugin_type: PluginType | None = None) -> list[IPlugin]:
        """列出所有插件

        Args:
            plugin_type: 插件类型(可选,用于过滤)

        Returns:
            插件列表
        """
        pass

    @abstractmethod
    def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否重新加载成功
        """
        pass


class IPluginRegistry(ABC):
    """插件注册表接口"""

    @abstractmethod
    def register(self, plugin: IPlugin) -> bool:
        """注册插件

        Args:
            plugin: 插件实例

        Returns:
            是否注册成功
        """
        pass

    @abstractmethod
    def unregister(self, plugin_name: str) -> bool:
        """注销插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否注销成功
        """
        pass

    @abstractmethod
    def get(self, plugin_name: str) -> IPlugin | None:
        """获取插件

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例,不存在返回None
        """
        pass

    @abstractmethod
    def find_by_type(self, plugin_type: PluginType) -> list[IPlugin]:
        """根据类型查找插件

        Args:
            plugin_type: 插件类型

        Returns:
            插件列表
        """
        pass

    @abstractmethod
    def find_by_capability(self, capability: str) -> list[IPlugin]:
        """根据能力查找插件

        Args:
            capability: 能力名称

        Returns:
            插件列表
        """
        pass


# --------- 轻量级默认实现，供开发/测试环境使用 ---------


class PluginLoadError(Exception):
    """插件加载失败"""


class SimplePlugin(IPlugin):
    """基础插件实现，可作为快速占位"""

    def __init__(
        self,
        name: str,
        plugin_type: PluginType = PluginType.INTEGRATION,
        version: str = "1.0.0",
        priority: PluginPriority = PluginPriority.NORMAL,
        capabilities: list[str] | None = None,
        executor: Callable[[str, dict[str, Any] | None], Any] | None = None,
    ):
        self._name = name
        self._type = plugin_type
        self._version = version
        self._priority = priority
        self._capabilities = capabilities or []
        self._executor = executor or (lambda action, params=None: {"action": action, "params": params})
        self._available = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def plugin_type(self) -> PluginType:
        return self._type

    @property
    def priority(self) -> PluginPriority:
        return self._priority

    def initialize(self, config: dict[str, Any] | None = None) -> bool:
        self._available = True
        return True

    def shutdown(self) -> None:
        self._available = False

    def is_available(self) -> bool:
        return self._available

    def get_capabilities(self) -> list[str]:
        return list(self._capabilities)

    def execute(self, action: str, params: dict[str, Any] | None = None) -> Any:
        return self._executor(action, params or {})


class InMemoryPluginRegistry(IPluginRegistry):
    """简单的内存注册表"""

    def __init__(self):
        self._plugins: dict[str, IPlugin] = {}

    def register(self, plugin: IPlugin) -> bool:
        self._plugins[plugin.name] = plugin
        return True

    def unregister(self, plugin_name: str) -> bool:
        return self._plugins.pop(plugin_name, None) is not None

    def get(self, plugin_name: str) -> IPlugin | None:
        return self._plugins.get(plugin_name)

    def find_by_type(self, plugin_type: PluginType) -> list[IPlugin]:
        return [p for p in self._plugins.values() if p.plugin_type == plugin_type]

    def find_by_capability(self, capability: str) -> list[IPlugin]:
        return [p for p in self._plugins.values() if capability in p.get_capabilities()]


class InMemoryPluginLoader(IPluginLoader):
    """基于 importlib 的轻量加载器"""

    def __init__(self, registry: IPluginRegistry | None = None) -> None:
        self.registry = registry or InMemoryPluginRegistry()

    def load_plugin(self, plugin_path: str) -> IPlugin | None:
        """支持 'module:attr' 或 'module.Class'"""
        try:
            if ":" in plugin_path:
                module_name, attr = plugin_path.split(":", 1)
            elif "." in plugin_path:
                module_name, attr = plugin_path.rsplit(".", 1)
            else:
                raise PluginLoadError("插件路径格式错误")
            module = importlib.import_module(module_name)
            plugin_cls = getattr(module, attr, None)
            if plugin_cls is None:
                raise PluginLoadError(f"无法在模块中找到 {attr}")
            plugin: IPlugin = plugin_cls() if callable(plugin_cls) else plugin_cls
            if not isinstance(plugin, IPlugin):
                raise PluginLoadError("加载的对象不是 IPlugin 实例")
            self.registry.register(plugin)
            return plugin
        except Exception as exc:  # pragma: no cover - 防御性提示
            raise PluginLoadError(str(exc)) from exc

    def unload_plugin(self, plugin_name: str) -> bool:
        return self.registry.unregister(plugin_name)

    def get_plugin(self, plugin_name: str) -> IPlugin | None:
        return self.registry.get(plugin_name)

    def list_plugins(self, plugin_type: PluginType | None = None) -> list[IPlugin]:
        if plugin_type is None:
            return list(self.registry._plugins.values())  # noqa: SLF001 - 受控访问
        return self.registry.find_by_type(plugin_type)

    def reload_plugin(self, plugin_name: str) -> bool:
        # 简化：仅注销后再无法自动重载，返回 False 以提示外部自行处理
        if self.registry.get(plugin_name):
            self.registry.unregister(plugin_name)
            return False
        return False
