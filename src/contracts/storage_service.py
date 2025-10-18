"""存储服务契约"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class StorageBackend(str, Enum):
    """存储后端类型"""

    JSON = "json"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"
    MEMORY = "memory"


class QueryOperator(str, Enum):
    """查询操作符"""

    EQ = "eq"  # 等于
    NE = "ne"  # 不等于
    GT = "gt"  # 大于
    GTE = "gte"  # 大于等于
    LT = "lt"  # 小于
    LTE = "lte"  # 小于等于
    IN = "in"  # 包含
    LIKE = "like"  # 模糊匹配
    BETWEEN = "between"  # 范围


@dataclass
class StorageServiceConfig:
    """存储服务配置"""

    backend: StorageBackend = StorageBackend.JSON  # 后端类型
    base_path: str = "data"  # 基础路径
    enable_cache: bool = True  # 是否启用缓存
    cache_ttl: int = 300  # 缓存过期时间(秒)
    enable_compression: bool = False  # 是否启用压缩
    enable_encryption: bool = False  # 是否启用加密
    max_retry: int = 3  # 最大重试次数
    batch_size: int = 100  # 批处理大小


@dataclass
class SaveRequest(Generic[T]):
    """保存请求DTO"""

    entity: T  # 实体对象
    entity_type: str  # 实体类型
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
    overwrite: bool = True  # 是否覆盖


@dataclass
class SaveResponse:
    """保存响应DTO"""

    success: bool  # 是否成功
    entity_id: str | None = None  # 实体ID
    message: str = ""  # 消息
    errors: list[str] = field(default_factory=list)  # 错误列表


@dataclass
class QueryFilter:
    """查询过滤器"""

    field: str  # 字段名
    operator: QueryOperator  # 操作符
    value: Any  # 值


@dataclass
class QueryRequest:
    """查询请求DTO"""

    entity_type: str  # 实体类型
    filters: list[QueryFilter] = field(default_factory=list)  # 过滤条件
    sort_by: str | None = None  # 排序字段
    sort_order: str = "asc"  # 排序顺序(asc/desc)
    limit: int | None = None  # 限制数量
    offset: int = 0  # 偏移量
    include_fields: list[str] | None = None  # 包含字段
    exclude_fields: list[str] | None = None  # 排除字段


@dataclass
class QueryResponse(Generic[T]):
    """查询响应DTO"""

    success: bool  # 是否成功
    data: list[T] = field(default_factory=list)  # 数据列表
    total_count: int = 0  # 总数量
    message: str = ""  # 消息
    has_more: bool = False  # 是否还有更多


@dataclass
class DeleteRequest:
    """删除请求DTO"""

    entity_type: str  # 实体类型
    entity_id: str  # 实体ID
    soft_delete: bool = False  # 是否软删除


@dataclass
class DeleteResponse:
    """删除响应DTO"""

    success: bool  # 是否成功
    deleted_count: int = 0  # 删除数量
    message: str = ""  # 消息


class StorageService(ABC):
    """存储服务抽象类"""

    @abstractmethod
    def save(self, request: SaveRequest) -> SaveResponse:
        """保存实体

        Args:
            request: 保存请求

        Returns:
            保存响应
        """
        pass

    @abstractmethod
    def query(self, request: QueryRequest) -> QueryResponse:
        """查询实体

        Args:
            request: 查询请求

        Returns:
            查询响应
        """
        pass

    @abstractmethod
    def get_by_id(self, entity_type: str, entity_id: str) -> Any | None:
        """根据ID获取实体

        Args:
            entity_type: 实体类型
            entity_id: 实体ID

        Returns:
            实体对象
        """
        pass

    @abstractmethod
    def delete(self, request: DeleteRequest) -> DeleteResponse:
        """删除实体

        Args:
            request: 删除请求

        Returns:
            删除响应
        """
        pass

    @abstractmethod
    def batch_save(self, requests: list[SaveRequest]) -> list[SaveResponse]:
        """批量保存

        Args:
            requests: 保存请求列表

        Returns:
            保存响应列表
        """
        pass

    @abstractmethod
    def batch_delete(self, requests: list[DeleteRequest]) -> list[DeleteResponse]:
        """批量删除

        Args:
            requests: 删除请求列表

        Returns:
            删除响应列表
        """
        pass

    @abstractmethod
    def count(self, entity_type: str, filters: list[QueryFilter] | None = None) -> int:
        """统计数量

        Args:
            entity_type: 实体类型
            filters: 过滤条件

        Returns:
            数量
        """
        pass

    @abstractmethod
    def exists(self, entity_type: str, entity_id: str) -> bool:
        """检查是否存在

        Args:
            entity_type: 实体类型
            entity_id: 实体ID

        Returns:
            是否存在
        """
        pass
