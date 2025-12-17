"""
日志系统测试
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.utils.logger import (
    EnhancedLogger,
    LogBuffer,
    LogEntry,
    StructuredFormatter,
    clear_log_buffer,
    export_logs,
    get_log_buffer,
    get_log_stats,
)


class TestLogEntry:
    """日志条目测试"""

    def test_log_entry_creation(self):
        """测试日志条目创建"""
        entry = LogEntry(
            timestamp=1234567890.0,
            level="INFO",
            logger_name="test",
            message="Test message",
            module="test_module",
            function="test_function",
            line_number=42,
            thread_id=1,
            process_id=100,
            extra_data={"key": "value"},
        )

        assert entry.timestamp == 1234567890.0
        assert entry.level == "INFO"
        assert entry.logger_name == "test"
        assert entry.message == "Test message"
        assert entry.extra_data == {"key": "value"}


class TestLogBuffer:
    """日志缓冲区测试"""

    def test_log_buffer_add_entry(self):
        """测试添加日志条目"""
        buffer = LogBuffer(max_size=5)

        entry = LogEntry(
            timestamp=1234567890.0,
            level="INFO",
            logger_name="test",
            message="Test message",
        )

        buffer.add_entry(entry)
        assert len(buffer.buffer) == 1
        assert buffer.buffer[0] == entry

    def test_log_buffer_max_size(self):
        """测试缓冲区最大大小限制"""
        buffer = LogBuffer(max_size=3)

        # 添加超过最大大小的条目
        for i in range(5):
            entry = LogEntry(
                timestamp=1234567890.0 + i,
                level="INFO",
                logger_name="test",
                message=f"Message {i}",
            )
            buffer.add_entry(entry)

        assert len(buffer.buffer) == 3
        # 应该保留最后3个条目
        assert buffer.buffer[0].message == "Message 2"
        assert buffer.buffer[1].message == "Message 3"
        assert buffer.buffer[2].message == "Message 4"

    def test_log_buffer_get_entries(self):
        """测试获取日志条目"""
        buffer = LogBuffer()

        # 添加不同级别的条目
        for level in ["INFO", "WARNING", "ERROR"]:
            entry = LogEntry(
                timestamp=1234567890.0,
                level=level,
                logger_name="test",
                message=f"{level} message",
            )
            buffer.add_entry(entry)

        # 获取所有条目
        all_entries = buffer.get_entries()
        assert len(all_entries) == 3

        # 按级别过滤
        error_entries = buffer.get_entries(level="ERROR")
        assert len(error_entries) == 1
        assert error_entries[0].level == "ERROR"

        # 限制数量
        limited_entries = buffer.get_entries(limit=2)
        assert len(limited_entries) == 2

    def test_log_buffer_stats(self):
        """测试缓冲区统计"""
        buffer = LogBuffer()

        # 添加不同级别的条目
        for level in ["INFO", "INFO", "WARNING", "ERROR"]:
            entry = LogEntry(
                timestamp=1234567890.0,
                level=level,
                logger_name="test",
                message=f"{level} message",
            )
            buffer.add_entry(entry)

        stats = buffer.get_stats()
        assert stats["total"] == 4
        assert stats["by_level"]["INFO"] == 2
        assert stats["by_level"]["WARNING"] == 1
        assert stats["by_level"]["ERROR"] == 1

    def test_log_buffer_clear(self):
        """测试清空缓冲区"""
        buffer = LogBuffer()

        entry = LogEntry(
            timestamp=1234567890.0,
            level="INFO",
            logger_name="test",
            message="Test message",
        )
        buffer.add_entry(entry)

        assert len(buffer.buffer) == 1
        buffer.clear()
        assert len(buffer.buffer) == 0


class TestStructuredFormatter:
    """结构化格式化器测试"""

    def test_structured_formatter_basic(self):
        """测试结构化格式化器基本功能"""
        formatter = StructuredFormatter()

        # 模拟日志记录
        class MockRecord:
            def __init__(self):
                self.created = 1234567890.0
                self.levelname = "INFO"
                self.name = "test_logger"
                self.getMessage = lambda: "Test message"
                self.module = "test_module"
                self.funcName = "test_function"
                self.lineno = 42
                self.thread = 1
                self.process = 100
                self.exc_info = None

        record = MockRecord()
        formatted = formatter.format(record)

        # 解析JSON
        log_data = json.loads(formatted)
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42

    def test_structured_formatter_with_extra_data(self):
        """测试带额外数据的结构化格式化器"""
        formatter = StructuredFormatter()

        class MockRecord:
            def __init__(self):
                self.created = 1234567890.0
                self.levelname = "INFO"
                self.name = "test_logger"
                self.getMessage = lambda: "Test message"
                self.module = "test_module"
                self.funcName = "test_function"
                self.lineno = 42
                self.thread = 1
                self.process = 100
                self.exc_info = None
                self.extra_data = {"user_id": "123", "action": "login"}

        record = MockRecord()
        formatted = formatter.format(record)

        log_data = json.loads(formatted)
        assert log_data["extra"]["user_id"] == "123"
        assert log_data["extra"]["action"] == "login"


class TestEnhancedLogger:
    """增强日志器测试"""

    def test_enhanced_logger_creation(self):
        """测试增强日志器创建"""
        logger = EnhancedLogger("test_logger")
        assert logger.name == "test_logger"
        assert logger.buffer is not None

    def test_enhanced_logger_logging(self):
        """测试增强日志器日志记录"""
        buffer = LogBuffer()
        logger = EnhancedLogger("test_logger", buffer)

        logger.info("Test info message", user_id="123", action="test")

        entries = buffer.get_entries()
        assert len(entries) == 1
        assert entries[0].level == "INFO"
        assert entries[0].message == "Test info message"
        assert entries[0].extra_data["user_id"] == "123"
        assert entries[0].extra_data["action"] == "test"

    def test_enhanced_logger_different_levels(self):
        """测试不同级别的日志记录"""
        buffer = LogBuffer()
        logger = EnhancedLogger("test_logger", buffer)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        entries = buffer.get_entries()
        assert len(entries) == 5

        levels = [entry.level for entry in entries]
        assert "DEBUG" in levels
        assert "INFO" in levels
        assert "WARNING" in levels
        assert "ERROR" in levels
        assert "CRITICAL" in levels


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_log_buffer(self):
        """测试获取全局日志缓冲区"""
        buffer = get_log_buffer()
        assert buffer is not None
        assert isinstance(buffer, LogBuffer)

    def test_get_log_stats(self):
        """测试获取日志统计"""
        buffer = get_log_buffer()

        # 添加一些条目
        entry = LogEntry(
            timestamp=1234567890.0,
            level="INFO",
            logger_name="test",
            message="Test message",
        )
        buffer.add_entry(entry)

        stats = get_log_stats()
        assert "total" in stats
        assert "by_level" in stats

    def test_clear_log_buffer(self):
        """测试清空日志缓冲区"""
        buffer = get_log_buffer()
        initial_count = len(buffer.buffer)

        # 添加条目
        entry = LogEntry(
            timestamp=1234567890.0,
            level="INFO",
            logger_name="test",
            message="Test message",
        )
        buffer.add_entry(entry)

        assert len(buffer.buffer) == initial_count + 1
        clear_log_buffer()
        assert len(buffer.buffer) == 0

    def test_export_logs(self):
        """测试导出日志"""
        buffer = get_log_buffer()
        initial_count = len(buffer.buffer)

        # 添加测试条目
        entry = LogEntry(
            timestamp=1234567890.0,
            level="INFO",
            logger_name="test",
            message="Test message",
            extra_data={"key": "value"},
        )
        buffer.add_entry(entry)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            success = export_logs(temp_file)
            assert success is True

            # 验证导出的文件
            with open(temp_file, encoding="utf-8") as f:
                lines = f.readlines()
                # 应该包含初始条目 + 新添加的条目
                assert len(lines) == initial_count + 1

                # 检查最后一行（新添加的条目）
                log_data = json.loads(lines[-1])
                assert log_data["level"] == "INFO"
                assert log_data["message"] == "Test message"
                assert log_data["extra"]["key"] == "value"

        finally:
            Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])
