"""日志配置 - 增强版本"""

import json
import logging
import logging.handlers
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

MASK_TEXT = "[REDACTED]"
SENSITIVE_FIELD_NAMES = {
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "secret",
    "password",
    "passwd",
    "pwd",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "email",
    "phone",
    "mobile",
    "license_key",
}
EMAIL_PATTERN = re.compile(r"(?P<local>[A-Za-z0-9._%+-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_PATTERN = re.compile(r"\b(\+?\d{1,3}[-.\s]?)?(\d{3})[-.\s]?(\d{4})[-.\s]?(\d{3,4})\b")
SECRET_PATTERN = re.compile(
    r"(?i)(?P<key>bearer|token|secret|password|passwd|pwd|api[_-]?key|access[_-]?token|refresh[_-]?token|authorization)"
    r"(?:\s*[:=]\s*|\s+)(?P<value>[-A-Za-z0-9._~+/]{4,})"
)


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


def _mask_secret(value: str) -> str:
    """掩码密钥类字符串"""
    if not value:
        return MASK_TEXT
    if len(value) <= 4:
        return MASK_TEXT
    return f"{value[:2]}***{value[-2:]}"


def _sanitize_text(text: str) -> str:
    """对字符串进行敏感信息脱敏"""
    if not text:
        return text

    def _mask_email(match: re.Match[str]) -> str:
        return f"***@{match.group('domain')}"

    def _mask_phone(match: re.Match[str]) -> str:
        country = match.group(1) or ""
        tail = match.group(4)
        return f"{country}***{tail}"

    def _mask_secret_value(match: re.Match[str]) -> str:
        masked = _mask_secret(match.group("value"))
        return match.group(0).replace(match.group("value"), masked)

    text = SECRET_PATTERN.sub(_mask_secret_value, text)
    text = EMAIL_PATTERN.sub(_mask_email, text)
    text = PHONE_PATTERN.sub(_mask_phone, text)
    return text


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_FIELD_NAMES)


