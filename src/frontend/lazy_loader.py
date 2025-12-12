"""
前端懒加载模块
实现组件懒加载、图片懒加载等性能优化
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class LazyLoader(QObject):
    """懒加载器 - 延迟加载重型组件"""

    loaded = Signal(str, object)  # 组件名, 组件实例
    load_failed = Signal(str, str)  # 组件名, 错误信息

    def __init__(self, parent=None, max_retries: int = 3):
        super().__init__(parent)
        self._registry: dict[str, Callable] = {}
        self._cache: dict[str, QWidget] = {}
        self._loading: set = set()
        self._retry_count: dict[str, int] = {}
        self._max_retries = max_retries

    def register(self, name: str, factory: Callable) -> None:
        """
        注册懒加载组件

        Args:
            name: 组件名称
            factory: 组件工厂函数
        """
        self._registry[name] = factory
        logger.debug(f"注册懒加载组件: {name}")

    def load(self, name: str, force: bool = False) -> QWidget | None:
        """
        加载组件（带重试机制）

        Args:
            name: 组件名称
            force: 是否强制重新加载

        Returns:
            组件实例或None
        """
        # 从缓存获取
        if not force and name in self._cache:
            logger.debug(f"从缓存获取组件: {name}")
            # 重置重试计数
            self._retry_count.pop(name, None)
            return self._cache[name]

        # 检查是否在加载中
        if name in self._loading:
            logger.warning(f"组件正在加载中: {name}")
            return None

        # 检查是否已注册
        if name not in self._registry:
            error_msg = f"未注册的组件: {name}"
            logger.error(error_msg)
            self.load_failed.emit(name, error_msg)
            return None

        # 检查重试次数
        retry_count = self._retry_count.get(name, 0)
        if retry_count >= self._max_retries:
            error_msg = f"组件加载失败次数过多: {name} (已重试{retry_count}次)"
            logger.error(error_msg)
            self.load_failed.emit(name, error_msg)
            return None

        try:
            self._loading.add(name)
            factory = self._registry[name]

            # 创建组件
            widget = factory()

            if widget is None:
                raise ValueError(f"工厂函数返回None: {name}")

            self._cache[name] = widget

            # 重置重试计数
            self._retry_count.pop(name, None)

            self.loaded.emit(name, widget)
            logger.info(f"成功加载组件: {name}")

            return widget

        except Exception as e:
            # 增加重试计数
            self._retry_count[name] = retry_count + 1
            error_msg = f"加载组件失败 {name} (第{self._retry_count[name]}次): {e}"
            logger.error(error_msg, exc_info=True)
            self.load_failed.emit(name, str(e))

            # 如果还能重试，延迟重试
            if self._retry_count[name] < self._max_retries:
                delay = 100 * (2 ** self._retry_count[name])  # 指数退避
                logger.info(f"将在{delay}ms后重试加载 {name}")
                QTimer.singleShot(delay, lambda: self.load(name, force))

            return None

        finally:
            self._loading.discard(name)

    def preload(self, names: list[str]) -> None:
        """
        预加载多个组件

        Args:
            names: 组件名称列表
        """
        for name in names:
            QTimer.singleShot(100, lambda n=name: self.load(n))

    def unload(self, name: str) -> None:
        """
        卸载组件以释放内存

        Args:
            name: 组件名称
        """
        if name in self._cache:
            widget = self._cache[name]
            widget.deleteLater()
            del self._cache[name]
            logger.info(f"卸载组件: {name}")

    def clear_cache(self) -> None:
        """清空缓存"""
        for widget in self._cache.values():
            widget.deleteLater()
        self._cache.clear()
        logger.info("清空懒加载缓存")


class ImageLazyLoader(QObject):
    """图片懒加载器"""

    image_loaded = Signal(str, object)  # 路径, QPixmap

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache: dict[str, Any] = {}
        self._loading: set = set()

    def load(self, path: str, size: tuple | None = None) -> Any | None:
        """
        加载图片

        Args:
            path: 图片路径
            size: 目标大小 (width, height)

        Returns:
            QPixmap或None
        """
        from PySide6.QtGui import QPixmap

        cache_key = f"{path}_{size}" if size else path

        # 从缓存获取
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 检查是否在加载中
        if cache_key in self._loading:
            return None

        try:
            self._loading.add(cache_key)

            # 加载图片
            pixmap = QPixmap(path)

            # 调整大小
            if size and not pixmap.isNull():
                pixmap = pixmap.scaled(
                    size[0],
                    size[1],
                    aspectMode=Qt.KeepAspectRatio,
                    mode=Qt.SmoothTransformation,
                )

            self._cache[cache_key] = pixmap
            self.image_loaded.emit(path, pixmap)

            return pixmap

        except Exception as e:
            logger.error(f"加载图片失败 {path}: {e}")
            return None

        finally:
            self._loading.discard(cache_key)

    def clear_cache(self) -> None:
        """清空图片缓存"""
        self._cache.clear()
        logger.info("清空图片缓存")


class AsyncLoader(QThread):
    """异步加载器 - 在后台线程加载数据"""

    loaded = Signal(object)  # 加载的数据
    error = Signal(str)  # 错误信息

    def __init__(self, loader_func: Callable, *args, **kwargs):
        super().__init__()
        self.loader_func = loader_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """执行加载"""
        try:
            result = self.loader_func(*self.args, **self.kwargs)
            self.loaded.emit(result)
        except Exception as e:
            self.error.emit(str(e))
            logger.error(f"异步加载失败: {e}", exc_info=True)


def lazy_load(threshold: int = 100):
    """
    懒加载装饰器 - 延迟执行耗时操作

    Args:
        threshold: 延迟时间(毫秒)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            QTimer.singleShot(threshold, lambda: func(*args, **kwargs))

        return wrapper

    return decorator


