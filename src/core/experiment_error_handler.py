"""实验错误处理器 - 提供实验运行时的错误处理和恢复机制"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """错误严重程度"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


class ErrorCategory(str, Enum):
    """错误分类"""

    VALIDATION = "validation"  # 验证错误
    TEMPLATE = "template"  # 模板错误
    RUNTIME = "runtime"  # 运行时错误
    DATA = "data"  # 数据错误
    SYSTEM = "system"  # 系统错误


@dataclass
class ExperimentError:
    """实验错误"""

    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    step_id: str | None = None
    context: dict[str, Any] | None = None
    timestamp: datetime | None = None
    recoverable: bool = True
    recovery_hint: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.context is None:
            self.context = {}


class ExperimentErrorHandler:
    """实验错误处理器"""

    def __init__(self):
        """初始化错误处理器"""
        self.error_history: list[ExperimentError] = []
        self.max_history = 100

    def handle_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        step_id: str | None = None,
        context: dict[str, Any] | None = None,
        recoverable: bool = True,
    ) -> ExperimentError:
        """处理错误

        Args:
            category: 错误分类
            severity: 严重程度
            message: 错误消息
            step_id: 相关步骤ID
            context: 错误上下文
            recoverable: 是否可恢复

        Returns:
            错误对象
        """
        error = ExperimentError(
            category=category,
            severity=severity,
            message=message,
            step_id=step_id,
            context=context or {},
            recoverable=recoverable,
            recovery_hint=self._get_recovery_hint(category, message),
        )

        # 记录错误
        self._log_error(error)

        # 保存到历史
        self.error_history.append(error)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

        return error

    def _log_error(self, error: ExperimentError):
        """记录错误到日志"""
        log_message = f"[{error.category.value}] {error.message}"

        if error.step_id:
            log_message = f"步骤 {error.step_id}: {log_message}"

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"error": error})
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message, extra={"error": error})
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message, extra={"error": error})
        else:
            logger.info(log_message, extra={"error": error})

    def _get_recovery_hint(self, category: ErrorCategory, message: str) -> str:
        """获取恢复提示

        Args:
            category: 错误分类
            message: 错误消息

        Returns:
            恢复提示
        """
        hints = {
            ErrorCategory.VALIDATION: "请检查输入数据的格式和范围",
            ErrorCategory.TEMPLATE: "请验证实验模板的完整性和正确性",
            ErrorCategory.RUNTIME: "请尝试重新启动实验或检查系统资源",
            ErrorCategory.DATA: "请检查数据文件是否存在和可访问",
            ErrorCategory.SYSTEM: "请检查系统配置和依赖",
        }

        base_hint = hints.get(category, "请联系技术支持")

        # 根据具体错误消息提供更详细的提示
        if "缺少" in message or "missing" in message.lower():
            return f"{base_hint}。确保所有必需字段都已提供。"
        elif "类型" in message or "type" in message.lower():
            return f"{base_hint}。检查数据类型是否正确。"
        elif "范围" in message or "range" in message.lower():
            return f"{base_hint}。确保数值在有效范围内。"

        return base_hint

    def get_recent_errors(
        self,
        count: int = 10,
        severity: ErrorSeverity | None = None,
        category: ErrorCategory | None = None,
    ) -> list[ExperimentError]:
        """获取最近的错误

        Args:
            count: 数量
            severity: 严重程度筛选
            category: 分类筛选

        Returns:
            错误列表
        """
        errors = self.error_history.copy()

        # 应用筛选
        if severity:
            errors = [e for e in errors if e.severity == severity]

        if category:
            errors = [e for e in errors if e.category == category]

        # 返回最近的
        return errors[-count:]

    def clear_history(self):
        """清空错误历史"""
        self.error_history.clear()

    def get_error_summary(self) -> dict[str, Any]:
        """获取错误摘要

        Returns:
            错误统计信息
        """
        summary = {
            "total_errors": len(self.error_history),
            "by_severity": {},
            "by_category": {},
            "recoverable_count": 0,
            "critical_count": 0,
        }

        for error in self.error_history:
            # 按严重程度统计
            severity_key = error.severity.value
            summary["by_severity"][severity_key] = (
                summary["by_severity"].get(severity_key, 0) + 1
            )

            # 按分类统计
            category_key = error.category.value
            summary["by_category"][category_key] = (
                summary["by_category"].get(category_key, 0) + 1
            )

            # 统计可恢复和严重错误
            if error.recoverable:
                summary["recoverable_count"] += 1
            if error.severity == ErrorSeverity.CRITICAL:
                summary["critical_count"] += 1

        return summary


# 全局错误处理器实例
_global_error_handler = ExperimentErrorHandler()


def get_error_handler() -> ExperimentErrorHandler:
    """获取全局错误处理器"""
    return _global_error_handler


# 便捷函数
def handle_validation_error(message: str, step_id: str | None = None, **kwargs):
    """处理验证错误"""
    return _global_error_handler.handle_error(
        ErrorCategory.VALIDATION, ErrorSeverity.WARNING, message, step_id, kwargs
    )


def handle_template_error(
    message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, **kwargs
):
    """处理模板错误"""
    return _global_error_handler.handle_error(
        ErrorCategory.TEMPLATE, severity, message, None, kwargs, recoverable=False
    )


def handle_runtime_error(message: str, step_id: str | None = None, **kwargs):
    """处理运行时错误"""
    return _global_error_handler.handle_error(
        ErrorCategory.RUNTIME, ErrorSeverity.ERROR, message, step_id, kwargs
    )


def handle_critical_error(
    message: str, category: ErrorCategory = ErrorCategory.SYSTEM, **kwargs
):
    """处理严重错误"""
    return _global_error_handler.handle_error(
        category, ErrorSeverity.CRITICAL, message, None, kwargs, recoverable=False
    )
