"""
完整的错误处理系统

提供统一的错误码、异常定义、错误处理、日志记录和恢复策略
"""

from .error_analytics import (
    ErrorAnalytics,
    ErrorMetrics,
    ErrorMonitor,
    error_monitor,
)
from .error_codes import ErrorCategory, ErrorCode, ErrorCodeRegistry
from .error_handler import (
    GlobalErrorHandler,
    async_safe_execute,
    error_handler,
    install_global_exception_hook,
    safe_context,
    safe_execute,
)
from .error_interceptor import (
    ConsoleErrorInterceptor,
    ErrorInterceptor,
    global_error_interceptor,
    install_console_error_interceptor,
    install_error_interceptor,
    uninstall_error_interceptor,
)
from .error_recovery import (
    ErrorRecoverySystem,
    RecoveryAction,
    RecoveryStrategy,
    auto_recover,
    fallback,
    recovery_manager,
    retry,
)
from .error_reporter import (
    ErrorReporter,
    NotificationChannel,
    NotificationLevel,
    error_reporter,
)
from .error_sampler import (
    ErrorSampler,
    SamplingRule,
    error_sampler,
)
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseAppException,
    ConfigurationError,
    DataValidationError,
    ExperimentError,
    LicenseError,
    NetworkError,
    ResourceNotFoundError,
    TemplateError,
    from_standard_exception,
)
from .exceptions import (
    SystemError as AppSystemError,
)

__all__ = [
    # 错误码
    "ErrorCode",
    "ErrorCodeRegistry",
    "ErrorCategory",
    # 异常类
    "BaseAppException",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "DataValidationError",
    "ExperimentError",
    "LicenseError",
    "NetworkError",
    "ResourceNotFoundError",
    "AppSystemError",
    "TemplateError",
    "from_standard_exception",
    # 错误处理
    "GlobalErrorHandler",
    "error_handler",
    "safe_execute",
    "async_safe_execute",
    "safe_context",
    "install_global_exception_hook",
    # 错误报告
    "ErrorReporter",
    "error_reporter",
    "NotificationChannel",
    "NotificationLevel",
    # 错误恢复
    "ErrorRecoverySystem",
    "RecoveryStrategy",
    "RecoveryAction",
    "recovery_manager",
    "auto_recover",
    "retry",
    "fallback",
    # 错误拦截
    "ErrorInterceptor",
    "global_error_interceptor",
    "install_error_interceptor",
    "uninstall_error_interceptor",
    "ConsoleErrorInterceptor",
    "install_console_error_interceptor",
    # 错误分析
    "ErrorAnalytics",
    "ErrorMonitor",
    "ErrorMetrics",
    "error_monitor",
    # 错误采样
    "ErrorSampler",
    "SamplingRule",
    "error_sampler",
]
