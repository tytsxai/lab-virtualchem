"""
存储接口定义

定义了统一的存储抽象，支持多种存储实现
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class StorageItem:
    """存储项"""

    key: str
    value: Any
    created_at: datetime = None
    updated_at: datetime = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class IStorage(ABC, Generic[T]):
    """存储接口"""

    @abstractmethod
    def save(self, key: str, value: T, metadata: dict | None = None) -> bool:
        """保存数据"""
        pass

    @abstractmethod
    def load(self, key: str) -> T | None:
        """加载数据"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除数据"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查是否存在"""
        pass

    @abstractmethod
    def list_keys(self, prefix: str | None = None) -> list[str]:
        """列出所有键"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """清空存储"""
        pass


class ILogger(ABC):
    """日志接口"""

    @abstractmethod
    def debug(self, message: str, **kwargs):
        """调试日志"""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs):
        """信息日志"""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs):
        """警告日志"""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs):
        """错误日志"""
        pass

    @abstractmethod
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        pass


class IConfig(ABC):
    """配置接口"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any):
        """设置配置"""
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        pass

    @abstractmethod
    def get_section(self, section: str) -> dict[str, Any]:
        """获取配置节"""
        pass

    @abstractmethod
    def reload(self):
        """重新加载配置"""
        pass


class IRepository(ABC, Generic[T]):
    """仓储接口 - 数据访问抽象"""

    @abstractmethod
    def add(self, entity: T) -> bool:
        """添加实体"""
        pass

    @abstractmethod
    def get(self, id: Any) -> T | None:
        """根据ID获取实体"""
        pass

    @abstractmethod
    def get_all(self) -> list[T]:
        """获取所有实体"""
        pass

    @abstractmethod
    def update(self, entity: T) -> bool:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, id: Any) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    def find_by(self, predicate) -> list[T]:
        """根据条件查找"""
        pass

    @abstractmethod
    def count(self) -> int:
        """统计数量"""
        pass
