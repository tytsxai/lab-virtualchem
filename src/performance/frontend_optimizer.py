"""
前端性能优化器
提供资源加载优化、UI渲染优化、懒加载等功能
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceLoadConfig:
    """资源加载配置"""

    lazy_load: bool = True
    preload_critical: bool = True
    cache_resources: bool = True
    max_cache_size_mb: int = 100
    image_quality: int = 85  # JPEG质量
    use_webp: bool = True


class ResourceLoader(QObject):
    """资源加载器 - 优化资源加载性能"""

    resource_loaded = Signal(str, object)  # 资源ID, 资源对象
    load_progress = Signal(int, int)  # 已加载, 总数

    def __init__(self, config: ResourceLoadConfig | None = None):
        super().__init__()
        self.config = config or ResourceLoadConfig()
        self.resource_cache: dict[str, Any] = {}
        self.cache_size = 0
        self.loading_queue: list[
            tuple[str, Callable, int]
        ] = []  # (id, loader, priority)
        self.is_loading = False

        logger.info("资源加载器初始化完成")

    def load_image(
        self, image_path: str, size: tuple[int, int] | None = None
    ) -> QPixmap:
        """加载图片（支持缓存和大小调整）"""
        cache_key = f"img:{image_path}:{size}"

        # 检查缓存
        if self.config.cache_resources and cache_key in self.resource_cache:
            logger.debug(f"从缓存加载图片: {image_path}")
            return self.resource_cache[cache_key]

        # 加载图片
        pixmap = QPixmap(image_path)

        # 调整大小
        if size and not pixmap.isNull():
            pixmap = pixmap.scaled(
                size[0],
                size[1],
                aspectRatioMode=1,  # KeepAspectRatio
                transformMode=1,  # SmoothTransformation
            )

        # 缓存
        if self.config.cache_resources and not pixmap.isNull():
            self._cache_resource(
                cache_key, pixmap, pixmap.width() * pixmap.height() * 4
            )

        return pixmap

    def preload_resources(self, resources: list[dict[str, Any]]):
        """预加载资源"""
        if not self.config.preload_critical:
            return

        logger.info(f"开始预加载 {len(resources)} 个资源")

        for i, resource in enumerate(resources):
            resource_type = resource.get("type", "unknown")
            resource_path = resource.get("path", "")

            if resource_type == "image":
                self.load_image(resource_path, resource.get("size"))

            self.load_progress.emit(i + 1, len(resources))

        logger.info("资源预加载完成")

    def queue_load(self, resource_id: str, loader_func: Callable, priority: int = 0):
        """将资源加载加入队列（按优先级）"""
        self.loading_queue.append((resource_id, loader_func, priority))
        self.loading_queue.sort(key=lambda x: x[2], reverse=True)

        if not self.is_loading:
            self._process_queue()

    def _process_queue(self):
        """处理加载队列"""
        if not self.loading_queue:
            return

        self.is_loading = True
        resource_id, loader_func, _ = self.loading_queue.pop(0)

        try:
            resource = loader_func()
            self.resource_loaded.emit(resource_id, resource)
            logger.debug(f"资源加载完成: {resource_id}")
        except Exception as e:
            logger.error(f"资源加载失败: {resource_id} - {e}")
        finally:
            self.is_loading = False
            if self.loading_queue:
                QTimer.singleShot(0, self._process_queue)

    def _cache_resource(self, key: str, resource: Any, size_bytes: int):
        """缓存资源"""
        max_size_bytes = self.config.max_cache_size_mb * 1024 * 1024

        # 检查缓存大小
        if self.cache_size + size_bytes > max_size_bytes:
            self._evict_cache(size_bytes)

        self.resource_cache[key] = resource
        self.cache_size += size_bytes

    def _evict_cache(self, needed_size: int):
        """驱逐缓存（简单的FIFO策略）"""
        keys_to_remove = []
        freed_size = 0

        for key in list(self.resource_cache.keys()):
            if freed_size >= needed_size:
                break
            keys_to_remove.append(key)
            # 简化估算
            freed_size += 1024 * 1024  # 假设每个资源1MB

        for key in keys_to_remove:
            del self.resource_cache[key]

        self.cache_size -= freed_size
        logger.debug(f"缓存驱逐: 移除 {len(keys_to_remove)} 个资源")

    def clear_cache(self):
        """清空缓存"""
        self.resource_cache.clear()
        self.cache_size = 0
        logger.info("资源缓存已清空")


class UIRenderOptimizer(QObject):
    """UI渲染优化器"""

    def __init__(self):
        super().__init__()
        self.render_queue: list[tuple[QWidget, Callable]] = []
        self.is_rendering = False
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self._process_batch)
        self.batch_timer.setInterval(16)  # 60 FPS

        logger.info("UI渲染优化器初始化完成")

    def queue_update(self, widget: QWidget, update_func: Callable):
        """队列更新（批处理）"""
        self.render_queue.append((widget, update_func))

        if not self.batch_timer.isActive():
            self.batch_timer.start()

    def _process_batch(self):
        """批处理更新"""
        if not self.render_queue:
            self.batch_timer.stop()
            return

        # 每帧处理最多10个更新
        batch_size = min(10, len(self.render_queue))

        for _ in range(batch_size):
            if not self.render_queue:
                break

            widget, update_func = self.render_queue.pop(0)

            try:
                if widget and not widget.isHidden():
                    update_func()
            except Exception as e:
                logger.error(f"UI更新失败: {e}")

    def optimize_widget_tree(self, root_widget: QWidget):
        """优化控件树（移除隐藏控件等）"""
        hidden_count = 0

        def traverse(widget: QWidget):
            nonlocal hidden_count

            # 检查子控件
            for child in widget.findChildren(QWidget):
                if not child.isVisible() and not child.parent():
                    child.deleteLater()
                    hidden_count += 1

        traverse(root_widget)

        if hidden_count > 0:
            logger.debug(f"优化控件树: 移除 {hidden_count} 个隐藏控件")


class LazyComponentLoader:
    """懒加载组件加载器"""

    def __init__(self):
        self.loaded_components: dict[str, Any] = {}
        self.loaders: dict[str, Callable] = {}
        self.priorities: dict[str, int] = {}

        logger.info("懒加载组件加载器初始化完成")

    def register(self, component_id: str, loader: Callable, priority: int = 0):
        """注册组件加载器"""
        self.loaders[component_id] = loader
        self.priorities[component_id] = priority
        logger.debug(f"注册懒加载组件: {component_id} (优先级: {priority})")

    def load(self, component_id: str) -> Any | None:
        """加载组件"""
        # 检查是否已加载
        if component_id in self.loaded_components:
            return self.loaded_components[component_id]

        # 检查是否注册
        if component_id not in self.loaders:
            logger.warning(f"未注册的组件: {component_id}")
            return None

        try:
            start_time = time.time()
            component = self.loaders[component_id]()
            load_time = (time.time() - start_time) * 1000

            self.loaded_components[component_id] = component
            logger.info(f"懒加载组件: {component_id} ({load_time:.2f}ms)")

            return component
        except Exception as e:
            logger.error(f"懒加载组件失败: {component_id} - {e}")
            return None

    def is_loaded(self, component_id: str) -> bool:
        """检查组件是否已加载"""
        return component_id in self.loaded_components

    def unload(self, component_id: str):
        """卸载组件"""
        if component_id in self.loaded_components:
            del self.loaded_components[component_id]
            logger.debug(f"卸载组件: {component_id}")


class RequestMerger:
    """请求合并器 - 减少API调用"""

    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests: list[dict[str, Any]] = []
        self.batch_timer: QTimer | None = None

    def add_request(
        self, request_id: str, endpoint: str, data: dict[str, Any], callback: Callable
    ):
        """添加请求到批处理队列"""
        self.pending_requests.append(
            {"id": request_id, "endpoint": endpoint, "data": data, "callback": callback}
        )

        # 检查是否需要立即执行
        if len(self.pending_requests) >= self.batch_size:
            self._execute_batch()
        else:
            # 启动超时定时器
            if not self.batch_timer:
                self.batch_timer = QTimer()
                self.batch_timer.timeout.connect(self._execute_batch)

            self.batch_timer.start(int(self.batch_timeout * 1000))

    def _execute_batch(self):
        """执行批处理请求"""
        if not self.pending_requests:
            return

        # 停止定时器
        if self.batch_timer:
            self.batch_timer.stop()

        # 按endpoint分组
        grouped: dict[str, list] = {}
        for req in self.pending_requests:
            endpoint = req["endpoint"]
            if endpoint not in grouped:
                grouped[endpoint] = []
            grouped[endpoint].append(req)

        # 执行批量请求
        for endpoint, requests in grouped.items():
            try:
                # 这里应该调用实际的批量API
                # 简化示例：单独调用每个请求的回调
                for req in requests:
                    req["callback"](req["data"])

                logger.debug(f"批量执行 {len(requests)} 个请求: {endpoint}")
            except Exception as e:
                logger.error(f"批量请求失败: {endpoint} - {e}")

        self.pending_requests.clear()


# 全局实例
_resource_loader: ResourceLoader | None = None
_ui_render_optimizer: UIRenderOptimizer | None = None
_lazy_component_loader: LazyComponentLoader | None = None


def get_resource_loader() -> ResourceLoader:
    """获取全局资源加载器"""
    global _resource_loader
    if _resource_loader is None:
        _resource_loader = ResourceLoader()
    return _resource_loader


def get_ui_render_optimizer() -> UIRenderOptimizer:
    """获取全局UI渲染优化器"""
    global _ui_render_optimizer
    if _ui_render_optimizer is None:
        _ui_render_optimizer = UIRenderOptimizer()
    return _ui_render_optimizer


def get_lazy_component_loader() -> LazyComponentLoader:
    """获取全局懒加载组件加载器"""
    global _lazy_component_loader
    if _lazy_component_loader is None:
        _lazy_component_loader = LazyComponentLoader()
    return _lazy_component_loader


# 便捷函数
def register_lazy_component(component_id: str, loader: Callable, priority: int = 0):
    """注册懒加载组件"""
    get_lazy_component_loader().register(component_id, loader, priority)


def load_lazy_component(component_id: str) -> Any | None:
    """加载懒加载组件"""
    return get_lazy_component_loader().load(component_id)
