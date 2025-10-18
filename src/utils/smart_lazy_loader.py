"""
智能懒加载系统
按需加载模块，优化启动时间和内存占用
"""

import importlib
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    priority: int = 0  # 优先级（数字越大越优先）
    dependencies: List[str] = field(default_factory=list)
    loaded: bool = False
    load_time: float = 0.0
    error: Optional[str] = None


class SmartLazyLoader:
    """智能懒加载器

    特性：
    - 按需加载模块
    - 后台预加载
    - 依赖管理
    - 加载统计
    """

    def __init__(self, enable_background_loading: bool = True):
        """初始化懒加载器

        Args:
            enable_background_loading: 是否启用后台预加载
        """
        self.enable_background_loading = enable_background_loading

        # 模块注册表
        self._modules: Dict[str, ModuleInfo] = {}

        # 已加载的模块缓存
        self._loaded_modules: Dict[str, Any] = {}

        # 加载锁
        self._lock = threading.Lock()

        # 后台加载线程
        self._background_thread: Optional[threading.Thread] = None
        self._background_loading = False

        # 统计信息
        self._stats = {
            'total_registered': 0,
            'total_loaded': 0,
            'background_loaded': 0,
            'load_errors': 0,
            'total_load_time': 0.0
        }

        logger.info("智能懒加载器初始化完成")

    def register(
        self,
        module_name: str,
        priority: int = 0,
        dependencies: Optional[List[str]] = None
    ):
        """注册模块

        Args:
            module_name: 模块名称（如 'src.core.config'）
            priority: 优先级（越高越优先预加载）
            dependencies: 依赖的模块列表
        """
        with self._lock:
            self._modules[module_name] = ModuleInfo(
                name=module_name,
                priority=priority,
                dependencies=dependencies or []
            )
            self._stats['total_registered'] += 1
            logger.debug(f"注册模块: {module_name} (优先级: {priority})")

    def load(self, module_name: str, force: bool = False) -> Any:
        """加载模块

        Args:
            module_name: 模块名称
            force: 强制重新加载

        Returns:
            加载的模块
        """
        with self._lock:
            # 检查缓存
            if not force and module_name in self._loaded_modules:
                return self._loaded_modules[module_name]

            # 加载依赖
            if module_name in self._modules:
                module_info = self._modules[module_name]
                for dep in module_info.dependencies:
                    if dep not in self._loaded_modules:
                        logger.debug(f"加载依赖: {dep}")
                        self.load(dep)

            # 加载模块
            try:
                start_time = time.time()
                module = importlib.import_module(module_name)
                load_time = time.time() - start_time

                # 缓存模块
                self._loaded_modules[module_name] = module

                # 更新信息
                if module_name in self._modules:
                    module_info = self._modules[module_name]
                    module_info.loaded = True
                    module_info.load_time = load_time

                # 更新统计
                self._stats['total_loaded'] += 1
                self._stats['total_load_time'] += load_time

                logger.debug(f"加载模块: {module_name} ({load_time*1000:.2f}ms)")
                return module

            except Exception as e:
                logger.error(f"加载模块失败 {module_name}: {e}")

                # 记录错误
                if module_name in self._modules:
                    self._modules[module_name].error = str(e)

                self._stats['load_errors'] += 1
                raise

    def load_many(self, module_names: List[str]) -> Dict[str, Any]:
        """批量加载模块

        Args:
            module_names: 模块名称列表

        Returns:
            模块字典
        """
        modules = {}
        for name in module_names:
            try:
                modules[name] = self.load(name)
            except Exception as e:
                logger.error(f"批量加载失败 {name}: {e}")

        return modules

    def start_background_loading(self):
        """启动后台预加载"""
        if not self.enable_background_loading:
            return

        if self._background_loading:
            logger.warning("后台加载已在运行")
            return

        self._background_loading = True
        self._background_thread = threading.Thread(
            target=self._background_load_loop,
            daemon=True
        )
        self._background_thread.start()
        logger.info("后台预加载已启动")

    def stop_background_loading(self):
        """停止后台预加载"""
        self._background_loading = False
        if self._background_thread:
            self._background_thread.join(timeout=1)
        logger.info("后台预加载已停止")

    def _background_load_loop(self):
        """后台加载循环"""
        # 按优先级排序模块
        sorted_modules = sorted(
            self._modules.values(),
            key=lambda m: m.priority,
            reverse=True
        )

        for module_info in sorted_modules:
            if not self._background_loading:
                break

            # 跳过已加载的模块
            if module_info.loaded or module_info.name in self._loaded_modules:
                continue

            try:
                # 后台加载
                self.load(module_info.name)
                self._stats['background_loaded'] += 1

                # 小延迟，避免影响主线程
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"后台加载失败 {module_info.name}: {e}")

        logger.info("后台预加载完成")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                **self._stats,
                'avg_load_time_ms': (
                    self._stats['total_load_time'] / self._stats['total_loaded'] * 1000
                    if self._stats['total_loaded'] > 0 else 0
                ),
                'cache_size': len(self._loaded_modules)
            }

    def get_loaded_modules(self) -> List[str]:
        """获取已加载的模块列表"""
        with self._lock:
            return list(self._loaded_modules.keys())

    def get_unloaded_modules(self) -> List[str]:
        """获取未加载的模块列表"""
        with self._lock:
            return [
                name for name, info in self._modules.items()
                if not info.loaded and name not in self._loaded_modules
            ]

    def clear_cache(self):
        """清空缓存"""
        with self._lock:
            self._loaded_modules.clear()
            for module_info in self._modules.values():
                module_info.loaded = False
        logger.info("模块缓存已清空")


# 全局懒加载器实例
_lazy_loader: Optional[SmartLazyLoader] = None


def get_lazy_loader() -> SmartLazyLoader:
    """获取全局懒加载器实例"""
    global _lazy_loader
    if _lazy_loader is None:
        _lazy_loader = SmartLazyLoader()
    return _lazy_loader


def lazy_import(module_name: str, *args, **kwargs) -> Any:
    """懒加载导入函数

    使用示例：
        config = lazy_import('src.core.config')
    """
    loader = get_lazy_loader()
    return loader.load(module_name)
