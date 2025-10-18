"""
内存管理器
优化前端内存使用，提供内存监控和垃圾回收功能
"""

import gc
import logging
from typing import Any

import psutil
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class MemoryManager(QObject):
    """内存管理器"""

    # 内存警告信号
    memory_warning = Signal(str, float)  # 警告类型, 内存使用率
    memory_critical = Signal(str, float)  # 严重警告, 内存使用率
    gc_completed = Signal(int)  # 垃圾回收完成, 释放的内存大小

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._monitoring = False
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._check_memory)

        # 内存阈值设置
        self.warning_threshold = 80.0  # 80% 内存使用率警告
        self.critical_threshold = 90.0  # 90% 内存使用率严重警告

        # 内存使用历史
        self._memory_history: list[float] = []
        self._max_history = 100

        # 自动垃圾回收设置
        self.auto_gc_enabled = True
        self.gc_interval_ms = 30000  # 30秒自动垃圾回收
        self._gc_timer = QTimer(self)
        self._gc_timer.timeout.connect(self._auto_garbage_collect)

        # 弱引用缓存
        self._weak_refs: dict[str, Any] = {}

    def start_monitoring(self, interval_ms: int = 5000) -> None:
        """开始内存监控"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_timer.start(interval_ms)

        if self.auto_gc_enabled:
            self._gc_timer.start(self.gc_interval_ms)

        logger.info("内存监控已启动")

    def stop_monitoring(self) -> None:
        """停止内存监控"""
        self._monitoring = False
        self._monitor_timer.stop()
        self._gc_timer.stop()
        logger.info("内存监控已停止")

    def _check_memory(self) -> None:
        """检查内存使用情况"""
        try:
            # 获取系统内存信息
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent

            # 记录内存使用历史
            self._memory_history.append(memory_percent)
            if len(self._memory_history) > self._max_history:
                self._memory_history.pop(0)

            # 检查内存警告
            if memory_percent >= self.critical_threshold:
                self.memory_critical.emit("内存使用率过高", memory_percent)
                logger.warning(f"内存使用率严重警告: {memory_percent:.1f}%")

                # 紧急垃圾回收
                self._emergency_garbage_collect()

            elif memory_percent >= self.warning_threshold:
                self.memory_warning.emit("内存使用率较高", memory_percent)
                logger.info(f"内存使用率警告: {memory_percent:.1f}%")

        except Exception as e:
            logger.error(f"内存检查失败: {e}", exc_info=True)

    def _auto_garbage_collect(self) -> None:
        """自动垃圾回收"""
        try:
            # 执行垃圾回收
            collected = gc.collect()

            if collected > 0:
                logger.info(f"自动垃圾回收完成，回收了 {collected} 个对象")
                self.gc_completed.emit(collected)

        except Exception as e:
            logger.error(f"自动垃圾回收失败: {e}", exc_info=True)

    def _emergency_garbage_collect(self) -> None:
        """紧急垃圾回收"""
        try:
            logger.warning("执行紧急垃圾回收...")

            # 强制垃圾回收
            collected = gc.collect()

            # 清理弱引用缓存
            self._cleanup_weak_refs()

            logger.warning(f"紧急垃圾回收完成，回收了 {collected} 个对象")
            self.gc_completed.emit(collected)

        except Exception as e:
            logger.error(f"紧急垃圾回收失败: {e}", exc_info=True)

    def _cleanup_weak_refs(self) -> None:
        """清理弱引用缓存"""
        try:
            # 清理已失效的弱引用
            dead_refs = []
            for key, ref in self._weak_refs.items():
                if ref() is None:
                    dead_refs.append(key)

            for key in dead_refs:
                del self._weak_refs[key]

            if dead_refs:
                logger.info(f"清理了 {len(dead_refs)} 个失效的弱引用")

        except Exception as e:
            logger.error(f"清理弱引用失败: {e}", exc_info=True)

    def add_weak_ref(self, key: str, obj: Any) -> None:
        """添加弱引用"""
        try:
            import weakref

            self._weak_refs[key] = weakref.ref(obj)
            logger.debug(f"添加弱引用: {key}")

        except Exception as e:
            logger.error(f"添加弱引用失败: {e}", exc_info=True)

    def remove_weak_ref(self, key: str) -> None:
        """移除弱引用"""
        try:
            if key in self._weak_refs:
                del self._weak_refs[key]
                logger.debug(f"移除弱引用: {key}")

        except Exception as e:
            logger.error(f"移除弱引用失败: {e}", exc_info=True)

    def get_memory_stats(self) -> dict[str, Any]:
        """获取内存统计信息"""
        try:
            # 获取系统内存信息
            memory_info = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()

            return {
                "system_memory": {
                    "total": memory_info.total,
                    "available": memory_info.available,
                    "percent": memory_info.percent,
                    "used": memory_info.used,
                    "free": memory_info.free,
                },
                "process_memory": {
                    "rss": process_memory.rss,  # 物理内存
                    "vms": process_memory.vms,  # 虚拟内存
                    "percent": process.memory_percent(),
                },
                "memory_history": self._memory_history.copy(),
                "weak_refs_count": len(self._weak_refs),
                "monitoring": self._monitoring,
            }

        except Exception as e:
            logger.error(f"获取内存统计失败: {e}", exc_info=True)
            return {}

    def optimize_memory(self) -> None:
        """优化内存使用"""
        try:
            logger.info("开始内存优化...")

            # 垃圾回收
            collected = gc.collect()

            # 清理弱引用
            self._cleanup_weak_refs()

            # 清理内存历史
            if len(self._memory_history) > 50:
                self._memory_history = self._memory_history[-50:]

            logger.info(f"内存优化完成，回收了 {collected} 个对象")
            self.gc_completed.emit(collected)

        except Exception as e:
            logger.error(f"内存优化失败: {e}", exc_info=True)

    def get_memory_warning_threshold(self) -> float:
        """获取内存警告阈值"""
        return self.warning_threshold

    def set_memory_warning_threshold(self, threshold: float) -> None:
        """设置内存警告阈值"""
        if 0 < threshold < 100:
            self.warning_threshold = threshold
            logger.info(f"内存警告阈值设置为: {threshold}%")
        else:
            logger.warning(f"无效的内存警告阈值: {threshold}")

    def get_memory_critical_threshold(self) -> float:
        """获取内存严重警告阈值"""
        return self.critical_threshold

    def set_memory_critical_threshold(self, threshold: float) -> None:
        """设置内存严重警告阈值"""
        if 0 < threshold < 100:
            self.critical_threshold = threshold
            logger.info(f"内存严重警告阈值设置为: {threshold}%")
        else:
            logger.warning(f"无效的内存严重警告阈值: {threshold}")

    def is_monitoring(self) -> bool:
        """检查是否正在监控"""
        return self._monitoring

    def get_memory_history(self) -> list[float]:
        """获取内存使用历史"""
        return self._memory_history.copy()

    def clear_memory_history(self) -> None:
        """清空内存使用历史"""
        self._memory_history.clear()
        logger.info("内存使用历史已清空")

    def force_garbage_collect(self) -> int:
        """强制垃圾回收"""
        try:
            collected = gc.collect()
            logger.info(f"强制垃圾回收完成，回收了 {collected} 个对象")
            self.gc_completed.emit(collected)
            return collected

        except Exception as e:
            logger.error(f"强制垃圾回收失败: {e}", exc_info=True)
            return 0


# 全局内存管理器实例
_global_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取全局内存管理器实例"""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


def start_memory_monitoring(interval_ms: int = 5000) -> None:
    """启动全局内存监控"""
    manager = get_memory_manager()
    manager.start_monitoring(interval_ms)


def stop_memory_monitoring() -> None:
    """停止全局内存监控"""
    manager = get_memory_manager()
    manager.stop_monitoring()


def optimize_memory() -> None:
    """优化内存使用"""
    manager = get_memory_manager()
    manager.optimize_memory()


def get_memory_stats() -> dict[str, Any]:
    """获取内存统计信息"""
    manager = get_memory_manager()
    return manager.get_memory_stats()
