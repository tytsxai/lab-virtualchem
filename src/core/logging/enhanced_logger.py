"""增强日志系统"""

import logging
import logging.handlers
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import traceback

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogFormat(Enum):
    """日志格式"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: float
    level: str
    message: str
    module: str
    function: str
    line: int
    thread_id: int
    process_id: int
    extra_data: Optional[Dict[str, Any]] = None
    exception_info: Optional[str] = None

class EnhancedLogger:
    """增强日志器"""

    def __init__(self, name: str = "virtualchemlab"):
        """初始化增强日志器"""
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 日志配置
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # 日志格式
        self.formats = {
            LogFormat.SIMPLE: logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ),
            LogFormat.DETAILED: logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s'
            ),
            LogFormat.JSON: self._create_json_formatter(),
            LogFormat.STRUCTURED: self._create_structured_formatter()
        }

        # 处理器
        self.handlers: Dict[str, logging.Handler] = {}

        # 日志条目存储
        self.log_entries: List[LogEntry] = []
        self.max_entries = 10000
        self.entries_lock = threading.Lock()

        # 性能统计
        self.stats = {
            'total_logs': 0,
            'debug_count': 0,
            'info_count': 0,
            'warning_count': 0,
            'error_count': 0,
            'critical_count': 0,
            'last_log_time': 0
        }

        # 初始化默认处理器
        self._setup_default_handlers()

    def _create_json_formatter(self):
        """创建JSON格式化器"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': record.created,
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno,
                    'thread_id': record.thread,
                    'process_id': record.process,
                }

                if hasattr(record, 'extra_data'):
                    log_data['extra_data'] = record.extra_data

                if record.exc_info:
                    log_data['exception_info'] = self.formatException(record.exc_info)

                return json.dumps(log_data, ensure_ascii=False)

        return JSONFormatter()

    def _create_structured_formatter(self):
        """创建结构化格式化器"""
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                # 基础信息
                parts = [
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))}]",
                    f"[{record.levelname}]",
                    f"[{record.module}:{record.funcName}:{record.lineno}]",
                    f"[T{record.thread}]",
                    f"[P{record.process}]",
                    record.getMessage()
                ]

                # 额外数据
                if hasattr(record, 'extra_data') and record.extra_data:
                    parts.append(f"[EXTRA: {json.dumps(record.extra_data, ensure_ascii=False)}]")

                # 异常信息
                if record.exc_info:
                    parts.append(f"[EXCEPTION: {self.formatException(record.exc_info)}]")

                return " ".join(parts)

        return StructuredFormatter()

    def _setup_default_handlers(self):
        """设置默认处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.formats[LogFormat.SIMPLE])
        self.add_handler("console", console_handler)

        # 文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.formats[LogFormat.DETAILED])
        self.add_handler("file", file_handler)

        # 错误文件处理器
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.formats[LogFormat.JSON])
        self.add_handler("error", error_handler)

        # 性能日志处理器
        performance_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "performance.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        performance_handler.setLevel(logging.INFO)
        performance_handler.setFormatter(self.formats[LogFormat.JSON])
        self.add_handler("performance", performance_handler)

    def add_handler(self, name: str, handler: logging.Handler):
        """添加处理器"""
        self.handlers[name] = handler
        self.logger.addHandler(handler)

    def remove_handler(self, name: str):
        """移除处理器"""
        if name in self.handlers:
            handler = self.handlers[name]
            self.logger.removeHandler(handler)
            handler.close()
            del self.handlers[name]

    def set_handler_level(self, name: str, level: LogLevel):
        """设置处理器级别"""
        if name in self.handlers:
            self.handlers[name].setLevel(getattr(logging, level.value))

    def set_handler_format(self, name: str, format_type: LogFormat):
        """设置处理器格式"""
        if name in self.handlers and format_type in self.formats:
            self.handlers[name].setFormatter(self.formats[format_type])

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录调试日志"""
        self._log(logging.DEBUG, message, extra_data, **kwargs)

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录信息日志"""
        self._log(logging.INFO, message, extra_data, **kwargs)

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录警告日志"""
        self._log(logging.WARNING, message, extra_data, **kwargs)

    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录错误日志"""
        self._log(logging.ERROR, message, extra_data, **kwargs)

    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录严重错误日志"""
        self._log(logging.CRITICAL, message, extra_data, **kwargs)

    def exception(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录异常日志"""
        self._log(logging.ERROR, message, extra_data, exc_info=True, **kwargs)

    def performance(self, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """记录性能日志"""
        # 使用性能处理器记录
        performance_logger = logging.getLogger(f"{self.name}.performance")
        performance_logger.info(message, extra={'extra_data': extra_data})

    def _log(self, level: int, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """内部日志记录方法"""
        # 创建日志条目
        entry = LogEntry(
            timestamp=time.time(),
            level=logging.getLevelName(level),
            message=message,
            module=kwargs.get('module', 'unknown'),
            function=kwargs.get('function', 'unknown'),
            line=kwargs.get('line', 0),
            thread_id=threading.get_ident(),
            process_id=kwargs.get('process_id', 0),
            extra_data=extra_data,
            exception_info=kwargs.get('exc_info')
        )

        # 存储日志条目
        with self.entries_lock:
            self.log_entries.append(entry)

            # 保持条目数量限制
            if len(self.log_entries) > self.max_entries:
                self.log_entries = self.log_entries[-self.max_entries:]

        # 更新统计
        self._update_stats(level)

        # 记录到标准日志器
        self.logger.log(level, message, extra={'extra_data': extra_data}, **kwargs)

    def _update_stats(self, level: int):
        """更新统计信息"""
        self.stats['total_logs'] += 1
        self.stats['last_log_time'] = time.time()

        level_name = logging.getLevelName(level)
        if level_name == 'DEBUG':
            self.stats['debug_count'] += 1
        elif level_name == 'INFO':
            self.stats['info_count'] += 1
        elif level_name == 'WARNING':
            self.stats['warning_count'] += 1
        elif level_name == 'ERROR':
            self.stats['error_count'] += 1
        elif level_name == 'CRITICAL':
            self.stats['critical_count'] += 1

    def get_log_entries(self, level: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        """获取日志条目"""
        with self.entries_lock:
            entries = self.log_entries.copy()

        if level:
            entries = [entry for entry in entries if entry.level == level]

        return entries[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.entries_lock:
            return {
                'stats': self.stats.copy(),
                'total_entries': len(self.log_entries),
                'handlers': list(self.handlers.keys()),
                'log_dir': str(self.log_dir),
                'max_entries': self.max_entries
            }

    def clear_entries(self):
        """清空日志条目"""
        with self.entries_lock:
            self.log_entries.clear()

    def export_logs(self, file_path: Union[str, Path], format_type: LogFormat = LogFormat.JSON):
        """导出日志"""
        file_path = Path(file_path)

        with self.entries_lock:
            entries = self.log_entries.copy()

        if format_type == LogFormat.JSON:
            data = [asdict(entry) for entry in entries]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(f"{entry.timestamp} - {entry.level} - {entry.message}\n")

    def set_level(self, level: LogLevel):
        """设置日志级别"""
        self.logger.setLevel(getattr(logging, level.value))

    def enable_handler(self, name: str):
        """启用处理器"""
        if name in self.handlers:
            self.handlers[name].setLevel(logging.DEBUG)

    def disable_handler(self, name: str):
        """禁用处理器"""
        if name in self.handlers:
            self.handlers[name].setLevel(logging.CRITICAL + 1)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type is not None:
            self.exception(f"Context manager exit error: {exc_val}")

        # 关闭所有处理器
        for handler in self.handlers.values():
            handler.close()
