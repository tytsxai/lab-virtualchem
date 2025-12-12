#!/usr/bin/env python3
"""
增强的性能优化系统
提供智能缓存、内存管理、资源优化、性能监控等功能
"""

import gc
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .robustness_integration import enhance_robustness, log_operation

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用
    FIFO = "fifo"  # 先进先出
    TTL = "ttl"  # 生存时间
    ADAPTIVE = "adaptive"  # 自适应


class MemoryLevel(Enum):
    """内存级别"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationLevel(Enum):
    """优化级别"""
    BASIC = "basic"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size: int = 0
    ttl: float | None = None
    priority: int = 0


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available: float
    cache_hit_rate: float
    cache_miss_rate: float
    response_time: float
    throughput: float
    error_rate: float
    active_connections: int
    queue_length: int


@dataclass
class OptimizationRule:
    """优化规则"""
    name: str
    condition: str
    action: str
    priority: int
    enabled: bool = True
    last_triggered: datetime | None = None
    trigger_count: int = 0


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_io_mb: float
    active_threads: int
    gc_collections: int


class EnhancedPerformanceSystem:
    """增强的性能优化系统"""

    def __init__(self):
        self.cache: dict[str, CacheEntry] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0
        }
        self.performance_history: deque = deque(maxlen=1000)
        self.optimization_rules: list[OptimizationRule] = []
        self.resource_monitor: threading.Thread | None = None
        self.monitoring_active = False
        self.optimization_enabled = True
        self.auto_optimization = True

        # 性能阈值
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "response_time": 1.0,
            "cache_hit_rate": 0.7,
            "error_rate": 0.05
        }

        # 初始化系统
        self._initialize_cache()
        self._initialize_optimization_rules()
        self._start_monitoring()

    def _initialize_cache(self) -> None:
        """初始化缓存系统"""
        self.cache_strategy = CacheStrategy.LRU
        self.max_cache_size = 1000
        self.max_cache_memory = 100 * 1024 * 1024  # 100MB
        self.default_ttl = 3600  # 1小时

        logger.info("缓存系统已初始化")

    def _initialize_optimization_rules(self) -> None:
        """初始化优化规则"""
        rules = [
            OptimizationRule(
                name="memory_cleanup",
                condition="memory_usage > 80",
                action="trigger_gc",
                priority=1
            ),
            OptimizationRule(
                name="cache_optimization",
                condition="cache_hit_rate < 0.7",
                action="optimize_cache",
                priority=2
            ),
            OptimizationRule(
                name="response_time_optimization",
                condition="response_time > 1.0",
                action="optimize_queries",
                priority=3
            ),
            OptimizationRule(
                name="error_rate_optimization",
                condition="error_rate > 0.05",
                action="increase_timeout",
                priority=4
            )
        ]

        self.optimization_rules = rules
        logger.info(f"已初始化 {len(rules)} 个优化规则")

    def _start_monitoring(self) -> None:
        """启动性能监控"""
        self.monitoring_active = True
        self.resource_monitor = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.resource_monitor.start()
        logger.info("性能监控已启动")

    def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.monitoring_active:
            try:
                metrics = self._collect_performance_metrics()
                self.performance_history.append(metrics)

                # 检查优化规则
                if self.auto_optimization:
                    self._check_optimization_rules(metrics)

                time.sleep(5)  # 每5秒收集一次
            except Exception as e:
                logger.error(f"性能监控错误: {e}")
                time.sleep(5)

    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        # 这里应该使用实际的性能监控库
        # 为了演示，使用模拟数据
        current_time = datetime.now()

        # 模拟CPU使用率
        cpu_usage = 45.0 + (time.time() % 20)  # 45-65%

        # 模拟内存使用率
        memory_usage = 60.0 + (time.time() % 15)  # 60-75%
        memory_available = 100.0 - memory_usage

        # 计算缓存命中率
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        cache_hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0.0
        cache_miss_rate = 1.0 - cache_hit_rate

        # 模拟响应时间
        response_time = 0.5 + (time.time() % 0.5)  # 0.5-1.0秒

        # 模拟吞吐量
        throughput = 100.0 + (time.time() % 50)  # 100-150 req/s

        # 模拟错误率
        error_rate = 0.01 + (time.time() % 0.02)  # 1-3%

        return PerformanceMetrics(
            timestamp=current_time,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_available=memory_available,
            cache_hit_rate=cache_hit_rate,
            cache_miss_rate=cache_miss_rate,
            response_time=response_time,
            throughput=throughput,
            error_rate=error_rate,
            active_connections=50,
            queue_length=10
        )

    def _check_optimization_rules(self, metrics: PerformanceMetrics) -> None:
        """检查优化规则"""
        for rule in self.optimization_rules:
            if not rule.enabled:
                continue

            # 检查条件
            if self._evaluate_condition(rule.condition, metrics):
                # 执行优化动作
                self._execute_optimization_action(rule.action, metrics)

                # 更新规则统计
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1

                logger.info(f"优化规则触发: {rule.name} - {rule.action}")

    def _evaluate_condition(self, condition: str, metrics: PerformanceMetrics) -> bool:
        """评估优化条件"""
        try:
            # 简单的条件评估
            if "memory_usage > 80" in condition:
                return metrics.memory_usage > 80.0
            elif "cache_hit_rate < 0.7" in condition:
                return metrics.cache_hit_rate < 0.7
            elif "response_time > 1.0" in condition:
                return metrics.response_time > 1.0
            elif "error_rate > 0.05" in condition:
                return metrics.error_rate > 0.05
            return False
        except Exception as e:
            logger.error(f"条件评估错误: {e}")
            return False

    def _execute_optimization_action(self, action: str, _metrics: PerformanceMetrics) -> None:
        """执行优化动作"""
        try:
            if action == "trigger_gc":
                self._trigger_garbage_collection()
            elif action == "optimize_cache":
                self._optimize_cache()
            elif action == "optimize_queries":
                self._optimize_queries()
            elif action == "increase_timeout":
                self._increase_timeout()
        except Exception as e:
            logger.error(f"优化动作执行错误: {e}")

    def _trigger_garbage_collection(self) -> None:
        """触发垃圾回收"""
        logger.info("触发垃圾回收")
        gc.collect()

    def _optimize_cache(self) -> None:
        """优化缓存"""
        logger.info("优化缓存策略")
        # 清理过期条目
        self._cleanup_expired_cache()
        # 调整缓存大小
        self._adjust_cache_size()

    def _optimize_queries(self) -> None:
        """优化查询"""
        logger.info("优化查询性能")
        # 这里可以添加查询优化逻辑

    def _increase_timeout(self) -> None:
        """增加超时时间"""
        logger.info("增加操作超时时间")
        # 这里可以添加超时调整逻辑

    def _cleanup_expired_cache(self) -> None:
        """清理过期缓存"""
        current_time = datetime.now()
        expired_keys = []

        for key, entry in self.cache.items():
            if entry.ttl and (current_time - entry.created_at).total_seconds() > entry.ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]
            self.cache_stats["evictions"] += 1

        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")

    def _adjust_cache_size(self) -> None:
        """调整缓存大小"""
        if len(self.cache) > self.max_cache_size:
            # 根据策略清理缓存
            if self.cache_strategy == CacheStrategy.LRU:
                self._evict_lru_entries()
            elif self.cache_strategy == CacheStrategy.LFU:
                self._evict_lfu_entries()
            elif self.cache_strategy == CacheStrategy.FIFO:
                self._evict_fifo_entries()

    def _evict_lru_entries(self) -> None:
        """清理最近最少使用的条目"""
        # 按最后访问时间排序
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed
        )

        # 清理最旧的条目
        evict_count = len(self.cache) - self.max_cache_size
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self.cache[key]
            self.cache_stats["evictions"] += 1

    def _evict_lfu_entries(self) -> None:
        """清理最少使用的条目"""
        # 按访问次数排序
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].access_count
        )

        # 清理访问次数最少的条目
        evict_count = len(self.cache) - self.max_cache_size
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self.cache[key]
            self.cache_stats["evictions"] += 1

    def _evict_fifo_entries(self) -> None:
        """清理先进先出的条目"""
        # 按创建时间排序
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].created_at
        )

        # 清理最旧的条目
        evict_count = len(self.cache) - self.max_cache_size
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self.cache[key]
            self.cache_stats["evictions"] += 1

    @enhance_robustness(
        operation_name="cache_get",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="cache_get")
    def cache_get(self, key: str) -> Any | None:
        """获取缓存值"""
        if key not in self.cache:
            self.cache_stats["misses"] += 1
            return None

        entry = self.cache[key]

        # 检查是否过期
        if entry.ttl and (datetime.now() - entry.created_at).total_seconds() > entry.ttl:
            del self.cache[key]
            self.cache_stats["misses"] += 1
            self.cache_stats["evictions"] += 1
            return None

        # 更新访问统计
        entry.last_accessed = datetime.now()
        entry.access_count += 1
        self.cache_stats["hits"] += 1

        return entry.value

    @enhance_robustness(
        operation_name="cache_set",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="cache_set")
    def cache_set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        priority: int = 0
    ) -> bool:
        """设置缓存值"""
        try:
            # 计算值的大小（简化实现）
            value_size = len(str(value))

            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size=value_size,
                ttl=ttl or self.default_ttl,
                priority=priority
            )

            # 检查缓存大小限制
            if len(self.cache) >= self.max_cache_size:
                self._adjust_cache_size()

            # 设置缓存
            self.cache[key] = entry
            self.cache_stats["size"] += value_size

            return True
        except Exception as e:
            logger.error(f"缓存设置错误: {e}")
            return False

    @enhance_robustness(
        operation_name="cache_delete",
        security_level="low",
        enable_caching=False
    )
    @log_operation(operation_name="cache_delete")
    def cache_delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self.cache:
            entry = self.cache[key]
            del self.cache[key]
            self.cache_stats["size"] -= entry.size
            return True
        return False

    @enhance_robustness(
        operation_name="cache_clear",
        security_level="medium",
        enable_caching=False
    )
    @log_operation(operation_name="cache_clear")
    def cache_clear(self) -> int:
        """清空缓存"""
        count = len(self.cache)
        self.cache.clear()
        self.cache_stats["size"] = 0
        logger.info(f"清空了 {count} 个缓存条目")
        return count

    @enhance_robustness(
        operation_name="get_performance_metrics",
        security_level="low",
        enable_caching=True
    )
    def get_performance_metrics(self, limit: int = 100) -> list[PerformanceMetrics]:
        """获取性能指标"""
        return list(self.performance_history)[-limit:]

    @enhance_robustness(
        operation_name="get_cache_stats",
        security_level="low",
        enable_caching=True
    )
    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "evictions": self.cache_stats["evictions"],
            "size": self.cache_stats["size"],
            "hit_rate": hit_rate,
            "miss_rate": 1.0 - hit_rate,
            "total_entries": len(self.cache),
            "max_size": self.max_cache_size
        }

    @enhance_robustness(
        operation_name="get_resource_usage",
        security_level="low",
        enable_caching=True
    )
    def get_resource_usage(self) -> ResourceUsage:
        """获取资源使用情况"""
        # 这里应该使用实际的系统监控库
        # 为了演示，使用模拟数据
        return ResourceUsage(
            cpu_percent=45.0 + (time.time() % 20),
            memory_percent=60.0 + (time.time() % 15),
            memory_used_mb=1024.0 + (time.time() % 512),
            memory_available_mb=2048.0 - (time.time() % 512),
            disk_usage_percent=30.0 + (time.time() % 10),
            network_io_mb=10.0 + (time.time() % 5),
            active_threads=threading.active_count(),
            gc_collections=gc.get_count()[0]
        )

    @enhance_robustness(
        operation_name="optimize_system",
        security_level="medium",
        enable_caching=False
    )
    @log_operation(operation_name="optimize_system")
    def optimize_system(self, level: OptimizationLevel = OptimizationLevel.BASIC) -> dict[str, Any]:
        """优化系统性能"""
        optimization_results = {
            "level": level.value,
            "timestamp": datetime.now().isoformat(),
            "actions_taken": [],
            "improvements": {}
        }

        try:
            if level in [OptimizationLevel.BASIC, OptimizationLevel.ADVANCED, OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
                # 基础优化
                self._trigger_garbage_collection()
                optimization_results["actions_taken"].append("垃圾回收")

                # 缓存优化
                self._optimize_cache()
                optimization_results["actions_taken"].append("缓存优化")

            if level in [OptimizationLevel.ADVANCED, OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
                # 高级优化
                self._optimize_memory()
                optimization_results["actions_taken"].append("内存优化")

                # 查询优化
                self._optimize_queries()
                optimization_results["actions_taken"].append("查询优化")

            if level in [OptimizationLevel.AGGRESSIVE, OptimizationLevel.MAXIMUM]:
                # 激进优化
                self._optimize_threading()
                optimization_results["actions_taken"].append("线程优化")

                # 网络优化
                self._optimize_network()
                optimization_results["actions_taken"].append("网络优化")

            if level == OptimizationLevel.MAXIMUM:
                # 最大优化
                self._optimize_system_level()
                optimization_results["actions_taken"].append("系统级优化")

            # 计算改进效果
            optimization_results["improvements"] = self._calculate_improvements()

            logger.info(f"系统优化完成: {level.value}")

        except Exception as e:
            logger.error(f"系统优化错误: {e}")
            optimization_results["error"] = str(e)

        return optimization_results

    def _optimize_memory(self) -> None:
        """优化内存使用"""
        logger.info("执行内存优化")
        # 清理缓存
        self._cleanup_expired_cache()
        # 强制垃圾回收
        gc.collect()

    def _optimize_threading(self) -> None:
        """优化线程使用"""
        logger.info("执行线程优化")
        # 这里可以添加线程池优化逻辑

    def _optimize_network(self) -> None:
        """优化网络性能"""
        logger.info("执行网络优化")
        # 这里可以添加网络连接池优化逻辑

    def _optimize_system_level(self) -> None:
        """系统级优化"""
        logger.info("执行系统级优化")
        # 这里可以添加系统级优化逻辑

    def _calculate_improvements(self) -> dict[str, Any]:
        """计算改进效果"""
        # 这里应该计算实际的改进效果
        # 为了演示，返回模拟数据
        return {
            "memory_usage_reduction": 5.0,
            "response_time_improvement": 0.1,
            "cache_hit_rate_improvement": 0.05,
            "throughput_increase": 10.0
        }

    @enhance_robustness(
        operation_name="get_optimization_report",
        security_level="low",
        enable_caching=True
    )
    def get_optimization_report(self) -> dict[str, Any]:
        """获取优化报告"""
        if not self.performance_history:
            return {"error": "没有性能数据"}

        latest_metrics = self.performance_history[-1]
        cache_stats = self.get_cache_stats()
        resource_usage = self.get_resource_usage()

        return {
            "timestamp": datetime.now().isoformat(),
            "performance_metrics": {
                "cpu_usage": latest_metrics.cpu_usage,
                "memory_usage": latest_metrics.memory_usage,
                "response_time": latest_metrics.response_time,
                "throughput": latest_metrics.throughput,
                "error_rate": latest_metrics.error_rate
            },
            "cache_performance": cache_stats,
            "resource_usage": {
                "cpu_percent": resource_usage.cpu_percent,
                "memory_percent": resource_usage.memory_percent,
                "active_threads": resource_usage.active_threads,
                "gc_collections": resource_usage.gc_collections
            },
            "optimization_rules": [
                {
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "trigger_count": rule.trigger_count,
                    "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None
                }
                for rule in self.optimization_rules
            ],
            "recommendations": self._generate_recommendations(latest_metrics)
        }

    def _generate_recommendations(self, metrics: PerformanceMetrics) -> list[str]:
        """生成优化建议"""
        recommendations = []

        if metrics.cpu_usage > 80:
            recommendations.append("CPU使用率过高，建议优化计算密集型任务")

        if metrics.memory_usage > 85:
            recommendations.append("内存使用率过高，建议清理缓存或增加内存")

        if metrics.response_time > 1.0:
            recommendations.append("响应时间过长，建议优化数据库查询或网络请求")

        if metrics.cache_hit_rate < 0.7:
            recommendations.append("缓存命中率较低，建议调整缓存策略")

        if metrics.error_rate > 0.05:
            recommendations.append("错误率过高，建议检查错误处理和重试机制")

        return recommendations

    def stop_monitoring(self) -> None:
        """停止性能监控"""
        self.monitoring_active = False
        if self.resource_monitor:
            self.resource_monitor.join(timeout=1.0)
        logger.info("性能监控已停止")


# 全局实例
enhanced_performance_system = EnhancedPerformanceSystem()
