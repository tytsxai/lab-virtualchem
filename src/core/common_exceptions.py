"""
统一异常处理系统
提供应用程序级别的统一异常定义和处理机制
"""

from __future__ import annotations

import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    NETWORK = "network"
    STORAGE = "storage"
    FILE_SYSTEM = "file_system"
    DATABASE = "database"
    UI = "ui"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"


class VirtualChemLabError(Exception):
    """VirtualChemLab 基础异常类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = self._get_timestamp()

        # 记录错误
        self._log_error()

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _log_error(self) -> None:
        """记录错误日志"""
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.INFO,
            ErrorSeverity.HIGH: logging.WARNING,
            ErrorSeverity.CRITICAL: logging.ERROR
        }.get(self.severity, logging.ERROR)

        logger.log(
            log_level,
            f"[{self.category.value}] {self.message} (Code: {self.error_code})"
        )

        if self.cause:
            logger.log(log_level, f"Caused by: {self.cause}")
            logger.log(log_level, traceback.format_exc())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "details": self.details,
            "timestamp": self.timestamp,
            "cause": str(self.cause) if self.cause else None
        }

    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}"


class ConfigurationError(VirtualChemLabError):
    """配置错误"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            error_code="CONFIG_ERROR",
            details=details,
            cause=cause
        )
        if config_key:
            self.details["config_key"] = config_key


class ValidationError(VirtualChemLabError):
    """验证错误"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            error_code="VALIDATION_ERROR",
            details=details,
            cause=cause
        )
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)


class NetworkError(VirtualChemLabError):
    """网络错误"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            error_code="NETWORK_ERROR",
            details=details,
            cause=cause
        )
        if url:
            self.details["url"] = url
        if status_code:
            self.details["status_code"] = status_code


class StorageError(VirtualChemLabError):
    """存储错误"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.HIGH,
            error_code="STORAGE_ERROR",
            details=details,
            cause=cause
        )
        if operation:
            self.details["operation"] = operation
        if path:
            self.details["path"] = path


class UIError(VirtualChemLabError):
    """UI错误"""

    def __init__(
        self,
        message: str,
        widget: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.UI,
            severity=ErrorSeverity.MEDIUM,
            error_code="UI_ERROR",
            details=details,
            cause=cause
        )
        if widget:
            self.details["widget"] = widget
        if action:
            self.details["action"] = action


class PerformanceError(VirtualChemLabError):
    """性能错误"""

    def __init__(
        self,
        message: str,
        metric: Optional[str] = None,
        threshold: Optional[float] = None,
        actual_value: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.PERFORMANCE,
            severity=ErrorSeverity.MEDIUM,
            error_code="PERFORMANCE_ERROR",
            details=details,
            cause=cause
        )
        if metric:
            self.details["metric"] = metric
        if threshold is not None:
            self.details["threshold"] = threshold
        if actual_value is not None:
            self.details["actual_value"] = actual_value


class SecurityError(VirtualChemLabError):
    """安全错误"""

    def __init__(
        self,
        message: str,
        threat_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.HIGH,
            error_code="SECURITY_ERROR",
            details=details,
            cause=cause
        )
        if threat_type:
            self.details["threat_type"] = threat_type


class BusinessLogicError(VirtualChemLabError):
    """业务逻辑错误"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details,
            cause=cause
        )
        if operation:
            self.details["operation"] = operation


class SystemError(VirtualChemLabError):
    """系统错误"""

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            error_code="SYSTEM_ERROR",
            details=details,
            cause=cause
        )
        if component:
            self.details["component"] = component


# 错误处理装饰器
def handle_errors(
    error_class: type[VirtualChemLabError] = VirtualChemLabError,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM
):
    """错误处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except VirtualChemLabError:
                # 重新抛出VirtualChemLabError
                raise
            except Exception as e:
                # 包装其他异常
                raise error_class(
                    message=f"Error in {func.__name__}: {str(e)}",
                    category=category,
                    severity=severity,
                    cause=e
                ) from e
        return wrapper
    return decorator


# 错误恢复装饰器
def recoverable_error(
    fallback_value: Any = None,
    retry_count: int = 0,
    error_class: type[VirtualChemLabError] = VirtualChemLabError
):
    """可恢复错误装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retry_count + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retry_count:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                        continue
                    break

            # 所有重试都失败，返回默认值或抛出异常
            if fallback_value is not None:
                logger.error(f"Function {func.__name__} failed after {retry_count} retries, using fallback")
                return fallback_value
            else:
                raise error_class(
                    message=f"Function {func.__name__} failed after {retry_count} retries",
                    cause=last_error
                )
        return wrapper
    return decorator
