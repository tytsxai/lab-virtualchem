"""
监控配置管理
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MonitoringConfig:
    """监控配置"""

    # 基础配置
    enabled: bool = True
    app_name: str = "VirtualChemLab"

    # 前端监控
    frontend_enabled: bool = True
    frontend_max_errors: int = 1000
    frontend_max_events: int = 10000

    # 后端监控
    backend_enabled: bool = True
    apm_enabled: bool = True
    resource_monitoring_enabled: bool = True
    resource_monitoring_interval: int = 60

    # 追踪
    tracing_enabled: bool = True
    tracing_sample_rate: float = 1.0

    # 告警
    alerting_enabled: bool = True
    alerting_auto_check: bool = True
    alerting_check_interval: int = 60

    # 健康检查阈值
    cpu_warning_threshold: int = 70
    cpu_critical_threshold: int = 85
    memory_warning_threshold: int = 80
    memory_critical_threshold: int = 90
    disk_warning_threshold: int = 80
    disk_critical_threshold: int = 90

    # 日志目录
    log_base_dir: Path = Path("logs")

    @classmethod
    def from_file(cls, config_file: Path) -> "MonitoringConfig":
        """从配置文件加载"""
        if not config_file.exists():
            return cls()

        with open(config_file, encoding="utf-8") as f:
            data = json.load(f)

        monitoring_config = data.get("monitoring", {})

        frontend_config = monitoring_config.get("frontend", {})
        backend_config = monitoring_config.get("backend", {})
        tracing_config = monitoring_config.get("tracing", {})
        alerting_config = monitoring_config.get("alerting", {})
        health_thresholds = backend_config.get("health_check", {}).get("thresholds", {})

        return cls(
            enabled=monitoring_config.get("enabled", True),
            app_name=monitoring_config.get("app_name", "VirtualChemLab"),
            # 前端
            frontend_enabled=frontend_config.get("error_tracking", {}).get(
                "enabled", True
            ),
            frontend_max_errors=frontend_config.get("error_tracking", {}).get(
                "max_errors", 1000
            ),
            frontend_max_events=frontend_config.get("behavior_tracking", {}).get(
                "max_events", 10000
            ),
            # 后端
            backend_enabled=backend_config.get("apm", {}).get("enabled", True),
            apm_enabled=backend_config.get("apm", {}).get("enabled", True),
            resource_monitoring_enabled=backend_config.get(
                "resource_monitoring", {}
            ).get("enabled", True),
            resource_monitoring_interval=backend_config.get(
                "resource_monitoring", {}
            ).get("interval_seconds", 60),
            # 追踪
            tracing_enabled=tracing_config.get("enabled", True),
            tracing_sample_rate=tracing_config.get("sample_rate", 1.0),
            # 告警
            alerting_enabled=alerting_config.get("enabled", True),
            alerting_auto_check=alerting_config.get("auto_check", True),
            alerting_check_interval=alerting_config.get("check_interval_seconds", 60),
            # 阈值
            cpu_warning_threshold=health_thresholds.get("cpu_warning", 70),
            cpu_critical_threshold=health_thresholds.get("cpu_critical", 85),
            memory_warning_threshold=health_thresholds.get("memory_warning", 80),
            memory_critical_threshold=health_thresholds.get("memory_critical", 90),
            disk_warning_threshold=health_thresholds.get("disk_warning", 80),
            disk_critical_threshold=health_thresholds.get("disk_critical", 90),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "enabled": self.enabled,
            "app_name": self.app_name,
            "frontend": {
                "enabled": self.frontend_enabled,
                "max_errors": self.frontend_max_errors,
                "max_events": self.frontend_max_events,
            },
            "backend": {
                "enabled": self.backend_enabled,
                "apm_enabled": self.apm_enabled,
                "resource_monitoring_enabled": self.resource_monitoring_enabled,
                "resource_monitoring_interval": self.resource_monitoring_interval,
            },
            "tracing": {
                "enabled": self.tracing_enabled,
                "sample_rate": self.tracing_sample_rate,
            },
            "alerting": {
                "enabled": self.alerting_enabled,
                "auto_check": self.alerting_auto_check,
                "check_interval": self.alerting_check_interval,
            },
            "thresholds": {
                "cpu_warning": self.cpu_warning_threshold,
                "cpu_critical": self.cpu_critical_threshold,
                "memory_warning": self.memory_warning_threshold,
                "memory_critical": self.memory_critical_threshold,
                "disk_warning": self.disk_warning_threshold,
                "disk_critical": self.disk_critical_threshold,
            },
        }


def load_monitoring_config(config_file: Path | None = None) -> MonitoringConfig:
    """加载监控配置"""
    if config_file is None:
        config_file = Path("config/monitoring_config.json")

    return MonitoringConfig.from_file(config_file)
