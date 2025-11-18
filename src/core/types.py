"""
类型定义模块

提供完整的类型注解和类型别名定义
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

# Python版本兼容性
from typing import (
    Any,
    Final,
    Generic,
    Literal,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    runtime_checkable,
)

from .. import __version__ as APP_VERSION

# 基础类型别名
StringDict: TypeAlias = dict[str, Any]
Number: TypeAlias = int | float
PathLike: TypeAlias = str | os.PathLike[str]

# 实验相关类型
ExperimentId: TypeAlias = str
StepId: TypeAlias = str
TemplateId: TypeAlias = str
UserId: TypeAlias = str
SessionId: TypeAlias = str

# 坐标和几何类型
Point2D: TypeAlias = tuple[float, float]
Point3D: TypeAlias = tuple[float, float, float]
Vector2D: TypeAlias = tuple[float, float]
Vector3D: TypeAlias = tuple[float, float, float]
BoundingBox: TypeAlias = tuple[float, float, float, float]  # x, y, width, height
ColorRGB: TypeAlias = tuple[int, int, int]
ColorRGBA: TypeAlias = tuple[int, int, int, int]

# 配置类型
ConfigValue: TypeAlias = str | int | float | bool | list[Any] | dict[str, Any]
ConfigDict: TypeAlias = dict[str, ConfigValue]

# 事件类型
EventType: TypeAlias = str
EventData: TypeAlias = dict[str, Any]
EventHandler: TypeAlias = Callable[[EventData], None]

# 回调函数类型
Callback: TypeAlias = Callable[[], None]
AsyncCallback: TypeAlias = Callable[[], Awaitable[None]]
ProgressCallback: TypeAlias = Callable[[float], None]  # progress: 0.0-1.0
ErrorCallback: TypeAlias = Callable[[Exception], None]

# 验证函数类型
Validator: TypeAlias = Callable[[Any], bool]
ValidatorWithMessage: TypeAlias = Callable[[Any], tuple[bool, str]]

# 序列化类型
Serializable: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]
SerializableDict: TypeAlias = dict[str, Serializable]

# 文件操作类型
FileMode: TypeAlias = Literal["r", "w", "a", "rb", "wb", "ab"]
FileEncoding: TypeAlias = Literal["utf-8", "gbk", "ascii"]

# 网络相关类型
HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
HttpStatus: TypeAlias = int
Url: TypeAlias = str

# 数据库相关类型
DbId: TypeAlias = int | str
DbRecord: TypeAlias = dict[str, Any]

# 缓存相关类型
CacheKey: TypeAlias = str
CacheValue: TypeAlias = Any
CacheTTL: TypeAlias = int | None

# 插件相关类型
PluginId: TypeAlias = str
PluginVersion: TypeAlias = str
PluginInfo: TypeAlias = dict[str, Any]

# 日志相关类型
LogLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogMessage: TypeAlias = str

# 泛型类型变量
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
R = TypeVar("R")


# 协议定义
@runtime_checkable
class SerializableProtocol(Protocol):
    """可序列化协议"""

    def to_dict(self) -> SerializableDict:
        """转换为字典"""
        ...

    @classmethod
    def from_dict(cls: type[T], data: SerializableDict) -> T:
        """从字典创建"""
        ...


@runtime_checkable
class CloneableProtocol(Protocol[T]):
    """可克隆协议"""

    def clone(self) -> T:
        """克隆对象"""
        ...


@runtime_checkable
class ComparableProtocol(Protocol):
    """可比较协议"""

    def __eq__(self, other: Any) -> bool:
        """等于比较"""
        ...

    def __lt__(self, other: Any) -> bool:
        """小于比较"""
        ...


@runtime_checkable
class HashableProtocol(Protocol):
    """可哈希协议"""

    def __hash__(self) -> int:
        """哈希值"""
        ...


# TypedDict 定义
class ExperimentConfig(TypedDict, total=False):
    """实验配置"""

    name: str
    description: str | None
    version: str
    author: str | None
    created_at: str | None
    updated_at: str | None
    tags: list[str]
    settings: ConfigDict


class StepConfig(TypedDict, total=False):
    """步骤配置"""

    id: StepId
    name: str
    description: str | None
    type: str
    parameters: ConfigDict
    duration: float | None
    order: int


class UserConfig(TypedDict, total=False):
    """用户配置"""

    user_id: UserId
    username: str
    email: str | None
    preferences: ConfigDict
    permissions: list[str]
    created_at: str
    last_login: str | None


class SystemInfo(TypedDict):
    """系统信息"""

    version: str
    build: str
    platform: str
    python_version: str
    qt_version: str
    memory_usage: int
    cpu_usage: float


class PerformanceMetrics(TypedDict):
    """性能指标"""

    fps: float
    frame_time: float
    memory_usage: int
    cpu_usage: float
    gpu_usage: float | None
    render_time: float
    update_time: float


class ErrorInfo(TypedDict):
    """错误信息"""

    code: str
    message: str
    details: StringDict | None
    timestamp: str
    traceback: str | None


class PluginMetadata(TypedDict):
    """插件元数据"""

    id: PluginId
    name: str
    version: PluginVersion
    description: str
    author: str
    dependencies: list[str]
    entry_point: str
    config_schema: ConfigDict | None


# 常量定义
class Constants:
    """应用常量"""

    # 版本信息
    VERSION: Final[str] = APP_VERSION
    BUILD: Final[str] = "20241201"

    # 默认值
    DEFAULT_TIMEOUT: Final[int] = 30
    DEFAULT_CACHE_SIZE: Final[int] = 1000
    DEFAULT_PAGE_SIZE: Final[int] = 20

    # 文件扩展名
    TEMPLATE_EXT: Final[str] = ".yaml"
    CONFIG_EXT: Final[str] = ".json"
    LOG_EXT: Final[str] = ".log"

    # 目录名
    TEMPLATES_DIR: Final[str] = "templates"
    CONFIGS_DIR: Final[str] = "configs"
    LOGS_DIR: Final[str] = "logs"
    PLUGINS_DIR: Final[str] = "plugins"

    # 配置键
    CONFIG_APP: Final[str] = "app"
    CONFIG_UI: Final[str] = "ui"
    CONFIG_EXPERIMENT: Final[str] = "experiment"
    CONFIG_PHYSICS: Final[str] = "physics"

    # 事件类型
    EVENT_EXPERIMENT_START: Final[str] = "experiment.start"
    EVENT_EXPERIMENT_END: Final[str] = "experiment.end"
    EVENT_STEP_START: Final[str] = "step.start"
    EVENT_STEP_END: Final[str] = "step.end"
    EVENT_ERROR: Final[str] = "error"
    EVENT_WARNING: Final[str] = "warning"

    # 日志级别
    LOG_DEBUG: Final[LogLevel] = "DEBUG"
    LOG_INFO: Final[LogLevel] = "INFO"
    LOG_WARNING: Final[LogLevel] = "WARNING"
    LOG_ERROR: Final[LogLevel] = "ERROR"
    LOG_CRITICAL: Final[LogLevel] = "CRITICAL"


# 类型检查工具
def is_number(value: Any) -> bool:
    """检查是否为数字"""
    return isinstance(value, (int, float))


def is_string(value: Any) -> bool:
    """检查是否为字符串"""
    return isinstance(value, str)


def is_dict(value: Any) -> bool:
    """检查是否为字典"""
    return isinstance(value, dict)


def is_list(value: Any) -> bool:
    """检查是否为列表"""
    return isinstance(value, list)


def is_callable(value: Any) -> bool:
    """检查是否为可调用对象"""
    return callable(value)


def is_optional(value: Any, expected_type: type) -> bool:
    """检查是否为可选类型（None或期望类型）"""
    return value is None or isinstance(value, expected_type)


# 类型转换工具
def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """安全转换为字符串"""
    try:
        return str(value)
    except Exception:
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """安全转换为布尔值"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return default


