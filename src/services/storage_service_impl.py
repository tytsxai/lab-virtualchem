"""
存储服务实现
"""

from typing import Any

from src.contracts.storage_service import (
    DeleteRequest,
    DeleteResponse,
    QueryFilter,
    QueryOperator,
    QueryRequest,
    QueryResponse,
    SaveRequest,
    SaveResponse,
    StorageService,
    StorageServiceConfig,
)
from src.interfaces.storage import IStorage


class StorageServiceImpl(StorageService):
    """存储服务具体实现"""

    def __init__(self, storage: IStorage, config: StorageServiceConfig | None = None):
        self.storage = storage
        self.config = config or StorageServiceConfig()

    def save(self, request: SaveRequest) -> SaveResponse:
        """保存实体"""
        try:
            key = self._generate_key(request.entity_type, request.entity)
            success = self.storage.save(key, request.entity, request.metadata)

            if success:
                return SaveResponse(success=True, entity_id=key, message="保存成功")
            else:
                return SaveResponse(success=False, message="保存失败")

        except Exception as e:
            return SaveResponse(success=False, message=f"保存失败: {str(e)}", errors=[str(e)])

    def query(self, request: QueryRequest) -> QueryResponse:
        """查询实体"""
        try:
            # 获取所有键
            prefix = f"{request.entity_type}/"
            keys = self.storage.list_keys(prefix)

            # 加载所有实体
            entities = []
            for key in keys:
                entity = self.storage.load(key)
                if entity and self._match_filters(entity, request.filters):
                    entities.append(entity)

            # 排序
            if request.sort_by:
                entities = self._sort_entities(entities, request.sort_by, request.sort_order)

            # 分页
            total_count = len(entities)
            start = request.offset
            end = start + request.limit if request.limit else len(entities)
            entities = entities[start:end]

            return QueryResponse(
                success=True,
                data=entities,
                total_count=total_count,
                has_more=end < total_count,
                message="查询成功",
            )

        except Exception as e:
            return QueryResponse(success=False, message=f"查询失败: {str(e)}")

    def get_by_id(self, entity_type: str, entity_id: str) -> Any | None:
        """根据ID获取实体"""
        key = f"{entity_type}/{entity_id}"
        return self.storage.load(key)

    def delete(self, request: DeleteRequest) -> DeleteResponse:
        """删除实体"""
        try:
            key = f"{request.entity_type}/{request.entity_id}"

            if request.soft_delete:
                # 软删除：标记为已删除
                entity = self.storage.load(key)
                if entity:
                    entity["_deleted"] = True
                    self.storage.save(key, entity)
                    return DeleteResponse(success=True, deleted_count=1, message="软删除成功")
            else:
                # 硬删除
                success = self.storage.delete(key)
                return DeleteResponse(
                    success=success,
                    deleted_count=1 if success else 0,
                    message="删除成功" if success else "删除失败",
                )

        except Exception as e:
            return DeleteResponse(success=False, deleted_count=0, message=f"删除失败: {str(e)}")

    def batch_save(self, requests: list[SaveRequest]) -> list[SaveResponse]:
        """批量保存"""
        responses = []
        for request in requests:
            responses.append(self.save(request))
        return responses

    def batch_delete(self, requests: list[DeleteRequest]) -> list[DeleteResponse]:
        """批量删除"""
        responses = []
        for request in requests:
            responses.append(self.delete(request))
        return responses

    def count(self, entity_type: str, filters: list[QueryFilter] | None = None) -> int:
        """统计数量"""
        prefix = f"{entity_type}/"
        keys = self.storage.list_keys(prefix)

        if not filters:
            return len(keys)

        count = 0
        for key in keys:
            entity = self.storage.load(key)
            if entity and self._match_filters(entity, filters):
                count += 1

        return count

    def exists(self, entity_type: str, entity_id: str) -> bool:
        """检查是否存在"""
        key = f"{entity_type}/{entity_id}"
        return self.storage.exists(key)

    def _generate_key(self, entity_type: str, entity: Any) -> str:
        """生成存储键"""
        if hasattr(entity, "id"):
            return f"{entity_type}/{entity.id}"
        return f"{entity_type}/{id(entity)}"

    def _match_filters(self, entity: Any, filters: list[QueryFilter]) -> bool:
        """检查实体是否匹配过滤条件"""
        if not filters:
            return True

        for filter in filters:
            value = getattr(entity, filter.field, None) if hasattr(entity, filter.field) else entity.get(filter.field)

            if filter.operator == QueryOperator.EQ:
                if value != filter.value:
                    return False
            elif filter.operator == QueryOperator.NE:
                if value == filter.value:
                    return False
            elif filter.operator == QueryOperator.GT:
                if not (value > filter.value):
                    return False
            elif filter.operator == QueryOperator.GTE:
                if not (value >= filter.value):
                    return False
            elif filter.operator == QueryOperator.LT:
                if not (value < filter.value):
                    return False
            elif filter.operator == QueryOperator.LTE:
                if not (value <= filter.value):
                    return False
            elif filter.operator == QueryOperator.IN:
                if value not in filter.value:
                    return False
            elif filter.operator == QueryOperator.LIKE and filter.value.lower() not in str(value).lower():
                return False

        return True

    def _sort_entities(self, entities: list[Any], sort_by: str, sort_order: str) -> list[Any]:
        """排序实体列表"""
        reverse = sort_order.lower() == "desc"
        return sorted(
            entities,
            key=lambda e: getattr(e, sort_by, None) if hasattr(e, sort_by) else e.get(sort_by),
            reverse=reverse,
        )
