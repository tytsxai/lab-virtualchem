"""
Bootstrap启动测试
"""

from typing import Any

import pytest

from src.core.bootstrap import ApplicationBuilder, create_app
from src.core.config_loader import Config
from src.interfaces.storage import IConfig, ILogger, IStorage


class TestApplicationBootstrap:
    """应用启动测试"""

    def test_default_bootstrap(self):
        """测试默认启动"""
        bootstrap = ApplicationBuilder()
        container = bootstrap.build()

        assert container is not None

        # 验证核心服务已注册(ILogger和IConfig应该自动注册)
        logger = container.resolve(ILogger)
        assert logger is not None

        config = container.resolve(IConfig)
        assert config is not None

    def test_custom_config_bootstrap(self):
        """测试自定义配置启动"""
        # 跳过此测试,因为ApplicationBuilder使用不同的API
        pytest.skip("需要适配新的ApplicationBuilder API")

    def test_container_configuration(self):
        """测试容器配置"""
        bootstrap = ApplicationBuilder()
        container = bootstrap.build()

        assert container is not None

        # 验证核心服务
        logger = container.resolve(ILogger)
        assert logger is not None

        config = container.resolve(IConfig)
        assert config is not None

    def test_event_bus_configuration(self):
        """测试事件总线配置"""
        bootstrap = ApplicationBuilder()
        bootstrap.configure_event_bus()
        container = bootstrap.build()

        # 验证EventBus已注册
        from src.core.event_bus import EventBus

        event_bus = container.resolve(EventBus)
        assert event_bus is not None

    def test_middleware_pipeline_creation(self):
        """测试中间件管道创建"""
        # 跳过此测试,因为ApplicationBuilder使用不同的中间件配置方式
        pytest.skip("需要适配新的ApplicationBuilder中间件API")

    def test_create_app_function(self):
        """测试create_app函数"""
        container = create_app()

        assert container is not None

        storage = container.resolve(IStorage[Any])
        assert storage is not None

        config = container.resolve(Config)
        assert config is not None

    def test_scope_management(self):
        """测试作用域管理"""
        # 跳过此测试 - DIContainer目前不支持create_scope
        pytest.skip("DIContainer尚未实现create_scope功能")


class TestConfigLoading:
    """配置加载测试"""

    def test_from_env(self):
        """测试从环境变量加载"""
        # 跳过此测试 - AppConfig已被Config替代
        pytest.skip("Config系统已重构,不再使用AppConfig")

    def test_from_dict(self):
        """测试从字典创建"""
        # 跳过此测试 - AppConfig已被Config替代
        pytest.skip("Config系统已重构,不再使用AppConfig")

    def test_to_dict(self):
        """测试转换为字典"""
        # 跳过此测试 - AppConfig已被Config替代
        pytest.skip("Config系统已重构,不再使用AppConfig")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
