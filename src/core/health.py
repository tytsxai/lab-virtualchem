"""
健康检查和监控系统

提供应用健康状态检查、依赖监控、指标收集等功能
"""

import asyncio
import contextlib
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康检查结果"""

    name: str
    status: HealthStatus
    message: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class SystemHealth:
    """系统健康状态"""

    status: HealthStatus
    checks: list[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "checks": [check.to_dict() for check in self.checks],
        }


class IHealthCheck(ABC):
    """健康检查接口"""

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """执行健康检查"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """检查名称"""
        pass


class DatabaseHealthCheck(IHealthCheck):
    """数据库健康检查"""

    def __init__(self, db_connection: Any, name: str = "database"):
        self.db_connection = db_connection
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def check(self) -> HealthCheckResult:
        """检查数据库连接"""
        start = time.time()

        try:
            # 执行简单查询测试连接
            # await self.db_connection.execute("SELECT 1")

            duration = (time.time() - start) * 1000

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="数据库连接正常",
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"数据库连接失败: {str(e)}",
                duration_ms=duration,
            )


class CacheHealthCheck(IHealthCheck):
    """缓存健康检查"""

    def __init__(self, cache: Any, name: str = "cache"):
        self.cache = cache
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def check(self) -> HealthCheckResult:
        """检查缓存"""
        start = time.time()

        try:
            # 测试缓存读写
            test_key = "__health_check__"
            test_value = "ok"

            self.cache.set(test_key, test_value, ttl=10)
            result = self.cache.get(test_key)

            if result == test_value:
                self.cache.delete(test_key)

                duration = (time.time() - start) * 1000

                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="缓存正常",
                    duration_ms=duration,
                    metadata={"size": self.cache.size()},
                )
            else:
                raise Exception("缓存值不匹配")

        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"缓存异常: {str(e)}",
                duration_ms=duration,
            )


class MessageQueueHealthCheck(IHealthCheck):
    """消息队列健康检查"""

    def __init__(self, queue: Any, name: str = "message_queue"):
        self.queue = queue
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def check(self) -> HealthCheckResult:
        """检查消息队列"""
        start = time.time()

        try:
            # 检查队列是否运行
            is_running = getattr(self.queue, "_running", False)

            duration = (time.time() - start) * 1000

            if is_running:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="消息队列正常运行",
                    duration_ms=duration,
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.DEGRADED,
                    message="消息队列未运行",
                    duration_ms=duration,
                )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"消息队列异常: {str(e)}",
                duration_ms=duration,
            )


class DiskSpaceHealthCheck(IHealthCheck):
    """磁盘空间健康检查"""

    def __init__(self, path: str = "/", threshold_percent: float = 90.0):
        self.path = path
        self.threshold_percent = threshold_percent

    @property
    def name(self) -> str:
        return "disk_space"

    async def check(self) -> HealthCheckResult:
        """检查磁盘空间"""
        start = time.time()

        try:
            disk = psutil.disk_usage(self.path)
            used_percent = disk.percent

            duration = (time.time() - start) * 1000

            if used_percent < self.threshold_percent:
                status = HealthStatus.HEALTHY
                message = f"磁盘空间充足 ({used_percent:.1f}% 已用)"
            elif used_percent < 95:
                status = HealthStatus.DEGRADED
                message = f"磁盘空间不足 ({used_percent:.1f}% 已用)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"磁盘空间严重不足 ({used_percent:.1f}% 已用)"

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    "total_gb": disk.total / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": used_percent,
                },
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"磁盘检查失败: {str(e)}",
                duration_ms=duration,
            )


class MemoryHealthCheck(IHealthCheck):
    """内存健康检查"""

    def __init__(self, threshold_percent: float = 90.0):
        self.threshold_percent = threshold_percent

    @property
    def name(self) -> str:
        return "memory"

    async def check(self) -> HealthCheckResult:
        """检查内存使用"""
        start = time.time()

        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent

            duration = (time.time() - start) * 1000

            if used_percent < self.threshold_percent:
                status = HealthStatus.HEALTHY
                message = f"内存使用正常 ({used_percent:.1f}% 已用)"
            elif used_percent < 95:
                status = HealthStatus.DEGRADED
                message = f"内存使用偏高 ({used_percent:.1f}% 已用)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"内存严重不足 ({used_percent:.1f}% 已用)"

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=duration,
                metadata={
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                    "percent": used_percent,
                },
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"内存检查失败: {str(e)}",
                duration_ms=duration,
            )


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self._checks: list[IHealthCheck] = []
        self._start_time = datetime.now()

    def register(self, check: IHealthCheck) -> None:
        """注册健康检查"""
        self._checks.append(check)

    async def check_all(self) -> SystemHealth:
        """执行所有健康检查"""
        results = await asyncio.gather(
            *[check.check() for check in self._checks], return_exceptions=True
        )

        check_results = []
        for result in results:
            if isinstance(result, HealthCheckResult):
                check_results.append(result)
            elif isinstance(result, Exception):
                check_results.append(
                    HealthCheckResult(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        message=f"检查失败: {str(result)}",
                    )
                )

        # 确定总体状态
        if all(r.status == HealthStatus.HEALTHY for r in check_results):
            overall_status = HealthStatus.HEALTHY
        elif any(r.status == HealthStatus.UNHEALTHY for r in check_results):
            overall_status = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in check_results):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNKNOWN

        # 计算运行时间
        uptime = (datetime.now() - self._start_time).total_seconds()

        return SystemHealth(
            status=overall_status, checks=check_results, uptime_seconds=uptime
        )


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._metrics: dict[str, deque] = {}
        self._lock = threading.Lock()

    def record(
        self, metric_name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        """记录指标"""
        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = deque(maxlen=self.max_history)

            self._metrics[metric_name].append(
                {"value": value, "timestamp": datetime.now(), "tags": tags or {}}
            )

    def get_metric(self, metric_name: str) -> list[dict[str, Any]]:
        """获取指标历史"""
        with self._lock:
            if metric_name in self._metrics:
                return list(self._metrics[metric_name])
            return []

    def get_latest(self, metric_name: str) -> dict[str, Any] | None:
        """获取最新指标值"""
        with self._lock:
            if metric_name in self._metrics and self._metrics[metric_name]:
                return self._metrics[metric_name][-1]
            return None

    def get_average(self, metric_name: str, duration: timedelta) -> float | None:
        """获取时间段内的平均值"""
        with self._lock:
            if metric_name not in self._metrics:
                return None

            cutoff = datetime.now() - duration
            values = [
                m["value"]
                for m in self._metrics[metric_name]
                if m["timestamp"] >= cutoff
            ]

            return sum(values) / len(values) if values else None


class HealthMonitor:
    """健康监控器"""

    def __init__(self, checker: HealthChecker, interval_seconds: int = 60):
        self.checker = checker
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_health: SystemHealth | None = None
        self._health_history: deque = deque(maxlen=100)

    async def start(self) -> None:
        """启动监控"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                health = await self.checker.check_all()
                self._last_health = health
                self._health_history.append(health)

                # 如果状态不健康，可以触发告警
                if health.status == HealthStatus.UNHEALTHY:
                    await self._alert(health)

            except Exception as e:
                logger.info(f"监控错误: {e}")

            await asyncio.sleep(self.interval_seconds)

    async def _alert(self, health: SystemHealth) -> None:
        """发送告警"""
        # 这里可以集成告警系统（邮件、短信、Slack等）
        logger.info(f"⚠️ 健康告警: 系统状态 {health.status.value}")
        for check in health.checks:
            if check.status == HealthStatus.UNHEALTHY:
                logger.info(f"  - {check.name}: {check.message}")

    def get_current_health(self) -> SystemHealth | None:
        """获取当前健康状态"""
        return self._last_health

    def get_health_history(self) -> list[SystemHealth]:
        """获取健康历史"""
        return list(self._health_history)


