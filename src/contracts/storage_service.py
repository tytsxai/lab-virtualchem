"""存储服务契约"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import uuid4

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


# --------- 轻量级内存实现，便于无外部依赖时使用 ---------


class InMemoryStorageService(StorageService):
    """基于内存字典的存储实现，满足测试/开发场景"""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def _resolve_id(self, entity: Any) -> str:
        """获取或生成实体ID"""
        if hasattr(entity, "id"):
            return str(entity.id)
        if hasattr(entity, "record_id"):
            return str(entity.record_id)
        return uuid4().hex

    def _match(self, value: Any, operator: QueryOperator, expected: Any) -> bool:
        """简单过滤匹配"""
        if operator == QueryOperator.EQ:
            return value == expected
        if operator == QueryOperator.NE:
            return value != expected
        if operator == QueryOperator.GT:
            return value > expected
        if operator == QueryOperator.GTE:
            return value >= expected
        if operator == QueryOperator.LT:
            return value < expected
        if operator == QueryOperator.LTE:
            return value <= expected
        if operator == QueryOperator.IN:
            return value in expected if isinstance(expected, (list, tuple, set)) else False
        if operator == QueryOperator.LIKE:
            return str(expected).lower() in str(value).lower()
        if operator == QueryOperator.BETWEEN:
            if isinstance(expected, (list, tuple)) and len(expected) == 2:
                return expected[0] <= value <= expected[1]
        return False

    def save(self, request: SaveRequest) -> SaveResponse:
        entity_id = getattr(request.entity, "id", None) or self._resolve_id(request.entity)
        bucket = self._store.setdefault(request.entity_type, {})
        if not request.overwrite and entity_id in bucket:
            return SaveResponse(success=False, entity_id=entity_id, message="实体已存在且不允许覆盖")
        bucket[entity_id] = request.entity
        return SaveResponse(success=True, entity_id=entity_id, message="保存成功")

    def query(self, request: QueryRequest) -> QueryResponse:
        bucket = self._store.get(request.entity_type, {})
        data = list(bucket.values())

        def _apply_filters(item: Any) -> bool:
            for f in request.filters:
                value = getattr(item, f.field, None) if not isinstance(item, dict) else item.get(f.field)
                if not self._match(value, f.operator, f.value):
                    return False
            return True

        if request.filters:
            data = [item for item in data if _apply_filters(item)]

        total = len(data)
        if request.sort_by:
            key_fn: Callable[[Any], Any] = (
                (lambda x: getattr(x, request.sort_by, None))
                if not isinstance(data[0], dict)
                else (lambda x: x.get(request.sort_by))
            )
            reverse = request.sort_order == "desc"
            data.sort(key=key_fn, reverse=reverse)

        if request.offset or request.limit is not None:
            data = data[request.offset : request.offset + request.limit if request.limit else None]

        return QueryResponse(success=True, data=data, total_count=total, has_more=len(data) < total)

    def get_by_id(self, entity_type: str, entity_id: str) -> Any | None:
        return self._store.get(entity_type, {}).get(entity_id)

    def delete(self, request: DeleteRequest) -> DeleteResponse:
        bucket = self._store.get(request.entity_type, {})
        if request.entity_id in bucket:
            del bucket[request.entity_id]
            return DeleteResponse(success=True, deleted_count=1, message="删除成功")
        return DeleteResponse(success=False, deleted_count=0, message="实体不存在")

    def batch_save(self, requests: list[SaveRequest]) -> list[SaveResponse]:
        return [self.save(r) for r in requests]

    def batch_delete(self, requests: list[DeleteRequest]) -> list[DeleteResponse]:
        return [self.delete(r) for r in requests]

    def count(self, entity_type: str, filters: list[QueryFilter] | None = None) -> int:
        bucket = self._store.get(entity_type, {})
        if not filters:
            return len(bucket)
        qr = QueryRequest(entity_type=entity_type, filters=filters)
        return len(self.query(qr).data)

    def exists(self, entity_type: str, entity_id: str) -> bool:
        return entity_id in self._store.get(entity_type, {})
