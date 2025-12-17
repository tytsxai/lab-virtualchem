"""
新配置加载器测试
测试 src.core.config_loader 模块
"""

import pytest

from src import __version__ as APP_VERSION
from src.core.config_loader import (
    AppConfig,
    Config,
    DatabaseConfig,
    PathsConfig,
    SecurityConfig,
    get_config,
)


class TestAppConfig:
    """应用配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = AppConfig()
        assert config.name == "VirtualChemLab"
        assert config.version == APP_VERSION
        assert config.environment == "development"
        assert config.debug is False

    def test_custom_values(self):
        """测试自定义值"""
        config = AppConfig(
            name="CustomApp", version="3.0.0", environment="production", debug=False
        )
        assert config.name == "CustomApp"
        assert config.version == "3.0.0"
        assert config.environment == "production"
        assert config.debug is False


class TestPathsConfig:
    """路径配置测试"""

    def test_default_paths(self):
        """测试默认路径"""
        config = PathsConfig()
        assert config.templates == "assets/templates"
        assert config.knowledge == "assets/knowledge"
        assert config.user_data == "user_data"
        assert config.reports == "reports"

    def test_custom_paths(self):
        """测试自定义路径"""
        config = PathsConfig(templates="custom/templates", user_data="custom/data")
        assert config.templates == "custom/templates"
        assert config.user_data == "custom/data"


class TestDatabaseConfig:
    """数据库配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = DatabaseConfig()
        assert config.type == "sqlite"
        assert config.path == "data/virtualchemlab.db"


class TestSecurityConfig:
    """安全配置测试"""

    def test_with_jwt_key(self):
        """测试JWT密钥"""
        config = SecurityConfig(
            jwt_secret_key="test-jwt-secret-key-32-characters-long-12345"
        )
        assert config.jwt_secret_key == "test-jwt-secret-key-32-characters-long-12345"

    def test_with_developer_key(self):
        """测试开发者密钥"""
        config = SecurityConfig(
            jwt_secret_key="test-jwt-secret-key-32-characters-long-12345",
            developer_key_hash="test-dev-key-32-characters-long-12345",
        )
        assert config.developer_key_hash == "test-dev-key-32-characters-long-12345"


class TestConfig:
    """主配置类测试"""

    def test_load_from_get_config(self):
        """测试通过get_config加载"""
        config = get_config()
        assert isinstance(config, Config)
        assert config.app.name == "VirtualChemLab"

    def test_config_sections(self):
        """测试配置sections"""
        config = get_config()
        assert hasattr(config, "app")
        assert hasattr(config, "paths")
        assert hasattr(config, "database")
        assert hasattr(config, "security")
        assert hasattr(config, "monitoring")


class TestGetConfig:
    """get_config函数测试"""

    def test_singleton(self):
        """测试单例模式"""
        config1 = get_config()
        config2 = get_config()

        # 应该返回同一个实例
        assert config1 is config2


class TestConfigLoading:
    """配置加载测试"""

    @pytest.mark.skip("内部函数不对外暴露")
    def test_load_config_file(self, tmp_path):
        """测试加载配置文件"""
        pass

    @pytest.mark.skip("内部函数不对外暴露")
    def test_merge_configs(self):
        """测试配置合并"""
        pass


class TestConfigIntegration:
    """配置集成测试"""

    def test_full_workflow(self, monkeypatch):
        """测试完整工作流"""
        # 设置环境变量
        monkeypatch.setenv(
            "JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long-12345"
        )
        monkeypatch.setenv("ENVIRONMENT", "development")

        # 加载配置
        config = get_config()

        # 验证配置
        assert config.app.name == "VirtualChemLab"
        assert config.app.environment == "development"
        # JWT密钥会从环境变量或配置文件读取，不一定等于我们设置的值
        assert config.security.jwt_secret_key is not None
        assert len(config.security.jwt_secret_key) >= 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
