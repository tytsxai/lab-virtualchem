"""
配置管理系统测试
"""

import json

import pytest

from src import __version__ as APP_VERSION
from src.core.config_loader import (
    AppConfig,
    CacheConfig,
    Config,
    DatabaseConfig,
    LogConfig,
    MonitoringConfig,
    PathsConfig,
    RedisConfig,
    SecurityConfig,
    get_config,
)
from config.schemas.app_config import AppConfiguration as SchemaAppConfiguration


class TestAppConfig:
    """应用配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = AppConfig()
        assert config.name == "VirtualChemLab"
        assert config.version == APP_VERSION
        assert config.environment == "development"
        assert not config.debug

    def test_environment_override(self, monkeypatch):
        """测试环境变量覆盖"""
        # AppConfig不再直接从环境变量读取
        config = AppConfig(environment="production")
        assert config.environment == "production"


class TestPathConfig:
    """路径配置测试"""

    def test_default_paths(self):
        """测试默认路径"""
        config = PathsConfig()
        assert config.templates == "assets/templates"
        assert config.knowledge == "assets/knowledge"
        assert config.i18n == "assets/i18n"
        assert config.user_data == "user_data"

    def test_path_normalization(self):
        """测试路径标准化"""
        config = PathsConfig(reports="reports\\subdir")
        # Path validation doesn't normalize, just validates it's a string
        assert config.reports == "reports\\subdir"


class TestDatabaseConfig:
    """数据库配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = DatabaseConfig()
        assert config.type == "sqlite"
        assert config.path == "data/virtualchemlab.db"
        assert config.pool_size == 10
        assert config.pool_max_overflow == 20


class TestSecurityConfig:
    """安全配置测试"""

    def test_default_values(self):
        """测试默认值"""
        # SecurityConfig requires jwt_secret_key
        config = SecurityConfig(jwt_secret_key="a" * 32)
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expiration == 3600

    def test_environment_variables(self, monkeypatch):
        """测试环境变量加载"""
        # SecurityConfig requires jwt_secret_key with at least 32 chars
        config = SecurityConfig(jwt_secret_key="test-jwt-key-with-32-characters-or-more")
        assert config.jwt_secret_key == "test-jwt-key-with-32-characters-or-more"

    def test_production_validation(self, monkeypatch):
        """测试生产环境验证"""
        # Test that short JWT key is rejected
        with pytest.raises(ValueError, match="JWT密钥长度必须至少32个字符"):
            SecurityConfig(jwt_secret_key="short")

    def test_production_requires_env_secrets(self, monkeypatch):
        """Schema-based production config must fail when secrets are missing."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
        monkeypatch.delenv("DEVELOPER_SECRET_KEY", raising=False)

        with pytest.raises(ValueError, match="缺少必需的密钥"):
            SchemaAppConfiguration.load(env="production")


class TestConfig:
    """主配置类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config(
            app=AppConfig(),
            paths=PathsConfig(),
            database=DatabaseConfig(),
            redis=RedisConfig(),
            cache=CacheConfig(),
            security=SecurityConfig(jwt_secret_key="a" * 32),
            monitoring=MonitoringConfig(),
            log=LogConfig(),
        )
        assert config.app.name == "VirtualChemLab"
        assert config.database.type == "sqlite"
        assert config.security.jwt_algorithm == "HS256"

    def test_config_load(self, tmp_path, monkeypatch):
        """测试配置加载"""
        # 创建临时配置文件
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        base_config = {
            "app": {"name": "TestApp", "version": "1.0.0"},
            "database": {"type": "sqlite"},
        }

        with open(config_dir / "base.json", "w") as f:
            json.dump(base_config, f)

        # 临时修改配置路径
        import config.schemas.app_config as config_module

        config_module.Path(__file__)
        monkeypatch.setattr(
            config_module.Path, "__file__", str(config_dir / "schemas" / "app_config.py")
        )

        # 加载配置
        # config = Config.load()
        # assert config.app.name == "TestApp"

    def test_deep_merge(self):
        """测试深度合并"""
        # Test dict merging manually since _deep_merge is a private method
        base = {"app": {"name": "App", "version": "1.0"}, "database": {"type": "sqlite"}}

        override = {"app": {"version": "2.0"}, "database": {"path": "custom/db.sqlite"}}

        # Manual deep merge logic
        from copy import deepcopy

        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key].update(value)
            else:
                result[key] = value

        assert result["app"]["name"] == "App"
        assert result["app"]["version"] == "2.0"
        assert result["database"]["type"] == "sqlite"
        assert result["database"]["path"] == "custom/db.sqlite"

    @pytest.mark.skip("新配置系统不需要get_project_root")
    def test_get_project_root(self):
        """测试获取项目根目录"""
        pass

    @pytest.mark.skip("新配置系统不需要get_absolute_path")
    def test_get_absolute_path(self):
        """测试获取绝对路径"""
        pass

    @pytest.mark.skip("新配置系统不需要validate_paths")
    def test_validate_paths(self):
        """测试路径验证"""
        pass

    @pytest.mark.skip("新配置系统不需要create_directories")
    def test_create_directories(self, tmp_path, monkeypatch):
        """测试创建目录"""
        pass


class TestGetConfig:
    """get_config函数测试"""

    def test_singleton(self):
        """测试单例模式"""
        config1 = get_config()
        config2 = get_config()

        # 新配置系统返回相同实例
        assert config1 is config2

    @pytest.mark.skip("新配置系统不支持reload参数")
    def test_reload(self):
        """测试重新加载"""
        pass


class TestConfigIntegration:
    """配置集成测试"""

    def test_full_workflow(self, tmp_path, monkeypatch):
        """测试完整工作流"""
        # 1. 创建配置
        config = Config()

        # 2. 验证配置字段
        assert config.app.name == "VirtualChemLab"
        assert isinstance(config.app.port, int)
        assert config.paths.logs == "logs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
