"""
配置管理系统

支持多种配置源和动态配置加载
"""

import json
import os
from typing import Any

from src.interfaces.storage import IConfig


class JsonConfig(IConfig):
    """JSON配置实现"""

    def __init__(self, config_file: str = "_config.json"):
        self.config_file = config_file
        self._data: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """重新加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）

        Examples:
            config.get("database.host")
            config.get("app.debug", False)
        """
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        keys = key.split(".")
        data = self._data

        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]

        data[keys[-1]] = value
        self._save()

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return self.get(key) is not None

    def get_section(self, section: str) -> dict[str, Any]:
        """获取配置节"""
        return self.get(section, {})

    def _save(self) -> None:
        """保存配置到文件"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


class EnvironmentConfig(IConfig):
    """环境变量配置"""

    def __init__(self, prefix: str = "APP_"):
        self.prefix = prefix

    def get(self, key: str, default: Any = None) -> Any:
        """从环境变量获取配置"""
        env_key = f"{self.prefix}{key.upper().replace('.', '_')}"
        return os.getenv(env_key, default)

    def set(self, key: str, value: Any) -> None:
        """设置环境变量"""
        env_key = f"{self.prefix}{key.upper().replace('.', '_')}"
        os.environ[env_key] = str(value)

    def has(self, key: str) -> bool:
        """检查环境变量是否存在"""
        env_key = f"{self.prefix}{key.upper().replace('.', '_')}"
        return env_key in os.environ

    def get_section(self, _section: str) -> dict[str, Any]:
        """获取配置节（环境变量不支持）"""
        return {}

    def reload(self) -> None:
        """环境变量无需重新加载"""
        pass


class CompositeConfig(IConfig):
    """组合配置（多个配置源）"""

    def __init__(self, *configs: IConfig):
        self.configs = list(configs)

    def get(self, key: str, default: Any = None) -> Any:
        """按顺序从配置源获取值"""
        for config in self.configs:
            value = config.get(key)
            if value is not None:
                return value
        return default

    def set(self, key: str, value: Any) -> None:
        """设置到第一个配置源"""
        if self.configs:
            self.configs[0].set(key, value)

    def has(self, key: str) -> bool:
        """检查任一配置源是否有该值"""
        return any(config.has(key) for config in self.configs)

    def get_section(self, section: str) -> dict[str, Any]:
        """从所有配置源合并配置节"""
        result = {}
        for config in reversed(self.configs):
            result.update(config.get_section(section))
        return result

    def reload(self) -> None:
        """重新加载所有配置源"""
        for config in self.configs:
            config.reload()
