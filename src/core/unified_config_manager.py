"""
统一配置管理器
整合所有配置管理功能，提供统一的配置接口
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

import jsonschema
import yaml

from .common_exceptions import ConfigurationError
from .error_handler import get_error_handler, safe_execute

logger = logging.getLogger(__name__)


@dataclass
class ConfigSection:
    """配置节"""
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    schema: Optional[Dict[str, Any]] = None
    required: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self.data[key] = value

    def has(self, key: str) -> bool:
        """检查配置键是否存在"""
        return key in self.data

    def remove(self, key: str) -> None:
        """移除配置键"""
        self.data.pop(key, None)

    def validate(self) -> bool:
        """验证配置"""
        if not self.schema:
            return True

        try:
            jsonschema.validate(self.data, self.schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Validation error in section {self.name}: {e}")
            return False


class UnifiedConfigManager:
    """统一配置管理器"""

    def __init__(self, config_dir: Optional[Path] = None):
        self._config_dir = config_dir or Path("config")
        self._sections: Dict[str, ConfigSection] = {}
        self._error_handler = get_error_handler()
        self._initialized = False

        # 确保配置目录存在
        self._config_dir.mkdir(exist_ok=True)

    def initialize(self) -> None:
        """初始化配置管理器"""
        if self._initialized:
            return

        try:
            self._load_default_sections()
            self._load_config_files()
            self._initialized = True
            logger.info("UnifiedConfigManager initialized successfully")
        except Exception as e:
            self._handle_initialization_error(e)

    def _load_default_sections(self) -> None:
        """加载默认配置节"""
        # 应用配置
        app_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "environment": {"type": "string", "enum": ["development", "production", "test"]},
                "debug": {"type": "boolean"},
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]}
            },
            "required": ["name", "version", "environment"]
        }

        self._sections["app"] = ConfigSection(
            name="app",
            data={
                "name": "VirtualChemLab",
                "version": "2.0.0",
                "environment": "development",
                "debug": True,
                "log_level": "INFO"
            },
            schema=app_schema,
            required=True
        )

        # UI配置
        ui_schema = {
            "type": "object",
            "properties": {
                "theme": {"type": "string", "enum": ["light", "dark", "auto"]},
                "language": {"type": "string"},
                "font_size": {"type": "integer", "minimum": 8, "maximum": 24},
                "window_width": {"type": "integer", "minimum": 800},
                "window_height": {"type": "integer", "minimum": 600}
            }
        }

        self._sections["ui"] = ConfigSection(
            name="ui",
            data={
                "theme": "auto",
                "language": "zh_CN",
                "font_size": 12,
                "window_width": 1200,
                "window_height": 800
            },
            schema=ui_schema
        )

        # 性能配置
        performance_schema = {
            "type": "object",
            "properties": {
                "enable_caching": {"type": "boolean"},
                "cache_size": {"type": "integer", "minimum": 0},
                "max_memory_usage": {"type": "integer", "minimum": 0},
                "enable_profiling": {"type": "boolean"}
            }
        }

        self._sections["performance"] = ConfigSection(
            name="performance",
            data={
                "enable_caching": True,
                "cache_size": 1000,
                "max_memory_usage": 512,
                "enable_profiling": False
            },
            schema=performance_schema
        )

        # 实验配置
        experiment_schema = {
            "type": "object",
            "properties": {
                "default_template": {"type": "string"},
                "auto_save": {"type": "boolean"},
                "save_interval": {"type": "integer", "minimum": 1},
                "max_history": {"type": "integer", "minimum": 1}
            }
        }

        self._sections["experiment"] = ConfigSection(
            name="experiment",
            data={
                "default_template": "basic_titration",
                "auto_save": True,
                "save_interval": 30,
                "max_history": 100
            },
            schema=experiment_schema
        )

    def _load_config_files(self) -> None:
        """加载配置文件"""
        # 加载主配置文件
        main_config_file = self._config_dir / "config.json"
        if main_config_file.exists():
            self._load_config_file(main_config_file)

        # 加载环境特定配置
        env_config_file = self._config_dir / f"config_{self.get('app.environment', 'development')}.json"
        if env_config_file.exists():
            self._load_config_file(env_config_file)

        # 加载用户配置
        user_config_file = self._config_dir / "user_config.json"
        if user_config_file.exists():
            self._load_config_file(user_config_file)

    def _load_config_file(self, config_file: Path) -> None:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() == '.yaml' or config_file.suffix.lower() == '.yml':
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            if isinstance(config_data, dict):
                for section_name, section_data in config_data.items():
                    if section_name in self._sections:
                        # 更新现有节
                        self._sections[section_name].data.update(section_data)
                    else:
                        # 创建新节
                        self._sections[section_name] = ConfigSection(
                            name=section_name,
                            data=section_data
                        )

            logger.info(f"Loaded config file: {config_file}")
        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if '.' not in key:
            raise ConfigurationError(f"Invalid config key format: {key}")

        section_name, config_key = key.split('.', 1)

        if section_name not in self._sections:
            return default

        return self._sections[section_name].get(config_key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        if '.' not in key:
            raise ConfigurationError(f"Invalid config key format: {key}")

        section_name, config_key = key.split('.', 1)

        if section_name not in self._sections:
            self._sections[section_name] = ConfigSection(name=section_name)

        self._sections[section_name].set(config_key, value)

    def has(self, key: str) -> bool:
        """检查配置键是否存在"""
        if '.' not in key:
            return False

        section_name, config_key = key.split('.', 1)

        if section_name not in self._sections:
            return False

        return self._sections[section_name].has(config_key)

    def remove(self, key: str) -> None:
        """移除配置键"""
        if '.' not in key:
            raise ConfigurationError(f"Invalid config key format: {key}")

        section_name, config_key = key.split('.', 1)

        if section_name in self._sections:
            self._sections[section_name].remove(config_key)

    def get_section(self, section_name: str) -> Optional[ConfigSection]:
        """获取配置节"""
        return self._sections.get(section_name)

    def add_section(self, section_name: str, schema: Optional[Dict[str, Any]] = None, required: bool = False) -> None:
        """添加配置节"""
        if section_name not in self._sections:
            self._sections[section_name] = ConfigSection(
                name=section_name,
                schema=schema,
                required=required
            )

    def validate_all(self) -> bool:
        """验证所有配置"""
        all_valid = True

        for section in self._sections.values():
            if not section.validate():
                all_valid = False

        return all_valid

    def save_config(self, filename: Optional[str] = None) -> None:
        """保存配置"""
        if not filename:
            filename = "config.json"

        config_file = self._config_dir / filename

        try:
            config_data = {}
            for section_name, section in self._sections.items():
                config_data[section_name] = section.data

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Config saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")

    def reload_config(self) -> None:
        """重新加载配置"""
        self._sections.clear()
        self._initialized = False
        self.initialize()

    def _handle_initialization_error(self, error: Exception) -> None:
        """处理初始化错误"""
        config_error = ConfigurationError(
            message=f"Failed to initialize UnifiedConfigManager: {str(error)}",
            cause=error
        )
        self._error_handler.handle_error(config_error)

    def get_all_sections(self) -> Dict[str, ConfigSection]:
        """获取所有配置节"""
        return self._sections.copy()

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局配置管理器实例
_global_config_manager = UnifiedConfigManager()


def get_config_manager() -> UnifiedConfigManager:
    """获取全局配置管理器"""
    return _global_config_manager


def get_config(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return _global_config_manager.get(key, default)


def set_config(key: str, value: Any) -> None:
    """设置配置值"""
    _global_config_manager.set(key, value)


def has_config(key: str) -> bool:
    """检查配置键是否存在"""
    return _global_config_manager.has(key)


def remove_config(key: str) -> None:
    """移除配置键"""
    _global_config_manager.remove(key)
