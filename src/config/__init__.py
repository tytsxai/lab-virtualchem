"""配置管理模块"""

from .config_manager import (
    ConfigError,
    ConfigManager,
    get_config,
    get_setting,
    load_config,
    set_setting,
)

class _SettingsProxy:
    def get(self, key: str, default=None):
        return get_setting(key, default)


def get_settings() -> _SettingsProxy:
    return _SettingsProxy()

__all__ = [
    "ConfigManager",
    "ConfigError",
    "get_config",
    "load_config",
    "get_setting",
    "set_setting",
    "get_settings",
]
