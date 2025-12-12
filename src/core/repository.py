"""
仓储模式实现 (Repository Pattern)

提供数据访问抽象层，隔离数据访问逻辑
"""

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from collections.abc import Callable as TypingCallable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class Entity:
    """实体基类"""

    id: Any = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class IRepository(ABC, Generic[T]):
    """仓储接口"""

    @abstractmethod
    def add(self, entity: T) -> T:
        """添加实体"""
        pass

    @abstractmethod
    def get(self, id: str) -> T | None:
        """根据ID获取实体"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """更新实体"""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    def find_all(self) -> list[T]:
        """查找所有实体"""
        pass

    @abstractmethod
    def find_by(self, predicate: Callable[[T], bool]) -> list[T]:
        """根据条件查找"""
        pass

    @abstractmethod
    def count(self) -> int:
        """统计数量"""
        pass

    @abstractmethod
    def exists(self, id: str) -> bool:
        """检查是否存在"""
        pass


class InMemoryRepository(IRepository[T]):
    """内存仓储实现"""

    def __init__(self):
        self._data: dict[str, T] = {}

    def add(self, entity: T) -> T:
        if hasattr(entity, "id"):
            self._data[entity.id] = entity
            if hasattr(entity, "created_at") and entity.created_at is None:
                entity.created_at = datetime.now()
            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.now()
        return entity

    def get(self, id: str) -> T | None:
        return self._data.get(id)

    def update(self, entity: T) -> T:
        if hasattr(entity, "id") and entity.id in self._data:
            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.now()
            self._data[entity.id] = entity
        return entity

    def delete(self, id: str) -> bool:
        if id in self._data:
            del self._data[id]
            return True
        return False

    def find_all(self) -> list[T]:
        return list(self._data.values())

    def find_by(self, predicate: Callable[[T], bool]) -> list[T]:
        return [entity for entity in self._data.values() if predicate(entity)]

    def count(self) -> int:
        return len(self._data)

    def exists(self, id: str) -> bool:
        return id in self._data

    def clear(self) -> None:
        """清空仓储"""
        self._data.clear()


class FileRepository(IRepository[T]):
    """文件仓储实现"""

    def __init__(self, file_path: str, serializer: TypingCallable | None = None):
        self.file_path = file_path
        self.serializer: TypingCallable = serializer or json
        self._data: dict[str, T] = {}
        self._load()

    def _load(self) -> None:
        """从文件加载数据"""
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = self.serializer.load(f)
                self._data = data if isinstance(data, dict) else {}
        except FileNotFoundError:
            self._data = {}

    def _save(self) -> None:
        """保存数据到文件"""
        with open(self.file_path, "w", encoding="utf-8") as f:
            self.serializer.dump(self._data, f, indent=2, ensure_ascii=False)

    def add(self, entity: T) -> T:
        if hasattr(entity, "id"):
            self._data[entity.id] = entity
            self._save()
        return entity

    def get(self, id: str) -> T | None:
        return self._data.get(id)

    def update(self, entity: T) -> T:
        if hasattr(entity, "id") and entity.id in self._data:
            self._data[entity.id] = entity
            self._save()
        return entity

    def delete(self, id: str) -> bool:
        if id in self._data:
            del self._data[id]
            self._save()
            return True
        return False

    def find_all(self) -> list[T]:
        return list(self._data.values())

    def find_by(self, predicate: Callable[[T], bool]) -> list[T]:
        return [entity for entity in self._data.values() if predicate(entity)]

    def count(self) -> int:
        return len(self._data)

    def exists(self, id: str) -> bool:
        return id in self._data


# 仓储工厂
class RepositoryFactory:
    """仓储工厂"""

    @staticmethod
    def create_memory_repository() -> IRepository[Any]:
        """创建内存仓储"""
        return InMemoryRepository()

    @staticmethod
    def create_file_repository(file_path: str) -> IRepository[Any]:
        """创建文件仓储"""
        return FileRepository(file_path)
