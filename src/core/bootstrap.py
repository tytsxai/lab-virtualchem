"""
应用启动器 (Application Bootstrap)

提供应用程序初始化和配置功能
"""

import logging
from collections.abc import Callable

from src.core.config_loader import Config, ConfigAdapter, get_config
from src.core.di_container import DIContainer
from src.core.event_bus import EventBus, get_event_bus
from src.interfaces.storage import IConfig, ILogger

logger = logging.getLogger(__name__)


class ConsoleLogger(ILogger):
    """控制台日志实现"""

    def __init__(self, name: str = "App"):
        self.name = name

    def _log(self, level: str, message: str, **_kwargs):
        extra = f" {_kwargs}" if _kwargs else ""
        logger.info(f"[{level}] {self.name}: {message}{extra}")

    def debug(self, message: str, **_kwargs):
        self._log("DEBUG", message, **_kwargs)

    def info(self, message: str, **_kwargs):
        self._log("INFO", message, **_kwargs)

    def warning(self, message: str, **_kwargs):
        self._log("WARNING", message, **_kwargs)

    def error(self, message: str, **_kwargs):
        self._log("ERROR", message, **_kwargs)

    def critical(self, message: str, **_kwargs):
        self._log("CRITICAL", message, **_kwargs)


class ApplicationBuilder:
    """应用构建器"""

    def __init__(self):
        self.container = DIContainer()
        self.config: IConfig | None = None
        self._startup_actions: list = []

    def configure_config(
        self,
        config_file: str = "config.json",
        use_environment: bool = True,
        use_new_config: bool = True,
    ) -> "ApplicationBuilder":
        """
        配置配置系统

        Args:
            config_file: 配置文件路径
            use_environment: 是否使用环境变量
            use_new_config: 是否使用新的配置加载器

        Returns:
            self
        """
        if use_new_config:
            # 使用新的统一配置加载器，并通过适配器兼容旧 IConfig 接口
            new_config = get_config()
            self.container.register_singleton(Config, instance=new_config)

            self.config = ConfigAdapter(new_config)
            self.container.register_singleton(IConfig, instance=self.config)
        else:
            # 兼容旧配置系统：仅在显式请求时启用
            from src.core.config import CompositeConfig, EnvironmentConfig, JsonConfig

            configs = [JsonConfig(config_file)]
            if use_environment:
                configs.append(EnvironmentConfig())
            self.config = CompositeConfig(*configs)
            self.container.register_singleton(IConfig, instance=self.config)

        return self

    def configure_logging(self, logger: ILogger | None = None) -> "ApplicationBuilder":
        """
        配置日志系统

        Args:
            logger: 自定义日志实现

        Returns:
            self
        """
        if logger is None:
            logger = ConsoleLogger()

        self.container.register_singleton(ILogger, instance=logger)

        return self

    def configure_event_bus(
        self, event_bus: EventBus | None = None
    ) -> "ApplicationBuilder":
        """
        配置事件总线

        Args:
            event_bus: 自定义事件总线

        Returns:
            self
        """
        if event_bus is None:
            event_bus = get_event_bus()

        self.container.register_singleton(EventBus, instance=event_bus)

        return self

    def configure_services(
        self, configurator: Callable[[DIContainer], None]
    ) -> "ApplicationBuilder":
        """
        配置服务

        Args:
            configurator: 服务配置函数

        Returns:
            self

        Examples:
            def configure(container: DIContainer):
                container.register_singleton(IStorage, FileStorage)

            builder.configure_services(configure)
        """
        configurator(self.container)
        return self

    def on_startup(self, action: Callable) -> "ApplicationBuilder":
        """
        添加启动操作

        Args:
            action: 启动时执行的操作

        Returns:
            self
        """
        self._startup_actions.append(action)
        return self

    def build(self) -> DIContainer:
        """
        构建应用

        Returns:
            配置好的DI容器
        """
        # 确保基础服务已注册
        if not self.container.is_registered(ILogger):
            self.configure_logging()

        if not self.container.is_registered(IConfig):
            self.configure_config()

        # 执行启动操作
        for action in self._startup_actions:
            action(self.container)

        app_logger = self.container.resolve(ILogger)
        app_logger.info("Application initialized successfully")

        return self.container


def create_app(
    _config_file: str = "config.json", configure_services: Callable | None = None
) -> DIContainer:
    """
    快速创建应用（向后兼容函数）

    ⚠️ 已弃用：建议使用 src.core.service_registration.configure_container()

    Args:
        config_file: 配置文件路径
        configure_services: 服务配置函数

    Returns:
        配置好的DI容器

    Examples:
        # 推荐方式（新）
        from src.core.service_registration import configure_container
        container = configure_container()

        # 旧方式（仍然支持）
        container = create_app()
    """
    # 使用新的服务注册系统
    from src.core.service_registration import configure_container as new_configure

    container = new_configure()

    # 如果有自定义服务配置，应用它
    if configure_services:
        configure_services(container)

    return container


# 启动钩子装饰器
_startup_hooks = []


def on_startup(func: Callable):
    """
    启动钩子装饰器

    Examples:
        @on_startup
        def init_database(container: DIContainer):
            db = container.resolve(IDatabase)
            db.connect()
    """
    _startup_hooks.append(func)
    return func


def run_startup_hooks(container: DIContainer):
    """运行所有启动钩子"""
    for hook in _startup_hooks:
        hook(container)
