"""
配置管理系统 - 增强版
提供应用程序配置的加载、保存和管理功能，支持验证和模式
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import jsonschema
from jsonschema import Draft7Validator

from src import __version__ as APP_VERSION
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigSchemaError(Exception):
    """配置模式错误"""
    pass


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)


class ConfigSchema:
    """配置模式定义"""

    def __init__(self, schema: dict[str, Any]):
        self.schema = schema
        self._compiled_schema: Draft7Validator | None = None

    def validate(self, config: dict[str, Any]) -> ConfigValidationResult:
        """验证配置"""
        result = ConfigValidationResult(is_valid=True)

        try:
            # 编译模式（如果尚未编译）
            if self._compiled_schema is None:
                self._compiled_schema = Draft7Validator(self.schema)

            # 验证配置
            errors = list(self._compiled_schema.iter_errors(config))

            if errors:
                result.is_valid = False
                for error in errors:
                    result.add_error(f"{error.path}: {error.message}")

        except jsonschema.SchemaError as e:
            result.add_error(f"模式错误: {e}")
        except Exception as e:
            result.add_error(f"验证失败: {e}")

        return result

    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        def extract_defaults(schema: dict[str, Any]) -> dict[str, Any]:
            defaults = {}

            if "properties" in schema:
                for key, prop in schema["properties"].items():
                    if "default" in prop:
                        defaults[key] = prop["default"]
                    elif prop.get("type") == "object":
                        defaults[key] = extract_defaults(prop)
                    elif prop.get("type") == "array" and "items" in prop:
                        defaults[key] = []

            return defaults

        return extract_defaults(self.schema)


class ConfigSection:
    """配置节"""

    def __init__(self, name: str, schema: dict[str, Any] | None = None):
        self.name = name
        self.schema = schema
        self.data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """设置值"""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        return self.data.get(key, default)

    def validate(self) -> ConfigValidationResult:
        """验证配置节"""
        if not self.schema:
            return ConfigValidationResult(is_valid=True)

        schema_obj = ConfigSchema(self.schema)
        return schema_obj.validate(self.data)


class ConfigManager:
    """配置管理器 - 增强版单例模式"""

    _instance: Optional["ConfigManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self.config_dir = Path.home() / ".virtualchemlab"
            self.config_file = self.config_dir / "config.json"
            self.schema_file = self.config_dir / "config.schema.json"
            self._config: dict[str, Any] = {}
            self._sections: dict[str, ConfigSection] = {}
            self._schema: ConfigSchema | None = None
            self._initialized = True

            # 确保配置目录存在
            self.config_dir.mkdir(exist_ok=True)

            # 加载模式和配置
            self._load_schema()
            self.load_config()

    def _load_schema(self) -> None:
        """加载配置模式"""
        try:
            if self.schema_file.exists():
                with self.schema_file.open("r", encoding="utf-8") as f:
                    schema_data = json.load(f)
                self._schema = ConfigSchema(schema_data)
                logger.info(f"配置模式加载成功: {self.schema_file}")
            else:
                # 创建默认模式
                self._create_default_schema()
                self.save_schema()
                logger.info("创建默认配置模式")
        except Exception as e:
            logger.error(f"加载配置模式失败: {e}")
            self._create_default_schema()

    def _create_default_schema(self) -> None:
        """创建默认配置模式"""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "VirtualChemLab"},
                        "version": {"type": "string", "default": APP_VERSION},
                        "language": {"type": "string", "default": "zh_CN"},
                        "theme": {"type": "string", "enum": ["light", "dark", "auto"], "default": "dark"},
                        "window": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "integer", "minimum": 800, "default": 1200},
                                "height": {"type": "integer", "minimum": 600, "default": 800},
                                "maximized": {"type": "boolean", "default": False}
                            }
                        }
                    }
                },
                "ui": {
                    "type": "object",
                    "properties": {
                        "font_size": {"type": "integer", "minimum": 8, "maximum": 24, "default": 12},
                        "font_family": {"type": "string", "default": "Arial"},
                        "animation_enabled": {"type": "boolean", "default": True},
                        "sound_enabled": {"type": "boolean", "default": True},
                        "particle_effects": {"type": "boolean", "default": True}
                    }
                },
                "game": {
                    "type": "object",
                    "properties": {
                        "physics_enabled": {"type": "boolean", "default": True},
                        "gravity_strength": {"type": "number", "minimum": 0, "maximum": 2, "default": 0.5},
                        "friction": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.9},
                        "bounce_factor": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.6},
                        "collision_detection": {"type": "boolean", "default": True},
                        "auto_save": {"type": "boolean", "default": True},
                        "auto_save_interval": {"type": "integer", "minimum": 60, "default": 300}
                    }
                },
                "experiment": {
                    "type": "object",
                    "properties": {
                        "auto_progression": {"type": "boolean", "default": False},
                        "step_validation": {"type": "boolean", "default": True},
                        "real_time_feedback": {"type": "boolean", "default": True},
                        "data_logging": {"type": "boolean", "default": True},
                        "backup_enabled": {"type": "boolean", "default": True}
                    }
                },
                "logging": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "default": "INFO"},
                        "file_logging": {"type": "boolean", "default": True},
                        "console_logging": {"type": "boolean", "default": True},
                        "max_file_size": {"type": "integer", "minimum": 1024, "default": 10485760},
                        "backup_count": {"type": "integer", "minimum": 1, "default": 5}
                    }
                }
            },
            "required": ["app", "ui", "game", "experiment", "logging"]
        }
        self._schema = ConfigSchema(schema)

    def save_schema(self) -> None:
        """保存配置模式"""
        if not self._schema:
            logger.warning("无法保存配置模式：尚未创建配置模式")
            return
        try:
            with self.schema_file.open("w", encoding="utf-8") as f:
                json.dump(self._schema.schema, f, indent=2, ensure_ascii=False)
            logger.info(f"配置模式保存成功: {self.schema_file}")
        except Exception as e:
            logger.error(f"保存配置模式失败: {e}")

    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with self.config_file.open("r", encoding="utf-8") as f:
                    self._config = json.load(f)

                # 验证配置
                if self._schema:
                    validation_result = self._schema.validate(self._config)
                    if not validation_result.is_valid:
                        logger.warning("配置验证失败，使用默认配置")
                        for error in validation_result.errors:
                            logger.warning(f"配置错误: {error}")
                        self._create_default_config()
                    else:
                        logger.info(f"配置加载成功: {self.config_file}")
                        if validation_result.warnings:
                            for warning in validation_result.warnings:
                                logger.warning(f"配置警告: {warning}")
                else:
                    logger.info(f"配置加载成功: {self.config_file}")
            else:
                # 创建默认配置
                self._create_default_config()
                self.save_config()
                logger.info("创建默认配置文件")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._create_default_config()

    def save_config(self) -> None:
        """保存配置文件"""
        try:
            # 验证配置
            if self._schema:
                validation_result = self._schema.validate(self._config)
                if not validation_result.is_valid:
                    raise ConfigValidationError(f"配置验证失败: {validation_result.errors}")

            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置保存成功: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise

    def validate_config(self, config: dict[str, Any] | None = None) -> ConfigValidationResult:
        """验证配置"""
        config_to_validate = config or self._config

        if not self._schema:
            return ConfigValidationResult(is_valid=True)

        return self._schema.validate(config_to_validate)

    def get_section(self, section_name: str) -> ConfigSection:
        """获取配置节"""
        if section_name not in self._sections:
            section_data = self._config.get(section_name, {})
            section_schema = None

            # 尝试从主模式中提取节模式
            if self._schema and "properties" in self._schema.schema:
                section_schema = self._schema.schema["properties"].get(section_name)

            self._sections[section_name] = ConfigSection(section_name, section_schema)
            self._sections[section_name].data = section_data

        return self._sections[section_name]

    def set_section(self, section_name: str, data: dict[str, Any]) -> None:
        """设置配置节"""
        self._config[section_name] = data

        # 更新节对象
        if section_name in self._sections:
            self._sections[section_name].data = data

        logger.debug(f"配置节更新: {section_name}")

    def validate_section(self, section_name: str) -> ConfigValidationResult:
        """验证配置节"""
        section = self.get_section(section_name)
        return section.validate()

    def get_default_config_from_schema(self) -> dict[str, Any]:
        """从模式获取默认配置"""
        if not self._schema:
            return self._create_default_config_dict()

        return self._schema.get_default_config()

    def migrate_config(self, from_version: str, to_version: str) -> bool:
        """迁移配置"""
        try:
            target_versions = {"2.0.0", APP_VERSION}
            # 简单的版本迁移逻辑
            if from_version == "1.0.0" and to_version in target_versions:
                # 迁移逻辑
                if "paths" in self._config:
                    # 移除旧的paths配置
                    del self._config["paths"]

                # 添加新的配置项
                if "logging" not in self._config:
                    self._config["logging"] = {
                        "level": "INFO",
                        "file_logging": True,
                        "console_logging": True,
                        "max_file_size": 10485760,
                        "backup_count": 5
                    }

                self._config.setdefault("app", {})["version"] = to_version
                logger.info(f"配置已从 {from_version} 迁移到 {to_version}")
                return True

            if from_version == "2.0.0" and to_version == APP_VERSION:
                self._config.setdefault("app", {})["version"] = APP_VERSION
                logger.info(f"配置已从 {from_version} 迁移到 {to_version}")
                return True

            return False
        except Exception as e:
            logger.error(f"配置迁移失败: {e}")
            return False

    def _create_default_config(self) -> None:
        """创建默认配置"""
        if self._schema:
            self._config = self.get_default_config_from_schema()
        else:
            self._config = self._create_default_config_dict()

    def _create_default_config_dict(self) -> dict[str, Any]:
        """创建默认配置字典"""
        return {
            "app": {
                "name": "VirtualChemLab",
                "version": APP_VERSION,
                "language": "zh_CN",
                "theme": "dark",
                "window": {"width": 1200, "height": 800, "maximized": False},
            },
            "ui": {
                "font_size": 12,
                "font_family": "Arial",
                "animation_enabled": True,
                "sound_enabled": True,
                "particle_effects": True,
            },
            "game": {
                "physics_enabled": True,
                "gravity_strength": 0.5,
                "friction": 0.9,
                "bounce_factor": 0.6,
                "collision_detection": True,
                "auto_save": True,
                "auto_save_interval": 300,  # 5分钟
            },
            "experiment": {
                "auto_progression": False,
                "step_validation": True,
                "real_time_feedback": True,
                "data_logging": True,
                "backup_enabled": True,
            },
            "logging": {
                "level": "INFO",
                "file_logging": True,
                "console_logging": True,
                "max_file_size": 10485760,  # 10MB
                "backup_count": 5,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split(".")
        config = self._config

        # 导航到目标位置
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 设置值
        config[keys[-1]] = value
        logger.debug(f"配置更新: {key} = {value}")

    def _get_section_dict(self, section: str) -> dict[str, Any]:
        """获取或初始化配置节"""
        current = self._config.get(section)
        if isinstance(current, dict):
            return current
        new_section: dict[str, Any] = {}
        self._config[section] = new_section
        return new_section

    def get_app_config(self) -> dict[str, Any]:
        """获取应用配置"""
        return self._get_section_dict("app")

    def get_ui_config(self) -> dict[str, Any]:
        """获取UI配置"""
        return self._get_section_dict("ui")

    def get_game_config(self) -> dict[str, Any]:
        """获取游戏配置"""
        return self._get_section_dict("game")

    def get_experiment_config(self) -> dict[str, Any]:
        """获取实验配置"""
        return self._get_section_dict("experiment")

    def get_paths_config(self) -> dict[str, Any]:
        """获取路径配置"""
        return self._get_section_dict("paths")

    def get_logging_config(self) -> dict[str, Any]:
        """获取日志配置"""
        return self._get_section_dict("logging")

    def update_app_config(self, config: dict[str, Any]) -> None:
        """更新应用配置"""
        self._get_section_dict("app").update(config)
        self.save_config()

    def update_ui_config(self, config: dict[str, Any]) -> None:
        """更新UI配置"""
        self._get_section_dict("ui").update(config)
        self.save_config()

    def update_game_config(self, config: dict[str, Any]) -> None:
        """更新游戏配置"""
        self._get_section_dict("game").update(config)
        self.save_config()

    def update_experiment_config(self, config: dict[str, Any]) -> None:
        """更新实验配置"""
        self._get_section_dict("experiment").update(config)
        self.save_config()

    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self._create_default_config()
        self.save_config()
        logger.info("配置已重置为默认值")

    def export_config(self, file_path: str) -> None:
        """导出配置到文件"""
        try:
            export_path = Path(file_path)
            with export_path.open("w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置导出成功: {export_path}")
        except Exception as e:
            logger.error(f"导出配置失败: {e}")

    def import_config(self, file_path: str) -> None:
        """从文件导入配置"""
        try:
            import_path = Path(file_path)
            if not import_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {file_path}")

            with import_path.open("r", encoding="utf-8") as f:
                imported_config = json.load(f)

            # 验证配置结构
            if self._validate_config(imported_config):
                self._config = imported_config
                self.save_config()
                logger.info(f"配置导入成功: {import_path}")
            else:
                raise ValueError("配置文件格式无效")
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            raise

    def _validate_config(self, config: dict[str, Any]) -> bool:
        """验证配置结构"""
        required_sections = ["app", "ui", "game", "experiment", "paths", "logging"]

        for section in required_sections:
            if section not in config:
                logger.error(f"配置缺少必需部分: {section}")
                return False

        return True

    def get_config_summary(self) -> dict[str, Any]:
        """获取配置摘要"""
        return {
            "config_file": str(self.config_file),
            "config_dir": str(self.config_dir),
            "sections": list(self._config.keys()),
            "total_keys": self._count_keys(self._config),
        }

    def _count_keys(self, config: dict[str, Any]) -> int:
        """递归计算配置键数量"""
        count = 0
        for _key, value in config.items():
            count += 1
            if isinstance(value, dict):
                count += self._count_keys(value)
        return count


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager()