# 全局健康检查器
_health_checker = HealthChecker()
_metrics_collector = MetricsCollector()


def get_health_checker() -> HealthChecker:
    """获取全局健康检查器"""
    return _health_checker


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return _metrics_collector


async def demo():
    """演示"""
    logger.info("=== 健康检查和监控系统演示 ===\n")

    # 1. 创建健康检查器
    checker = HealthChecker()

    # 2. 注册检查项
    logger.info("1. 注册健康检查项...")
    checker.register(DiskSpaceHealthCheck())
    checker.register(MemoryHealthCheck())

    # 3. 执行健康检查
    logger.info("\n2. 执行健康检查:")
    health = await checker.check_all()

    logger.info(f"总体状态: {health.status.value}")
    logger.info(f"运行时间: {health.uptime_seconds:.2f}秒")
    logger.info("\n检查结果:")

    for check in health.checks:
        status_icon = "✅" if check.status == HealthStatus.HEALTHY else "⚠️"
        logger.info(
            f"{status_icon} {check.name}: {check.message} ({check.duration_ms:.2f}ms)"
        )
        if check.metadata:
            for key, value in check.metadata.items():
                if isinstance(value, float):
                    logger.info(f"    {key}: {value:.2f}")
                else:
                    logger.info(f"    {key}: {value}")

    # 4. 指标收集
    logger.info("\n3. 指标收集:")
    metrics = get_metrics_collector()

    metrics.record("request_count", 100, {"endpoint": "/api/experiments"})
    metrics.record("response_time", 0.25, {"endpoint": "/api/experiments"})

    latest = metrics.get_latest("response_time")
    if latest:
        logger.info(f"最新响应时间: {latest['value']}s")

    # 5. 健康监控
    logger.info("\n4. 启动健康监控（5秒）...")
    monitor = HealthMonitor(checker, interval_seconds=2)
    await monitor.start()

    await asyncio.sleep(5)

    await monitor.stop()

    logger.info("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(demo())
