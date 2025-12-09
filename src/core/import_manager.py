"""
导入管理器
统一管理模块导入，避免循环依赖和重复导入
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, Optional, Type

from .common_exceptions import SystemError
from .error_handler import get_error_handler, safe_execute

logger = logging.getLogger(__name__)


class ImportManager:
    """导入管理器"""

    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._lazy_modules: Dict[str, str] = {}
        self._import_cache: Dict[str, Any] = {}
        self._error_handler = get_error_handler()

    def register_module(self, name: str, module: Any) -> None:
        """注册模块"""
        self._modules[name] = module
        logger.debug(f"Module {name} registered")

    def register_lazy_module(self, name: str, module_path: str) -> None:
        """注册懒加载模块"""
        self._lazy_modules[name] = module_path
        logger.debug(f"Lazy module {name} registered with path {module_path}")

    def get_module(self, name: str) -> Optional[Any]:
        """获取模块"""
        # 首先检查已注册的模块
        if name in self._modules:
            return self._modules[name]

        # 检查懒加载模块
        if name in self._lazy_modules:
            return self._load_lazy_module(name)

        # 尝试直接导入
        try:
            module = importlib.import_module(name)
            self._modules[name] = module
            return module
        except ImportError as e:
            logger.error(f"Failed to import module {name}: {e}")
            return None

    def _load_lazy_module(self, name: str) -> Optional[Any]:
        """加载懒加载模块"""
        if name not in self._lazy_modules:
            return None

        module_path = self._lazy_modules[name]

        try:
            module = importlib.import_module(module_path)
            self._modules[name] = module
            return module
        except ImportError as e:
            logger.error(f"Failed to load lazy module {name} from {module_path}: {e}")
            return None

    def import_class(self, module_name: str, class_name: str) -> Optional[Type]:
        """导入类"""
        module = self.get_module(module_name)
        if module is None:
            return None

        try:
            return getattr(module, class_name)
        except AttributeError as e:
            logger.error(f"Class {class_name} not found in module {module_name}: {e}")
            return None

    def import_function(self, module_name: str, function_name: str) -> Optional[Callable]:
        """导入函数"""
        module = self.get_module(module_name)
        if module is None:
            return None

        try:
            return getattr(module, function_name)
        except AttributeError as e:
            logger.error(f"Function {function_name} not found in module {module_name}: {e}")
            return None

    def safe_import(self, module_name: str, default: Any = None) -> Any:
        """安全导入模块"""
        return safe_execute(
            self.get_module,
            module_name,
            error_class=SystemError,
            fallback_value=default
        )

    def clear_cache(self) -> None:
        """清除缓存"""
        self._import_cache.clear()
        logger.debug("Import cache cleared")


# 全局导入管理器实例
_global_import_manager = ImportManager()


def get_import_manager() -> ImportManager:
    """获取全局导入管理器"""
    return _global_import_manager


def register_module(name: str, module: Any) -> None:
    """注册模块"""
    _global_import_manager.register_module(name, module)


def register_lazy_module(name: str, module_path: str) -> None:
    """注册懒加载模块"""
    _global_import_manager.register_lazy_module(name, module_path)


def get_module(name: str) -> Optional[Any]:
    """获取模块"""
    return _global_import_manager.get_module(name)


def import_class(module_name: str, class_name: str) -> Optional[Type]:
    """导入类"""
    return _global_import_manager.import_class(module_name, class_name)


def import_function(module_name: str, function_name: str) -> Optional[Callable]:
    """导入函数"""
    return _global_import_manager.import_function(module_name, function_name)


def safe_import(module_name: str, default: Any = None) -> Any:
    """安全导入模块"""
    return _global_import_manager.safe_import(module_name, default)