# 泛型容器类型
class TypedList(list[T], Generic[T]):
    """类型化列表"""

    def __init__(self, item_type: type[T], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_type = item_type

    def append(self, item: T) -> None:
        """添加项目"""
        if not isinstance(item, self.item_type):
            raise TypeError(f"Expected {self.item_type.__name__}, got {type(item).__name__}")
        super().append(item)

    def extend(self, items: list[T]) -> None:
        """扩展列表"""
        for item in items:
            self.append(item)


class TypedDict(dict[K, V], Generic[K, V]):
    """类型化字典"""

    def __init__(self, key_type: type[K], value_type: type[V], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_type = key_type
        self.value_type = value_type

    def __setitem__(self, key: K, value: V) -> None:
        """设置项目"""
        if not isinstance(key, self.key_type):
            raise TypeError(f"Expected key type {self.key_type.__name__}, got {type(key).__name__}")
        if not isinstance(value, self.value_type):
            raise TypeError(f"Expected value type {self.value_type.__name__}, got {type(value).__name__}")
        super().__setitem__(key, value)


# 装饰器类型
def type_check(func: Callable[..., R]) -> Callable[..., R]:
    """类型检查装饰器"""

    def wrapper(*args, **kwargs):
        # 这里可以添加运行时类型检查逻辑
        return func(*args, **kwargs)

    return wrapper


def validate_types(**type_map: type) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """类型验证装饰器"""

    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        def wrapper(*args, **kwargs):
            # 验证参数类型
            for param_name, expected_type in type_map.items():
                if param_name in kwargs and not isinstance(kwargs[param_name], expected_type):
                    raise TypeError(f"Parameter '{param_name}' must be of type {expected_type.__name__}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


# 导出所有类型
__all__ = [
    # 基础类型别名
    "StringDict",
    "Number",
    "PathLike",
    # ID类型
    "ExperimentId",
    "StepId",
    "TemplateId",
    "UserId",
    "SessionId",
    # 几何类型
    "Point2D",
    "Point3D",
    "Vector2D",
    "Vector3D",
    "BoundingBox",
    "ColorRGB",
    "ColorRGBA",
    # 配置类型
    "ConfigValue",
    "ConfigDict",
    # 事件类型
    "EventType",
    "EventData",
    "EventHandler",
    # 回调类型
    "Callback",
    "AsyncCallback",
    "ProgressCallback",
    "ErrorCallback",
    # 验证类型
    "Validator",
    "ValidatorWithMessage",
    # 序列化类型
    "Serializable",
    "SerializableDict",
    # 文件类型
    "FileMode",
    "FileEncoding",
    # 网络类型
    "HttpMethod",
    "HttpStatus",
    "Url",
    # 数据库类型
    "DbId",
    "DbRecord",
    # 缓存类型
    "CacheKey",
    "CacheValue",
    "CacheTTL",
    # 插件类型
    "PluginId",
    "PluginVersion",
    "PluginInfo",
    # 日志类型
    "LogLevel",
    "LogMessage",
    # 泛型变量
    "T",
    "K",
    "V",
    "R",
    # 协议
    "SerializableProtocol",
    "CloneableProtocol",
    "ComparableProtocol",
    "HashableProtocol",
    # TypedDict
    "ExperimentConfig",
    "StepConfig",
    "UserConfig",
    "SystemInfo",
    "PerformanceMetrics",
    "ErrorInfo",
    "PluginMetadata",
    # 常量
    "Constants",
    # 工具函数
    "is_number",
    "is_string",
    "is_dict",
    "is_list",
    "is_callable",
    "is_optional",
    "safe_int",
    "safe_float",
    "safe_str",
    "safe_bool",
    # 泛型容器
    "TypedList",
    "TypedDict",
    # 装饰器
    "type_check",
    "validate_types",
]
