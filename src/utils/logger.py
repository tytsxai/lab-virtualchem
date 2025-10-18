"""日志配置 - 增强版本"""

import contextlib
import json
import logging
import logging.handlers
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """结构化日志条目"""
    timestamp: float
    level: str
    logger_name: str
    message: str
    module: str = ""
    function: str = ""
    line_number: int = 0
    thread_id: int = 0
    process_id: int = 0
    extra_data: dict[str, Any] = field(default_factory=dict)
    exception_info: str | None = None


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, include_stack_info: bool = False):
        super().__init__()
        self.include_stack_info = include_stack_info

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础信息
        log_entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            module=record.module or "",
            function=record.funcName or "",
            line_number=record.lineno,
            thread_id=record.thread,
            process_id=record.process,
        )

        # 异常信息
        if record.exc_info:
            log_entry.exception_info = self.formatException(record.exc_info)

        # 额外数据
        if hasattr(record, 'extra_data'):
            log_entry.extra_data = record.extra_data

        # 转换为JSON格式
        return json.dumps({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(log_entry.timestamp)),
            "level": log_entry.level,
            "logger": log_entry.logger_name,
            "message": log_entry.message,
            "module": log_entry.module,
            "function": log_entry.function,
            "line": log_entry.line_number,
            "thread": log_entry.thread_id,
            "process": log_entry.process_id,
            "extra": log_entry.extra_data,
            "exception": log_entry.exception_info,
        }, ensure_ascii=False)


class LogBuffer:
    """日志缓冲区 - 用于内存中的日志存储"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: list[LogEntry] = []
        self._lock = threading.RLock()

    def add_entry(self, entry: LogEntry) -> None:
        """添加日志条目"""
        with self._lock:
            self.buffer.append(entry)
            if len(self.buffer) > self.max_size:
                self.buffer = self.buffer[-self.max_size:]

    def get_entries(self, level: str | None = None, limit: int | None = None) -> list[LogEntry]:
        """获取日志条目"""
        with self._lock:
            entries = self.buffer.copy()

            if level:
                entries = [e for e in entries if e.level == level]

            if limit:
                entries = entries[-limit:]

            return entries

    def clear(self) -> None:
        """清空缓冲区"""
        with self._lock:
            self.buffer.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            if not self.buffer:
                return {"total": 0, "by_level": {}}

            stats = {"total": len(self.buffer)}
            by_level = {}

            for entry in self.buffer:
                by_level[entry.level] = by_level.get(entry.level, 0) + 1

            stats["by_level"] = by_level
            return stats


class EnhancedLogger:
    """增强的日志器"""

    def __init__(self, name: str, buffer: LogBuffer | None = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.buffer = buffer or LogBuffer()
        self._setup_logger()

    def _setup_logger(self) -> None:
        """设置日志器"""
        if not self.logger.handlers:
            # 添加结构化处理器
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)

    def log_with_context(self, level: int, message: str, **extra_data: Any) -> None:
        """带上下文的日志记录"""
        # 创建日志记录
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, message, (), None
        )

        # 添加额外数据
        record.extra_data = extra_data

        # 记录到缓冲区
        if self.buffer:
            log_entry = LogEntry(
                timestamp=time.time(),
                level=logging.getLevelName(level),
                logger_name=self.name,
                message=message,
                extra_data=extra_data,
            )
            self.buffer.add_entry(log_entry)

        # 处理日志
        self.logger.handle(record)

    def debug(self, message: str, **extra_data: Any) -> None:
        """调试日志"""
        self.log_with_context(logging.DEBUG, message, **extra_data)

    def info(self, message: str, **extra_data: Any) -> None:
        """信息日志"""
        self.log_with_context(logging.INFO, message, **extra_data)

    def warning(self, message: str, **extra_data: Any) -> None:
        """警告日志"""
        self.log_with_context(logging.WARNING, message, **extra_data)

    def error(self, message: str, **extra_data: Any) -> None:
        """错误日志"""
        self.log_with_context(logging.ERROR, message, **extra_data)

    def critical(self, message: str, **extra_data: Any) -> None:
        """严重错误日志"""
        self.log_with_context(logging.CRITICAL, message, **extra_data)


def setup_logger(
    name: str = "virtualchemlab",
    level: int = logging.INFO,
    log_file: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
) -> logging.Logger:
    """配置日志器（优化版本）

    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径(可选)
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的备份文件数量
        enable_console: 是否启用控制台输出

    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)

    # 避免重复配置
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器 - 设置UTF-8编码以正确显示中文
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        # Windows系统强制使用UTF-8编码
        if hasattr(console_handler.stream, "reconfigure"):
            # 在Windows上设置UTF-8编码
            if sys.platform == "win32":
                try:
                    console_handler.stream.reconfigure(encoding="utf-8")
                except Exception:
                    pass
        logger.addHandler(console_handler)

    # 文件处理器(如果提供) - 使用轮转
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        # 使用RotatingFileHandler自动轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 全局日志缓冲区
_global_log_buffer = LogBuffer(max_size=2000)


def get_logger(name: str = "virtualchemlab") -> EnhancedLogger:
    """获取增强的日志器"""
    return EnhancedLogger(name, _global_log_buffer)


def get_log_buffer() -> LogBuffer:
    """获取全局日志缓冲区"""
    return _global_log_buffer


def get_log_stats() -> dict[str, Any]:
    """获取日志统计信息"""
    return _global_log_buffer.get_stats()


def clear_log_buffer() -> None:
    """清空日志缓冲区"""
    _global_log_buffer.clear()


def export_logs(file_path: str, level: str | None = None, limit: int | None = None) -> bool:
    """导出日志到文件"""
    try:
        entries = _global_log_buffer.get_entries(level=level, limit=limit)

        with open(file_path, 'w', encoding='utf-8') as f:
            for entry in entries:
                log_data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp)),
                    "level": entry.level,
                    "logger": entry.logger_name,
                    "message": entry.message,
                    "module": entry.module,
                    "function": entry.function,
                    "line": entry.line_number,
                    "thread": entry.thread_id,
                    "process": entry.process_id,
                    "extra": entry.extra_data,
                    "exception": entry.exception_info,
                }
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')

        return True
    except Exception as e:
        print(f"导出日志失败: {e}")
        return False


# 兼容性别名
setup_logger = setup_logger
