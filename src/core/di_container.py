"""
依赖注入容器 (Dependency Injection Container)

提供完整的依赖注入功能，支持：
- 单例和瞬态生命周期
- 自动依赖解析
- 接口绑定
- 延迟实例化
- 装饰器注入
"""

import inspect
import logging
import threading
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Lifetime(Enum):
    """服务生命周期"""

    SINGLETON = "singleton"  # 单例：整个应用生命周期内只创建一次
    TRANSIENT = "transient"  # 瞬态：每次请求都创建新实例
    SCOPED = "scoped"  # 作用域：在特定作用域内是单例


class ServiceDescriptor:
    """服务描述符"""

    def __init__(
        self,
        service_type: type,
        implementation: type | None = None,
        factory: Callable | None = None,
        instance: Any | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime

    def __repr__(self):
        return f"ServiceDescriptor({self.service_type.__name__}, lifetime={self.lifetime.value})"


class DIContainer:
    """依赖注入容器"""

    def __init__(self):
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        self._resolving: list[type] = []  # 用于检测循环依赖

    def register(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> "DIContainer":
        """
        注册服务

        Args:
            service_type: 服务类型（通常是接口或抽象类）
            implementation: 实现类型（具体类）
            factory: 工厂函数
            instance: 已存在的实例（用于单例）
            lifetime: 生命周期

        Returns:
            self（支持链式调用）

        Examples:
            # 注册接口到实现
            container.register(IStorage, FileStorage, lifetime=Lifetime.SINGLETON)

            # 注册工厂函数
            container.register(ILogger, factory=lambda: create_logger())

            # 注册实例
            container.register(IConfig, instance=config_obj)
        """
        if instance is not None:
            lifetime = Lifetime.SINGLETON
            self._singletons[service_type] = instance

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            instance=instance,
            lifetime=lifetime,
        )

        self._services[service_type] = descriptor
        return self

    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
    ) -> "DIContainer":
        """注册单例服务"""
        return self.register(service_type, implementation, factory, instance, Lifetime.SINGLETON)

    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "DIContainer":
        """注册瞬态服务"""
        return self.register(service_type, implementation, factory, lifetime=Lifetime.TRANSIENT)

    def resolve(self, service_type: type[T]) -> T:
        """
        解析服务

        Args:
            service_type: 要解析的服务类型

        Returns:
            服务实例

        Raises:
            ValueError: 服务未注册
            RuntimeError: 循环依赖

        Examples:
            storage = container.resolve(IStorage)
            logger = container.resolve(ILogger)
        """
        # 检测循环依赖
        if service_type in self._resolving:
            chain = " -> ".join(t.__name__ for t in self._resolving)
            raise RuntimeError(f"Circular dependency detected: {chain} -> {service_type.__name__}")

        # 检查是否已注册
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} is not registered")

        descriptor = self._services[service_type]

        # 如果是单例且已创建，直接返回
        if descriptor.lifetime == Lifetime.SINGLETON and service_type in self._singletons:
            return self._singletons[service_type]

        # 标记正在解析（用于循环依赖检测）
        self._resolving.append(service_type)

        try:
            # 创建实例
            instance = self._create_instance(descriptor)

            # 如果是单例，缓存实例
            if descriptor.lifetime == Lifetime.SINGLETON:
                self._singletons[service_type] = instance

            return instance

        finally:
            # 移除解析标记
            self._resolving.remove(service_type)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例"""
        # 如果提供了实例，直接返回
        if descriptor.instance is not None:
            return descriptor.instance

        # 如果提供了工厂函数，使用工厂
        if descriptor.factory is not None:
            return descriptor.factory()

        # 使用实现类创建实例
        if descriptor.implementation is None:
            raise ValueError(f"No implementation or factory provided for {descriptor.service_type.__name__}")

        # 自动解析构造函数依赖
        return self._create_with_dependencies(descriptor.implementation)

    def _create_with_dependencies(self, cls: type[T]) -> T:
        """
        自动解析构造函数依赖并创建实例

        检查构造函数的类型注解，自动注入依赖
        """
        # 获取构造函数签名
        sig = inspect.signature(cls.__init__)

        # 解析参数
        kwargs = {}
        for param_name, param in sig.parameters.items():
            # 跳过 self
            if param_name == "self":
                continue

            # 如果有类型注解，尝试解析
            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation

                # 如果该类型已注册，自动注入
                if param_type in self._services:
                    kwargs[param_name] = self.resolve(param_type)
                # 如果有默认值，使用默认值
                elif param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default

        return cls(**kwargs)

    def is_registered(self, service_type: type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services

    def get_all_services(self) -> list[type]:
        """获取所有已注册的服务类型"""
        return list(self._services.keys())

    def clear(self):
        """清空容器（主要用于测试）"""
        self._services.clear()
        self._singletons.clear()
        self._resolving.clear()


# 全局容器实例（线程安全）
_global_container: DIContainer | None = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """获取全局容器实例（线程安全）"""
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:  # 双重检查锁
                _global_container = DIContainer()
    return _global_container


def inject(*dependencies: type):
    """
    依赖注入装饰器

    自动从容器中解析依赖并注入到函数参数

    Examples:
        @inject(IStorage, ILogger)
        def my_function(storage: IStorage, logger: ILogger):
            storage.save("data")
            logger.log("Saved")
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            container = get_container()

            # 解析依赖
            resolved_deps = [container.resolve(dep) for dep in dependencies]

            # 调用原函数
            return func(*args, *resolved_deps, **kwargs)

        return wrapper

    return decorator


# 示例用法
if __name__ == "__main__":
    from abc import ABC, abstractmethod

    # 定义接口
    class ILogger(ABC):
        @abstractmethod
        def log(self, message: str):
            pass

    class IStorage(ABC):
        @abstractmethod
        def save(self, data: str):
            pass

    # 实现类
    class ConsoleLogger(ILogger):
        def log(self, message: str):
            logger.info(f"[LOG] {message}")

    class FileStorage(IStorage):
        def __init__(self, logger: ILogger):  # 构造函数注入
            self.logger = logger

        def save(self, data: str):
            self.logger.log(f"Saving: {data}")
            # 实际保存逻辑...

    # 创建容器并注册服务
    container = DIContainer()
    container.register_singleton(ILogger, ConsoleLogger)
    container.register_transient(IStorage, FileStorage)

    # 解析服务（自动注入依赖）
    storage_instance = container.resolve(IStorage)
    storage_instance.save("test data")

    # 使用装饰器
    @inject(IStorage)
    def process_data(storage: IStorage):
        storage.save("processed data")

    # 需要传入storage参数
    process_data(storage=storage_instance)
