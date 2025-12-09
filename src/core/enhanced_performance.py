#!/usr/bin/env python3
"""
增强的性能优化系统
提供全面的性能监控、优化建议、资源管理等功能
"""

import functools
import gc
import logging
import os

try:
    import psutil
except ImportError:
    psutil = None
import threading
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """性能级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


class OptimizationStrategy(Enum):
    """优化策略"""
    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    NETWORK = "network"
    CACHE = "cache"
    LAZY_LOADING = "lazy_loading"
    BATCH_PROCESSING = "batch_processing"


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    cpu_usage: float
    memory_usage: float
    memory_available: float
    disk_usage: float
    network_io: Dict[str, float]
    gc_stats: Dict[str, int]
    thread_count: int
    process_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationMetrics:
    """操作指标"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    cpu_time: Optional[float] = None
    memory_delta: Optional[float] = None
    success: bool = False
    error_count: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    strategy: OptimizationStrategy
    description: str
    expected_improvement: str
    implementation_cost: str
    priority: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.operation_metrics: Dict[str, List[OperationMetrics]] = {}
        self.optimization_suggestions: List[OptimizationSuggestion] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()

        # 性能阈值
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'operation_duration': 5.0
        }

        # 启动内存追踪
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        logger.info("性能监控器初始化完成")

    def start_monitoring(self, interval: float = 5.0) -> None:
        """开始监控"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"性能监控已启动，间隔: {interval}秒")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("性能监控已停止")

    def _monitoring_loop(self, interval: float) -> None:
        """监控循环"""
        while self.monitoring_active:
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                self._analyze_performance(metrics)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"性能监控错误: {e}")
                time.sleep(interval)

    def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        if psutil is None:
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_usage=0.0,
                memory_usage=0.0,
                memory_available=0.0,
                disk_usage=0.0,
                network_io={},
                gc_stats={},
                thread_count=0,
                process_count=0
            )

        # CPU使用率
        cpu_usage = psutil.cpu_percent(interval=0.1)

        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        memory_available = memory.available / (1024**3)  # GB

        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100

        # 网络IO
        network_io = {}
        try:
            net_io = psutil.net_io_counters()
            network_io = {
                'bytes_sent': float(net_io.bytes_sent),
                'bytes_recv': float(net_io.bytes_recv),
                'packets_sent': float(net_io.packets_sent),
                'packets_recv': float(net_io.packets_recv)
            }
        except Exception:
            network_io = {
                'bytes_sent': 0.0,
                'bytes_recv': 0.0,
                'packets_sent': 0.0,
                'packets_recv': 0.0
            }

        # GC统计
        gc_stats = {
            'collections': gc.get_count()[0],
            'collected': gc.get_count()[1],
            'uncollectable': gc.get_count()[2]
        }

        # 线程和进程数
        thread_count = threading.active_count()
        process_count = len(psutil.pids())

        return PerformanceMetrics(
            timestamp=time.time(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_available=memory_available,
            disk_usage=disk_usage,
            network_io=network_io,
            gc_stats=gc_stats,
            thread_count=thread_count,
            process_count=process_count
        )

    def _store_metrics(self, metrics: PerformanceMetrics) -> None:
        """存储指标"""
        with self.lock:
            self.metrics_history.append(metrics)

            # 限制历史记录长度
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-500:]

    def _analyze_performance(self, metrics: PerformanceMetrics) -> None:
        """分析性能"""
        suggestions = []

        # CPU使用率分析
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            suggestions.append(OptimizationSuggestion(
                strategy=OptimizationStrategy.CPU,
                description=f"CPU使用率过高: {metrics.cpu_usage:.1f}%",
                expected_improvement="减少CPU密集型操作，使用异步处理",
                implementation_cost="中等",
                priority=1
            ))

        # 内存使用率分析
        if metrics.memory_usage > self.thresholds['memory_usage']:
            suggestions.append(OptimizationSuggestion(
                strategy=OptimizationStrategy.MEMORY,
                description=f"内存使用率过高: {metrics.memory_usage:.1f}%",
                expected_improvement="优化内存使用，清理无用对象",
                implementation_cost="低",
                priority=2
            ))

        # 磁盘使用率分析
        if metrics.disk_usage > self.thresholds['disk_usage']:
            suggestions.append(OptimizationSuggestion(
                strategy=OptimizationStrategy.IO,
                description=f"磁盘使用率过高: {metrics.disk_usage:.1f}%",
                expected_improvement="清理临时文件，优化存储",
                implementation_cost="低",
                priority=3
            ))

        # 更新建议
        with self.lock:
            self.optimization_suggestions.extend(suggestions)

            # 限制建议数量
            if len(self.optimization_suggestions) > 100:
                self.optimization_suggestions = self.optimization_suggestions[-50:]

    def record_operation(self, operation_name: str, metrics: OperationMetrics) -> None:
        """记录操作指标"""
        with self.lock:
            if operation_name not in self.operation_metrics:
                self.operation_metrics[operation_name] = []

            self.operation_metrics[operation_name].append(metrics)

            # 限制操作指标数量
            if len(self.operation_metrics[operation_name]) > 100:
                self.operation_metrics[operation_name] = self.operation_metrics[operation_name][-50:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self.lock:
            if not self.metrics_history:
                return {}

            recent_metrics = self.metrics_history[-10:] if len(self.metrics_history) >= 10 else self.metrics_history

            return {
                "cpu_usage": {
                    "current": recent_metrics[-1].cpu_usage,
                    "average": sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics),
                    "max": max(m.cpu_usage for m in recent_metrics)
                },
                "memory_usage": {
                    "current": recent_metrics[-1].memory_usage,
                    "average": sum(m.memory_usage for m in recent_metrics) / len(recent_metrics),
                    "max": max(m.memory_usage for m in recent_metrics)
                },
                "disk_usage": {
                    "current": recent_metrics[-1].disk_usage,
                    "average": sum(m.disk_usage for m in recent_metrics) / len(recent_metrics),
                    "max": max(m.disk_usage for m in recent_metrics)
                },
                "thread_count": recent_metrics[-1].thread_count,
                "process_count": recent_metrics[-1].process_count
            }

    def get_operation_stats(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """获取操作统计"""
        with self.lock:
            if operation_name not in self.operation_metrics:
                return None

            operations = self.operation_metrics[operation_name]
            if not operations:
                return None

            durations = [op.duration for op in operations if op.duration is not None]
            success_count = sum(1 for op in operations if op.success)

            return {
                "total_operations": len(operations),
                "successful_operations": success_count,
                "success_rate": success_count / len(operations) if operations else 0,
                "average_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0
            }

    def get_optimization_suggestions(self) -> List[OptimizationSuggestion]:
        """获取优化建议"""
        with self.lock:
            return self.optimization_suggestions.copy()


class PerformanceOptimizer:
    """性能优化器"""

    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.optimization_cache: Dict[str, Any] = {}
        self.optimization_history: List[Dict[str, Any]] = []
        self.lock = threading.RLock()

        logger.info("性能优化器初始化完成")

    def optimize_memory(self) -> Dict[str, Any]:
        """优化内存"""
        optimization_result = {
            "strategy": "memory",
            "timestamp": time.time(),
            "actions_taken": [],
            "improvement": {}
        }

        try:
            # 强制垃圾回收
            before_gc = gc.get_count()
            gc.collect()
            after_gc = gc.get_count()

            optimization_result["actions_taken"].append("强制垃圾回收")
            optimization_result["improvement"]["gc_collections"] = before_gc[0] - after_gc[0]

            # 清理优化缓存
            with self.lock:
                cache_size_before = len(self.optimization_cache)
                self.optimization_cache.clear()
                optimization_result["actions_taken"].append("清理优化缓存")
                optimization_result["improvement"]["cache_cleared"] = cache_size_before

            logger.info("内存优化完成")

        except Exception as e:
            logger.error(f"内存优化失败: {e}")
            optimization_result["error"] = str(e)

        return optimization_result

    def optimize_cpu(self) -> Dict[str, Any]:
        """优化CPU"""
        optimization_result = {
            "strategy": "cpu",
            "timestamp": time.time(),
            "actions_taken": [],
            "improvement": {}
        }

        try:
            # 调整GC阈值
            gc.set_threshold(700, 10, 10)
            optimization_result["actions_taken"].append("调整GC阈值")

            # 如果psutil可用，尝试进程优先级调整
            if psutil is not None:
                try:
                    current_process = psutil.Process()
                    current_process.nice(psutil.HIGH_PRIORITY_CLASS)
                    optimization_result["actions_taken"].append("提高进程优先级")
                except Exception:
                    pass

            # 设置进程优先级（已在上面处理）
            pass

            logger.info("CPU优化完成")

        except Exception as e:
            logger.error(f"CPU优化失败: {e}")
            optimization_result["error"] = str(e)

        return optimization_result

    def optimize_io(self) -> Dict[str, Any]:
        """优化IO"""
        optimization_result = {
            "strategy": "io",
            "timestamp": time.time(),
            "actions_taken": [],
            "improvement": {}
        }

        try:
            # 清理临时文件
            temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "temp")
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                optimization_result["actions_taken"].append("清理临时文件")

            logger.info("IO优化完成")

        except Exception as e:
            logger.error(f"IO优化失败: {e}")
            optimization_result["error"] = str(e)

        return optimization_result

    def auto_optimize(self) -> List[Dict[str, Any]]:
        """自动优化"""
        results = []

        # 获取性能摘要
        summary = self.monitor.get_performance_summary()
        if not summary:
            return results

        # 根据性能指标决定优化策略
        if summary.get("cpu_usage", {}).get("current", 0) > 80:
            results.append(self.optimize_cpu())

        if summary.get("memory_usage", {}).get("current", 0) > 85:
            results.append(self.optimize_memory())

        if summary.get("disk_usage", {}).get("current", 0) > 90:
            results.append(self.optimize_io())

        # 记录优化历史
        with self.lock:
            self.optimization_history.extend(results)
            if len(self.optimization_history) > 100:
                self.optimization_history = self.optimization_history[-50:]

        return results


class EnhancedPerformanceManager:
    """增强性能管理器"""

    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.optimizer = PerformanceOptimizer(self.monitor)
        self.operation_timers: Dict[str, float] = {}
        self.lock = threading.RLock()

        # 启动监控
        self.monitor.start_monitoring()

        logger.info("增强性能管理器初始化完成")

    def start_operation_timer(self, operation_name: str) -> float:
        """开始操作计时"""
        start_time = time.time()
        with self.lock:
            self.operation_timers[operation_name] = start_time
        return start_time

    def end_operation_timer(self, operation_name: str, start_time: float, success: bool = True) -> OperationMetrics:
        """结束操作计时"""
        end_time = time.time()
        duration = end_time - start_time

        # 收集性能数据
        try:
            if psutil is not None:
                process = psutil.Process()
                cpu_times = process.cpu_times()
                cpu_time = cpu_times.user + cpu_times.system

                memory_info = process.memory_info()
                memory_delta = memory_info.rss / (1024**2)  # MB
            else:
                cpu_time = None
                memory_delta = None
        except Exception:
            cpu_time = None
            memory_delta = None

        # 创建操作指标
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            cpu_time=cpu_time,
            memory_delta=memory_delta,
            success=success
        )

        # 记录到监控器
        self.monitor.record_operation(operation_name, metrics)

        # 清理计时器
        with self.lock:
            if operation_name in self.operation_timers:
                del self.operation_timers[operation_name]

        return metrics

    def get_performance_report(self) -> str:
        """获取性能报告"""
        report = []
        report.append("=" * 80)
        report.append("VirtualChemLab 性能报告")
        report.append("=" * 80)
        report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 系统性能摘要
        summary = self.monitor.get_performance_summary()
        if summary:
            report.append("## 系统性能摘要")
            report.append(f"CPU使用率: {summary['cpu_usage']['current']:.1f}%")
            report.append(f"内存使用率: {summary['memory_usage']['current']:.1f}%")
            report.append(f"磁盘使用率: {summary['disk_usage']['current']:.1f}%")
            report.append(f"线程数: {summary['thread_count']}")
            report.append(f"进程数: {summary['process_count']}")
            report.append("")

        # 操作性能统计
        operation_stats = {}
        for operation_name in self.monitor.operation_metrics.keys():
            stats = self.monitor.get_operation_stats(operation_name)
            if stats:
                operation_stats[operation_name] = stats

        if operation_stats:
            report.append("## 操作性能统计")
            for operation_name, stats in operation_stats.items():
                report.append(f"### {operation_name}")
                report.append(f"总操作数: {stats['total_operations']}")
                report.append(f"成功率: {stats['success_rate']:.1%}")
                report.append(f"平均执行时间: {stats['average_duration']:.3f}秒")
                report.append(f"最大执行时间: {stats['max_duration']:.3f}秒")
                report.append("")

        # 优化建议
        suggestions = self.monitor.get_optimization_suggestions()
        if suggestions:
            report.append("## 优化建议")
            for suggestion in suggestions[-10:]:  # 最近10个建议
                report.append(f"- **{suggestion.strategy.value}**: {suggestion.description}")
                report.append(f"  预期改进: {suggestion.expected_improvement}")
                report.append(f"  实施成本: {suggestion.implementation_cost}")
                report.append(f"  优先级: {suggestion.priority}")
                report.append("")

        return "\n".join(report)

    def cleanup(self) -> None:
        """清理资源"""
        self.monitor.stop_monitoring()
        logger.info("性能管理器清理完成")


# 全局实例
performance_manager = EnhancedPerformanceManager()


def performance_monitor(operation_name: Optional[str] = None):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = performance_manager.start_operation_timer(name)
            try:
                result = func(*args, **kwargs)
                performance_manager.end_operation_timer(name, start_time, success=True)
                return result
            except Exception:
                performance_manager.end_operation_timer(name, start_time, success=False)
                raise

        return wrapper
    return decorator


@contextmanager
def performance_context(operation_name: str):
    """性能上下文管理器"""
    start_time = performance_manager.start_operation_timer(operation_name)
    try:
        yield
        performance_manager.end_operation_timer(operation_name, start_time, success=True)
    except Exception:
        performance_manager.end_operation_timer(operation_name, start_time, success=False)
        raise


def get_performance_manager() -> EnhancedPerformanceManager:
    """获取性能管理器实例"""
    return performance_manager
