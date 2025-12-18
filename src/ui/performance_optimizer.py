"""
性能优化器
提供UI性能优化、内存管理和响应速度提升功能
"""

from __future__ import annotations

import gc
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QWidget

from ..utils.logger import get_logger
from .qt_event_utils import process_events_safely

logger = get_logger(__name__)


class OptimizationLevel(Enum):
    """优化级别"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class PerformanceMetrics:
    """性能指标"""

    fps: float = 0.0
    memory_usage: float = 0.0  # MB
    cpu_usage: float = 0.0
    render_time: float = 0.0  # ms
    update_time: float = 0.0  # ms
    widget_count: int = 0
    active_animations: int = 0
    timestamp: float = 0.0


class PerformanceOptimizer(QObject):
    """性能优化器"""

    # 信号
    performance_updated = Signal(PerformanceMetrics)
    optimization_applied = Signal(str, dict)  # 优化类型, 参数

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.optimization_level = OptimizationLevel.MEDIUM
        self.metrics = PerformanceMetrics()
        self.optimization_timer: QTimer | None = None
        self.metrics_timer: QTimer | None = None

        # 优化配置
        self.optimization_config = {
            OptimizationLevel.LOW: {
                "gc_interval": 30000,  # 30秒
                "widget_cleanup_interval": 60000,  # 1分钟
                "animation_limit": 10,
                "memory_threshold": 500,  # MB
            },
            OptimizationLevel.MEDIUM: {
                "gc_interval": 15000,  # 15秒
                "widget_cleanup_interval": 30000,  # 30秒
                "animation_limit": 5,
                "memory_threshold": 300,  # MB
            },
            OptimizationLevel.HIGH: {
                "gc_interval": 10000,  # 10秒
                "widget_cleanup_interval": 20000,  # 20秒
                "animation_limit": 3,
                "memory_threshold": 200,  # MB
            },
            OptimizationLevel.MAXIMUM: {
                "gc_interval": 5000,  # 5秒
                "widget_cleanup_interval": 10000,  # 10秒
                "animation_limit": 2,
                "memory_threshold": 100,  # MB
            },
        }

        # 优化状态
        self.optimizations_applied: set[str] = set()
        self.widget_cache: dict[str, QWidget] = {}
        self.animation_tracker: set[QObject] = set()

        self.setup_timers()

        logger.info("性能优化器初始化完成")

    def setup_timers(self):
        """设置定时器"""
        # 性能监控定时器
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.update_metrics)
        self.metrics_timer.start(1000)  # 每秒更新

        # 优化定时器
        self.optimization_timer = QTimer(self)
        self.optimization_timer.timeout.connect(self.run_optimizations)
        self.start_optimization_timer()

    def start_optimization_timer(self):
        """启动优化定时器"""
        if self.optimization_timer:
            config = self.optimization_config[self.optimization_level]
            interval = min(config["gc_interval"], config["widget_cleanup_interval"])
            self.optimization_timer.start(interval)

    def set_optimization_level(self, level: OptimizationLevel):
        """设置优化级别"""
        self.optimization_level = level
        self.start_optimization_timer()

        logger.info(f"设置性能优化级别: {level.value}")

    def update_metrics(self):
        """更新性能指标"""
        try:
            # 获取内存使用情况
            import psutil

            process = psutil.Process()
            self.metrics.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            self.metrics.cpu_usage = process.cpu_percent()

            # 获取FPS（简化计算）
            self.metrics.fps = self.calculate_fps()

            # 获取控件数量
            self.metrics.widget_count = len(QApplication.allWidgets())

            # 获取活跃动画数量
            self.metrics.active_animations = len(self.animation_tracker)

            self.metrics.timestamp = time.time()

            # 发送信号
            self.performance_updated.emit(self.metrics)

        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")

    def calculate_fps(self) -> float:
        """计算FPS"""
        # 简化的FPS计算
        # 实际应用中可以使用更精确的方法
        return 60.0  # 占位符

    def run_optimizations(self):
        """运行优化"""
        try:
            config = self.optimization_config[self.optimization_level]

            # 内存优化
            if self.metrics.memory_usage > config["memory_threshold"]:
                self.optimize_memory()

            # 垃圾回收
            self.run_garbage_collection()

            # 控件清理
            self.cleanup_widgets()

            # 动画优化
            if self.metrics.active_animations > config["animation_limit"]:
                self.optimize_animations()

            # UI响应优化
            self.optimize_ui_responsiveness()

        except Exception as e:
            logger.error(f"运行性能优化失败: {e}")

    def optimize_memory(self):
        """内存优化"""
        try:
            # 清理控件缓存
            self.widget_cache.clear()

            # 强制垃圾回收
            gc.collect()

            # 清理临时对象
            self.cleanup_temporary_objects()

            self.optimizations_applied.add("memory_optimization")
            self.optimization_applied.emit(
                "memory_optimization", {"level": self.optimization_level.value}
            )

            logger.debug("内存优化完成")

        except Exception as e:
            logger.error(f"内存优化失败: {e}")

    def run_garbage_collection(self):
        """运行垃圾回收"""
        try:
            # 收集垃圾
            collected = gc.collect()

            if collected > 0:
                logger.debug(f"垃圾回收完成，清理了 {collected} 个对象")

            self.optimizations_applied.add("garbage_collection")

        except Exception as e:
            logger.error(f"垃圾回收失败: {e}")

    def cleanup_widgets(self):
        """清理控件"""
        try:
            # 注意：遍历 QApplication.allWidgets() 并对“无父控件/不可见”的控件执行 deleteLater()
            # 很容易误删顶层窗口或仍在使用中的控件，导致 Qt 内部状态（包括定时器队列）被破坏。
            #
            # 这里改为仅清理缓存中已失效的引用，不主动销毁任何 QWidget。
            import shiboken6

            before = len(self.widget_cache)
            invalid_keys = [
                key
                for key, widget in self.widget_cache.items()
                if widget is None or not shiboken6.isValid(widget)
            ]
            for key in invalid_keys:
                self.widget_cache.pop(key, None)

            removed = before - len(self.widget_cache)
            if removed:
                logger.debug(f"从缓存中移除了 {removed} 个失效控件引用")

            self.optimizations_applied.add("widget_cleanup")

        except Exception as e:
            logger.error(f"控件清理失败: {e}")

    def optimize_animations(self):
        """优化动画"""
        try:
            config = self.optimization_config[self.optimization_level]
            limit = config["animation_limit"]

            if len(self.animation_tracker) > limit:
                # 暂停多余的动画
                animations_to_pause = list(self.animation_tracker)[limit:]
                for animation in animations_to_pause:
                    if hasattr(animation, "pause"):
                        animation.pause()

                logger.debug(f"暂停了 {len(animations_to_pause)} 个动画")

            self.optimizations_applied.add("animation_optimization")

        except Exception as e:
            logger.error(f"动画优化失败: {e}")

    def optimize_ui_responsiveness(self):
        """优化UI响应性"""
        try:
            # 处理待处理的事件（仅主线程、短时间片，避免重入）
            process_events_safely(5)

            # 优化事件处理
            self.optimize_event_processing()

            self.optimizations_applied.add("ui_responsiveness")

        except Exception as e:
            logger.error(f"UI响应性优化失败: {e}")

    def optimize_event_processing(self):
        """优化事件处理"""
        try:
            # 限制事件处理时间：避免在 Python 层 while 循环反复 processEvents()（容易重入）。
            if QApplication.hasPendingEvents():
                process_events_safely(16)

        except Exception as e:
            logger.error(f"事件处理优化失败: {e}")

    def cleanup_temporary_objects(self):
        """清理临时对象"""
        try:
            # 清理临时文件
            import os
            import tempfile

            temp_dir = tempfile.gettempdir()
            temp_files = [f for f in os.listdir(temp_dir) if f.startswith("vcl_")]

            for temp_file in temp_files:
                try:
                    file_path = os.path.join(temp_dir, temp_file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception:
                    pass  # 忽略删除失败的文件

            logger.debug(f"清理了 {len(temp_files)} 个临时文件")

        except Exception as e:
            logger.error(f"清理临时对象失败: {e}")

    def register_animation(self, animation: QObject):
        """注册动画"""
        self.animation_tracker.add(animation)

        # 连接动画完成信号
        if hasattr(animation, "finished"):
            animation.finished.connect(lambda: self.unregister_animation(animation))

    def unregister_animation(self, animation: QObject):
        """注销动画"""
        self.animation_tracker.discard(animation)

    def cache_widget(self, key: str, widget: QWidget):
        """缓存控件"""
        self.widget_cache[key] = widget

    def get_cached_widget(self, key: str) -> QWidget | None:
        """获取缓存的控件"""
        return self.widget_cache.get(key)

    def clear_widget_cache(self):
        """清空控件缓存"""
        self.widget_cache.clear()
        logger.debug("控件缓存已清空")

    def get_performance_report(self) -> dict[str, Any]:
        """获取性能报告"""
        return {
            "metrics": {
                "fps": self.metrics.fps,
                "memory_usage": self.metrics.memory_usage,
                "cpu_usage": self.metrics.cpu_usage,
                "widget_count": self.metrics.widget_count,
                "active_animations": self.metrics.active_animations,
            },
            "optimization_level": self.optimization_level.value,
            "optimizations_applied": list(self.optimizations_applied),
            "cache_size": len(self.widget_cache),
        }

    def apply_optimization(self, optimization_type: str, **_kwargs) -> bool:
        """应用特定优化"""
        try:
            if optimization_type == "memory":
                self.optimize_memory()
            elif optimization_type == "garbage_collection":
                self.run_garbage_collection()
            elif optimization_type == "widget_cleanup":
                self.cleanup_widgets()
            elif optimization_type == "animation":
                self.optimize_animations()
            elif optimization_type == "ui_responsiveness":
                self.optimize_ui_responsiveness()
            else:
                logger.warning(f"未知的优化类型: {optimization_type}")
                return False

            logger.info(f"应用优化: {optimization_type}")
            return True

        except Exception as e:
            logger.error(f"应用优化失败: {optimization_type} - {e}")
            return False

    def stop(self):
        """停止优化器"""
        if self.metrics_timer:
            self.metrics_timer.stop()

        if self.optimization_timer:
            self.optimization_timer.stop()

        logger.info("性能优化器已停止")


class LazyLoader:
    """懒加载器"""

    def __init__(self):
        self.loaded_components: set[str] = set()
        self.loading_queue: list[Callable] = []
        self.is_loading = False

        logger.info("懒加载器初始化完成")

    def load_component(
        self, component_id: str, loader_func: Callable, _priority: int = 0
    ):
        """加载组件"""
        if component_id in self.loaded_components:
            return True

        if self.is_loading:
            # 添加到队列
            self.loading_queue.append((_priority, component_id, loader_func))
            self.loading_queue.sort(key=lambda x: x[0], reverse=True)
            return False

        try:
            self.is_loading = True
            loader_func()
            self.loaded_components.add(component_id)
            logger.info(f"懒加载组件: {component_id}")
            return True

        except Exception as e:
            logger.error(f"懒加载组件失败: {component_id} - {e}")
            return False

        finally:
            self.is_loading = False
            self.process_queue()

    def process_queue(self):
        """处理队列"""
        if not self.loading_queue or self.is_loading:
            return

        priority, component_id, loader_func = self.loading_queue.pop(0)
        self.load_component(component_id, loader_func, priority)

    def is_component_loaded(self, component_id: str) -> bool:
        """检查组件是否已加载"""
        return component_id in self.loaded_components


class ResourceManager:
    """资源管理器"""

    def __init__(self):
        self.resource_cache: dict[str, Any] = {}
        self.cache_size_limit = 100  # MB
        self.current_cache_size = 0

        logger.info("资源管理器初始化完成")

    def cache_resource(self, key: str, resource: Any, size: int = 0):
        """缓存资源"""
        try:
            # 检查缓存大小限制
            if self.current_cache_size + size > self.cache_size_limit * 1024 * 1024:
                self.cleanup_cache()

            self.resource_cache[key] = resource
            self.current_cache_size += size

            logger.debug(f"缓存资源: {key} ({size} bytes)")

        except Exception as e:
            logger.error(f"缓存资源失败: {key} - {e}")

    def get_cached_resource(self, key: str) -> Any | None:
        """获取缓存的资源"""
        return self.resource_cache.get(key)

    def cleanup_cache(self):
        """清理缓存"""
        try:
            # 清理一半的缓存
            keys_to_remove = list(self.resource_cache.keys())[
                : len(self.resource_cache) // 2
            ]

            for key in keys_to_remove:
                if key in self.resource_cache:
                    del self.resource_cache[key]

            self.current_cache_size = 0  # 简化计算

            logger.debug(f"清理了 {len(keys_to_remove)} 个缓存资源")

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")

    def clear_cache(self):
        """清空缓存"""
        self.resource_cache.clear()
        self.current_cache_size = 0
        logger.debug("资源缓存已清空")


# 全局性能优化器实例
_performance_optimizer: PerformanceOptimizer | None = None
_lazy_loader: LazyLoader | None = None
_resource_manager: ResourceManager | None = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


def get_lazy_loader() -> LazyLoader:
    """获取全局懒加载器"""
    global _lazy_loader
    if _lazy_loader is None:
        _lazy_loader = LazyLoader()
    return _lazy_loader


def get_resource_manager() -> ResourceManager:
    """获取全局资源管理器"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


# 便捷函数
def optimize_performance(level: OptimizationLevel = OptimizationLevel.MEDIUM):
    """优化性能"""
    optimizer = get_performance_optimizer()
    optimizer.set_optimization_level(level)


def lazy_load_component(
    component_id: str, loader_func: Callable, _priority: int = 0
) -> bool:
    """懒加载组件"""
    loader = get_lazy_loader()
    return loader.load_component(component_id, loader_func, _priority)


def cache_resource(key: str, resource: Any, size: int = 0):
    """缓存资源"""
    manager = get_resource_manager()
    manager.cache_resource(key, resource, size)


def get_cached_resource(key: str) -> Any | None:
    """获取缓存的资源"""
    manager = get_resource_manager()
    return manager.get_cached_resource(key)


# 全局实例
performance_optimizer = get_performance_optimizer()
