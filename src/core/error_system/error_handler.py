"""
全局错误处理器

提供统一的错误处理、日志记录和上下文管理
"""

import functools
import logging
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from .error_sampler import error_sampler
from .exceptions import BaseAppException, from_standard_exception

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GlobalErrorHandler:
    """全局错误处理器"""

    def __init__(self, log_dir: Path | None = None):
        """
        初始化错误处理器

        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir or Path("logs/errors")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.error_history: list[dict[str, Any]] = []
        self.max_history = 1000
        self._error_callbacks: list[Callable[[BaseAppException, str], None]] = []

    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        user_id: str | None = None,
        session_id: str | None = None,
        reraise: bool = False,
    ) -> BaseAppException:
        """
        处理异常

        Args:
            exception: 异常对象
            context: 上下文信息
            user_id: 用户ID
            session_id: 会话ID
            reraise: 是否重新抛出异常

        Returns:
            应用异常对象
        """
        # 转换为应用异常
        if isinstance(exception, BaseAppException):
            app_exception = exception
        else:
            app_exception = from_standard_exception(exception, context)

        # 记录错误
        self._log_error(app_exception, context, user_id, session_id)

        # 保存到历史
        self._save_to_history(app_exception, context, user_id, session_id)

        # 触发回调
        self._trigger_callbacks(app_exception, context)

        # 是否重新抛出
        if reraise:
            raise app_exception

        return app_exception

    def _log_error(
        self,
        exception: BaseAppException,
        context: str,
        user_id: str | None,
        session_id: str | None,
    ) -> None:
        """记录错误到日志（带采样）"""
        # 使用采样器判断是否应该记录
        should_log, sampling_metadata = error_sampler.should_sample(exception, context)

        if not should_log:
            # 被采样抑制 - 只记录简单的统计信息
            if sampling_metadata.get("reason") == "suppressed":
                logger.debug(
                    f"Error suppressed by sampler: [{exception.error_code.name}] "
                    f"(count: {sampling_metadata.get('total_count')}, "
                    f"sampled: {sampling_metadata.get('sampled_count')})"
                )
            return

        # 构建错误信息
        error_info = {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "错误码": exception.error_code.code,
            "错误类型": exception.error_code.name,
            "错误消息": exception.message,
            "用户消息": exception.user_message,
            "上下文": context,
            "用户ID": user_id,
            "会话ID": session_id,
            "严重程度": exception.error_code.severity,
            "是否可恢复": exception.error_code.recoverable,
            "详细信息": exception.details,
            "采样信息": sampling_metadata,  # 添加采样元数据
        }

        # 根据严重程度选择日志级别
        log_message = (
            f"[{exception.error_code.name}] {exception.message}\n" f"上下文: {context}\n" f"详细: {exception.details}"
        )

        # 添加采样信息到日志
        if sampling_metadata.get("reason") == "sampled":
            log_message += (
                f"\n[采样] 此错误已发生 {sampling_metadata['total_count']} 次，"
                f"本次为第 {sampling_metadata['sampled_count']} 次记录，"
                f"已抑制 {sampling_metadata.get('suppressed', 0)} 次"
            )
        elif sampling_metadata.get("reason") == "burst_detected":
            log_message += (
                "\n[突发] 检测到错误突发！"
                f"总计 {sampling_metadata['total_count']} 次，"
                f"突发计数 {sampling_metadata['burst_count']}"
            )

        if exception.error_code.severity == "critical":
            logger.critical(log_message, exc_info=exception.original_exception)
        elif exception.error_code.severity == "error":
            logger.error(log_message, exc_info=exception.original_exception)
        elif exception.error_code.severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 写入错误日志文件
        self._write_error_log(error_info)

    def _write_error_log(self, error_info: dict[str, Any]) -> None:
        """写入错误日志文件"""
        try:
            log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"

            with open(log_file, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 80 + "\n")
                for key, value in error_info.items():
                    value_str = str(value) if value is not None else ""
                    f.write(f"{key}: {value_str}\n")
                f.write("=" * 80 + "\n")
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")

    def _save_to_history(
        self,
        exception: BaseAppException,
        context: str,
        user_id: str | None,
        session_id: str | None,
    ) -> None:
        """保存错误到历史记录"""
        error_record = {
            "timestamp": datetime.now(),
            "error_code": exception.error_code.code,
            "error_type": exception.error_code.name,
            "message": exception.message,
            "user_message": exception.user_message,
            "context": context,
            "user_id": user_id,
            "session_id": session_id,
            "severity": exception.error_code.severity,
            "recoverable": exception.error_code.recoverable,
            "details": exception.details,
            "exception": exception,
        }

        self.error_history.append(error_record)

        # 限制历史记录大小
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

    def _trigger_callbacks(self, exception: BaseAppException, context: str) -> None:
        """触发错误回调"""
        for callback in self._error_callbacks:
            try:
                callback(exception, context)
            except Exception as e:
                logger.error("Error callback failed: %s", e)

    def add_error_callback(self, callback: Callable[[BaseAppException, str], None]) -> None:
        """
        添加错误回调

        Args:
            callback: 回调函数，签名为 (exception, context) -> None
        """
        self._error_callbacks.append(callback)

    def get_error_history(
        self,
        limit: int = 100,
        severity: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        获取错误历史

        Args:
            limit: 返回数量
            severity: 严重程度筛选
            category: 分类筛选

        Returns:
            错误历史列表
        """
        errors = self.error_history.copy()

        # 应用筛选
        if severity:
            errors = [e for e in errors if e["severity"] == severity]

        if category:
            errors = [e for e in errors if e["exception"].error_code.category.value == category]

        # 返回最近的记录
        return errors[-limit:]

    def get_error_stats(self) -> dict[str, Any]:
        """获取错误统计"""
        total_errors = len(self.error_history)

        # 按严重程度统计
        by_severity: dict[str, int] = {}
        for error in self.error_history:
            severity = error["severity"]
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # 按分类统计
        by_category: dict[str, int] = {}
        for error in self.error_history:
            category = error["exception"].error_code.category.value
            by_category[category] = by_category.get(category, 0) + 1

        # 按错误码统计
        by_code: dict[int, int] = {}
        for error in self.error_history:
            code = error["error_code"]
            by_code[code] = by_code.get(code, 0) + 1

        # 可恢复错误数
        recoverable_count = sum(1 for e in self.error_history if e["recoverable"])

        return {
            "total_errors": total_errors,
            "by_severity": by_severity,
            "by_category": by_category,
            "by_code": by_code,
            "recoverable_count": recoverable_count,
            "critical_count": by_severity.get("critical", 0),
        }

    def clear_history(self) -> None:
        """清空错误历史"""
        self.error_history.clear()

    def export_errors(self, filepath: str) -> None:
        """
        导出错误历史到文件

        Args:
            filepath: 文件路径
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("错误历史报告\n")
                f.write("=" * 80 + "\n\n")

                for i, error in enumerate(self.error_history, 1):
                    f.write(f"\n错误 #{i}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"时间: {error['timestamp']}\n")
                    f.write(f"错误码: {error['error_code']}\n")
                    f.write(f"错误类型: {error['error_type']}\n")
                    f.write(f"消息: {error['message']}\n")
                    f.write(f"用户消息: {error['user_message']}\n")
                    f.write(f"上下文: {error['context']}\n")
                    f.write(f"严重程度: {error['severity']}\n")
                    f.write(f"是否可恢复: {error['recoverable']}\n")
                    f.write(f"详细信息: {error['details']}\n")
                    f.write("-" * 80 + "\n")

                # 添加统计信息
                stats = self.get_error_stats()
                f.write("\n\n统计信息\n")
                f.write("=" * 80 + "\n")
                f.write(f"总错误数: {stats['total_errors']}\n")
                f.write(f"可恢复错误数: {stats['recoverable_count']}\n")
                f.write(f"严重错误数: {stats['critical_count']}\n")
                f.write("\n按严重程度:\n")
                for severity, count in stats["by_severity"].items():
                    f.write(f"  {severity}: {count}\n")
                f.write("\n按分类:\n")
                for category, count in stats["by_category"].items():
                    f.write(f"  {category}: {count}\n")

        except Exception as e:
            logger.error(f"Failed to export errors: {e}")


# 全局错误处理器实例
error_handler = GlobalErrorHandler()


# 装饰器：安全执行
def safe_execute(
    context: str = "",
    default_return: Any = None,
    reraise: bool = False,
    user_id: str | None = None,
    session_id: str | None = None,
) -> Any:
    """
    安全执行装饰器

    Args:
        context: 上下文信息
        default_return: 出错时的默认返回值
        reraise: 是否重新抛出异常
        user_id: 用户ID
        session_id: 会话ID

    使用示例:
        @safe_execute(context="加载实验", default_return=None)
        def load_experiment(exp_id):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ctx = context or f"{func.__module__}.{func.__name__}"
                error_handler.handle_exception(e, ctx, user_id, session_id, reraise=reraise)
                return default_return

        return wrapper

    return decorator


