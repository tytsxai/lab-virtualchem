"""
配置访问抽象层
提供统一的配置访问接口，减少重复的配置访问模式
"""

import threading
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .config_loader import get_config, Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


_MISSING = object()


class ConfigAccessLayer:
    """配置访问抽象层"""

    def __init__(self, config: Optional[Config] = None):
        self._config = config or get_config()
        self._cache: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）"""
        with self._lock:
            # 检查缓存
            if key in self._cache:
                cached_value = self._cache[key]
                if cached_value is _MISSING:
                    return default
                return cached_value

            # 解析配置路径
            value = self._get_nested_value(self._config, key)

            # 缓存结果
            self._cache[key] = value if value is not None else _MISSING

            return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """设置配置值（运行时修改，不持久化）"""
        with self._lock:
            self._cache[key] = value
            logger.warning(f"运行时配置修改: {key} = {value} (不会持久化)")

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return self.get(key) is not None

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        value = self.get(section)
        if value is None:
            return {}

        # 如果是Pydantic模型，转为字典
        if hasattr(value, "dict"):
            return value.dict()

        return value if isinstance(value, dict) else {}

    def get_path(self, key: str, base_path: Optional[Path] = None) -> Path:
        """获取路径配置，自动解析为Path对象"""
        path_str = self.get(key)
        if not path_str:
            raise ValueError(f"Path configuration not found: {key}")

        path = Path(path_str)

        # 如果是相对路径，基于base_path解析
        if not path.is_absolute() and base_path:
            path = base_path / path

        return path

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer config: {key} = {value}, using default: {default}")
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid float config: {key} = {value}, using default: {default}")
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")

        return bool(value)

    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """获取列表配置"""
        value = self.get(key, default)
        if value is None:
            return default or []

        if isinstance(value, list):
            return value

        # 尝试转换
        if isinstance(value, str):
            # 简单的逗号分隔列表
            return [item.strip() for item in value.split(",") if item.strip()]

        return [value]

    def get_dict(self, key: str, default: Optional[dict] = None) -> dict:
        """获取字典配置"""
        value = self.get(key, default)
        if value is None:
            return default or {}

        if isinstance(value, dict):
            return value

        # 如果是Pydantic模型，转为字典
        if hasattr(value, "dict"):
            return value.dict()

        logger.warning(f"Invalid dict config: {key} = {value}, using default: {default}")
        return default or {}

    def _get_nested_value(self, obj: Any, key: str) -> Any:
        """获取嵌套值"""
        parts = key.split(".")
        value = obj

        try:
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
        except (AttributeError, KeyError):
            return None

    def clear_cache(self) -> None:
        """清除配置缓存"""
        with self._lock:
            self._cache.clear()

    def reload(self) -> None:
        """重新加载配置"""
        with self._lock:
            self._config = get_config()
            self._cache.clear()
            logger.info("配置已重新加载")

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.dict() if hasattr(self._config, "dict") else {}

    def validate_required(self, *keys: str) -> None:
        """验证必需的配置项"""
        missing = []
        for key in keys:
            if not self.has(key):
                missing.append(key)

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    def get_with_validation(self, key: str, validator: callable, default: Any = None) -> Any:
        """获取配置并验证"""
        value = self.get(key, default)

        try:
            return validator(value)
        except Exception as e:
            logger.error(f"Configuration validation failed for {key}: {e}")
            return default


# 全局配置访问层实例
_config_access_layer: Optional[ConfigAccessLayer] = None
_config_access_lock = threading.Lock()


def get_config_access() -> ConfigAccessLayer:
    """获取全局配置访问层实例"""
    global _config_access_layer
    if _config_access_layer is None:
        with _config_access_lock:
            if _config_access_layer is None:
                _config_access_layer = ConfigAccessLayer()
    return _config_access_layer


def reload_config_access() -> None:
    """重新加载全局配置访问层"""
    global _config_access_layer
    with _config_access_lock:
        instance = _config_access_layer() if callable(_config_access_layer) else _config_access_layer
        if instance is not None:
            instance.reload()
        else:
            _config_access_layer = ConfigAccessLayer()


# 便捷函数
def config_get(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return get_config_access().get(key, default)


def config_set(key: str, value: Any) -> None:
    """设置配置值"""
    get_config_access().set(key, value)


def config_has(key: str) -> bool:
    """检查配置是否存在"""
    return get_config_access().has(key)


def config_get_section(section: str) -> Dict[str, Any]:
    """获取配置节"""
    return get_config_access().get_section(section)


def config_get_path(key: str, base_path: Optional[Path] = None) -> Path:
    """获取路径配置"""
    return get_config_access().get_path(key, base_path)


def config_get_int(key: str, default: int = 0) -> int:
    """获取整数配置"""
    return get_config_access().get_int(key, default)


def config_get_float(key: str, default: float = 0.0) -> float:
    """获取浮点数配置"""
    return get_config_access().get_float(key, default)


def config_get_bool(key: str, default: bool = False) -> bool:
    """获取布尔配置"""
    return get_config_access().get_bool(key, default)


def config_get_list(key: str, default: Optional[list] = None) -> list:
    """获取列表配置"""
    return get_config_access().get_list(key, default)


def config_get_dict(key: str, default: Optional[dict] = None) -> dict:
    """获取字典配置"""
    return get_config_access().get_dict(key, default)


def config_validate_required(*keys: str) -> None:
    """验证必需的配置项"""
    get_config_access().validate_required(*keys)


def config_get_with_validation(key: str, validator: callable, default: Any = None) -> Any:
    """获取配置并验证"""
    return get_config_access().get_with_validation(key, validator, default)


class _ConfigProxy:
    """延迟访问全局配置访问层的代理"""

    def __getattr__(self, item: str) -> Any:
        return getattr(get_config_access(), item)


# 向后兼容的别名
config = _ConfigProxy()
