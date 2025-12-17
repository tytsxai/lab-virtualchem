"""系统维护服务契约"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..interfaces.maintenance import (
    IssueSeverity,
    MaintenanceIssue,
    MaintenanceResult,
    MaintenanceTaskType,
)


class CacheType(str, Enum):
    """缓存类型"""

    MEMORY = "memory"  # 内存缓存
    DISK = "disk"  # 磁盘缓存
    REDIS = "redis"  # Redis缓存
    QUERY = "query"  # 查询缓存
    TEMPLATE = "template"  # 模板缓存
    ASSET = "asset"  # 资源缓存
    ALL = "all"  # 所有缓存


@dataclass
class MaintenanceServiceConfig:
    """维护服务配置"""

    auto_clean_cache: bool = True  # 是否自动清理缓存
    cache_max_age_hours: int = 24  # 缓存最大年龄(小时)
    auto_fix_errors: bool = False  # 是否自动修复错误
    log_max_age_days: int = 30  # 日志最大年龄(天)
    temp_max_age_hours: int = 2  # 临时文件最大年龄(小时)
    enable_scheduled_tasks: bool = True  # 启用计划任务
    max_history_records: int = 1000  # 最大历史记录数


@dataclass
class CacheInfo:
    """缓存信息"""

    cache_type: CacheType  # 缓存类型
    item_count: int  # 项目数量
    size_bytes: int  # 大小(字节)
    expired_count: int = 0  # 过期数量
    last_cleaned: datetime | None = None  # 最后清理时间
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class CleanupRequest:
    """清理请求DTO"""

    cache_types: list[CacheType] = field(
        default_factory=lambda: [CacheType.ALL]
    )  # 缓存类型
    include_expired_only: bool = False  # 仅清理过期项
    max_age_hours: int | None = None  # 最大年龄(小时)
    dry_run: bool = False  # 试运行(不实际删除)


@dataclass
class CleanupResponse:
    """清理响应DTO"""

    success: bool  # 是否成功
    cache_infos: list[CacheInfo] = field(default_factory=list)  # 缓存信息
    total_items_cleaned: int = 0  # 清理项目总数
    total_bytes_freed: int = 0  # 释放字节总数
    duration_seconds: float = 0.0  # 持续时间
    message: str = ""  # 消息
    errors: list[str] = field(default_factory=list)  # 错误列表


@dataclass
class DiagnosisRequest:
    """诊断请求DTO"""

    scan_cache: bool = True  # 扫描缓存
    scan_data: bool = True  # 扫描数据
    scan_config: bool = True  # 扫描配置
    scan_permissions: bool = True  # 扫描权限
    scan_logs: bool = True  # 扫描日志
    severity_threshold: IssueSeverity = IssueSeverity.LOW  # 严重程度阈值


@dataclass
class DiagnosisResponse:
    """诊断响应DTO"""

    success: bool  # 是否成功
    issues: list[MaintenanceIssue] = field(default_factory=list)  # 问题列表
    fixable_count: int = 0  # 可修复数量
    critical_count: int = 0  # 严重问题数量
    health_score: float = 100.0  # 健康评分(0-100)
    message: str = ""  # 消息


@dataclass
class FixRequest:
    """修复请求DTO"""

    issue_ids: list[str] = field(default_factory=list)  # 问题ID列表
    fix_all: bool = False  # 修复所有
    severity_threshold: IssueSeverity = IssueSeverity.MEDIUM  # 严重程度阈值
    auto_backup: bool = True  # 自动备份
    dry_run: bool = False  # 试运行


@dataclass
class FixResponse:
    """修复响应DTO"""

    success: bool  # 是否成功
    fixed_issues: list[str] = field(default_factory=list)  # 已修复问题ID
    failed_issues: list[str] = field(default_factory=list)  # 失败问题ID
    total_fixed: int = 0  # 修复总数
    total_failed: int = 0  # 失败总数
    backup_path: str | None = None  # 备份路径
    message: str = ""  # 消息
    errors: list[str] = field(default_factory=list)  # 错误列表


@dataclass
class HealthCheckResponse:
    """健康检查响应DTO"""

    healthy: bool  # 是否健康
    health_score: float  # 健康评分(0-100)
    cache_status: dict[str, Any] = field(default_factory=dict)  # 缓存状态
    data_status: dict[str, Any] = field(default_factory=dict)  # 数据状态
    error_status: dict[str, Any] = field(default_factory=dict)  # 错误状态
    system_status: dict[str, Any] = field(default_factory=dict)  # 系统状态
    issues_summary: dict[str, int] = field(default_factory=dict)  # 问题摘要
    recommendations: list[str] = field(default_factory=list)  # 建议
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳


@dataclass
class MaintenanceTaskRequest:
    """维护任务请求DTO"""

    task_types: list[MaintenanceTaskType]  # 任务类型列表
    auto_fix: bool = False  # 自动修复
    cleanup_cache: bool = True  # 清理缓存
    cleanup_logs: bool = True  # 清理日志
    validate_data: bool = True  # 验证数据
    optimize_database: bool = False  # 优化数据库
    dry_run: bool = False  # 试运行
    options: dict[str, Any] = field(default_factory=dict)  # 额外选项


@dataclass
class MaintenanceTaskResponse:
    """维护任务响应DTO"""

    success: bool  # 是否成功
    results: list[MaintenanceResult] = field(default_factory=list)  # 结果列表
    total_duration_seconds: float = 0.0  # 总持续时间
    total_items_processed: int = 0  # 处理项目总数
    total_bytes_freed: int = 0  # 释放字节总数
    message: str = ""  # 消息
    errors: list[str] = field(default_factory=list)  # 错误列表
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳


class MaintenanceService(ABC):
    """系统维护服务抽象类"""

    @abstractmethod
    def cleanup_cache(self, request: CleanupRequest) -> CleanupResponse:
        """
        清理缓存

        Args:
            request: 清理请求

        Returns:
            清理响应
        """
        pass

    @abstractmethod
    def diagnose_system(self, request: DiagnosisRequest) -> DiagnosisResponse:
        """
        诊断系统

        Args:
            request: 诊断请求

        Returns:
            诊断响应
        """
        pass

    @abstractmethod
    def fix_issues(self, request: FixRequest) -> FixResponse:
        """
        修复问题

        Args:
            request: 修复请求

        Returns:
            修复响应
        """
        pass

    @abstractmethod
    def check_health(self) -> HealthCheckResponse:
        """
        检查健康状态

        Returns:
            健康检查响应
        """
        pass

    @abstractmethod
    def run_maintenance(
        self, request: MaintenanceTaskRequest
    ) -> MaintenanceTaskResponse:
        """
        运行维护任务

        Args:
            request: 维护任务请求

        Returns:
            维护任务响应
        """
        pass

    @abstractmethod
    def get_cache_info(self, cache_type: CacheType | None = None) -> list[CacheInfo]:
        """
        获取缓存信息

        Args:
            cache_type: 缓存类型(可选)

        Returns:
            缓存信息列表
        """
        pass

    @abstractmethod
    def get_maintenance_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        获取维护历史

        Args:
            limit: 限制数量

        Returns:
            维护历史列表
        """
        pass

    @abstractmethod
    def export_report(self, output_path: str, format: str = "json") -> bool:
        """
        导出报告

        Args:
            output_path: 输出路径
            format: 格式(json/csv/html)

        Returns:
            是否成功
        """
        pass