# 装饰器：异步安全执行
def async_safe_execute(
    context: str = "",
    default_return: Any = None,
    reraise: bool = False,
    user_id: str | None = None,
    session_id: str | None = None,
) -> Any:
    """
    异步安全执行装饰器

    Args:
        context: 上下文信息
        default_return: 出错时的默认返回值
        reraise: 是否重新抛出异常
        user_id: 用户ID
        session_id: 会话ID
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ctx = context or f"{func.__module__}.{func.__name__}"
                error_handler.handle_exception(e, ctx, user_id, session_id, reraise=reraise)
                return default_return

        return wrapper

    return decorator


# 上下文管理器：安全执行
class safe_context:
    """
    安全执行上下文管理器

    使用示例:
        with safe_context("数据保存", reraise=True):
            save_data()
    """

    def __init__(
        self,
        context: str = "",
        reraise: bool = False,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        self.context = context
        self.reraise = reraise
        self.user_id = user_id
        self.session_id = session_id

    def __enter__(self) -> "safe_context":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_val is not None:
            error_handler.handle_exception(exc_val, self.context, self.user_id, self.session_id, self.reraise)
            # 返回True表示异常已处理，不需要传播
            return not self.reraise
        return False


# 全局异常钩子
def install_global_exception_hook() -> None:
    """安装全局异常钩子"""

    def exception_hook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        """全局异常钩子"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 转换为Exception类型（handle_exception期望Exception而不是BaseException）
        if isinstance(exc_value, Exception):
            error_handler.handle_exception(exc_value, "全局未捕获异常")

        # 打印到stderr
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook
