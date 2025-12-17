"""
系统健康检查和监控模块
提供系统资源监控、性能指标收集和健康状态检查
"""

import logging
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        """初始化健康检查器"""
        # 阈值配置
        self.disk_space_warning_percent = 20  # 磁盘空间警告阈值(%)
        self.disk_space_critical_percent = 10  # 磁盘空间严重阈值(%)
        self.memory_warning_percent = 80  # 内存使用警告阈值(%)
        self.memory_critical_percent = 90  # 内存使用严重阈值(%)
        self.cpu_warning_percent = 70  # CPU使用警告阈值(%)
        self.cpu_critical_percent = 85  # CPU使用严重阈值(%)

    def check_disk_space(self, path: str = ".") -> dict[str, Any]:
        """检查磁盘空间

        Args:
            path: 要检查的路径

        Returns:
            磁盘空间检查结果
        """
        try:
            disk_usage = psutil.disk_usage(path)
            free_percent = (disk_usage.free / disk_usage.total) * 100

            status = "healthy"
            if free_percent < self.disk_space_critical_percent:
                status = "critical"
            elif free_percent < self.disk_space_warning_percent:
                status = "warning"

            return {
                "check": "disk_space",
                "status": status,
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "free_percent": round(free_percent, 2),
                "message": f"磁盘剩余空间: {round(free_percent, 1)}%",
            }
        except Exception as e:
            logger.error(f"磁盘空间检查失败: {e}")
            return {
                "check": "disk_space",
                "status": "error",
                "message": f"检查失败: {e}",
            }

    def check_memory(self) -> dict[str, Any]:
        """检查内存使用

        Returns:
            内存检查结果
        """
        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent

            status = "healthy"
            if used_percent > self.memory_critical_percent:
                status = "critical"
            elif used_percent > self.memory_warning_percent:
                status = "warning"

            return {
                "check": "memory",
                "status": status,
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": round(used_percent, 2),
                "message": f"内存使用率: {round(used_percent, 1)}%",
            }
        except Exception as e:
            logger.error(f"内存检查失败: {e}")
            return {"check": "memory", "status": "error", "message": f"检查失败: {e}"}

    def check_cpu(self) -> dict[str, Any]:
        """检查CPU使用

        Returns:
            CPU检查结果
        """
        try:
            # 短暂间隔获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.5)

            status = "healthy"
            if cpu_percent > self.cpu_critical_percent:
                status = "critical"
            elif cpu_percent > self.cpu_warning_percent:
                status = "warning"

            return {
                "check": "cpu",
                "status": status,
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": round(cpu_percent, 2),
                "message": f"CPU使用率: {round(cpu_percent, 1)}%",
            }
        except Exception as e:
            logger.error(f"CPU检查失败: {e}")
            return {"check": "cpu", "status": "error", "message": f"检查失败: {e}"}

    def check_directories(self, directories: list[str]) -> dict[str, Any]:
        """检查目录是否存在和可访问

        Args:
            directories: 目录列表

        Returns:
            目录检查结果
        """
        results = []
        overall_status = "healthy"

        for directory in directories:
            try:
                dir_path = Path(directory)

                if not dir_path.exists():
                    results.append(
                        {
                            "path": directory,
                            "exists": False,
                            "readable": False,
                            "writable": False,
                            "status": "critical",
                        }
                    )
                    overall_status = "critical"
                else:
                    readable = os.access(dir_path, os.R_OK)
                    writable = os.access(dir_path, os.W_OK)

                    status = "healthy"
                    if not readable or not writable:
                        status = "warning"
                        if overall_status != "critical":
                            overall_status = "warning"

                    results.append(
                        {
                            "path": directory,
                            "exists": True,
                            "readable": readable,
                            "writable": writable,
                            "status": status,
                        }
                    )
            except Exception as e:
                logger.error(f"检查目录失败 {directory}: {e}")
                results.append({"path": directory, "error": str(e), "status": "error"})
                if overall_status == "healthy":
                    overall_status = "error"

        return {
            "check": "directories",
            "status": overall_status,
            "directories": results,
            "message": f"检查了 {len(directories)} 个目录",
        }

    def check_files(self, files: list[str]) -> dict[str, Any]:
        """检查文件是否存在和可访问

        Args:
            files: 文件列表

        Returns:
            文件检查结果
        """
        results = []
        overall_status = "healthy"

        for file_path in files:
            try:
                file = Path(file_path)

                if not file.exists():
                    results.append(
                        {
                            "path": file_path,
                            "exists": False,
                            "readable": False,
                            "status": "warning",
                        }
                    )
                    if overall_status == "healthy":
                        overall_status = "warning"
                else:
                    readable = os.access(file, os.R_OK)

                    results.append(
                        {
                            "path": file_path,
                            "exists": True,
                            "readable": readable,
                            "size_kb": round(file.stat().st_size / 1024, 2),
                            "status": "healthy" if readable else "warning",
                        }
                    )
            except Exception as e:
                logger.error(f"检查文件失败 {file_path}: {e}")
                results.append({"path": file_path, "error": str(e), "status": "error"})
                if overall_status == "healthy":
                    overall_status = "error"

        return {
            "check": "files",
            "status": overall_status,
            "files": results,
            "message": f"检查了 {len(files)} 个文件",
        }

    def run_all_checks(
        self, data_dirs: list[str] | None = None, config_files: list[str] | None = None
    ) -> dict[str, Any]:
        """运行所有健康检查

        Args:
            data_dirs: 要检查的数据目录列表
            config_files: 要检查的配置文件列表

        Returns:
            完整的健康检查报告
        """
        checks = []

        # 系统资源检查
        checks.append(self.check_disk_space())
        checks.append(self.check_memory())
        checks.append(self.check_cpu())

        # 目录检查
        if data_dirs:
            checks.append(self.check_directories(data_dirs))

        # 文件检查
        if config_files:
            checks.append(self.check_files(config_files))

        # 汇总状态
        statuses = [check["status"] for check in checks]
        if "critical" in statuses:
            overall_status = "critical"
        elif "error" in statuses:
            overall_status = "error"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "healthy": statuses.count("healthy"),
                "warnings": statuses.count("warning"),
                "critical": statuses.count("critical"),
                "errors": statuses.count("error"),
            },
        }


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, max_metrics: int = 1000):
        """初始化性能监控器

        Args:
            max_metrics: 保留的最大指标数量
        """
        self.max_metrics = max_metrics
        self._metrics: dict[str, deque] = {}
        self._lock = Lock()

    def record_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """记录性能指标

        Args:
            operation: 操作名称
            duration_ms: 持续时间(毫秒)
            success: 是否成功
            metadata: 额外的元数据
        """
        with self._lock:
            if operation not in self._metrics:
                self._metrics[operation] = deque(maxlen=self.max_metrics)

            metric = {
                "timestamp": datetime.now().isoformat(),
                "duration_ms": duration_ms,
                "success": success,
                "metadata": metadata or {},
            }

            self._metrics[operation].append(metric)

    def get_stats(self, operation: str) -> dict[str, Any]:
        """获取操作的统计信息

        Args:
            operation: 操作名称

        Returns:
            统计信息字典
        """
        with self._lock:
            if operation not in self._metrics or not self._metrics[operation]:
                return {"operation": operation, "count": 0, "message": "没有记录"}

            metrics = list(self._metrics[operation])
            durations = [m["duration_ms"] for m in metrics]
            successes = [m["success"] for m in metrics]

            return {
                "operation": operation,
                "count": len(metrics),
                "avg_duration_ms": round(sum(durations) / len(durations), 2),
                "min_duration_ms": round(min(durations), 2),
                "max_duration_ms": round(max(durations), 2),
                "success_rate": round(
                    (successes.count(True) / len(successes)) * 100, 2
                ),
                "total_successes": successes.count(True),
                "total_failures": successes.count(False),
            }

    def get_all_stats(self) -> dict[str, Any]:
        """获取所有操作的统计信息

        Returns:
            所有统计信息
        """
        with self._lock:
            return {
                "operations": {
                    operation: self.get_stats(operation) for operation in self._metrics
                },
                "total_operations": len(self._metrics),
            }

    def clear_metrics(self, operation: str | None = None) -> None:
        """清空指标

        Args:
            operation: 操作名称,如果为None则清空所有
        """
        with self._lock:
            if operation:
                if operation in self._metrics:
                    self._metrics[operation].clear()
            else:
                self._metrics.clear()

    def get_recent_metrics(
        self, operation: str, count: int = 10
    ) -> list[dict[str, Any]]:
        """获取最近的指标

        Args:
            operation: 操作名称
            count: 返回数量

        Returns:
            最近的指标列表
        """
        with self._lock:
            if operation not in self._metrics:
                return []

            metrics = list(self._metrics[operation])
            return metrics[-count:]


# 全局健康检查器和性能监控器
health_checker = HealthChecker()
performance_monitor = PerformanceMonitor()


def time_operation(operation_name: str):
    """操作计时装饰器

    使用方法:
    @time_operation("保存记录")
    def save_record(self, record):
        ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                metadata = {"error": error} if error else {}
                performance_monitor.record_metric(
                    operation_name, duration_ms, success, metadata
                )

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
