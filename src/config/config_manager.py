"""
全局配置管理器
提供统一的配置访问接口和验证
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误"""


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance: ConfigManager | None = None
    _config: dict[str, Any] = {}
    _config_file: Path | None = None
    _defaults: dict[str, Any] = {
        # 应用设置
        "app": {
            "name": "VirtualChemLab",
            "version": "1.0.0",
            "language": "zh_CN",
            "theme": "auto",  # auto, light, dark
        },
        # UI设置
        "ui": {
            "window_width": 1280,
            "window_height": 800,
            "sidebar_width": 250,
            "font_size": 12,
            "enable_animations": True,
        },
        # 性能设置
        "performance": {
            "enable_virtual_list": True,
            "enable_lazy_loading": True,
            "debounce_delay": 300,
            "throttle_interval": 100,
            "memory_threshold_mb": 500,
        },
        # 开发者设置
        "developer": {
            "enable_console": False,
            "enable_debug_logs": False,
            "log_level": "INFO",
        },
        # 实验设置
        "experiment": {
            "auto_save": True,
            "auto_save_interval": 300,  # 秒
            "max_history": 50,
        },
    }

    def __new__(cls) -> ConfigManager:
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if not hasattr(self, "_initialized"):
            self._config = self._defaults.copy()
            self._initialized = True

    def load(self, config_file: str | Path) -> None:
        """
        加载配置文件

        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)
        self._config_file = config_path

        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    user_config = json.load(f)

                # 深度合并配置
                self._config = self._deep_merge(self._defaults.copy(), user_config)
                logger.info(f"配置加载成功: {config_path}")
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {config_path}")
                # 创建默认配置文件
                self.save()
        except json.JSONDecodeError as e:
            msg = f"配置文件格式错误: {e}"
            logger.error(msg)
            raise ConfigError(msg) from e
        except Exception as e:
            msg = f"加载配置失败: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e

    def save(self) -> None:
        """保存配置到文件"""
        if not self._config_file:
            logger.warning("未指定配置文件，无法保存")
            return

        try:
            # 确保目录存在
            self._config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

            logger.info(f"配置保存成功: {self._config_file}")
        except Exception as e:
            msg = f"保存配置失败: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）

        Args:
            key: 配置键，支持 "app.name" 格式
            default: 默认值

        Returns:
            配置值
        """
        try:
            keys = key.split(".")
            value = self._config

            for k in keys:
                value = value[k]

            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        设置配置值（支持点号路径）

        Args:
            key: 配置键，支持 "app.name" 格式
            value: 配置值
            save: 是否立即保存到文件
        """
        try:
            keys = key.split(".")
            config = self._config

            # 导航到最后一个键的父级
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]

            # 设置值
            config[keys[-1]] = value
            logger.debug(f"配置已更新: {key} = {value}")

            if save:
                self.save()
        except Exception as e:
            msg = f"设置配置失败: {key} = {value}, 错误: {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e

    def reset(self, key: str | None = None) -> None:
        """
        重置配置为默认值

        Args:
            key: 要重置的配置键，None表示重置全部
        """
        if key is None:
            self._config = self._defaults.copy()
            logger.info("所有配置已重置为默认值")
        else:
            default_value = self._get_from_defaults(key)
            if default_value is not None:
                self.set(key, default_value, save=False)
                logger.info(f"配置已重置: {key}")
            else:
                logger.warning(f"未找到默认配置: {key}")

    def validate(self) -> list[str]:
        """
        验证配置

        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []

        # 验证窗口尺寸
        width = self.get("ui.window_width")
        height = self.get("ui.window_height")
        if not isinstance(width, int) or width < 800:
            errors.append("ui.window_width 必须是大于等于800的整数")
        if not isinstance(height, int) or height < 600:
            errors.append("ui.window_height 必须是大于等于600的整数")

        # 验证主题
        theme = self.get("app.theme")
        if theme not in ["auto", "light", "dark"]:
            errors.append("app.theme 必须是 'auto', 'light' 或 'dark'")

        # 验证语言
        language = self.get("app.language")
        if not isinstance(language, str) or not language:
            errors.append("app.language 必须是非空字符串")

        # 验证性能参数
        memory_threshold = self.get("performance.memory_threshold_mb")
        if not isinstance(memory_threshold, (int, float)) or memory_threshold <= 0:
            errors.append("performance.memory_threshold_mb 必须是正数")

        debounce_delay = self.get("performance.debounce_delay")
        if not isinstance(debounce_delay, int) or debounce_delay < 0:
            errors.append("performance.debounce_delay 必须是非负整数")

        return errors

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """
        深度合并字典

        Args:
            base: 基础字典
            update: 更新字典

        Returns:
            合并后的字典
        """
        result = base.copy()

        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _get_from_defaults(self, key: str) -> Any:
        """从默认配置中获取值"""
        try:
            keys = key.split(".")
            value = self._defaults

            for k in keys:
                value = value[k]

            return value
        except (KeyError, TypeError):
            return None

    def export(self) -> dict[str, Any]:
        """
        导出配置为字典

        Returns:
            配置字典
        """
        return self._config.copy()

    def import_config(self, config: dict[str, Any], merge: bool = True) -> None:
        """
        导入配置

        Args:
            config: 配置字典
            merge: 是否与现有配置合并
        """
        if merge:
            self._config = self._deep_merge(self._config, config)
        else:
            self._config = config

        logger.info("配置已导入")


# 全局单例
_config_manager: ConfigManager | None = None


def get_config() -> ConfigManager:
    """
    获取全局配置管理器实例

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 便捷函数
def load_config(config_file: str | Path) -> None:
    """加载配置文件"""
    get_config().load(config_file)


def get_setting(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return get_config().get(key, default)


def set_setting(key: str, value: Any, save: bool = True) -> None:
    """设置配置值"""
    get_config().set(key, value, save)


if __name__ == "__main__":
    """测试配置管理器"""
    import tempfile

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        test_config_file = f.name

    # 测试配置管理器
    config = get_config()
    config.load(test_config_file)

    # 测试获取配置
    print("App Name:", config.get("app.name"))
    print("Window Width:", config.get("ui.window_width"))

    # 测试设置配置
    config.set("app.theme", "dark", save=False)
    print("Theme after set:", config.get("app.theme"))

    # 测试验证
    errors = config.validate()
    print("Validation errors:", errors)

    # 保存配置
    config.save()
    logger.info(f"配置已保存到: {test_config_file}")

    # 清理
    import os

    os.unlink(test_config_file)