def sanitize_log_value(value: Any) -> Any:
    """递归脱敏日志值"""
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, dict):
        return {k: (MASK_TEXT if _is_sensitive_key(k) else sanitize_log_value(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        container_type = type(value)
        sanitized_items = [sanitize_log_value(v) for v in value]
        return container_type(sanitized_items)  # type: ignore[call-arg]
    return value


class SensitiveDataFilter(logging.Filter):
    """敏感信息过滤器"""

    def filter(self, record: logging.LogRecord) -> bool:
        raw_message = record.getMessage()
        sanitized_message = sanitize_log_value(raw_message)
        record.msg = sanitized_message
        record.args = ()

        if hasattr(record, "extra_data"):
            record.extra_data = sanitize_log_value(record.extra_data)

        for key, value in list(record.__dict__.items()):
            if key in {
                "msg", "args", "name", "levelno", "levelname", "pathname", "filename", "module",
                "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName", "process",
            }:
                continue

            if _is_sensitive_key(key):
                record.__dict__[key] = MASK_TEXT
            elif isinstance(value, (str, dict, list, tuple, set)):
                record.__dict__[key] = sanitize_log_value(value)

        return True


def _ensure_sensitive_filter(target: logging.Logger | logging.Handler) -> None:
    """确保目标挂载敏感信息过滤器"""
    if not any(isinstance(f, SensitiveDataFilter) for f in getattr(target, "filters", [])):
        target.addFilter(SensitiveDataFilter())


def _resolve_log_level(level: int | str) -> int:
    """解析并校正日志级别，生产环境不低于INFO"""
    resolved = level
    if isinstance(level, str):
        resolved = getattr(logging, level.upper(), logging.INFO)

    environment = os.getenv("ENVIRONMENT", "").lower() or os.getenv("APP_ENV", "").lower()
    if environment == "production" and resolved < logging.INFO:
        return logging.INFO
    return int(resolved)


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
            message=sanitize_log_value(record.getMessage()),
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
            log_entry.extra_data = sanitize_log_value(record.extra_data)

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
            entry.message = sanitize_log_value(entry.message)
            entry.extra_data = sanitize_log_value(entry.extra_data)
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
            _ensure_sensitive_filter(handler)
            self.logger.addHandler(handler)
        else:
            for handler in self.logger.handlers:
                _ensure_sensitive_filter(handler)
        _ensure_sensitive_filter(self.logger)

    def log_with_context(self, level: int, message: str, **extra_data: Any) -> None:
        """带上下文的日志记录"""
        sanitized_message = sanitize_log_value(message)
        sanitized_extra = sanitize_log_value(extra_data)
        # 创建日志记录
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, sanitized_message, (), None
        )

        # 添加额外数据
        record.extra_data = sanitized_extra

        # 记录到缓冲区
        if self.buffer:
            log_entry = LogEntry(
                timestamp=time.time(),
                level=logging.getLevelName(level),
                logger_name=self.name,
                message=sanitized_message,
                extra_data=sanitized_extra,
            )
            self.buffer.add_entry(log_entry)

        # 处理日志
        self.logger.handle(record)

    def debug(self, message: str, *args: Any, **extra_data: Any) -> None:
        """调试日志 (兼容标准logging接口)"""
        if args:
            try:
                message = message % args
            except Exception:
                message = f"{message} | args={args}"
        self.log_with_context(logging.DEBUG, message, **extra_data)

    def info(self, message: str, *args: Any, **extra_data: Any) -> None:
        """信息日志"""
        if args:
            try:
                message = message % args
            except Exception:
                message = f"{message} | args={args}"
        self.log_with_context(logging.INFO, message, **extra_data)

    def warning(self, message: str, *args: Any, **extra_data: Any) -> None:
        """警告日志"""
        if args:
            try:
                message = message % args
            except Exception:
                message = f"{message} | args={args}"
        self.log_with_context(logging.WARNING, message, **extra_data)

    def error(self, message: str, *args: Any, **extra_data: Any) -> None:
        """错误日志"""
        if args:
            try:
                message = message % args
            except Exception:
                message = f"{message} | args={args}"
        self.log_with_context(logging.ERROR, message, **extra_data)

    def critical(self, message: str, *args: Any, **extra_data: Any) -> None:
        """严重错误日志"""
        if args:
            try:
                message = message % args
            except Exception:
                message = f"{message} | args={args}"
        self.log_with_context(logging.CRITICAL, message, **extra_data)


def setup_logger(
    name: str = "virtualchemlab",
    level: int | str = logging.INFO,
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
    resolved_level = _resolve_log_level(level)
    logger.setLevel(resolved_level)
    log_file_path = Path(log_file).expanduser().resolve() if log_file else None

    # 格式化器
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器 - 设置UTF-8编码以正确显示中文
    has_stdout_handler = any(isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) == sys.stdout for h in logger.handlers)
    if enable_console and not has_stdout_handler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(resolved_level)
        console_handler.setFormatter(formatter)
        _ensure_sensitive_filter(console_handler)
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
    has_same_file_handler = False
    if log_file_path:
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                existing = Path(getattr(handler, "baseFilename", ""))
                if existing == log_file_path:
                    has_same_file_handler = True
                    break

    if log_file_path and not has_same_file_handler:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        # 使用RotatingFileHandler自动轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        _ensure_sensitive_filter(file_handler)
        logger.addHandler(file_handler)

    for handler in logger.handlers:
        handler.setLevel(resolved_level)
        _ensure_sensitive_filter(handler)

    _ensure_sensitive_filter(logger)
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
                # 确保导出时再次脱敏
                safe_message = sanitize_log_value(entry.message)
                safe_extra = sanitize_log_value(entry.extra_data)
                log_data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp)),
                    "level": entry.level,
                    "logger": entry.logger_name,
                    "message": safe_message,
                    "module": entry.module,
                    "function": entry.function,
                    "line": entry.line_number,
                    "thread": entry.thread_id,
                    "process": entry.process_id,
                    "extra": safe_extra,
                    "exception": entry.exception_info,
                }
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')

        return True
    except Exception as e:
        print(f"导出日志失败: {e}")
        return False


# 兼容性别名
setup_logger = setup_logger
