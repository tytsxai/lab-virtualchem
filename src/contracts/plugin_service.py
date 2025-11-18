"""插件服务契约"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..interfaces.plugin import PluginPriority, PluginType


class PluginStatus(str, Enum):
    """插件状态"""

    ACTIVE = "active"  # 激活
    INACTIVE = "inactive"  # 未激活
    ERROR = "error"  # 错误
    DISABLED = "disabled"  # 禁用
    NOT_INSTALLED = "not_installed"  # 未安装


@dataclass
class PluginServiceConfig:
    """插件服务配置"""

    plugin_dir: str = "plugins"  # 插件目录
    enable_auto_load: bool = True  # 是否自动加载
    enable_hot_reload: bool = False  # 是否热重载
    sandboxed: bool = True  # 是否沙箱隔离
    max_execution_time: int = 30  # 最大执行时间(秒)
    enable_logging: bool = True  # 是否启用日志


@dataclass
class PluginInfo:
    """插件信息DTO"""

    name: str  # 插件名称
    version: str  # 版本
    plugin_type: PluginType  # 插件类型
    priority: PluginPriority  # 优先级
    status: PluginStatus  # 状态
    description: str = ""  # 描述
    author: str = ""  # 作者
    license: str = ""  # 许可证
    dependencies: list[str] = field(default_factory=list)  # 依赖列表
    capabilities: list[str] = field(default_factory=list)  # 能力列表
    config: dict[str, Any] = field(default_factory=dict)  # 配置
    error_msg: str | None = None  # 错误信息


@dataclass
class PluginExecuteRequest:
    """插件执行请求DTO"""

    plugin_name: str  # 插件名称
    action: str  # 动作名称
    params: dict[str, Any] = field(default_factory=dict)  # 参数
    timeout: int | None = None  # 超时时间(秒)
    async_execution: bool = False  # 是否异步执行


@dataclass
class PluginExecuteResponse:
    """插件执行响应DTO"""

    success: bool  # 是否成功
    result: Any = None  # 结果
    message: str = ""  # 消息
    execution_time: float = 0.0  # 执行时间(秒)
    errors: list[str] = field(default_factory=list)  # 错误列表
    error: str | None = None  # 主要错误信息(向后兼容字段)


@dataclass
class PluginInstallRequest:
    """插件安装请求DTO"""

    plugin_path: str  # 插件路径
    install_dependencies: bool = True  # 是否安装依赖
    force_reinstall: bool = False  # 是否强制重装


@dataclass
class PluginInstallResponse:
    """插件安装响应DTO"""

    success: bool  # 是否成功
    plugin_name: str | None = None  # 插件名称
    message: str = ""  # 消息
    installed_dependencies: list[str] = field(default_factory=list)  # 已安装依赖


class PluginService(ABC):
    """插件服务抽象类"""

    @abstractmethod
    def execute_plugin(self, request: PluginExecuteRequest) -> PluginExecuteResponse:
        """执行插件

        Args:
            request: 执行请求

        Returns:
            执行响应
        """
        pass

    @abstractmethod
    def get_plugin_info(self, plugin_name: str) -> PluginInfo | None:
        """获取插件信息

        Args:
            plugin_name: 插件名称

        Returns:
            插件信息
        """
        pass

    @abstractmethod
    def list_plugins(
        self, plugin_type: PluginType | None = None, status: PluginStatus | None = None
    ) -> list[PluginInfo]:
        """列出插件

        Args:
            plugin_type: 插件类型(可选)
            status: 插件状态(可选)

        Returns:
            插件信息列表
        """
        pass

    @abstractmethod
    def install_plugin(self, request: PluginInstallRequest) -> PluginInstallResponse:
        """安装插件

        Args:
            request: 安装请求

        Returns:
            安装响应
        """
        pass

    @abstractmethod
    def uninstall_plugin(self, plugin_name: str) -> bool:
        """卸载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def find_plugins_by_capability(self, capability: str) -> list[PluginInfo]:
        """根据能力查找插件

        Args:
            capability: 能力名称

        Returns:
            插件信息列表
        """
        pass
