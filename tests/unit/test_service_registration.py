"""
服务注册系统测试
测试 src.core.service_registration 模块
"""

import pytest

from src.core.di_container import DIContainer
from src.core.event_bus import EventBus
from src.core.service_registration import (
    ServiceRegistry,
    configure_container,
    get_configured_container,
)
from src.core.template_engine import TemplateEngine
from src.interfaces.storage import IStorage
from src.storage.json_store import JSONStore
from src.utils.i18n import I18n


class TestServiceRegistry:
    """服务注册表测试"""

    def test_create_registry(self):
        """测试创建注册表"""
        registry = ServiceRegistry()
        assert isinstance(registry, ServiceRegistry)

    def test_register_all_services(self):
        """测试注册所有服务"""
        container = DIContainer()
        registry = ServiceRegistry()
        registry.register_all(container)

        # 验证关键服务已注册
        assert container.is_registered(TemplateEngine)
        assert container.is_registered(EventBus)
        assert container.is_registered(IStorage)
        assert container.is_registered(I18n)


class TestConfigureContainer:
    """容器配置测试"""

    def test_configure_with_defaults(self):
        """测试默认配置"""
        container = configure_container()

        assert isinstance(container, DIContainer)
        assert container.is_registered(TemplateEngine)
        assert container.is_registered(EventBus)

    def test_configure_with_custom_config(self, monkeypatch):
        """测试自定义配置"""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long-12345")

        from src.core.config_loader import get_config

        config = get_config()

        container = configure_container(config=config)
        assert isinstance(container, DIContainer)


class TestGetConfiguredContainer:
    """全局容器测试"""

    def test_get_global_container(self):
        """测试获取全局容器"""
        container = get_configured_container()

        assert isinstance(container, DIContainer)
        assert container.is_registered(TemplateEngine)

    def test_singleton_container(self):
        """测试单例模式"""
        container1 = get_configured_container()
        container2 = get_configured_container()

        # 应该返回同一个实例
        assert container1 is container2


class TestServiceResolution:
    """服务解析测试"""

    def test_resolve_template_engine(self):
        """测试解析TemplateEngine"""
        container = configure_container()
        engine = container.resolve(TemplateEngine)

        assert isinstance(engine, TemplateEngine)

    def test_resolve_event_bus(self):
        """测试解析EventBus"""
        container = configure_container()
        bus = container.resolve(EventBus)

        assert isinstance(bus, EventBus)

    def test_resolve_storage(self):
        """测试解析IStorage"""
        container = configure_container()
        storage = container.resolve(IStorage)

        assert isinstance(storage, JSONStore)

    def test_resolve_i18n(self):
        """测试解析I18n"""
        container = configure_container()
        i18n = container.resolve(I18n)

        assert isinstance(i18n, I18n)


class TestServiceLifetime:
    """服务生命周期测试"""

    def test_singleton_services(self):
        """测试单例服务"""
        container = configure_container()

        # 多次解析应该返回同一个实例
        engine1 = container.resolve(TemplateEngine)
        engine2 = container.resolve(TemplateEngine)

        assert engine1 is engine2

    def test_multiple_storage_instances(self):
        """测试存储服务（单例）"""
        container = configure_container()

        storage1 = container.resolve(IStorage)
        storage2 = container.resolve(IStorage)

        # IStorage应该是单例
        assert storage1 is storage2


class TestServiceDependencies:
    """服务依赖测试"""

    def test_template_engine_initialization(self):
        """测试TemplateEngine初始化"""
        container = configure_container()
        engine = container.resolve(TemplateEngine)

        # 验证模板引擎正确初始化
        assert engine.templates_dir is not None

    def test_event_bus_initialization(self):
        """测试EventBus初始化"""
        container = configure_container()
        bus = container.resolve(EventBus)

        # 验证事件总线正确初始化
        assert hasattr(bus, "publish")
        assert hasattr(bus, "subscribe")


class TestIntegration:
    """集成测试"""

    def test_full_container_setup(self, monkeypatch):
        """测试完整容器设置"""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long-12345")

        # 1. 配置容器
        container = configure_container()

        # 2. 解析多个服务
        engine = container.resolve(TemplateEngine)
        bus = container.resolve(EventBus)
        storage = container.resolve(IStorage)
        i18n = container.resolve(I18n)

        # 3. 验证所有服务
        assert isinstance(engine, TemplateEngine)
        assert isinstance(bus, EventBus)
        assert isinstance(storage, JSONStore)
        assert isinstance(i18n, I18n)

    def test_service_interaction(self):
        """测试服务交互"""
        container = configure_container()

        # 获取服务
        storage = container.resolve(IStorage)
        engine = container.resolve(TemplateEngine)

        # 验证服务可以正常工作
        assert storage is not None
        assert engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
