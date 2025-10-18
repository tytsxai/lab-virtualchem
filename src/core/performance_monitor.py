"""
性能监控系统
提供应用程序性能监控、内存使用跟踪和优化建议
"""

import gc
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime, timedelta
from typing import Any

try:
    import psutil
except ImportError:
    # psutil 不可用时的占位符
    class psutil:  # type: ignore
        @staticmethod
        def cpu_percent(_interval: float | None = None) -> float:
            return 0.0

        @staticmethod
        def virtual_memory() -> Any:
            class MemoryInfo:
                percent = 0.0
                available = 0
                total = 0

            return MemoryInfo()

        @staticmethod
        def disk_usage(_path: str) -> Any:
            class DiskInfo:
                percent = 0.0
                free = 0
                total = 0

            return DiskInfo()


from PySide6.QtCore import QObject, QTimer, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    fps: float
    frame_time_ms: float
    physics_update_time_ms: float
    particle_count: int
    active_items: int
    # 新增指标
    gpu_usage: float = 0.0
    network_io_bytes: int = 0
    disk_io_bytes: int = 0
    thread_count: int = 0
    event_queue_size: int = 0
    memory_fragmentation: float = 0.0
    # 元数据
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass
class OptimizationSuggestion:
    """优化建议数据类"""

    category: str
    priority: str  # low, medium, high, critical
    title: str
    description: str
    impact: str
    effort: str
    # 新增字段
    auto_fixable: bool = False
    estimated_improvement: float = 0.0  # 预期改善百分比
    tags: list[str] = dataclass_field(default_factory=list)
    metadata: dict[str, Any] = dataclass_field(default_factory=dict)


