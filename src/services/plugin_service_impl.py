"""
插件服务实现
"""

from src.contracts.plugin_service import (
    PluginExecuteRequest,
    PluginExecuteResponse,
    PluginInfo,
    PluginInstallRequest,
    PluginInstallResponse,
    PluginService,
    PluginServiceConfig,
    PluginStatus,
    PluginType,
)
from src.interfaces.plugin import IPluginLoader, IPluginRegistry


class PluginServiceImpl(PluginService):
    """插件服务具体实现"""

    def __init__(
        self,
        loader: IPluginLoader,
        registry: IPluginRegistry,
        config: PluginServiceConfig | None = None,
    ):
        self.loader = loader
        self.registry = registry
        self.config = config or PluginServiceConfig()

    def execute_plugin(self, request: PluginExecuteRequest) -> PluginExecuteResponse:
        """执行插件"""
        try:
            # 获取插件
            plugin = self.registry.get(request.plugin_name)
            if not plugin:
                return PluginExecuteResponse(
                    success=False, error=f"插件不存在: {request.plugin_name}"
                )

            # 检查插件是否可用
            if not plugin.is_available():
                return PluginExecuteResponse(
                    success=False, error=f"插件不可用: {request.plugin_name}"
                )

            # 执行插件
            result = plugin.execute(request.action, request.params)

            return PluginExecuteResponse(success=True, result=result)

        except Exception as e:
            return PluginExecuteResponse(success=False, error=f"执行插件失败: {str(e)}")

    def get_plugin_info(self, plugin_name: str) -> PluginInfo | None:
        """获取插件信息"""
        plugin = self.registry.get(plugin_name)
        if not plugin:
            return None

        return PluginInfo(
            name=plugin.name,
            version=plugin.version,
            plugin_type=plugin.plugin_type,
            status=PluginStatus.ENABLED
            if plugin.is_available()
            else PluginStatus.DISABLED,
            capabilities=plugin.get_capabilities(),
            description=f"{plugin.name} v{plugin.version}",
        )

    def list_plugins(
        self, plugin_type: PluginType | None = None, status: PluginStatus | None = None
    ) -> list[PluginInfo]:
        """列出插件"""
        plugins = []

        if plugin_type:
            plugin_list = self.registry.find_by_type(plugin_type)
        else:
            # 获取所有插件
            plugin_list = []
            for pt in PluginType:
                plugin_list.extend(self.registry.find_by_type(pt))

        for plugin in plugin_list:
            info = self.get_plugin_info(plugin.name)
            if info and (status is None or info.status == status):
                plugins.append(info)

        return plugins

    def install_plugin(self, request: PluginInstallRequest) -> PluginInstallResponse:
        """安装插件"""
        try:
            # 加载插件
            plugin = self.loader.load_plugin(request.plugin_path)
            if not plugin:
                return PluginInstallResponse(
                    success=False, message=f"加载插件失败: {request.plugin_path}"
                )

            # 注册插件
            success = self.registry.register(plugin)
            if not success:
                return PluginInstallResponse(
                    success=False, message=f"注册插件失败: {plugin.name}"
                )

            # 初始化插件
            if plugin.initialize(request.config):
                return PluginInstallResponse(
                    success=True,
                    plugin_name=plugin.name,
                    message=f"插件安装成功: {plugin.name}",
                )
            else:
                # 初始化失败，取消注册
                self.registry.unregister(plugin.name)
                return PluginInstallResponse(
                    success=False, message=f"插件初始化失败: {plugin.name}"
                )

        except Exception as e:
            return PluginInstallResponse(
                success=False, message=f"安装插件失败: {str(e)}"
            )

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        try:
            # 获取插件
            plugin = self.registry.get(plugin_name)
            if plugin:
                # 关闭插件
                plugin.shutdown()

            # 注销插件
            self.registry.unregister(plugin_name)

            # 卸载插件
            return self.loader.unload_plugin(plugin_name)

        except Exception:
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        try:
            plugin = self.registry.get(plugin_name)
            if not plugin:
                return False

            return plugin.initialize()

        except Exception:
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        try:
            plugin = self.registry.get(plugin_name)
            if not plugin:
                return False

            plugin.shutdown()
            return True

        except Exception:
            return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            if not self.loader.reload_plugin(plugin_name):
                return False

            plugin = self.loader.get_plugin(plugin_name)
            if not plugin:
                return False

            self.registry.unregister(plugin_name)
            return self.registry.register(plugin)
        except Exception:
            return False

    def find_plugins_by_capability(self, capability: str) -> list[PluginInfo]:
        """根据能力查找插件"""
        try:
            plugins = self.registry.find_by_capability(capability)
        except Exception:
            return []

        results: list[PluginInfo] = []
        for plugin in plugins:
            info = self.get_plugin_info(plugin.name)
            if info:
                results.append(info)
        return results
