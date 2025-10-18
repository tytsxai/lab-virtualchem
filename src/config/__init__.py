"""配置管理模块"""

from .config_manager import (
    ConfigError,
    ConfigManager,
    get_config,
    get_setting,
    load_config,
    set_setting,
)

# 添加settings别名以保持兼容性
settings = None  # 实际的settings对象将在运行时设置

__all__ = [
    "ConfigManager",
    "ConfigError",
    "get_config",
    "load_config",
    "get_setting",
    "set_setting",
    "settings",
]
