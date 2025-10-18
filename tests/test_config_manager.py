"""
配置管理器测试
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config_manager import (
    ConfigManager,
    ConfigSchema,
    ConfigSection,
    ConfigValidationError,
    ConfigValidationResult,
)


class TestConfigSchema:
    """配置模式测试"""

    def test_schema_validation_success(self):
        """测试模式验证成功"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }

        config_schema = ConfigSchema(schema)
        config = {"name": "test", "age": 25}

        result = config_schema.validate(config)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_schema_validation_failure(self):
        """测试模式验证失败"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }

        config_schema = ConfigSchema(schema)
        config = {"age": -5}  # 缺少name，age为负数

        result = config_schema.validate(config)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_get_default_config(self):
        """测试获取默认配置"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "default": "default_name"},
                "age": {"type": "integer", "default": 18},
                "settings": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean", "default": True},
                    },
                },
            },
        }

        config_schema = ConfigSchema(schema)
        default_config = config_schema.get_default_config()

        assert default_config["name"] == "default_name"
        assert default_config["age"] == 18
        assert default_config["settings"]["enabled"] is True


class TestConfigSection:
    """配置节测试"""

    def test_config_section_basic(self):
        """测试配置节基本功能"""
        section = ConfigSection("test")

        section.set("key1", "value1")
        section.set("key2", 42)

        assert section.get("key1") == "value1"
        assert section.get("key2") == 42
        assert section.get("key3", "default") == "default"

    def test_config_section_validation(self):
        """测试配置节验证"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer", "minimum": 0},
            },
        }

        section = ConfigSection("test", schema)
        section.set("name", "test")
        section.set("count", 5)

        result = section.validate()
        assert result.is_valid is True

    def test_config_section_validation_failure(self):
        """测试配置节验证失败"""
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "minimum": 0},
            },
        }

        section = ConfigSection("test", schema)
        section.set("count", -1)  # 违反最小值约束

        result = section.validate()
        assert result.is_valid is False


class TestConfigManager:
    """配置管理器测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()

        assert manager1 is manager2

    def test_load_and_save_config(self):
        """测试配置加载和保存"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "config.json"

            # 创建测试配置
            test_config = {
                "app": {"name": "TestApp", "version": "1.0.0"},
                "ui": {"theme": "dark"},
            }

            with config_file.open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            # 创建新的管理器实例
            manager = ConfigManager.__new__(ConfigManager)
            manager._initialized = False
            manager.config_dir = temp_path
            manager.config_file = config_file
            manager.schema_file = temp_path / "config.schema.json"
            manager._config = {}
            manager._sections = {}
            manager._schema = None

            # 手动初始化
            manager._initialized = True
            manager.load_config()

            assert manager.get("app.name") == "TestApp"
            assert manager.get("app.version") == "1.0.0"
            assert manager.get("ui.theme") == "dark"

    def test_config_validation(self):
        """测试配置验证"""
        manager = ConfigManager()

        # 测试有效配置（包含所有必需字段）
        valid_config = {
            "app": {"name": "TestApp", "version": "1.0.0"},
            "ui": {"theme": "dark"},
            "game": {"physics_enabled": True},
            "experiment": {"auto_progression": False},
            "logging": {"level": "INFO"},
        }

        result = manager.validate_config(valid_config)
        assert result.is_valid is True

    def test_get_section(self):
        """测试获取配置节"""
        manager = ConfigManager()
        manager._config = {
            "app": {"name": "TestApp", "version": "1.0.0"},
            "ui": {"theme": "dark"},
        }

        app_section = manager.get_section("app")
        assert app_section.name == "app"
        assert app_section.get("name") == "TestApp"
        assert app_section.get("version") == "1.0.0"

    def test_set_section(self):
        """测试设置配置节"""
        manager = ConfigManager()

        section_data = {"name": "TestApp", "version": "1.0.0"}
        manager.set_section("app", section_data)

        assert manager._config["app"] == section_data

    def test_migrate_config(self):
        """测试配置迁移"""
        manager = ConfigManager()
        manager._config = {
            "app": {"version": "1.0.0"},
            "paths": {"data": "data"},  # 旧配置
        }

        success = manager.migrate_config("1.0.0", "2.0.0")
        assert success is True
        assert "paths" not in manager._config
        assert "logging" in manager._config

    def test_get_default_config_from_schema(self):
        """测试从模式获取默认配置"""
        manager = ConfigManager()

        # 模拟有模式的情况
        schema_data = {
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "DefaultApp"},
                        "version": {"type": "string", "default": "1.0.0"},
                    },
                },
            },
        }
        manager._schema = ConfigSchema(schema_data)

        default_config = manager.get_default_config_from_schema()
        assert default_config["app"]["name"] == "DefaultApp"
        assert default_config["app"]["version"] == "1.0.0"


if __name__ == "__main__":
    pytest.main([__file__])
