"""性能优化引擎"""

import gc
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil


class OptimizationLevel(Enum):
    """优化级别"""
    NONE = "none"
    BASIC = "basic"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"

@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: float
    threshold: Optional[float] = None

@dataclass
class OptimizationRule:
    """优化规则"""
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[], None]
    priority: int = 0
    enabled: bool = True

class PerformanceOptimizer:
    """性能优化器"""

    def __init__(self):
        """初始化优化器"""
        self.metrics: Dict[str, List[PerformanceMetric]] = {}
        self.rules: List[OptimizationRule] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.optimization_level = OptimizationLevel.BASIC
        self.lock = threading.Lock()

        # 性能阈值
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 1000.0,  # 毫秒
        }

        # 初始化优化规则
        self._initialize_rules()

    def _initialize_rules(self):
        """初始化优化规则"""
        # CPU优化规则
        self.add_rule(OptimizationRule(
            name="high_cpu_usage",
            condition=lambda metrics: metrics.get('cpu_usage', 0) > self.thresholds['cpu_usage'],
            action=self._optimize_cpu,
            priority=1
        ))

        # 内存优化规则
        self.add_rule(OptimizationRule(
            name="high_memory_usage",
            condition=lambda metrics: metrics.get('memory_usage', 0) > self.thresholds['memory_usage'],
            action=self._optimize_memory,
            priority=2
        ))

        # 磁盘优化规则
        self.add_rule(OptimizationRule(
            name="high_disk_usage",
            condition=lambda metrics: metrics.get('disk_usage', 0) > self.thresholds['disk_usage'],
            action=self._optimize_disk,
            priority=3
        ))

        # 响应时间优化规则
        self.add_rule(OptimizationRule(
            name="slow_response",
            condition=lambda metrics: metrics.get('response_time', 0) > self.thresholds['response_time'],
            action=self._optimize_response_time,
            priority=4
        ))

    def add_rule(self, rule: OptimizationRule):
        """添加优化规则"""
        with self.lock:
            self.rules.append(rule)
            self.rules.sort(key=lambda r: r.priority)

    def remove_rule(self, name: str):
        """移除优化规则"""
        with self.lock:
            self.rules = [r for r in self.rules if r.name != name]

    def start_monitoring(self, interval: float = 1.0):
        """开始性能监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止性能监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集性能指标
                metrics = self._collect_metrics()

                # 存储指标
                self._store_metrics(metrics)

                # 检查优化规则
                self._check_optimization_rules(metrics)

                time.sleep(interval)

            except Exception as e:
                print(f"性能监控错误: {e}")
                time.sleep(interval)

    def _collect_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        metrics = {}

        try:
            # CPU使用率
            metrics['cpu_usage'] = psutil.cpu_percent(interval=0.1)

            # 内存使用率
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = memory.percent
            metrics['memory_available'] = memory.available

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            metrics['disk_usage'] = (disk.used / disk.total) * 100
            metrics['disk_free'] = disk.free

            # 进程信息
            process = psutil.Process()
            metrics['process_cpu'] = process.cpu_percent()
            metrics['process_memory'] = process.memory_info().rss

            # 系统负载
            if hasattr(psutil, 'getloadavg'):
                metrics['load_avg'] = psutil.getloadavg()[0]

            # 网络统计
            net_io = psutil.net_io_counters()
            metrics['network_sent'] = net_io.bytes_sent
            metrics['network_recv'] = net_io.bytes_recv

        except Exception as e:
            print(f"收集性能指标错误: {e}")

        return metrics

    def _store_metrics(self, metrics: Dict[str, Any]):
        """存储性能指标"""
        timestamp = time.time()

        with self.lock:
            for name, value in metrics.items():
                if name not in self.metrics:
                    self.metrics[name] = []

                metric = PerformanceMetric(
                    name=name,
                    value=value,
                    unit=self._get_unit(name),
                    timestamp=timestamp,
                    threshold=self.thresholds.get(name)
                )

                self.metrics[name].append(metric)

                # 保持最近1000个指标
                if len(self.metrics[name]) > 1000:
                    self.metrics[name] = self.metrics[name][-1000:]

    def _get_unit(self, metric_name: str) -> str:
        """获取指标单位"""
        units = {
            'cpu_usage': '%',
            'memory_usage': '%',
            'disk_usage': '%',
            'response_time': 'ms',
            'memory_available': 'bytes',
            'disk_free': 'bytes',
            'process_memory': 'bytes',
            'network_sent': 'bytes',
            'network_recv': 'bytes',
        }
        return units.get(metric_name, '')

    def _check_optimization_rules(self, metrics: Dict[str, Any]):
        """检查优化规则"""
        with self.lock:
            for rule in self.rules:
                if not rule.enabled:
                    continue

                try:
                    if rule.condition(metrics):
                        rule.action()
                except Exception as e:
                    print(f"优化规则执行错误 {rule.name}: {e}")

    def _optimize_cpu(self):
        """优化CPU使用"""
        if self.optimization_level == OptimizationLevel.NONE:
            return

        # 基础优化
        if self.optimization_level >= OptimizationLevel.BASIC:
            # 强制垃圾回收
            gc.collect()

        # 激进优化
        if self.optimization_level >= OptimizationLevel.AGGRESSIVE:
            # 降低进程优先级
            try:
                process = psutil.Process()
                process.nice(10)  # 降低优先级
            except Exception:
                pass

        # 最大优化
        if self.optimization_level >= OptimizationLevel.MAXIMUM:
            # 暂停非关键线程
            self._pause_non_critical_threads()

    def _optimize_memory(self):
        """优化内存使用"""
        if self.optimization_level == OptimizationLevel.NONE:
            return

        # 基础优化
        if self.optimization_level >= OptimizationLevel.BASIC:
            # 强制垃圾回收
            gc.collect()

        # 激进优化
        if self.optimization_level >= OptimizationLevel.AGGRESSIVE:
            # 清理缓存
            self._clear_caches()

        # 最大优化
        if self.optimization_level >= OptimizationLevel.MAXIMUM:
            # 卸载非关键模块
            self._unload_non_critical_modules()

    def _optimize_disk(self):
        """优化磁盘使用"""
        if self.optimization_level == OptimizationLevel.NONE:
            return

        # 基础优化
        if self.optimization_level >= OptimizationLevel.BASIC:
            # 清理临时文件
            self._cleanup_temp_files()

        # 激进优化
        if self.optimization_level >= OptimizationLevel.AGGRESSIVE:
            # 压缩日志文件
            self._compress_logs()

        # 最大优化
        if self.optimization_level >= OptimizationLevel.MAXIMUM:
            # 清理缓存文件
            self._cleanup_cache_files()

    def _optimize_response_time(self):
        """优化响应时间"""
        if self.optimization_level == OptimizationLevel.NONE:
            return

        # 基础优化
        if self.optimization_level >= OptimizationLevel.BASIC:
            # 预热缓存
            self._warmup_caches()

        # 激进优化
        if self.optimization_level >= OptimizationLevel.AGGRESSIVE:
            # 优化数据库连接
            self._optimize_database_connections()

        # 最大优化
        if self.optimization_level >= OptimizationLevel.MAXIMUM:
            # 启用压缩
            self._enable_compression()

    def _pause_non_critical_threads(self):
        """暂停非关键线程"""
        # 实现线程暂停逻辑
        pass

    def _clear_caches(self):
        """清理缓存"""
        # 实现缓存清理逻辑
        pass

    def _unload_non_critical_modules(self):
        """卸载非关键模块"""
        # 实现模块卸载逻辑
        pass

    def _cleanup_temp_files(self):
        """清理临时文件"""
        # 实现临时文件清理逻辑
        pass

    def _compress_logs(self):
        """压缩日志文件"""
        # 实现日志压缩逻辑
        pass

    def _cleanup_cache_files(self):
        """清理缓存文件"""
        # 实现缓存文件清理逻辑
        pass

    def _warmup_caches(self):
        """预热缓存"""
        # 实现缓存预热逻辑
        pass

    def _optimize_database_connections(self):
        """优化数据库连接"""
        # 实现数据库连接优化逻辑
        pass

    def _enable_compression(self):
        """启用压缩"""
        # 实现压缩启用逻辑
        pass

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self.lock:
            summary = {
                'monitoring': self.is_monitoring,
                'optimization_level': self.optimization_level.value,
                'rules_count': len(self.rules),
                'metrics_count': sum(len(metrics) for metrics in self.metrics.values()),
                'current_metrics': {}
            }

            # 获取当前指标
            current_metrics = self._collect_metrics()
            for name, value in current_metrics.items():
                summary['current_metrics'][name] = {
                    'value': value,
                    'unit': self._get_unit(name),
                    'threshold': self.thresholds.get(name)
                }

            return summary

    def set_optimization_level(self, level: OptimizationLevel):
        """设置优化级别"""
        self.optimization_level = level

    def set_threshold(self, metric_name: str, threshold: float):
        """设置性能阈值"""
        self.thresholds[metric_name] = threshold

    def get_metrics_history(self, metric_name: str, limit: int = 100) -> List[PerformanceMetric]:
        """获取指标历史"""
        with self.lock:
            if metric_name not in self.metrics:
                return []

            return self.metrics[metric_name][-limit:]

    def clear_metrics(self):
        """清空指标"""
        with self.lock:
            self.metrics.clear()

    def __enter__(self):
        """上下文管理器入口"""
        self.start_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_monitoring()
