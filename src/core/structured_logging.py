"""
结构化日志系统

支持日志聚合、上下文追踪、性能分析等
"""

import json
import logging
import sys
import threading
import traceback
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.utils.logger import SensitiveDataFilter

from .. import __version__ as APP_VERSION

# 尝试导入额外的日志库
try:
    import structlog  # noqa: F401

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """日志上下文"""

    request_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    experiment_id: str | None = None
    correlation_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LogEntry:
    """日志条目"""

    timestamp: datetime
    level: str
    message: str
    logger_name: str
    context: dict[str, Any] = field(default_factory=dict)
    exception: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        entry = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "logger": self.logger_name,
        }

        if self.context:
            entry["context"] = self.context

        if self.exception:
            entry["exception"] = self.exception

        return entry

    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ContextVar:
    """线程本地上下文变量"""

    def __init__(self):
        self._local = threading.local()

    def get(self) -> LogContext:
        """获取上下文"""
        if not hasattr(self._local, "context"):
            self._local.context = LogContext()
        return self._local.context

    def set(self, context: LogContext) -> None:
        """设置上下文"""
        self._local.context = context

    def clear(self) -> None:
        """清除上下文"""
        if hasattr(self._local, "context"):
            delattr(self._local, "context")


# 全局上下文
_log_context = ContextVar()


def _ensure_filter(handler: logging.Handler) -> None:
    """确保日志处理器附带敏感信息过滤器"""
    if not any(isinstance(f, SensitiveDataFilter) for f in handler.filters):
        handler.addFilter(SensitiveDataFilter())


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础信息
        entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
        )

        # 添加上下文
        context = _log_context.get()
        if context:
            entry.context = context.to_dict()

        # 添加异常信息
        if record.exc_info:
            entry.exception = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加额外字段
        if hasattr(record, "extra_fields"):
            entry.context.update(record.extra_fields)

        return entry.to_json()


