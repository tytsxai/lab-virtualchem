"""
前端性能优化工具
提供防抖、节流、内存管理等性能优化功能
"""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class Debouncer(QObject):
    """防抖器 - 延迟执行，多次调用只执行最后一次"""

    triggered = Signal()

    def __init__(self, delay_ms: int = 300, parent: QObject | None = None):
        super().__init__(parent)
        self.delay_ms = delay_ms
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timeout)
        self.callback: Callable | None = None
        self.args = ()
        self.kwargs = {}

    def call(self, callback: Callable, *args, **kwargs):
        """调用函数（防抖）"""
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # 重启定时器
        self.timer.stop()
        self.timer.start(self.delay_ms)

    def _on_timeout(self):
        """定时器触发"""
        if self.callback:
            try:
                self.callback(*self.args, **self.kwargs)
                self.triggered.emit()
            except Exception as e:
                logger.error(f"防抖回调执行失败: {e}", exc_info=True)

    def cancel(self):
        """取消待执行的调用"""
        self.timer.stop()
        self.callback = None


class Throttler(QObject):
    """节流器 - 限制执行频率"""

    triggered = Signal()

    def __init__(self, interval_ms: int = 100, parent: QObject | None = None):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self.last_call_time = 0
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timeout)
        self.pending_callback: Callable | None = None
        self.pending_args = ()
        self.pending_kwargs = {}

    def call(self, callback: Callable, *args, **kwargs):
        """调用函数（节流）"""
        current_time = time.time() * 1000  # 毫秒

        # 如果距上次调用超过间隔，立即执行
        if current_time - self.last_call_time >= self.interval_ms:
            self.last_call_time = current_time
            try:
                callback(*args, **kwargs)
                self.triggered.emit()
            except Exception as e:
                logger.error(f"节流回调执行失败: {e}", exc_info=True)
        else:
            # 否则延迟执行
            self.pending_callback = callback
            self.pending_args = args
            self.pending_kwargs = kwargs

            if not self.timer.isActive():
                remaining = self.interval_ms - (current_time - self.last_call_time)
                self.timer.start(int(remaining))

    def _on_timeout(self):
        """定时器触发"""
        if self.pending_callback:
            self.last_call_time = time.time() * 1000
            try:
                self.pending_callback(*self.pending_args, **self.pending_kwargs)
                self.triggered.emit()
            except Exception as e:
                logger.error(f"节流回调执行失败: {e}", exc_info=True)
            finally:
                self.pending_callback = None


def debounce(delay_ms: int = 300):
    """防抖装饰器"""

    def decorator(func: Callable) -> Callable:
        debouncer = Debouncer(delay_ms)

        @wraps(func)
        def wrapper(*args, **kwargs):
            debouncer.call(func, *args, **kwargs)

        wrapper.cancel = debouncer.cancel
        return wrapper

    return decorator


def throttle(interval_ms: int = 100):
    """节流装饰器"""

    def decorator(func: Callable) -> Callable:
        throttler = Throttler(interval_ms)

        @wraps(func)
        def wrapper(*args, **kwargs):
            throttler.call(func, *args, **kwargs)

        return wrapper

    return decorator


class MemoryMonitor(QObject):
    """内存监控器"""

    high_memory_warning = Signal(float)  # MB

    def __init__(
        self,
        threshold_mb: float = 500,
        check_interval_ms: int = 5000,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.threshold_mb = threshold_mb
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_memory)
        self.timer.start(check_interval_ms)
        self._last_warning_time = 0
        self._warning_cooldown = 60000  # 1分钟冷却

    def _check_memory(self):
        """检查内存使用"""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.threshold_mb:
                current_time = time.time() * 1000
                # 避免频繁警告
                if current_time - self._last_warning_time > self._warning_cooldown:
                    logger.warning(f"内存使用过高: {memory_mb:.2f} MB")
                    self.high_memory_warning.emit(memory_mb)
                    self._last_warning_time = current_time

        except ImportError:
            logger.debug("psutil未安装，无法监控内存")
            self.timer.stop()
        except Exception as e:
            logger.error(f"内存检查失败: {e}")

    def stop(self):
        """停止监控"""
        self.timer.stop()


