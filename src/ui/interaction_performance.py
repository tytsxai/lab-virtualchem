"""
交互性能优化
提供流畅的用户交互体验
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QWidget

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class InteractionMetrics:
    """交互指标"""

    action: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool

    @property
    def is_fast(self) -> bool:
        """是否足够快（<100ms）"""
        return self.duration_ms < 100

    @property
    def is_acceptable(self) -> bool:
        """是否可接受（<300ms）"""
        return self.duration_ms < 300


class InteractionPerformanceMonitor(QObject):
    """交互性能监控器"""

    # 信号
    slow_interaction_detected = Signal(str, float)  # 动作名, 耗时(ms)
    performance_degraded = Signal(float)  # 平均响应时间

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 指标历史（保留最近100个）
        self.metrics_history: deque[InteractionMetrics] = deque(maxlen=100)

        # 性能阈值
        self.slow_threshold_ms = 300  # 慢交互阈值
        self.degraded_threshold_ms = 150  # 性能降级阈值

        # 统计数据
        self.total_interactions = 0
        self.slow_interactions = 0

        logger.info("交互性能监控器初始化完成")

    def track_interaction(self, action: str, duration_ms: float, success: bool = True):
        """追踪交互

        Args:
            action: 动作名称
            duration_ms: 耗时（毫秒）
            success: 是否成功
        """
        now = time.time()
        metrics = InteractionMetrics(
            action=action,
            start_time=now - duration_ms / 1000,
            end_time=now,
            duration_ms=duration_ms,
            success=success,
        )

        self.metrics_history.append(metrics)
        self.total_interactions += 1

        # 检测慢交互
        if duration_ms > self.slow_threshold_ms:
            self.slow_interactions += 1
            self.slow_interaction_detected.emit(action, duration_ms)
            logger.warning(f"慢交互检测: {action} 耗时 {duration_ms:.1f}ms")

        # 检查性能降级
        avg_time = self.get_average_response_time()
        if avg_time > self.degraded_threshold_ms:
            self.performance_degraded.emit(avg_time)
            logger.warning(f"性能降级: 平均响应时间 {avg_time:.1f}ms")

    def get_average_response_time(self, recent_count: int = 10) -> float:
        """获取平均响应时间

        Args:
            recent_count: 最近N次交互

        Returns:
            平均耗时（毫秒）
        """
        if not self.metrics_history:
            return 0.0

        recent = list(self.metrics_history)[-recent_count:]
        return sum(m.duration_ms for m in recent) / len(recent)

    def get_slow_interaction_rate(self) -> float:
        """获取慢交互比率"""
        if self.total_interactions == 0:
            return 0.0

        return self.slow_interactions / self.total_interactions

    def get_performance_report(self) -> dict:
        """获取性能报告"""
        if not self.metrics_history:
            return {
                "total_interactions": 0,
                "average_time_ms": 0.0,
                "slow_rate": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
            }

        times = sorted([m.duration_ms for m in self.metrics_history])
        count = len(times)

        return {
            "total_interactions": self.total_interactions,
            "average_time_ms": sum(times) / count,
            "slow_rate": self.get_slow_interaction_rate(),
            "p50_ms": times[int(count * 0.5)],  # 中位数
            "p95_ms": times[int(count * 0.95)],  # 95%分位
            "p99_ms": times[int(count * 0.99)],  # 99%分位
        }


class DebounceHelper:
    """防抖动辅助类"""

    def __init__(self, delay_ms: int = 300):
        """
        Args:
            delay_ms: 防抖延迟（毫秒）
        """
        self.delay_ms = delay_ms
        self.timer: QTimer | None = None
        self.callback: Callable | None = None

    def debounce(self, callback: Callable):
        """防抖动执行

        Args:
            callback: 要执行的回调函数
        """
        if self.timer:
            self.timer.stop()

        self.callback = callback
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._execute)
        self.timer.start(self.delay_ms)

    def _execute(self):
        """执行回调"""
        if self.callback:
            self.callback()
            self.callback = None


class ThrottleHelper:
    """节流辅助类"""

    def __init__(self, interval_ms: int = 100):
        """
        Args:
            interval_ms: 节流间隔（毫秒）
        """
        self.interval_ms = interval_ms
        self.last_exec_time = 0.0
        self.pending_callback: Callable | None = None
        self.timer: QTimer | None = None

    def throttle(self, callback: Callable):
        """节流执行

        Args:
            callback: 要执行的回调函数
        """
        now = time.time() * 1000  # 转换为毫秒

        # 如果距离上次执行超过间隔，立即执行
        if now - self.last_exec_time >= self.interval_ms:
            callback()
            self.last_exec_time = now
            return

        # 否则，缓存回调并在间隔后执行
        self.pending_callback = callback

        if not self.timer or not self.timer.isActive():
            delay = int(self.interval_ms - (now - self.last_exec_time))
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self._execute_pending)
            self.timer.start(delay)

    def _execute_pending(self):
        """执行待处理的回调"""
        if self.pending_callback:
            self.pending_callback()
            self.last_exec_time = time.time() * 1000
            self.pending_callback = None


class BatchUpdateHelper:
    """批量更新辅助类"""

    def __init__(self, batch_size: int = 10, delay_ms: int = 16):
        """
        Args:
            batch_size: 批量大小
            delay_ms: 延迟时间（默认16ms = 60fps）
        """
        self.batch_size = batch_size
        self.delay_ms = delay_ms
        self.pending_updates: list[Callable] = []
        self.timer: QTimer | None = None

    def add_update(self, update_func: Callable):
        """添加更新

        Args:
            update_func: 更新函数
        """
        self.pending_updates.append(update_func)

        # 达到批量大小，立即执行
        if len(self.pending_updates) >= self.batch_size:
            self.flush()
            return

        # 否则，延迟执行
        if not self.timer or not self.timer.isActive():
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.flush)
            self.timer.start(self.delay_ms)

    def flush(self):
        """立即执行所有待处理的更新"""
        if not self.pending_updates:
            return

        logger.debug(f"批量执行 {len(self.pending_updates)} 个更新")

        for update_func in self.pending_updates:
            try:
                update_func()
            except Exception as e:
                logger.error(f"批量更新失败: {e}")

        self.pending_updates.clear()


class LazyWidgetLoader:
    """懒加载控件"""

    def __init__(self):
        self.loaded_widgets: dict[str, QWidget] = {}
        self.factories: dict[str, Callable[[], QWidget]] = {}

    def register(self, name: str, factory: Callable[[], QWidget]):
        """注册控件工厂

        Args:
            name: 控件名称
            factory: 控件工厂函数
        """
        self.factories[name] = factory
        logger.debug(f"注册懒加载控件: {name}")

    def load(self, name: str) -> QWidget | None:
        """加载控件

        Args:
            name: 控件名称

        Returns:
            控件实例
        """
        # 如果已加载，直接返回
        if name in self.loaded_widgets:
            return self.loaded_widgets[name]

        # 如果有工厂，创建实例
        if name in self.factories:
            start_time = time.time()
            widget = self.factories[name]()
            elapsed = (time.time() - start_time) * 1000

            self.loaded_widgets[name] = widget
            logger.info(f"懒加载控件 {name} 完成 ({elapsed:.1f}ms)")

            return widget

        logger.warning(f"未找到控件: {name}")
        return None

    def is_loaded(self, name: str) -> bool:
        """检查控件是否已加载"""
        return name in self.loaded_widgets

    def unload(self, name: str):
        """卸载控件"""
        if name in self.loaded_widgets:
            widget = self.loaded_widgets.pop(name)
            widget.deleteLater()
            logger.debug(f"卸载控件: {name}")


class InteractionOptimizer:
    """交互优化器（便捷访问类）"""

    _monitor: InteractionPerformanceMonitor | None = None
    _lazy_loader: LazyWidgetLoader | None = None

    @classmethod
    def get_monitor(cls) -> InteractionPerformanceMonitor:
        """获取性能监控器"""
        if cls._monitor is None:
            cls._monitor = InteractionPerformanceMonitor()
        return cls._monitor

    @classmethod
    def get_lazy_loader(cls) -> LazyWidgetLoader:
        """获取懒加载器"""
        if cls._lazy_loader is None:
            cls._lazy_loader = LazyWidgetLoader()
        return cls._lazy_loader

    @staticmethod
    def measure_interaction(action: str):
        """装饰器：测量交互性能

        Usage:
            @InteractionOptimizer.measure_interaction("button_click")
            def on_button_clicked(self):
                # 处理点击
                pass
        """

        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    success = False
                    raise e
                finally:
                    elapsed = (time.time() - start) * 1000
                    InteractionOptimizer.get_monitor().track_interaction(
                        action, elapsed, success
                    )

            return wrapper

        return decorator