class PerformanceMonitor(QObject):
    """性能监控器"""

    # 信号
    metrics_updated = Signal(PerformanceMetrics)
    performance_warning = Signal(str, str)  # category, message
    optimization_suggested = Signal(OptimizationSuggestion)
    threshold_exceeded = Signal(str, float, float)  # metric_name, current_value, threshold

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # 监控设置
        self.monitoring_enabled = True
        self.update_interval = 1000  # 1秒
        self.max_history = 300  # 5分钟历史
        self.adaptive_sampling = True
        self.sampling_factor = 1.0

        # 性能数据
        self.metrics_history: deque[PerformanceMetrics] = deque(maxlen=self.max_history)
        self.current_metrics: PerformanceMetrics | None = None
        self._lock = threading.Lock()

        # 性能阈值
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "fps": 30.0,
            "frame_time_ms": 33.33,
            "gpu_usage": 90.0,
            "memory_fragmentation": 50.0,
        }

        # 统计信息
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.physics_update_times: deque[float] = deque(maxlen=60)
        self.particle_counts: deque[int] = deque(maxlen=60)
        self.active_item_counts: deque[int] = deque(maxlen=60)

        # 新增统计
        self.network_io_history: deque[int] = deque(maxlen=60)
        self.disk_io_history: deque[int] = deque(maxlen=60)
        self.gpu_usage_history: deque[float] = deque(maxlen=60)
        self.last_network_io = 0
        self.last_disk_io = 0

        # 定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_metrics)

        # 进程信息
        self.process = psutil.Process(os.getpid())

        # 性能回调
        self.performance_callbacks: list[Callable[[PerformanceMetrics], None]] = []

        logger.info("性能监控器初始化完成")

    def start_monitoring(self) -> None:
        """开始监控"""
        if self.monitoring_enabled:
            self.monitor_timer.start(self.update_interval)
            logger.info("性能监控已启动")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitor_timer.stop()
        logger.info("性能监控已停止")

    def update_metrics(self) -> None:
        """更新性能指标"""
        try:
            # 获取系统资源使用情况
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            memory_mb = memory_info.rss / 1024 / 1024

            # 计算FPS
            current_time = time.time()
            fps = self._calculate_fps(current_time)
            frame_time_ms = 1000.0 / fps if fps > 0 else 0

            # 计算物理更新时间
            physics_update_time_ms = self._calculate_physics_update_time()

            # 获取粒子数量
            particle_count = self._get_particle_count()

            # 获取活跃物品数量
            active_items = self._get_active_item_count()

            # 获取新增指标
            gpu_usage = self._get_gpu_usage()
            network_io_bytes = self._get_network_io()
            disk_io_bytes = self._get_disk_io()
            thread_count = self.process.num_threads()
            event_queue_size = self._get_event_queue_size()
            memory_fragmentation = self._calculate_memory_fragmentation()

            # 创建性能指标
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                fps=fps,
                frame_time_ms=frame_time_ms,
                physics_update_time_ms=physics_update_time_ms,
                particle_count=particle_count,
                active_items=active_items,
                gpu_usage=gpu_usage,
                network_io_bytes=network_io_bytes,
                disk_io_bytes=disk_io_bytes,
                thread_count=thread_count,
                event_queue_size=event_queue_size,
                memory_fragmentation=memory_fragmentation,
                metadata={
                    "sampling_factor": self.sampling_factor,
                    "adaptive_enabled": self.adaptive_sampling,
                },
            )

            # 更新历史记录
            self.metrics_history.append(metrics)
            self.current_metrics = metrics

            # 自适应采样调整
            if self.adaptive_sampling:
                self._adjust_sampling_rate(metrics)

            # 检查性能警告
            self._check_performance_warnings(metrics)

            # 生成优化建议
            self._generate_optimization_suggestions(metrics)

            # 执行性能回调
            for callback in self.performance_callbacks:
                try:
                    callback(metrics)
                except Exception as e:
                    logger.error(f"性能回调执行失败: {e}")

            # 发送信号
            self.metrics_updated.emit(metrics)

        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")

    def _calculate_fps(self, current_time: float) -> float:
        """计算FPS"""
        if self.frame_count == 0:
            self.last_frame_time = current_time
            return 0.0

        time_diff = current_time - self.last_frame_time
        if time_diff > 0:
            fps = self.frame_count / time_diff
            self.frame_count = 0
            self.last_frame_time = current_time
            return fps

        return 0.0

    def _calculate_physics_update_time(self) -> float:
        """计算物理更新时间"""
        if self.physics_update_times:
            return sum(self.physics_update_times) / len(self.physics_update_times)
        return 0.0

    def _get_particle_count(self) -> int:
        """获取粒子数量"""
        if self.particle_counts:
            return sum(self.particle_counts) // len(self.particle_counts)
        return 0

    def _get_active_item_count(self) -> int:
        """获取活跃物品数量"""
        if self.active_item_counts:
            return sum(self.active_item_counts) // len(self.active_item_counts)
        return 0

    def record_frame(self) -> None:
        """记录帧"""
        self.frame_count += 1

    def record_physics_update(self, update_time_ms: float) -> None:
        """记录物理更新时间"""
        self.physics_update_times.append(update_time_ms)

    def record_particle_count(self, count: int) -> None:
        """记录粒子数量"""
        self.particle_counts.append(count)

    def record_active_items(self, count: int) -> None:
        """记录活跃物品数量"""
        self.active_item_counts.append(count)

    def _check_performance_warnings(self, metrics: PerformanceMetrics) -> None:
        """检查性能警告"""
        # CPU使用率警告
        if metrics.cpu_percent > self.thresholds["cpu_percent"]:
            self.performance_warning.emit("cpu", f"CPU使用率过高: {metrics.cpu_percent:.1f}%")

        # 内存使用率警告
        if metrics.memory_percent > self.thresholds["memory_percent"]:
            self.performance_warning.emit("memory", f"内存使用率过高: {metrics.memory_percent:.1f}%")

        # FPS警告
        if metrics.fps < self.thresholds["fps"] and metrics.fps > 0:
            self.performance_warning.emit("fps", f"帧率过低: {metrics.fps:.1f} FPS")

        # 帧时间警告
        if metrics.frame_time_ms > self.thresholds["frame_time_ms"]:
            self.performance_warning.emit("frame_time", f"帧时间过长: {metrics.frame_time_ms:.1f}ms")

    def _generate_optimization_suggestions(self, metrics: PerformanceMetrics) -> None:
        """生成优化建议"""
        suggestions = []

        # CPU优化建议
        if metrics.cpu_percent > 70:
            suggestions.append(
                OptimizationSuggestion(
                    category="cpu",
                    priority="high" if metrics.cpu_percent > 85 else "medium",
                    title="降低CPU使用率",
                    description="减少物理更新频率或优化碰撞检测算法",
                    impact="high",
                    effort="medium",
                )
            )

        # 内存优化建议
        if metrics.memory_percent > 75:
            suggestions.append(
                OptimizationSuggestion(
                    category="memory",
                    priority="high" if metrics.memory_percent > 90 else "medium",
                    title="优化内存使用",
                    description="清理未使用的粒子效果和缓存数据",
                    impact="high",
                    effort="low",
                )
            )

        # FPS优化建议
        if metrics.fps < 45 and metrics.fps > 0:
            suggestions.append(
                OptimizationSuggestion(
                    category="fps",
                    priority="high" if metrics.fps < 30 else "medium",
                    title="提高帧率",
                    description="减少粒子效果数量或优化渲染性能",
                    impact="high",
                    effort="medium",
                )
            )

        # 粒子优化建议
        if metrics.particle_count > 500:
            suggestions.append(
                OptimizationSuggestion(
                    category="particles",
                    priority="medium",
                    title="减少粒子数量",
                    description="限制同时显示的粒子效果数量",
                    impact="medium",
                    effort="low",
                )
            )

        # 物理优化建议
        if metrics.physics_update_time_ms > 16:
            suggestions.append(
                OptimizationSuggestion(
                    category="physics",
                    priority="medium",
                    title="优化物理计算",
                    description="使用空间分割或简化碰撞检测",
                    impact="medium",
                    effort="high",
                )
            )

        # 发送优化建议
        for suggestion in suggestions:
            self.optimization_suggested.emit(suggestion)

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        if not self.current_metrics:
            return {}

        # 计算平均值
        if self.metrics_history:
            avg_cpu = sum(m.cpu_percent for m in self.metrics_history) / len(self.metrics_history)
            avg_memory = sum(m.memory_percent for m in self.metrics_history) / len(self.metrics_history)
            avg_fps = sum(m.fps for m in self.metrics_history if m.fps > 0) / max(
                1, sum(1 for m in self.metrics_history if m.fps > 0)
            )
        else:
            avg_cpu = avg_memory = avg_fps = 0

        return {
            "current": {
                "cpu_percent": self.current_metrics.cpu_percent,
                "memory_percent": self.current_metrics.memory_percent,
                "memory_mb": self.current_metrics.memory_mb,
                "fps": self.current_metrics.fps,
                "frame_time_ms": self.current_metrics.frame_time_ms,
                "physics_update_time_ms": self.current_metrics.physics_update_time_ms,
                "particle_count": self.current_metrics.particle_count,
                "active_items": self.current_metrics.active_items,
            },
            "average": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "fps": avg_fps,
            },
            "history_count": len(self.metrics_history),
            "monitoring_enabled": self.monitoring_enabled,
        }

    def get_optimization_recommendations(self) -> list[OptimizationSuggestion]:
        """获取优化建议"""
        if not self.current_metrics:
            return []

        recommendations = []

        # 基于当前性能生成建议
        if self.current_metrics.cpu_percent > 80:
            recommendations.append(
                OptimizationSuggestion(
                    category="cpu",
                    priority="critical",
                    title="紧急CPU优化",
                    description="立即减少物理计算负载",
                    impact="critical",
                    effort="low",
                )
            )

        if self.current_metrics.memory_percent > 90:
            recommendations.append(
                OptimizationSuggestion(
                    category="memory",
                    priority="critical",
                    title="紧急内存清理",
                    description="立即执行垃圾回收和缓存清理",
                    impact="critical",
                    effort="low",
                )
            )

        if self.current_metrics.fps < 20 and self.current_metrics.fps > 0:
            recommendations.append(
                OptimizationSuggestion(
                    category="fps",
                    priority="critical",
                    title="紧急帧率优化",
                    description="立即减少渲染负载",
                    impact="critical",
                    effort="low",
                )
            )

        return recommendations

    def force_garbage_collection(self) -> None:
        """强制垃圾回收"""
        try:
            collected = gc.collect()
            logger.info(f"垃圾回收完成，清理了 {collected} 个对象")
        except Exception as e:
            logger.error(f"垃圾回收失败: {e}")

    def clear_caches(self) -> None:
        """清理缓存"""
        try:
            # 清理性能历史记录
            self.metrics_history.clear()
            self.physics_update_times.clear()
            self.particle_counts.clear()
            self.active_item_counts.clear()

            logger.info("缓存清理完成")
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")

    def set_thresholds(
        self,
        cpu_threshold: float | None = None,
        memory_threshold: float | None = None,
        fps_threshold: float | None = None,
        frame_time_threshold: float | None = None,
    ) -> None:
        """设置性能阈值"""
        if cpu_threshold is not None:
            self.thresholds["cpu_percent"] = cpu_threshold
        if memory_threshold is not None:
            self.thresholds["memory_percent"] = memory_threshold
        if fps_threshold is not None:
            self.thresholds["fps"] = fps_threshold
        if frame_time_threshold is not None:
            self.thresholds["frame_time_ms"] = frame_time_threshold

        logger.info(
            f"性能阈值已更新: CPU={self.thresholds['cpu_percent']}%, Memory={self.thresholds['memory_percent']}%, FPS={self.thresholds['fps']}"
        )

    def enable_monitoring(self, enabled: bool) -> None:
        """启用/禁用监控"""
        self.monitoring_enabled = enabled
        if enabled:
            self.start_monitoring()
        else:
            self.stop_monitoring()

        logger.info(f"性能监控{'启用' if enabled else '禁用'}")

    def _get_gpu_usage(self) -> float:
        """获取GPU使用率"""
        try:
            # 尝试使用nvidia-ml-py或其他GPU监控库
            import GPUtil  # type: ignore

            gpus = GPUtil.getGPUs()
            if gpus:
                return float(gpus[0].load * 100)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"获取GPU使用率失败: {e}")

        return 0.0

    def _get_network_io(self) -> int:
        """获取网络IO字节数"""
        try:
            net_io = self.process.io_counters()
            current_network_io = net_io.bytes_sent + net_io.bytes_recv
            network_io_diff = current_network_io - self.last_network_io
            self.last_network_io = current_network_io
            self.network_io_history.append(network_io_diff)
            return int(network_io_diff)
        except Exception as e:
            logger.debug(f"获取网络IO失败: {e}")
            return 0

    def _get_disk_io(self) -> int:
        """获取磁盘IO字节数"""
        try:
            disk_io = self.process.io_counters()
            current_disk_io = disk_io.read_bytes + disk_io.write_bytes
            disk_io_diff = current_disk_io - self.last_disk_io
            self.last_disk_io = current_disk_io
            self.disk_io_history.append(disk_io_diff)
            return int(disk_io_diff)
        except Exception as e:
            logger.debug(f"获取磁盘IO失败: {e}")
            return 0

    def _get_event_queue_size(self) -> int:
        """获取Qt事件队列大小"""
        try:
            from PySide6.QtCore import QCoreApplication

            app = QCoreApplication.instance()
            if app:
                return app.eventDispatcher().remainingTime(0) if hasattr(app.eventDispatcher(), "remainingTime") else 0
        except Exception as e:
            logger.debug(f"获取事件队列大小失败: {e}")
        return 0

    def _calculate_memory_fragmentation(self) -> float:
        """计算内存碎片率"""
        try:
            memory_info = self.process.memory_info()
            # 简化的内存碎片计算
            fragmentation = (memory_info.vms - memory_info.rss) / memory_info.vms * 100
            return float(max(0, min(100, fragmentation)))
        except Exception as e:
            logger.debug(f"计算内存碎片率失败: {e}")
            return 0.0

    def _adjust_sampling_rate(self, metrics: PerformanceMetrics) -> None:
        """调整采样率"""
        try:
            # 根据性能状况调整采样频率
            if metrics.cpu_percent > 80 or metrics.memory_percent > 85:
                self.sampling_factor = min(2.0, self.sampling_factor * 1.1)
                self.update_interval = int(1000 * self.sampling_factor)
            elif metrics.cpu_percent < 30 and metrics.memory_percent < 50:
                self.sampling_factor = max(0.5, self.sampling_factor * 0.9)
                self.update_interval = int(1000 * self.sampling_factor)

            # 重启定时器以应用新的间隔
            if self.monitor_timer.isActive():
                self.monitor_timer.stop()
                self.monitor_timer.start(self.update_interval)
        except Exception as e:
            logger.error(f"调整采样率失败: {e}")

    def add_performance_callback(self, callback: Callable[[PerformanceMetrics], None]) -> None:
        """添加性能回调"""
        self.performance_callbacks.append(callback)

    def remove_performance_callback(self, callback: Callable[[PerformanceMetrics], None]) -> None:
        """移除性能回调"""
        if callback in self.performance_callbacks:
            self.performance_callbacks.remove(callback)

    def set_threshold(self, metric_name: str, threshold: float) -> None:
        """设置性能阈值"""
        if metric_name in self.thresholds:
            self.thresholds[metric_name] = threshold
            logger.info(f"阈值已更新: {metric_name} = {threshold}")

    def get_threshold(self, metric_name: str) -> float | None:
        """获取性能阈值"""
        return self.thresholds.get(metric_name)

    def get_performance_trends(self, duration_minutes: int = 5) -> dict[str, list[float]]:
        """获取性能趋势数据"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]

        if not recent_metrics:
            return {}

        trends = {}
        for field in ["cpu_percent", "memory_percent", "fps", "gpu_usage"]:
            trends[field] = [getattr(m, field) for m in recent_metrics]

        return trends

    def export_performance_data(self, file_path: str) -> bool:
        """导出性能数据"""
        try:
            import json

            data = {
                "metrics": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "cpu_percent": m.cpu_percent,
                        "memory_percent": m.memory_percent,
                        "memory_mb": m.memory_mb,
                        "fps": m.fps,
                        "frame_time_ms": m.frame_time_ms,
                        "physics_update_time_ms": m.physics_update_time_ms,
                        "particle_count": m.particle_count,
                        "active_items": m.active_items,
                        "gpu_usage": m.gpu_usage,
                        "network_io_bytes": m.network_io_bytes,
                        "disk_io_bytes": m.disk_io_bytes,
                        "thread_count": m.thread_count,
                        "event_queue_size": m.event_queue_size,
                        "memory_fragmentation": m.memory_fragmentation,
                    }
                    for m in self.metrics_history
                ],
                "thresholds": self.thresholds,
                "export_time": datetime.now().isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"性能数据已导出到: {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出性能数据失败: {e}")
            return False


# 全局性能监控器实例
_performance_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
