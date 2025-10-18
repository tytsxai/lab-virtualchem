"""
服务契约层 - 定义服务级别的契约和数据传输对象(DTO)
遵循单一职责原则(SRP)和里氏替换原则(LSP)
"""

from .experiment_service import (
    ExperimentRequest,
    ExperimentResponse,
    ExperimentService,
    ExperimentServiceConfig,
    StepSubmissionRequest,
    StepSubmissionResponse,
)
from .maintenance_service import (
    CacheType,
    CleanupRequest,
    CleanupResponse,
    DiagnosisRequest,
    DiagnosisResponse,
    FixRequest,
    FixResponse,
    HealthCheckResponse,
    MaintenanceService,
    MaintenanceServiceConfig,
    MaintenanceTaskRequest,
    MaintenanceTaskResponse,
)
from .plugin_service import (
    PluginExecuteRequest,
    PluginExecuteResponse,
    PluginService,
    PluginServiceConfig,
)
from .report_service import (
    ReportRequest,
    ReportResponse,
    ReportService,
    ReportServiceConfig,
)
from .storage_service import (
    QueryRequest,
    QueryResponse,
    SaveRequest,
    SaveResponse,
    StorageService,
    StorageServiceConfig,
)

__all__ = [
    # 实验服务
    "ExperimentService",
    "ExperimentServiceConfig",
    "ExperimentRequest",
    "ExperimentResponse",
    "StepSubmissionRequest",
    "StepSubmissionResponse",
    # 存储服务
    "StorageService",
    "StorageServiceConfig",
    "SaveRequest",
    "SaveResponse",
    "QueryRequest",
    "QueryResponse",
    # 报告服务
    "ReportService",
    "ReportServiceConfig",
    "ReportRequest",
    "ReportResponse",
    # 插件服务
    "PluginService",
    "PluginServiceConfig",
    "PluginExecuteRequest",
    "PluginExecuteResponse",
    # 维护服务
    "MaintenanceService",
    "MaintenanceServiceConfig",
    "CacheType",
    "CleanupRequest",
    "CleanupResponse",
    "DiagnosisRequest",
    "DiagnosisResponse",
    "FixRequest",
    "FixResponse",
    "HealthCheckResponse",
    "MaintenanceTaskRequest",
    "MaintenanceTaskResponse",
]
