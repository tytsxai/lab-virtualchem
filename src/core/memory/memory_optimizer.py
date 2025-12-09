"""内存优化器"""

import gc
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

class OptimizationTarget(Enum):
    """优化目标"""
    MEMORY_USAGE = "memory_usage"
    GARBAGE_COLLECTION = "garbage_collection"
    MEMORY_LEAKS = "memory_leaks"
    FRAGMENTATION = "fragmentation"
    CACHE_SIZE = "cache_size"

@dataclass
class MemoryOptimizationRule:
    """内存优化规则"""
    name: str
    target: OptimizationTarget
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[], None]
    priority: int = 0
    enabled: bool = True
    cooldown: float = 60.0  # 冷却时间（秒）

class MemoryOptimizer:
    """内存优化器"""

    def __init__(self):
        """初始化内存优化器"""
        self.rules: List[MemoryOptimizationRule] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_execution: Dict[str, float] = {}
        self.optimization_stats: Dict[str, int] = {}
        self.lock = threading.Lock()

        # 内存阈值
        self.thresholds = {
            'memory_usage_percent': 80.0,
            'memory_usage_mb': 1024.0,  # 1GB
            'gc_threshold': 1000,
            'fragmentation_rate': 0.3,
            'cache_size_mb': 512.0,  # 512MB
        }

        # 初始化默认规则
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """初始化默认优化规则"""
        # 高内存使用率优化
        self.add_rule(MemoryOptimizationRule(
            name="high_memory_usage",
            target=OptimizationTarget.MEMORY_USAGE,
            condition=lambda metrics: metrics.get('memory_percent', 0) > self.thresholds['memory_usage_percent'],
            action=self._optimize_memory_usage,
            priority=1
        ))

        # 垃圾回收优化
        self.add_rule(MemoryOptimizationRule(
            name="garbage_collection",
            target=OptimizationTarget.GARBAGE_COLLECTION,
            condition=lambda metrics: metrics.get('gc_count', 0) > self.thresholds['gc_threshold'],
            action=self._optimize_garbage_collection,
            priority=2
        ))

        # 内存泄漏检测
        self.add_rule(MemoryOptimizationRule(
            name="memory_leak_detection",
            target=OptimizationTarget.MEMORY_LEAKS,
            condition=lambda metrics: metrics.get('memory_growth_rate', 0) > 0.1,
            action=self._detect_memory_leaks,
            priority=3
        ))

        # 内存碎片化优化
        self.add_rule(MemoryOptimizationRule(
            name="fragmentation_optimization",
            target=OptimizationTarget.FRAGMENTATION,
            condition=lambda metrics: metrics.get('fragmentation_rate', 0) > self.thresholds['fragmentation_rate'],
            action=self._optimize_fragmentation,
            priority=4
        ))

        # 缓存大小优化
        self.add_rule(MemoryOptimizationRule(
            name="cache_size_optimization",
            target=OptimizationTarget.CACHE_SIZE,
            condition=lambda metrics: metrics.get('cache_size_mb', 0) > self.thresholds['cache_size_mb'],
            action=self._optimize_cache_size,
            priority=5
        ))

    def add_rule(self, rule: MemoryOptimizationRule):
        """添加优化规则"""
        with self.lock:
            self.rules.append(rule)
            self.rules.sort(key=lambda r: r.priority)

    def remove_rule(self, name: str):
        """移除优化规则"""
        with self.lock:
            self.rules = [r for r in self.rules if r.name != name]

    def start_monitoring(self, interval: float = 5.0):
        """开始内存监控"""
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
        """停止内存监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集内存指标
                metrics = self._collect_memory_metrics()

                # 检查优化规则
                self._check_optimization_rules(metrics)

                time.sleep(interval)

            except Exception as e:
                logger.error(f"内存监控错误: {e}")
                time.sleep(interval)

    def _collect_memory_metrics(self) -> Dict[str, Any]:
        """收集内存指标"""
        metrics = {}

        try:
            # 系统内存信息
            memory = psutil.virtual_memory()
            metrics['memory_percent'] = memory.percent
            metrics['memory_available'] = memory.available
            metrics['memory_used'] = memory.used
            metrics['memory_total'] = memory.total

            # 进程内存信息
            process = psutil.Process()
            process_memory = process.memory_info()
            metrics['process_rss'] = process_memory.rss
            metrics['process_vms'] = process_memory.vms

            # 垃圾回收统计
            gc_stats = gc.get_stats()
            metrics['gc_count'] = sum(stat['collections'] for stat in gc_stats)
            metrics['gc_collected'] = sum(stat['collected'] for stat in gc_stats)
            metrics['gc_uncollectable'] = sum(stat['uncollectable'] for stat in gc_stats)

            # 内存碎片化率
            metrics['fragmentation_rate'] = self._calculate_fragmentation_rate()

            # 缓存大小（估算）
            metrics['cache_size_mb'] = self._estimate_cache_size()

            # 内存增长率
            metrics['memory_growth_rate'] = self._calculate_memory_growth_rate()

        except Exception as e:
            logger.error(f"收集内存指标错误: {e}")

        return metrics

    def _calculate_fragmentation_rate(self) -> float:
        """计算内存碎片化率"""
        try:
            # 获取内存映射
            process = psutil.Process()
            memory_maps = process.memory_maps()

            if not memory_maps:
                return 0.0

            # 计算碎片化率
            total_size = sum(map.rss for map in memory_maps)
            if total_size == 0:
                return 0.0

            # 计算碎片数量
            fragments = len(memory_maps)
            fragmentation_rate = fragments / (total_size / 1024 / 1024)  # 每MB的碎片数

            return min(fragmentation_rate, 1.0)  # 限制在0-1之间

        except Exception:
            return 0.0

    def _estimate_cache_size(self) -> float:
        """估算缓存大小"""
        try:
            # 这里可以实现具体的缓存大小估算逻辑
            # 目前返回一个估算值
            return 0.0
        except Exception:
            return 0.0

    def _calculate_memory_growth_rate(self) -> float:
        """计算内存增长率"""
        try:
            # 这里可以实现内存增长率计算逻辑
            # 目前返回一个估算值
            return 0.0
        except Exception:
            return 0.0

    def _check_optimization_rules(self, metrics: Dict[str, Any]):
        """检查优化规则"""
        with self.lock:
            for rule in self.rules:
                if not rule.enabled:
                    continue

                # 检查冷却时间
                if self._is_in_cooldown(rule.name):
                    continue

                try:
                    if rule.condition(metrics):
                        self._execute_optimization_rule(rule)
                except Exception as e:
                    logger.error(f"优化规则执行错误 {rule.name}: {e}")

    def _is_in_cooldown(self, rule_name: str) -> bool:
        """检查是否在冷却时间"""
        if rule_name not in self.last_execution:
            return False

        last_time = self.last_execution[rule_name]
        cooldown_time = self.rules[0].cooldown  # 使用第一个规则的冷却时间

        return time.time() - last_time < cooldown_time

    def _execute_optimization_rule(self, rule: MemoryOptimizationRule):
        """执行优化规则"""
        logger.info(f"执行内存优化规则: {rule.name}")

        try:
            rule.action()

            # 记录执行时间
            self.last_execution[rule.name] = time.time()

            # 更新统计
            if rule.name not in self.optimization_stats:
                self.optimization_stats[rule.name] = 0
            self.optimization_stats[rule.name] += 1

        except Exception as e:
            logger.error(f"优化规则执行失败 {rule.name}: {e}")

    # 优化动作实现
    def _optimize_memory_usage(self):
        """优化内存使用"""
        logger.info("执行内存使用优化")

        # 强制垃圾回收
        gc.collect()

        # 清理缓存
        self._clear_caches()

        # 卸载未使用的模块
        self._unload_unused_modules()

    def _optimize_garbage_collection(self):
        """优化垃圾回收"""
        logger.info("执行垃圾回收优化")

        # 设置垃圾回收阈值
        gc.set_threshold(700, 10, 10)

        # 强制垃圾回收
        gc.collect()

        # 清理循环引用
        gc.collect()

    def _detect_memory_leaks(self):
        """检测内存泄漏"""
        logger.info("执行内存泄漏检测")

        # 获取当前内存使用
        current_memory = psutil.Process().memory_info().rss

        # 记录内存使用历史
        if not hasattr(self, '_memory_history'):
            self._memory_history = []

        self._memory_history.append({
            'timestamp': time.time(),
            'memory': current_memory
        })

        # 保持最近100个记录
        if len(self._memory_history) > 100:
            self._memory_history = self._memory_history[-100:]

        # 分析内存增长趋势
        if len(self._memory_history) >= 10:
            self._analyze_memory_trend()

    def _optimize_fragmentation(self):
        """优化内存碎片化"""
        logger.info("执行内存碎片化优化")

        # 强制垃圾回收
        gc.collect()

        # 整理内存
        self._defragment_memory()

    def _optimize_cache_size(self):
        """优化缓存大小"""
        logger.info("执行缓存大小优化")

        # 清理过期缓存
        self._clear_expired_caches()

        # 压缩缓存
        self._compress_caches()

    def _clear_caches(self):
        """清理缓存"""
        # 实现缓存清理逻辑
        pass

    def _unload_unused_modules(self):
        """卸载未使用的模块"""
        # 实现模块卸载逻辑
        pass

    def _analyze_memory_trend(self):
        """分析内存趋势"""
        if len(self._memory_history) < 10:
            return

        # 计算内存增长率
        recent = self._memory_history[-10:]
        memory_values = [record['memory'] for record in recent]

        # 简单线性回归
        n = len(memory_values)
        x_sum = sum(range(n))
        y_sum = sum(memory_values)
        xy_sum = sum(i * memory_values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        if slope > 1024 * 1024:  # 每秒增长超过1MB
            logger.warning(f"检测到内存泄漏趋势: {slope / 1024 / 1024:.2f} MB/s")

    def _defragment_memory(self):
        """整理内存"""
        # 实现内存整理逻辑
        pass

    def _clear_expired_caches(self):
        """清理过期缓存"""
        # 实现过期缓存清理逻辑
        pass

    def _compress_caches(self):
        """压缩缓存"""
        # 实现缓存压缩逻辑
        pass

    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计"""
        with self.lock:
            return {
                'is_monitoring': self.is_monitoring,
                'rules_count': len(self.rules),
                'enabled_rules': len([r for r in self.rules if r.enabled]),
                'optimization_stats': self.optimization_stats.copy(),
                'last_execution': self.last_execution.copy(),
                'thresholds': self.thresholds.copy()
            }

    def set_threshold(self, threshold_name: str, value: float):
        """设置阈值"""
        if threshold_name in self.thresholds:
            self.thresholds[threshold_name] = value

    def enable_rule(self, rule_name: str):
        """启用规则"""
        with self.lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    rule.enabled = True
                    break

    def disable_rule(self, rule_name: str):
        """禁用规则"""
        with self.lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    rule.enabled = False
                    break

    def force_optimization(self, target: OptimizationTarget):
        """强制优化"""
        with self.lock:
            for rule in self.rules:
                if rule.target == target and rule.enabled:
                    try:
                        rule.action()
                        logger.info(f"强制执行优化: {rule.name}")
                    except Exception as e:
                        logger.error(f"强制优化失败 {rule.name}: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        self.start_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_monitoring()