class ConsoleFormatter(logging.Formatter):
    """控制台彩色格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志"""
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # 时间戳
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # 基础格式
        parts = [
            f"{timestamp}",
            f"{color}{record.levelname:8}{reset}",
            f"{record.name}",
            f"{record.getMessage()}",
        ]

        # 添加上下文
        context = _log_context.get()
        if context and context.request_id:
            parts.insert(3, f"[{context.request_id}]")

        return " - ".join(parts)


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        self.name = name

    def _log(self, level: str, message: str, exc_info: bool = False, **kwargs) -> None:
        """内部日志方法"""
        extra = {"extra_fields": kwargs} if kwargs else {}

        log_method = getattr(self.logger, level.lower())
        log_method(message, exc_info=exc_info, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """错误日志"""
        self._log("ERROR", message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """严重错误日志"""
        self._log("CRITICAL", message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """异常日志"""
        self._log("ERROR", message, exc_info=True, **kwargs)

    @contextmanager
    def context(self, **kwargs):
        """临时上下文"""
        old_context = _log_context.get()
        new_context = LogContext(**{**old_context.to_dict(), **kwargs})

        _log_context.set(new_context)
        try:
            yield
        finally:
            _log_context.set(old_context)


class LoggerFactory:
    """日志记录器工厂"""

    _configured = False
    _loggers: dict[str, StructuredLogger] = {}

    @classmethod
    def configure(
        cls,
        log_level: str = "INFO",
        log_file: str | None = None,
        console: bool = True,
        json_format: bool = False,
    ) -> None:
        """配置日志系统"""
        if cls._configured:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level))

        # 清除现有处理器
        root_logger.handlers.clear()

        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            if json_format:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(ConsoleFormatter())
            _ensure_filter(console_handler)
            root_logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(StructuredFormatter())
            _ensure_filter(file_handler)
            root_logger.addHandler(file_handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> StructuredLogger:
        """获取日志记录器"""
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(name)
        return cls._loggers[name]


class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    @contextmanager
    def measure(self, operation: str, **context):
        """测量操作耗时"""
        start = datetime.now()
        error = None

        try:
            yield
        except Exception as e:
            error = e
            raise
        finally:
            duration = (datetime.now() - start).total_seconds()

            log_data = {"operation": operation, "duration_seconds": duration, **context}

            if error:
                self.logger.error(f"操作失败: {operation}", exc_info=True, **log_data)
            elif duration > 1.0:  # 慢操作
                self.logger.warning(f"慢操作: {operation}", **log_data)
            else:
                self.logger.info(f"操作完成: {operation}", **log_data)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_action(self, action: str, resource: str, user_id: str, result: str = "success", **details) -> None:
        """记录用户操作"""
        self.logger.info(
            f"审计: {action}",
            action=action,
            resource=resource,
            user_id=user_id,
            result=result,
            **details,
        )

    def log_access(self, resource: str, user_id: str, granted: bool, **details) -> None:
        """记录访问控制"""
        self.logger.info(f"访问: {resource}", resource=resource, user_id=user_id, granted=granted, **details)


class LogAggregator:
    """日志聚合器"""

    def __init__(self):
        self._logs: list[LogEntry] = []
        self._max_size = 10000

    def add(self, entry: LogEntry) -> None:
        """添加日志条目"""
        self._logs.append(entry)

        # 限制大小
        if len(self._logs) > self._max_size:
            self._logs = self._logs[-self._max_size :]

    def query(
        self,
        level: str | None = None,
        logger_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[LogEntry]:
        """查询日志"""
        results = self._logs

        if level:
            results = [log for log in results if log.level == level]

        if logger_name:
            results = [log for log in results if log.logger_name == logger_name]

        if start_time:
            results = [log for log in results if log.timestamp >= start_time]

        if end_time:
            results = [log for log in results if log.timestamp <= end_time]

        return results

    def export_to_file(self, file_path: str) -> None:
        """导出到文件"""
        with open(file_path, "w", encoding="utf-8") as f:
            for entry in self._logs:
                f.write(entry.to_json() + "\n")


def set_context(**kwargs) -> None:
    """设置日志上下文"""
    context = LogContext(**kwargs)
    _log_context.set(context)


def get_context() -> LogContext:
    """获取日志上下文"""
    return _log_context.get()


def clear_context() -> None:
    """清除日志上下文"""
    _log_context.clear()


if __name__ == "__main__":
    # 配置日志系统
    LoggerFactory.configure(
        log_level="DEBUG",
        console=True,
        json_format=False,  # 控制台使用彩色格式
    )

    # 创建logger用于演示
    logger = LoggerFactory.get_logger(__name__)
    logger.info("=== 结构化日志系统演示 ===\n")

    # 2. 获取日志记录器
    logger = LoggerFactory.get_logger("VirtualChemLab")

    # 3. 基础日志
    logger.info("1. 基础日志:")
    logger.info("应用程序启动")
    logger.debug("调试信息", version=f"v{APP_VERSION}")
    logger.warning("这是一个警告")

    logger.info("\n2. 带上下文的日志:")
    # 4. 设置上下文
    set_context(request_id="req_12345", user_id="user_001", experiment_id="exp_789")

    logger.info("用户开始实验")
    logger.info("实验步骤完成", step=1, data={"temperature": 25.5})

    # 5. 临时上下文
    logger.info("\n3. 临时上下文:")
    with logger.context(session_id="session_abc"):
        logger.info("会话中的操作")

    logger.info("会话外的操作")  # 不包含session_id

    # 6. 性能日志
    logger.info("\n4. 性能测量:")
    perf_logger = PerformanceLogger(logger)

    with perf_logger.measure("实验计算", experiment_id="exp_001"):
        import time

        time.sleep(0.5)

    # 7. 审计日志
    logger.info("\n5. 审计日志:")
    audit_logger = AuditLogger(logger)

    audit_logger.log_action(
        action="create_experiment",
        resource="experiment:exp_001",
        user_id="user_001",
        result="success",
    )

    audit_logger.log_access(resource="report:rep_001", user_id="user_001", granted=True)

    # 8. 异常日志
    logger.info("\n6. 异常日志:")
    try:
        raise ValueError("这是一个测试异常")
    except ValueError:
        logger.exception("发生异常", operation="test")

    logger.info("\n✅ 演示完成")
