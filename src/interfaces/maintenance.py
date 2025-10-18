"""
系统维护接口定义

定义缓存清理、错误修复等系统维护功能的抽象接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MaintenanceTaskType(str, Enum):
    """维护任务类型"""

    CACHE_CLEAR = "cache_clear"  # 缓存清理
    ERROR_FIX = "error_fix"  # 错误修复
    DATA_VALIDATE = "data_validate"  # 数据验证
    LOG_CLEANUP = "log_cleanup"  # 日志清理
    TEMP_CLEANUP = "temp_cleanup"  # 临时文件清理
    DATABASE_OPTIMIZE = "database_optimize"  # 数据库优化
    CONFIG_VALIDATE = "config_validate"  # 配置验证
    PERMISSION_FIX = "permission_fix"  # 权限修复


class MaintenanceStatus(str, Enum):
    """维护状态"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class IssueSeverity(str, Enum):
    """问题严重程度"""

    CRITICAL = "critical"  # 严重
    HIGH = "high"  # 高
    MEDIUM = "medium"  # 中
    LOW = "low"  # 低
    INFO = "info"  # 信息


@dataclass
class MaintenanceIssue:
    """维护问题"""

    issue_id: str  # 问题ID
    severity: IssueSeverity  # 严重程度
    category: str  # 分类
    title: str  # 标题
    description: str  # 描述
    fix_available: bool = False  # 是否可修复
    fix_description: str = ""  # 修复说明
    metadata: dict[str, Any] = None  # 元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MaintenanceResult:
    """维护结果"""

    task_type: MaintenanceTaskType  # 任务类型
    status: MaintenanceStatus  # 状态
    success: bool  # 是否成功
    message: str  # 消息
    items_processed: int = 0  # 处理项目数
    items_fixed: int = 0  # 修复项目数
    bytes_freed: int = 0  # 释放字节数
    duration_seconds: float = 0.0  # 持续时间(秒)
    details: dict[str, Any] = None  # 详细信息
    errors: list[str] = None  # 错误列表

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.errors is None:
            self.errors = []


class ICacheCleaner(ABC):
    """缓存清理器接口"""

    @abstractmethod
    def scan_cache(self) -> dict[str, Any]:
        """
        扫描缓存

        Returns:
            缓存信息字典
        """
        pass

    @abstractmethod
    def clear_cache(self, cache_types: list[str] | None = None) -> MaintenanceResult:
        """
        清理缓存

        Args:
            cache_types: 缓存类型列表，None表示清理所有

        Returns:
            维护结果
        """
        pass

    @abstractmethod
    def clear_expired_cache(self) -> MaintenanceResult:
        """
        清理过期缓存

        Returns:
            维护结果
        """
        pass

    @abstractmethod
    def get_cache_size(self) -> int:
        """
        获取缓存总大小

        Returns:
            缓存大小（字节）
        """
        pass


class IErrorFixer(ABC):
    """错误修复器接口"""

    @abstractmethod
    def diagnose_issues(self) -> list[MaintenanceIssue]:
        """
        诊断问题

        Returns:
            问题列表
        """
        pass

    @abstractmethod
    def fix_issue(self, issue_id: str) -> MaintenanceResult:
        """
        修复单个问题

        Args:
            issue_id: 问题ID

        Returns:
            维护结果
        """
        pass

    @abstractmethod
    def fix_all_issues(self, severity_threshold: IssueSeverity = IssueSeverity.MEDIUM) -> MaintenanceResult:
        """
        修复所有问题

        Args:
            severity_threshold: 严重程度阈值

        Returns:
            维护结果
        """
        pass

    @abstractmethod
    def validate_system(self) -> tuple[bool, list[str]]:
        """
        验证系统

        Returns:
            (是否健康, 问题列表)
        """
        pass


class IDataValidator(ABC):
    """数据验证器接口"""

    @abstractmethod
    def validate_data_integrity(self) -> list[MaintenanceIssue]:
        """
        验证数据完整性

        Returns:
            问题列表
        """
        pass

    @abstractmethod
    def repair_data(self, issue_id: str) -> MaintenanceResult:
        """
        修复数据

        Args:
            issue_id: 问题ID

        Returns:
            维护结果
        """
        pass


class ISystemMaintenance(ABC):
    """系统维护接口 - 主接口"""

    @abstractmethod
    def run_maintenance(
        self,
        task_types: list[MaintenanceTaskType],
        options: dict[str, Any] | None = None,
    ) -> list[MaintenanceResult]:
        """
        运行维护任务

        Args:
            task_types: 任务类型列表
            options: 选项

        Returns:
            维护结果列表
        """
        pass

    @abstractmethod
    def get_system_health(self) -> dict[str, Any]:
        """
        获取系统健康状态

        Returns:
            健康状态字典
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
    def schedule_maintenance(
        self,
        task_type: MaintenanceTaskType,
        schedule_time: datetime,
        options: dict[str, Any] | None = None,
    ) -> str:
        """
        计划维护任务

        Args:
            task_type: 任务类型
            schedule_time: 计划时间
            options: 选项

        Returns:
            任务ID
        """
        pass

    @abstractmethod
    def cancel_scheduled_task(self, task_id: str) -> bool:
        """
        取消计划任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功
        """
        pass
