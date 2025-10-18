"""插件相关接口定义"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


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