class PerformanceTimer:
    """性能计时器 - 测量代码执行时间"""

    def __init__(self, name: str = "操作", log_threshold_ms: float = 100):
        self.name = name
        self.log_threshold_ms = log_threshold_ms
        self.start_time = 0
        self.end_time = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        duration_ms = (self.end_time - self.start_time) * 1000

        if duration_ms > self.log_threshold_ms:
            logger.warning(f"{self.name} 耗时: {duration_ms:.2f}ms")
        else:
            logger.debug(f"{self.name} 耗时: {duration_ms:.2f}ms")

    @property
    def elapsed_ms(self) -> float:
        """获取已用时间（毫秒）"""
        if self.end_time > 0:
            return (self.end_time - self.start_time) * 1000
        return (time.perf_counter() - self.start_time) * 1000


class RequestAnimationFrame(QObject):
    """requestAnimationFrame - 类似浏览器的动画帧"""

    def __init__(self, fps: int = 60, parent: QObject | None = None):
        super().__init__(parent)
        self.fps = fps
        self.interval_ms = 1000 // fps
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.callbacks: list[Callable] = []

    def request(self, callback: Callable):
        """请求动画帧"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

        if not self.timer.isActive():
            self.timer.start(self.interval_ms)

    def cancel(self, callback: Callable):
        """取消动画帧"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

        if not self.callbacks:
            self.timer.stop()

    def _tick(self):
        """帧回调"""
        timestamp = time.time() * 1000  # 毫秒时间戳

        # 复制回调列表以避免在迭代时修改
        callbacks = self.callbacks.copy()

        for callback in callbacks:
            try:
                callback(timestamp)
            except Exception as e:
                logger.error(f"动画帧回调失败: {e}", exc_info=True)

        # 如果没有待执行的回调，停止定时器
        if not self.callbacks:
            self.timer.stop()


class BatchUpdater(QObject):
    """批量更新器 - 合并多个更新为一次"""

    updated = Signal()

    def __init__(self, delay_ms: int = 16, parent: QObject | None = None):
        super().__init__(parent)
        self.delay_ms = delay_ms
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._flush)
        self.pending_updates: set = set()

    def schedule_update(self, key: Any):
        """调度更新"""
        self.pending_updates.add(key)

        if not self.timer.isActive():
            self.timer.start(self.delay_ms)

    def _flush(self):
        """刷新更新"""
        if self.pending_updates:
            logger.debug(f"批量更新: {len(self.pending_updates)}项")
            self.updated.emit()
            self.pending_updates.clear()

    def get_pending(self) -> set:
        """获取待更新项"""
        return self.pending_updates.copy()

    def clear(self):
        """清空待更新项"""
        self.pending_updates.clear()
        self.timer.stop()


# 单例实例
_memory_monitor: MemoryMonitor | None = None
_raf: RequestAnimationFrame | None = None


def get_memory_monitor() -> MemoryMonitor:
    """获取全局内存监控器"""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor()
    return _memory_monitor


def get_raf() -> RequestAnimationFrame:
    """获取全局动画帧调度器"""
    global _raf
    if _raf is None:
        _raf = RequestAnimationFrame()
    return _raf


if __name__ == "__main__":
    """性能工具测试"""
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 测试防抖
    logger.info("=== 防抖测试 ===")
    debouncer = Debouncer(500)

    def debounced_func():
        logger.info(f"防抖函数执行: {time.time()}")

    # 快速调用多次
    for _i in range(5):
        debouncer.call(debounced_func)
        time.sleep(0.1)

    # 测试节流
    logger.info("\n=== 节流测试 ===")
    throttler = Throttler(200)

    def throttled_func():
        logger.info(f"节流函数执行: {time.time()}")

    # 快速调用多次
    for _i in range(5):
        throttler.call(throttled_func)
        time.sleep(0.05)

    # 测试性能计时器
    logger.info("\n=== 性能计时器测试 ===")
    with PerformanceTimer("测试操作"):
        time.sleep(0.15)  # 模拟耗时操作

    app.exec()
