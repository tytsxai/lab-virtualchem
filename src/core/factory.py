"""
工厂模式实现 (Factory Pattern)

提供灵活的对象创建机制
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class IFactory(ABC, Generic[T]):
    """工厂接口"""

    @abstractmethod
    def create(self, type_name: str, **kwargs) -> T:
        """创建对象"""
        pass

    @abstractmethod
    def register(self, type_name: str, creator: Callable):
        """注册创建器"""
        pass


class Factory(IFactory[T]):
    """通用工厂实现"""

    def __init__(self):
        self._creators: dict[str, Callable] = {}

    def register(self, type_name: str, creator: Callable) -> "Factory":
        """
        注册创建器

        Args:
            type_name: 类型名称
            creator: 创建函数

        Returns:
            self（支持链式调用）

        Examples:
            factory = Factory()
            factory.register("json", lambda: JsonStorage())
            factory.register("file", lambda: FileStorage())
        """
        self._creators[type_name] = creator
        return self

    def register_type(self, type_name: str, cls: type[T]) -> "Factory":
        """
        注册类型

        Args:
            type_name: 类型名称
            cls: 类

        Examples:
            factory.register_type("json", JsonStorage)
        """
        self._creators[type_name] = lambda **kwargs: cls(**kwargs)
        return self

    def create(self, type_name: str, **kwargs) -> T:
        """
        创建对象

        Args:
            type_name: 类型名称
            **kwargs: 创建参数

        Returns:
            创建的对象

        Raises:
            ValueError: 类型未注册

        Examples:
            storage = factory.create("json", path="data.json")
        """
        if type_name not in self._creators:
            raise ValueError(f"Type '{type_name}' is not registered")

        creator = self._creators[type_name]
        return creator(**kwargs)

    def has_type(self, type_name: str) -> bool:
        """检查类型是否已注册"""
        return type_name in self._creators

    def get_types(self) -> list:
        """获取所有已注册的类型"""
        return list(self._creators.keys())


class SingletonFactory(Factory[T]):
    """单例工厂"""

    def __init__(self):
        super().__init__()
        self._instances: dict[str, T] = {}

    def create(self, type_name: str, **kwargs) -> T:
        """创建单例对象"""
        if type_name not in self._instances:
            self._instances[type_name] = super().create(type_name, **kwargs)
        return self._instances[type_name]

    def clear_instance(self, type_name: str):
        """清除单例实例"""
        if type_name in self._instances:
            del self._instances[type_name]

    def clear_all_instances(self):
        """清除所有单例实例"""
        self._instances.clear()


# 示例：存储工厂
from typing import Generic  # noqa: E402, F811

from src.interfaces.storage import IStorage  # noqa: E402


class StorageFactory(Factory[IStorage]):
    """存储工厂"""

    pass
