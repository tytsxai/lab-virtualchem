"""
健康监控模块

监控应用健康状态，包括：
- 存储空间
- 内存使用
- 依赖可用性
- 配置完整性
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from .log_safety import sanitize_log_data

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """健康状态"""

    status: str  # healthy, degraded, unhealthy
    message: str
    timestamp: datetime
    details: dict[str, Any]


class HealthMonitor:
    """健康监控器"""

    def __init__(self, config: dict | None = None):
        """
        初始化健康监控器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.checks = []
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """注册默认检查项"""
        self.checks = [
            self.check_storage,
            self.check_memory,
            self.check_dependencies,
            self.check_configuration,
        ]

    def check_storage(self) -> HealthStatus:
        """检查存储空间"""
        try:
            # 检查数据目录
            data_dir = Path("data")
            if not data_dir.exists():
                data_dir.mkdir(parents=True, exist_ok=True)

            # 检查磁盘空间
            disk = psutil.disk_usage(str(data_dir.resolve()))
            free_gb = disk.free / (1024**3)
            percent_free = (disk.free / disk.total) * 100

            if free_gb < 1.0:  # 小于1GB
                return HealthStatus(
                    status="unhealthy",
                    message=f"磁盘空间不足: {free_gb:.2f}GB",
                    timestamp=datetime.now(),
                    details={"free_gb": free_gb, "percent_free": percent_free},
                )
            elif free_gb < 5.0:  # 小于5GB
                return HealthStatus(
                    status="degraded",
                    message=f"磁盘空间较低: {free_gb:.2f}GB",
                    timestamp=datetime.now(),
                    details={"free_gb": free_gb, "percent_free": percent_free},
                )

            return HealthStatus(
                status="healthy",
                message=f"存储正常: {free_gb:.2f}GB 可用",
                timestamp=datetime.now(),
                details={"free_gb": free_gb, "percent_free": percent_free},
            )

        except Exception as e:
            logger.error("存储检查失败: %s", sanitize_log_data(str(e)))
            return HealthStatus(
                status="unhealthy",
                message=f"存储检查失败: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    def check_memory(self) -> HealthStatus:
        """检查内存使用"""
        try:
            # 系统内存
            mem = psutil.virtual_memory()
            percent_used = mem.percent

            # 进程内存
            process = psutil.Process()
            process_mem_mb = process.memory_info().rss / (1024**2)

            max_usage_mb = (
                self.config.get("performance", {})
                .get("memory", {})
                .get("max_usage_mb", 500)
            )

            if process_mem_mb > max_usage_mb * 1.5:
                return HealthStatus(
                    status="unhealthy",
                    message=f"内存使用过高: {process_mem_mb:.0f}MB / {max_usage_mb}MB",
                    timestamp=datetime.now(),
                    details={
                        "process_mb": process_mem_mb,
                        "system_percent": percent_used,
                        "limit_mb": max_usage_mb,
                    },
                )
            elif process_mem_mb > max_usage_mb:
                return HealthStatus(
                    status="degraded",
                    message=f"内存使用较高: {process_mem_mb:.0f}MB / {max_usage_mb}MB",
                    timestamp=datetime.now(),
                    details={
                        "process_mb": process_mem_mb,
                        "system_percent": percent_used,
                        "limit_mb": max_usage_mb,
                    },
                )

            return HealthStatus(
                status="healthy",
                message=f"内存正常: {process_mem_mb:.0f}MB",
                timestamp=datetime.now(),
                details={
                    "process_mb": process_mem_mb,
                    "system_percent": percent_used,
                    "limit_mb": max_usage_mb,
                },
            )

        except Exception as e:
            logger.error("内存检查失败: %s", sanitize_log_data(str(e)))
            return HealthStatus(
                status="unhealthy",
                message=f"内存检查失败: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    def check_dependencies(self) -> HealthStatus:
        """检查依赖可用性"""
        try:
            missing_core: list[str] = []
            missing_optional: list[str] = []

            # 核心依赖：缺失则无法启动/运行核心功能
            core_deps = {
                "PySide6": "PySide6",
                "numpy": "numpy",
                "pydantic": "pydantic",
                "PyYAML": "yaml",
            }

            # 可选依赖：缺失仅导致部分功能降级（例如打包 lite 构建会主动排除）
            optional_deps = {
                "matplotlib": "matplotlib",
                "pandas": "pandas",
                "numba": "numba",
            }

            for display_name, module_name in core_deps.items():
                try:
                    __import__(module_name)
                except ImportError:
                    missing_core.append(display_name)

            for display_name, module_name in optional_deps.items():
                try:
                    __import__(module_name)
                except ImportError:
                    missing_optional.append(display_name)

            if missing_core:
                return HealthStatus(
                    status="unhealthy",
                    message=f"缺少关键依赖: {', '.join(missing_core)}",
                    timestamp=datetime.now(),
                    details={
                        "missing_core": missing_core,
                        "missing_optional": missing_optional,
                    },
                )

            if missing_optional:
                return HealthStatus(
                    status="degraded",
                    message=f"部分可选依赖缺失（功能将降级）: {', '.join(missing_optional)}",
                    timestamp=datetime.now(),
                    details={"missing_optional": missing_optional},
                )

            return HealthStatus(
                status="healthy",
                message="所有依赖可用",
                timestamp=datetime.now(),
                details={
                    "checked_core": list(core_deps.keys()),
                    "checked_optional": list(optional_deps.keys()),
                },
            )

        except Exception as e:
            logger.error("依赖检查失败: %s", sanitize_log_data(str(e)))
            return HealthStatus(
                status="unhealthy",
                message=f"依赖检查失败: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    def check_configuration(self) -> HealthStatus:
        """检查配置完整性"""
        try:
            # 检查关键配置文件
            config_files = [
                "config/default.yaml",
                "config/experiments",
                "config/equipment",
            ]

            missing_configs = []
            for config_path in config_files:
                if not Path(config_path).exists():
                    missing_configs.append(config_path)

            if missing_configs:
                return HealthStatus(
                    status="degraded",
                    message=f"部分配置缺失: {len(missing_configs)}个文件",
                    timestamp=datetime.now(),
                    details={"missing": missing_configs},
                )

            return HealthStatus(
                status="healthy",
                message="配置完整",
                timestamp=datetime.now(),
                details={"checked": len(config_files)},
            )

        except Exception as e:
            logger.error("配置检查失败: %s", sanitize_log_data(str(e)))
            return HealthStatus(
                status="unhealthy",
                message=f"配置检查失败: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
            )

    def run_all_checks(self) -> dict[str, HealthStatus]:
        """运行所有健康检查"""
        results = {}

        for check in self.checks:
            check_name = check.__name__.replace("check_", "")
            try:
                results[check_name] = check()
            except Exception as e:
                logger.error(
                    "检查 %s 失败: %s",
                    sanitize_log_data(check_name),
                    sanitize_log_data(str(e)),
                )
                results[check_name] = HealthStatus(
                    status="unhealthy",
                    message=f"检查失败: {str(e)}",
                    timestamp=datetime.now(),
                    details={"error": str(e)},
                )

        return results

    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        results = self.run_all_checks()

        # 统计各状态数量
        status_counts = {"healthy": 0, "degraded": 0, "unhealthy": 0}

        for result in results.values():
            status_counts[result.status] += 1

        # 决定整体状态
        if status_counts["unhealthy"] > 0:
            overall = "unhealthy"
            message = f"发现 {status_counts['unhealthy']} 个严重问题"
        elif status_counts["degraded"] > 0:
            overall = "degraded"
            message = f"发现 {status_counts['degraded']} 个警告"
        else:
            overall = "healthy"
            message = "系统运行正常"

        return HealthStatus(
            status=overall,
            message=message,
            timestamp=datetime.now(),
            details={"checks": results, "summary": status_counts},
        )


# 单例实例
_health_monitor: HealthMonitor | None = None


def get_health_monitor(config: dict | None = None) -> HealthMonitor:
    """获取健康监控器单例"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor(config)
    return _health_monitor
