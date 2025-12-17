"""
自定义异常类体系

提供统一的异常定义，所有异常继承自BaseAppException
"""

import traceback
from typing import Any

from .error_codes import ErrorCode, ErrorCodeRegistry


class BaseAppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode | None = None,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
        user_message: str | None = None,
        recovery_hint: str | None = None,
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误码对象
            details: 详细信息
            original_exception: 原始异常
            user_message: 用户友好消息
            recovery_hint: 恢复提示
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or ErrorCodeRegistry.UNKNOWN_ERROR
        self.details = details or {}
        self.original_exception = original_exception
        self.user_message = user_message or self.error_code.message_zh
        self.recovery_hint = recovery_hint
        self.traceback = traceback.format_exc() if original_exception else None

    def to_dict(self, language: str = "zh") -> dict[str, Any]:
        """
        转换为字典

        Args:
            language: 语言 (zh/en)

        Returns:
            字典表示
        """
        error_message = (
            self.error_code.message_zh
            if language == "zh"
            else self.error_code.message_en
        )

        return {
            "success": False,
            "error": {
                "code": self.error_code.code,
                "type": self.error_code.name,
                "category": self.error_code.category.value,
                "message": error_message,
                "user_message": self.user_message,
                "details": self.details,
                "recoverable": self.error_code.recoverable,
                "severity": self.error_code.severity,
                "recovery_hint": self.recovery_hint,
                "help_url": self.error_code.help_url,
            },
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.error_code.name}] {self.message}"

    def __repr__(self) -> str:
        """开发者表示"""
        return (
            f"{self.__class__.__name__}(code={self.error_code.code}, "
            f"message='{self.message}', details={self.details})"
        )


class AuthenticationError(BaseAppException):
    """认证错误"""

    def __init__(
        self,
        message: str = "认证失败",
        error_code: ErrorCode | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.AUTH_REQUIRED
        super().__init__(message, error_code, **kwargs)


class AuthorizationError(BaseAppException):
    """授权错误"""

    def __init__(
        self,
        message: str = "权限不足",
        error_code: ErrorCode | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.AUTH_INSUFFICIENT_PERMISSION
        super().__init__(message, error_code, **kwargs)


class DataValidationError(BaseAppException):
    """数据验证错误"""

    def __init__(
        self,
        message: str = "数据验证失败",
        error_code: ErrorCode | None = None,
        field: str | None = None,
        value: Any = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.DATA_VALIDATION_FAILED

        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class ResourceNotFoundError(BaseAppException):
    """资源不存在错误"""

    def __init__(
        self,
        message: str = "资源不存在",
        error_code: ErrorCode | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.RESOURCE_NOT_FOUND

        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class ExperimentError(BaseAppException):
    """实验错误"""

    def __init__(
        self,
        message: str = "实验执行错误",
        error_code: ErrorCode | None = None,
        experiment_id: str | None = None,
        step_id: str | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.EXP_INVALID_STATE

        details = kwargs.get("details", {})
        if experiment_id:
            details["experiment_id"] = experiment_id
        if step_id:
            details["step_id"] = step_id
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class TemplateError(BaseAppException):
    """模板错误"""

    def __init__(
        self,
        message: str = "模板加载失败",
        error_code: ErrorCode | None = None,
        template_id: str | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.TEMPLATE_LOAD_ERROR

        details = kwargs.get("details", {})
        if template_id:
            details["template_id"] = template_id
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class ConfigurationError(BaseAppException):
    """配置错误"""

    def __init__(
        self,
        message: str = "配置错误",
        error_code: ErrorCode | None = None,
        config_key: str | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.SYS_INTERNAL_ERROR

        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class LicenseError(BaseAppException):
    """许可证错误"""

    def __init__(
        self,
        message: str = "许可证无效",
        error_code: ErrorCode | None = None,
        license_id: str | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.LICENSE_INVALID

        details = kwargs.get("details", {})
        if license_id:
            details["license_id"] = license_id
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class NetworkError(BaseAppException):
    """网络错误"""

    def __init__(
        self,
        message: str = "网络连接失败",
        error_code: ErrorCode | None = None,
        url: str | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.NET_CONNECTION_FAILED

        details = kwargs.get("details", {})
        if url:
            details["url"] = url
        kwargs["details"] = details

        super().__init__(message, error_code, **kwargs)


class SystemError(BaseAppException):
    """系统错误"""

    def __init__(
        self,
        message: str = "系统内部错误",
        error_code: ErrorCode | None = None,
        **kwargs,
    ):
        if error_code is None:
            error_code = ErrorCodeRegistry.SYS_INTERNAL_ERROR

        super().__init__(message, error_code, **kwargs)


# 便捷函数：从标准Python异常创建应用异常
def from_standard_exception(exc: Exception, context: str = "") -> BaseAppException:
    """
    从标准Python异常创建应用异常

    Args:
        exc: 标准异常
        context: 上下文信息

    Returns:
        应用异常对象
    """
    message = f"{context}: {str(exc)}" if context else str(exc)

    # 文件相关错误
    if isinstance(exc, FileNotFoundError):
        return SystemError(
            message,
            error_code=ErrorCodeRegistry.SYS_FILE_NOT_FOUND,
            original_exception=exc,
            details={"file": str(exc.filename) if hasattr(exc, "filename") else None},
        )

    # 权限错误
    if isinstance(exc, PermissionError):
        return SystemError(
            message,
            error_code=ErrorCodeRegistry.SYS_PERMISSION_DENIED,
            original_exception=exc,
        )

    # 超时错误
    if isinstance(exc, TimeoutError):
        return NetworkError(
            message,
            error_code=ErrorCodeRegistry.NET_TIMEOUT,
            original_exception=exc,
        )

    # 键错误（配置相关）
    if isinstance(exc, KeyError):
        return ConfigurationError(
            message,
            original_exception=exc,
            details={"missing_key": str(exc)},
        )

    # 值错误（验证相关）
    if isinstance(exc, ValueError):
        return DataValidationError(
            message,
            error_code=ErrorCodeRegistry.VALIDATION_INVALID_TYPE,
            original_exception=exc,
        )

    # 类型错误
    if isinstance(exc, TypeError):
        return DataValidationError(
            message,
            error_code=ErrorCodeRegistry.VALIDATION_INVALID_TYPE,
            original_exception=exc,
        )

    # 默认：未知错误
    return BaseAppException(
        message,
        error_code=ErrorCodeRegistry.UNKNOWN_ERROR,
        original_exception=exc,
    )
