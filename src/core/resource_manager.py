"""
资源管理器
统一管理应用资源的创建和清理
"""

import atexit
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class ResourceManager:
    """资源管理器 - 统一管理应用资源"""

    def __init__(self):
        self._resources: dict[str, Any] = {}
        self._cleanup_functions: list[Callable[[], None]] = []
        self._lock = threading.RLock()
        self._registered = False

    def register_resource(self, name: str, resource: Any, cleanup_func: Callable[[], None] | None = None):
        """注册资源

        Args:
            name: 资源名称
            resource: 资源对象
            cleanup_func: 清理函数
        """
        with self._lock:
            self._resources[name] = resource
            if cleanup_func:
                self._cleanup_functions.append(cleanup_func)
            logger.debug(f"注册资源: {name}")

    def get_resource(self, name: str) -> Any | None:
        """获取资源

        Args:
            name: 资源名称

        Returns:
            资源对象或None
        """
        with self._lock:
            return self._resources.get(name)

    def cleanup_all(self):
        """清理所有资源"""
        with self._lock:
            logger.info("开始清理应用资源...")

            # 执行清理函数
            for cleanup_func in self._cleanup_functions:
                try:
                    cleanup_func()
                except Exception as e:
                    logger.error(f"资源清理失败: {e}")

            # 清空资源
            self._resources.clear()
            self._cleanup_functions.clear()

            logger.info("应用资源清理完成")

    def register_atexit(self):
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


def register_resource(name: str, resource: Any, cleanup_func: Callable[[], None] | None = None):
    """注册资源（便捷函数）"""
    _resource_manager.register_resource(name, resource, cleanup_func)


def cleanup_all_resources():
    """清理所有资源（便捷函数）"""
    _resource_manager.cleanup_all()


# 自动注册退出时清理
_resource_manager.register_atexit()