class CodeSplitter:
    """代码分割器 - 动态导入模块"""

    _modules: dict[str, Any] = {}

    @classmethod
    def import_module(cls, module_name: str) -> Any | None:
        """
        动态导入模块

        Args:
            module_name: 模块名称

        Returns:
            模块对象或None
        """
        if module_name in cls._modules:
            return cls._modules[module_name]

        try:
            import importlib

            module = importlib.import_module(module_name)
            cls._modules[module_name] = module
            logger.info(f"动态加载模块: {module_name}")
            return module

        except ImportError as e:
            logger.error(f"导入模块失败 {module_name}: {e}")
            return None

    @classmethod
    def clear_cache(cls) -> None:
        """清空模块缓存"""
        cls._modules.clear()


class ViewportLoader(QObject):
    """视口加载器 - 只加载可见区域的内容"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible_items: set = set()

    def is_in_viewport(self, widget: QWidget, viewport: QWidget) -> bool:
        """
        检查组件是否在视口内

        Args:
            widget: 被检查的组件
            viewport: 视口组件

        Returns:
            是否在视口内
        """
        widget_rect = widget.geometry()
        viewport_rect = viewport.rect()

        return viewport_rect.intersects(widget_rect)

    def load_visible(self, items: list, viewport: QWidget, loader: Callable) -> None:
        """
        加载可见项

        Args:
            items: 所有项
            viewport: 视口
            loader: 加载函数
        """
        for item in items:
            if self.is_in_viewport(item, viewport) and id(item) not in self._visible_items:
                loader(item)
                self._visible_items.add(id(item))


if __name__ == "__main__":
    # 演示使用
    import sys

    from PySide6.QtWidgets import QApplication, QLabel

    app = QApplication(sys.argv)

    # 懒加载器
    lazy_loader = LazyLoader()

    # 注册组件
    lazy_loader.register("heavy_widget", lambda: QLabel("Heavy Component"))

    # 加载组件
    widget = lazy_loader.load("heavy_widget")
    if widget:
        widget.show()

    sys.exit(app.exec())
