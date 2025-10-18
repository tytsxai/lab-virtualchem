"""
错误处理工具
提供统一的错误处理和日志记录
"""

import functools
import logging
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

# 延迟导入以避免循环依赖

logger = logging.getLogger(__name__)


class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def log_error(error: Exception, context: str = "", _user_message: str = "") -> None:
        """
        记录错误信息

        Args:
            error: 异常对象
            context: 错误上下文
            user_message: 用户友好的错误消息
        """
        error_info = {
            "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "上下文": context,
            "错误类型": type(error).__name__,
            "错误消息": str(error),
            "堆栈跟踪": traceback.format_exc(),
        }

        logger.error(
            f"错误发生在: {context}\n"
            f"错误类型: {error_info['错误类型']}\n"
            f"错误消息: {error_info['错误消息']}\n"
            f"堆栈跟踪:\n{error_info['堆栈跟踪']}"
        )

        # 可选：将错误写入文件
        ErrorHandler.write_error_log(error_info)

    @staticmethod
    def write_error_log(error_info: dict[str, Any]) -> None:
        """将错误写入日志文件"""
        try:
            log_dir = Path("logs/errors")
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"

            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write("\n" + "=" * 80 + "\n")
                    for key, value in error_info.items():
                        # 确保值是字符串类型
                        value_str = str(value) if value is not None else ""
                        f.write(f"{key}: {value_str}\n")
                    f.write("=" * 80 + "\n")
            except Exception as write_error:
                # 避免在错误处理中再次输出中文，防止编码问题
                import contextlib

                with contextlib.suppress(Exception):
                    logger.error(f"Failed to write error log: {write_error}")
        except Exception:
            # 创建日志目录失败，静默处理
            pass

    @staticmethod
    def handle_exception(
        func: Callable[..., Any], context: str = "", default_return: Any = None, raise_error: bool = False
    ) -> Callable[..., Any]:
        """
        异常处理装饰器

        Args:
            func: 被装饰的函数
            context: 错误上下文
            default_return: 发生错误时的默认返回值
            raise_error: 是否重新抛出异常
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ctx = context or f"{func.__module__}.{func.__name__}"
                ErrorHandler.log_error(e, ctx)

                if raise_error:
                    raise
                return default_return

        return wrapper


def safe_execute(
    context: str = "", default_return: Any = None, raise_error: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    安全执行装饰器

    使用方法:
    @safe_execute(context="加载实验", default_return=None)
    def load_experiment(self, exp_id):
        ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return ErrorHandler.handle_exception(
            func, context=context, default_return=default_return, raise_error=raise_error
        )

    return decorator


def safe_call(func: Callable[..., Any], *args: Any, default_return: Any = None, **kwargs: Any) -> Any:
    """
    安全调用函数

    Args:
        func: 要调用的函数
        *args: 位置参数
        default_return: 出错时的默认返回值
        **kwargs: 关键字参数

    Returns:
        函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        ErrorHandler.log_error(e, f"调用 {func.__name__}")
        return default_return


# 使用统一的错误处理系统


def validate_not_none(value: Any, name: str = "参数") -> None:
    """验证值不为None"""
    if value is None:
        from ..core.validation import ValidationError
        raise ValidationError(field=name, message=f"{name}不能为None")


def validate_type(value: Any, expected_type: type, name: str = "参数") -> None:
    """验证值的类型"""
    if not isinstance(value, expected_type):
        from ..core.validation import ValidationError
        raise ValidationError(
            field=name,
            message=f"{name}类型错误: 期望 {expected_type.__name__}, 实际 {type(value).__name__}"
        )


def validate_range(
    value: float, min_val: float | None = None, max_val: float | None = None, name: str = "参数"
) -> None:
    """验证值在指定范围内"""
    if min_val is not None and value < min_val:
        from ..core.validation import ValidationError
        raise ValidationError(f"{name}不能小于 {min_val}", field=name, value=value)
    if max_val is not None and value > max_val:
        from ..core.validation import ValidationError
        raise ValidationError(f"{name}不能大于 {max_val}", field=name, value=value)


def validate_not_empty(value: str, name: str = "参数") -> None:
    """验证字符串不为空"""
    if not value or not value.strip():
        from ..core.validation import ValidationError
        raise ValidationError(f"{name}不能为空", field=name, value=value)


def validate_file_exists(file_path: str, name: str = "文件") -> None:
    """验证文件存在"""
    if not Path(file_path).exists():
        from ..core.validation import ValidationError
        raise ValidationError(f"{name}不存在: {file_path}", field=name, value=file_path)


class ErrorLogger:
    """错误日志记录器"""

    def __init__(self, name: str = "app"):
        self.logger = logging.getLogger(name)
        self.errors = []

    def log(self, error: Exception, context: str = "") -> None:
        """记录错误"""
        error_info = {
            "time": datetime.now(),
            "context": context,
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
        self.errors.append(error_info)
        self.logger.error(f"[{context}] {error}")

    def get_recent_errors(self, count: int = 10) -> list:
        """获取最近的错误"""
        return self.errors[-count:]

    def clear(self) -> None:
        """清空错误记录"""
        self.errors.clear()

    def export_to_file(self, filepath: str) -> None:
        """导出错误到文件"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for error in self.errors:
                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"Time: {error['time']}\n")
                    f.write(f"Context: {error['context']}\n")
                    f.write(f"Type: {error['type']}\n")
                    f.write(f"Message: {error['message']}\n")
                    f.write(f"Traceback:\n{error['traceback']}\n")
        except Exception as e:
            self.logger.error(f"导出错误日志失败: {e}")


# 全局错误记录器
global_error_logger = ErrorLogger("VirtualChemLab")
