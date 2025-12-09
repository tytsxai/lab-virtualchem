"""
公共错误处理模块
减少重复的错误处理逻辑，提供统一的错误处理接口
"""

import logging
from functools import wraps
from typing import Any, Callable, Type

from .common_exceptions import ErrorCategory, ErrorSeverity, VirtualChemLabError

logger = logging.getLogger(__name__)


class CommonErrorHandlers:
    """公共错误处理器"""

    @staticmethod
    def safe_execute_with_default(
        func: Callable,
        default_value: Any = None,
        error_class: Type[VirtualChemLabError] = VirtualChemLabError,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        *args,
        **kwargs
    ) -> Any:
        """安全执行函数，出错时返回默认值"""
        try:
            return func(*args, **kwargs)
        except VirtualChemLabError:
            raise
        except Exception as e:
            error = error_class(
                message=f"Error executing {func.__name__}: {str(e)}",
                category=category,
                severity=severity,
                cause=e
            )
            logger.error(f"Safe execute failed: {error}")
            return default_value

    @staticmethod
    def retry_on_failure(
        max_retries: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        error_class: Type[VirtualChemLabError] = VirtualChemLabError,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        """重试装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time

                last_exception = None
                current_delay = delay

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e

                        if attempt == max_retries:
                            # 最后一次尝试失败，抛出错误
                            error = error_class(
                                message=f"Function {func.__name__} failed after {max_retries} retries: {str(e)}",
                                category=category,
                                severity=severity,
                                cause=e
                            )
                            logger.error(f"Retry failed: {error}")
                            raise error from e

                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor

                # 不应该到达这里，但为了类型检查
                if last_exception is not None:
                    raise last_exception
                else:
                    raise RuntimeError("重试失败，没有异常信息")

            return wrapper
        return decorator

    @staticmethod
    def log_and_continue(
        error: Exception,
        message: str = "Error occurred but continuing",
        level: int = logging.WARNING,
        category: ErrorCategory = ErrorCategory.SYSTEM
    ) -> None:
        """记录错误但继续执行"""
        logger.log(level, f"[{category.value}] {message}: {error}")

    @staticmethod
    def log_and_raise(
        error: Exception,
        error_class: Type[VirtualChemLabError] = VirtualChemLabError,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> None:
        """记录错误并重新抛出"""
        logger.error(f"[{category.value}] Error occurred: {error}")

        raise error_class(
            message=str(error),
            category=category,
            severity=severity,
            cause=error
        )

    @staticmethod
    def handle_file_operation(
        operation: str,
        file_path: str,
        error_class: Type[VirtualChemLabError] = VirtualChemLabError,
        category: ErrorCategory = ErrorCategory.FILE_SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        """文件操作错误处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except FileNotFoundError as e:
                    error = error_class(
                        message=f"File not found during {operation}: {file_path}",
                        category=category,
                        severity=severity,
                        cause=e
                    )
                    logger.error(f"File operation failed: {error}")
                    raise error from e
                except PermissionError as e:
                    error = error_class(
                        message=f"Permission denied during {operation}: {file_path}",
                        category=category,
                        severity=severity,
                        cause=e
                    )
                    logger.error(f"File operation failed: {error}")
                    raise error from e
                except Exception as e:
                    error = error_class(
                        message=f"Unexpected error during {operation}: {file_path}",
                        category=category,
                        severity=severity,
                        cause=e
                    )
                    logger.error(f"File operation failed: {error}")
                    raise error from e

            return wrapper
        return decorator

    @staticmethod
    def handle_database_operation(
        operation: str,
        error_class: Type[VirtualChemLabError] = VirtualChemLabError,
        category: ErrorCategory = ErrorCategory.DATABASE,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        """数据库操作错误处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error = error_class(
                        message=f"Database operation failed: {operation}",
                        category=category,
                        severity=severity,
                        cause=e
                    )
                    logger.error(f"Database operation failed: {error}")
                    raise error from e

            return wrapper
        return decorator

    @staticmethod
    def handle_network_operation(
        operation: str,
        url: str = "",
        error_class: Type[VirtualChemLabError] = VirtualChemLabError,
        category: ErrorCategory = ErrorCategory.NETWORK,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        """网络操作错误处理装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error = error_class(
                        message=f"Network operation failed: {operation} {url}",
                        category=category,
                        severity=severity,
                        cause=e
                    )
                    logger.error(f"Network operation failed: {error}")
                    raise error from e

            return wrapper
        return decorator


# 便捷函数
def safe_execute_with_default(
    func: Callable,
    default_value: Any = None,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    *args,
    **kwargs
) -> Any:
    """安全执行函数，出错时返回默认值"""
    return CommonErrorHandlers.safe_execute_with_default(
        func, default_value, error_class, category, severity, *args, **kwargs
    )


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """重试装饰器"""
    return CommonErrorHandlers.retry_on_failure(
        max_retries, delay, backoff_factor, error_class, category, severity
    )


def handle_file_operation(
    operation: str,
    file_path: str,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: ErrorCategory = ErrorCategory.STORAGE,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """文件操作错误处理装饰器"""
    return CommonErrorHandlers.handle_file_operation(
        operation, file_path, error_class, category, severity
    )


def handle_database_operation(
    operation: str,
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: ErrorCategory = ErrorCategory.STORAGE,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """数据库操作错误处理装饰器"""
    return CommonErrorHandlers.handle_database_operation(
        operation, error_class, category, severity
    )


def handle_network_operation(
    operation: str,
    url: str = "",
    error_class: Type[VirtualChemLabError] = VirtualChemLabError,
    category: ErrorCategory = ErrorCategory.NETWORK,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """网络操作错误处理装饰器"""
    return CommonErrorHandlers.handle_network_operation(
        operation, url, error_class, category, severity
    )


# 向后兼容的别名
auto_recover = safe_execute_with_default
retry = retry_on_failure
fallback = safe_execute_with_default
