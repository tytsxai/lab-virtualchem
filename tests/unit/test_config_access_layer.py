"""
配置访问抽象层测试
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src import __version__ as APP_VERSION
from src.core.config_access_layer import (
    ConfigAccessLayer,
    config,
    config_get,
    config_get_bool,
    config_get_dict,
    config_get_float,
    config_get_int,
    config_get_list,
    config_get_path,
    config_get_section,
    config_get_with_validation,
    config_has,
    config_set,
    config_validate_required,
    get_config_access,
    reload_config_access,
)


class MockConfig:
    """模拟配置对象"""

    def __init__(self):
        self.app = MockAppConfig()
        self.database = MockDatabaseConfig()
        self.cache = MockCacheConfig()

    def dict(self):
        return {
            "app": self.app.dict(),
            "database": self.database.dict(),
            "cache": self.cache.dict(),
        }


class MockAppConfig:
    """模拟应用配置"""

    def __init__(self):
        self.name = "VirtualChemLab"
        self.version = APP_VERSION
        self.debug = True

    def dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "debug": self.debug,
        }


class MockDatabaseConfig:
    """模拟数据库配置"""

    def __init__(self):
        self.type = "sqlite"
        self.path = "data/test.db"

    def dict(self):
        return {
            "type": self.type,
            "path": self.path,
        }


class MockCacheConfig:
    """模拟缓存配置"""

    def __init__(self):
        self.enabled = True
        self.max_size = 1000

    def dict(self):
        return {
            "enabled": self.enabled,
            "max_size": self.max_size,
        }


class TestConfigAccessLayer:
    """测试配置访问抽象层"""

    def setup_method(self):
        """测试前准备"""
        self.mock_config = MockConfig()
        self.access_layer = ConfigAccessLayer(self.mock_config)

    def test_get_basic_value(self):
        """测试获取基本值"""
        assert self.access_layer.get("app.name") == "VirtualChemLab"
        assert self.access_layer.get("app.version") == APP_VERSION
        assert self.access_layer.get("app.debug") is True

    def test_get_nested_value(self):
        """测试获取嵌套值"""
        assert self.access_layer.get("database.type") == "sqlite"
        assert self.access_layer.get("database.path") == "data/test.db"

    def test_get_nonexistent_value(self):
        """测试获取不存在的值"""
        assert self.access_layer.get("nonexistent.key") is None
        assert self.access_layer.get("nonexistent.key", "default") == "default"

    def test_set_value(self):
        """测试设置值"""
        self.access_layer.set("test.key", "test_value")
        assert self.access_layer.get("test.key") == "test_value"

    def test_has_value(self):
        """测试检查值是否存在"""
        assert self.access_layer.has("app.name") is True
        assert self.access_layer.has("nonexistent.key") is False

    def test_get_section(self):
        """测试获取配置节"""
        app_section = self.access_layer.get_section("app")
        assert isinstance(app_section, dict)
        assert app_section["name"] == "VirtualChemLab"
        assert app_section["version"] == APP_VERSION

    def test_get_section_nonexistent(self):
        """测试获取不存在的配置节"""
        section = self.access_layer.get_section("nonexistent")
        assert section == {}

    def test_get_path(self):
        """测试获取路径配置"""
        path = self.access_layer.get_path("database.path")
        assert isinstance(path, Path)
        assert str(path) == "data/test.db"

    def test_get_path_with_base_path(self):
        """测试获取路径配置（带基础路径）"""
        base_path = Path("/base")
        path = self.access_layer.get_path("database.path", base_path)
        assert isinstance(path, Path)
        assert str(path) == "/base/data/test.db"

    def test_get_path_nonexistent(self):
        """测试获取不存在的路径配置"""
        with pytest.raises(ValueError, match="Path configuration not found"):
            self.access_layer.get_path("nonexistent.path")

    def test_get_int(self):
        """测试获取整数配置"""
        self.access_layer.set("test.int", "123")
        assert self.access_layer.get_int("test.int") == 123
        assert self.access_layer.get_int("test.int", 456) == 123
        assert self.access_layer.get_int("nonexistent", 456) == 456

    def test_get_int_invalid(self):
        """测试获取无效整数配置"""
        self.access_layer.set("test.invalid", "not_a_number")
        assert self.access_layer.get_int("test.invalid", 456) == 456

    def test_get_float(self):
        """测试获取浮点数配置"""
        self.access_layer.set("test.float", "123.45")
        assert self.access_layer.get_float("test.float") == 123.45
        assert self.access_layer.get_float("test.float", 456.78) == 123.45
        assert self.access_layer.get_float("nonexistent", 456.78) == 456.78

    def test_get_float_invalid(self):
        """测试获取无效浮点数配置"""
        self.access_layer.set("test.invalid", "not_a_number")
        assert self.access_layer.get_float("test.invalid", 456.78) == 456.78

    def test_get_bool(self):
        """测试获取布尔配置"""
        self.access_layer.set("test.bool_true", True)
        self.access_layer.set("test.bool_false", False)
        self.access_layer.set("test.string_true", "true")
        self.access_layer.set("test.string_false", "false")
        self.access_layer.set("test.string_1", "1")
        self.access_layer.set("test.string_0", "0")

        assert self.access_layer.get_bool("test.bool_true") is True
        assert self.access_layer.get_bool("test.bool_false") is False
        assert self.access_layer.get_bool("test.string_true") is True
        assert self.access_layer.get_bool("test.string_false") is False
        assert self.access_layer.get_bool("test.string_1") is True
        assert self.access_layer.get_bool("test.string_0") is False
        assert self.access_layer.get_bool("nonexistent", True) is True

    def test_get_list(self):
        """测试获取列表配置"""
        self.access_layer.set("test.list", ["item1", "item2", "item3"])
        self.access_layer.set("test.string_list", "item1,item2,item3")
        self.access_layer.set("test.single_item", "single")

        assert self.access_layer.get_list("test.list") == ["item1", "item2", "item3"]
        assert self.access_layer.get_list("test.string_list") == [
            "item1",
            "item2",
            "item3",
        ]
        assert self.access_layer.get_list("test.single_item") == ["single"]
        assert self.access_layer.get_list("nonexistent") == []
        assert self.access_layer.get_list("nonexistent", ["default"]) == ["default"]

    def test_get_dict(self):
        """测试获取字典配置"""
        test_dict = {"key1": "value1", "key2": "value2"}
        self.access_layer.set("test.dict", test_dict)

        assert self.access_layer.get_dict("test.dict") == test_dict
        assert self.access_layer.get_dict("nonexistent") == {}
        assert self.access_layer.get_dict("nonexistent", {"default": "value"}) == {
            "default": "value"
        }

    def test_clear_cache(self):
        """测试清除缓存"""
        # 先获取一个值，使其被缓存
        self.access_layer.get("app.name")

        # 清除缓存
        self.access_layer.clear_cache()

        # 再次获取应该重新从配置中读取
        assert self.access_layer.get("app.name") == "VirtualChemLab"

    def test_get_all(self):
        """测试获取所有配置"""
        all_config = self.access_layer.get_all()
        assert isinstance(all_config, dict)
        assert "app" in all_config
        assert "database" in all_config
        assert "cache" in all_config

    def test_validate_required(self):
        """测试验证必需配置"""
        # 应该通过验证
        self.access_layer.validate_required("app.name", "app.version")

        # 应该抛出异常
        with pytest.raises(ValueError, match="Missing required configuration"):
            self.access_layer.validate_required("app.name", "nonexistent.key")

    def test_get_with_validation(self):
        """测试获取配置并验证"""

        def positive_validator(value):
            if value <= 0:
                raise ValueError("Value must be positive")
            return value

        self.access_layer.set("test.positive", 5)
        assert (
            self.access_layer.get_with_validation("test.positive", positive_validator)
            == 5
        )

        self.access_layer.set("test.negative", -5)
        assert (
            self.access_layer.get_with_validation(
                "test.negative", positive_validator, 10
            )
            == 10
        )


class TestGlobalFunctions:
    """测试全局函数"""

    def setup_method(self):
        """测试前准备"""
        self.mock_config = MockConfig()

    @patch("src.core.config_access_layer.get_config")
    def test_get_config_access(self, mock_get_config):
        """测试获取全局配置访问层"""
        mock_get_config.return_value = self.mock_config

        access_layer = get_config_access()
        assert isinstance(access_layer, ConfigAccessLayer)

    @patch("src.core.config_access_layer._config_access_layer")
    def test_reload_config_access(self, mock_config_access_layer):
        """测试重新加载全局配置访问层"""
        mock_layer = MagicMock()
        mock_config_access_layer.return_value = mock_layer

        reload_config_access()
        mock_layer.reload.assert_called_once()

    @patch("src.core.config_access_layer.get_config_access")
    def test_convenience_functions(self, mock_get_config_access):
        """测试便捷函数"""
        mock_layer = MagicMock()
        mock_get_config_access.return_value = mock_layer

        # 测试各种便捷函数
        config_get("test.key", "default")
        config_set("test.key", "value")
        config_has("test.key")
        config_get_section("test")
        config_get_path("test.path")
        config_get_int("test.int", 0)
        config_get_float("test.float", 0.0)
        config_get_bool("test.bool", False)
        config_get_list("test.list", [])
        config_get_dict("test.dict", {})
        config_validate_required("test.key")
        config_get_with_validation("test.key", lambda x: x, "default")

        # 验证调用
        assert mock_layer.get.called
        assert mock_layer.set.called
        assert mock_layer.has.called
        assert mock_layer.get_section.called
        assert mock_layer.get_path.called
        assert mock_layer.get_int.called
        assert mock_layer.get_float.called
        assert mock_layer.get_bool.called
        assert mock_layer.get_list.called
        assert mock_layer.get_dict.called
        assert mock_layer.validate_required.called
        assert mock_layer.get_with_validation.called


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @patch("src.core.config_access_layer.get_config_access")
    def test_config_alias(self, mock_get_config_access):
        """测试config别名"""
        mock_layer = MagicMock()
        mock_get_config_access.return_value = mock_layer

        # 使用别名
        config.get("test.key", "default")

        # 验证调用
        mock_layer.get.assert_called_once_with("test.key", "default")


class TestPerformance:
    """性能测试"""

    def setup_method(self):
        """测试前准备"""
        self.mock_config = MockConfig()
        self.access_layer = ConfigAccessLayer(self.mock_config)

    def test_get_performance(self):
        """测试获取性能"""
        import time

        start_time = time.time()
        for _ in range(1000):
            self.access_layer.get("app.name")
        elapsed_time = time.time() - start_time

        assert elapsed_time < 1.0  # 1000次获取应该在1秒内完成

    def test_cache_performance(self):
        """测试缓存性能"""
        import time

        # 第一次获取（无缓存）
        start_time = time.time()
        self.access_layer.get("app.name")
        first_time = time.time() - start_time

        # 第二次获取（有缓存）
        start_time = time.time()
        self.access_layer.get("app.name")
        second_time = time.time() - start_time

        # 缓存应该更快
        assert second_time < first_time


if __name__ == "__main__":
    pytest.main([__file__])
