"""
资源管理器
统一管理应用资源的创建和清理

本模块同时提供：
- 面向应用的 ResourceManager 类
- 面向测试的简单函数式接口（register_resource / unregister_resource 等）
"""

import atexit
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class InspectableRLock:
    """带 locked() 方法的可检测 RLock，用于测试"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._depth = 0

    def acquire(self, *args, **kwargs) -> bool:  # type: ignore[override]
        acquired = self._lock.acquire(*args, **kwargs)
        if acquired:
            self._depth += 1
        return acquired

    def release(self) -> None:  # type: ignore[override]
        self._lock.release()
        self._depth = max(0, self._depth - 1)

    def locked(self) -> bool:
        return self._depth > 0

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


# 全局资源表与锁（测试直接引用）
# _resources 的值为 (resource, cleanup_func)
_resources: dict[str, tuple[Any, Callable[[Any | None], None]]] = {}
_resource_lock: InspectableRLock = InspectableRLock()


class ResourceManager:
    """资源管理器 - 统一管理应用资源"""

    def __init__(self):
        # 使用模块级全局结构，保证函数式接口与类共享状态
        self._resources = _resources
        self._lock = _resource_lock
        self._registered = False

    def register_resource(
        self,
        name: str,
        resource: Any,
        cleanup_func: Callable[[Any | None], None] | None = None,
    ) -> None:
        """注册资源

        Args:
            name: 资源名称（非空字符串）
            resource: 资源对象
            cleanup_func: 清理函数，接受资源对象作为参数
        """
        if not isinstance(name, str) or not name:
            raise ValueError("资源名称不能为空")
        if cleanup_func is None:
            raise ValueError("清理函数不能为空")

        with self._lock:
            # 存储为 (resource, cleanup_func) 元组，符合测试期望
            self._resources[name] = (resource, cleanup_func)
            logger.debug(f"注册资源: {name}")

    def get_resource(self, name: str) -> Any | None:
        """获取资源"""
        with self._lock:
            item = self._resources.get(name)
            return item[0] if item is not None else None

    def unregister_resource(self, name: str) -> None:
        """注销资源（不执行清理，仅移除引用）"""
        with self._lock:
            self._resources.pop(name, None)

    def cleanup_all(self) -> None:
        """清理所有资源（按注册的反向顺序执行清理函数）"""
        with self._lock:
            logger.info("开始清理应用资源...")

            # 按注册顺序的反向执行清理
            names = list(self._resources.keys())
            for name in reversed(names):
                entry = self._resources.get(name)
                if entry is None:
                    continue
                resource, cleanup_func = entry
                try:
                    # 兼容两种签名：当资源为 None 时不传参数
                    if resource is None:
                        cleanup_func()
                    else:
                        cleanup_func(resource)
                except Exception as e:  # pragma: no cover - 防御性日志
                    logger.error(f"资源清理失败 [{name}]: {e}")

            # 只移除本次清理涉及的资源，保持清理期间新注册的资源
            for name in names:
                self._resources.pop(name, None)

            logger.info("应用资源清理完成")

    def register_atexit(self) -> None:
        """注册退出时清理"""
        if not self._registered:
            atexit.register(self.cleanup_all)
            self._registered = True
            logger.info("已注册退出时资源清理")


# 全局资源管理器
_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """获取全局资源管理器"""
    return _resource_manager


def register_resource(
    name: str, resource: Any, cleanup_func: Callable[[Any], None] | None = None
) -> None:
    """注册资源（便捷函数）"""
    _resource_manager.register_resource(name, resource, cleanup_func)


def unregister_resource(name: str) -> None:
    """注销资源（便捷函数）"""
    _resource_manager.unregister_resource(name)


def cleanup_resources() -> None:
    """清理所有资源（便捷函数，供测试使用）"""
    _resource_manager.cleanup_all()


def cleanup_all_resources() -> None:
    """兼容旧接口"""
    cleanup_resources()


# 自动注册退出时清理
_resource_manager.register_atexit()
