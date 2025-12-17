"""
统一日志记录接口测试
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.unified_logging import (
    LogContext,
    LogLevel,
    UnifiedLogger,
    critical,
    debug,
    error,
    info,
    log_context,
    log_operation,
    log_operation_end,
    log_operation_error,
    log_operation_start,
    log_performance,
    log_security_event,
    log_system_event,
    log_user_action,
    warning,
)
from src.core.unified_logging import (
    log_performance as log_perf,
)
from src.core.unified_logging import (
    log_user_action as log_user,
)


class TestLogContext:
    """测试日志上下文"""

    def test_log_context_creation(self):
        """测试日志上下文创建"""
        context = LogContext(
            operation="test_op",
            component="test_comp",
            user_id="user123",
            session_id="session456",
            request_id="req789",
            extra_data={"key": "value"},
        )

        assert context.operation == "test_op"
        assert context.component == "test_comp"
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.request_id == "req789"
        assert context.extra_data == {"key": "value"}

    def test_log_context_defaults(self):
        """测试日志上下文默认值"""
        context = LogContext(operation="test_op", component="test_comp")

        assert context.user_id is None
        assert context.session_id is None
        assert context.request_id is None
        assert context.extra_data == {}


class TestUnifiedLogger:
    """测试统一日志记录器"""

    def test_logger_creation(self):
        """测试日志记录器创建"""
        logger = UnifiedLogger("test_module")
        assert logger.logger is not None
        assert len(logger._context_stack) == 0

    def test_basic_logging(self):
        """测试基本日志记录"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")
            logger.critical("critical message")

            assert mock_logger.debug.called
            assert mock_logger.info.called
            assert mock_logger.warning.called
            assert mock_logger.error.called
            assert mock_logger.critical.called

    def test_context_manager(self):
        """测试上下文管理器"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            with logger.context("test_op", "test_comp", user_id="user123"):
                logger.info("message in context")

            # 检查上下文是否正确应用
            call_args = mock_logger.info.call_args[0][0]
            assert "[test_comp]" in call_args
            assert "[test_op]" in call_args
            assert "[user:user123]" in call_args

    def test_log_operation_start_end(self):
        """测试操作开始和结束日志"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            logger.log_operation_start("test_op", "test_comp")
            logger.log_operation_end("test_op", "test_comp", duration=1.5)

            assert mock_logger.info.call_count == 2

            # 检查开始日志
            start_call = mock_logger.info.call_args_list[0][0][0]
            assert "开始执行: test_op" in start_call

            # 检查结束日志
            end_call = mock_logger.info.call_args_list[1][0][0]
            assert "完成执行: test_op" in end_call
            assert "耗时: 1.5秒" in end_call

    def test_log_operation_error(self):
        """测试操作错误日志"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            test_error = ValueError("test error")
            logger.log_operation_error("test_op", "test_comp", test_error)

            assert mock_logger.error.called
            call_args = mock_logger.error.call_args[0][0]
            assert "执行失败: test_op" in call_args
            assert "test error" in call_args

    def test_log_performance(self):
        """测试性能日志"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            logger.log_performance("test_op", "test_comp", 0.5)
            logger.log_performance("slow_op", "test_comp", 2.0)

            assert mock_logger.info.called
            assert mock_logger.warning.called

    def test_log_user_action(self):
        """测试用户操作日志"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            logger.log_user_action("login", "user123")

            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            assert "用户操作: login" in call_args
            assert "[user:user123]" in call_args

    def test_log_system_event(self):
        """测试系统事件日志"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            logger.log_system_event("system_start")

            assert mock_logger.info.called
            call_args = mock_logger.info.call_args[0][0]
            assert "系统事件: system_start" in call_args

    def test_log_security_event(self):
        """测试安全事件日志"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            logger.log_security_event("unauthorized_access", LogLevel.ERROR)

            assert mock_logger.error.called
            call_args = mock_logger.error.call_args[0][0]
            assert "安全事件: unauthorized_access" in call_args


class TestDecorators:
    """测试装饰器"""

    def test_log_operation_decorator(self):
        """测试操作日志装饰器"""
        with patch("src.core.unified_logging.get_unified_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            @log_operation("test_op", "test_comp")
            def test_func():
                return "success"

            result = test_func()

            assert result == "success"
            assert mock_logger.log_operation_start.called
            assert mock_logger.log_operation_end.called

    def test_log_operation_decorator_with_error(self):
        """测试操作日志装饰器（带错误）"""
        with patch("src.core.unified_logging.get_unified_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            @log_operation("test_op", "test_comp")
            def test_func():
                raise ValueError("test error")

            with pytest.raises(ValueError):
                test_func()

            assert mock_logger.log_operation_start.called
            assert mock_logger.log_operation_error.called

    def test_log_performance_decorator(self):
        """测试性能日志装饰器"""
        with patch("src.core.unified_logging.get_unified_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            @log_performance("test_op", "test_comp")
            def test_func():
                return "success"

            result = test_func()

            assert result == "success"
            assert mock_logger.log_performance.called

    def test_log_user_action_decorator(self):
        """测试用户操作日志装饰器"""
        with patch("src.core.unified_logging.get_unified_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            @log_user_action("login", "user123")
            def test_func():
                return "success"

            result = test_func()

            assert result == "success"
            assert mock_logger.log_user_action.called


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_global_logging_functions(self):
        """测试全局日志函数"""
        with patch("src.core.unified_logging._unified_logger") as mock_logger:
            debug("debug message")
            info("info message")
            warning("warning message")
            error("error message")
            critical("critical message")

            assert mock_logger.debug.called
            assert mock_logger.info.called
            assert mock_logger.warning.called
            assert mock_logger.error.called
            assert mock_logger.critical.called

    def test_global_operation_functions(self):
        """测试全局操作函数"""
        with patch("src.core.unified_logging._unified_logger") as mock_logger:
            log_operation_start("test_op", "test_comp")
            log_operation_end("test_op", "test_comp", duration=1.0)
            log_operation_error("test_op", "test_comp", ValueError("test"))
            log_perf("test_op", "test_comp", 1.0)
            log_user("login", "user123")
            log_system_event("system_start")
            log_security_event("security_event")

            assert mock_logger.log_operation_start.called
            assert mock_logger.log_operation_end.called
            assert mock_logger.log_operation_error.called
            assert mock_logger.log_performance.called
            assert mock_logger.log_user_action.called
            assert mock_logger.log_system_event.called
            assert mock_logger.log_security_event.called

    def test_log_context_function(self):
        """测试日志上下文函数"""
        with patch("src.core.unified_logging._unified_logger") as mock_logger:
            with log_context("test_op", "test_comp", user_id="user123"):
                pass

            assert mock_logger.context.called


class TestPerformance:
    """性能测试"""

    def test_logging_performance(self):
        """测试日志记录性能"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            start_time = datetime.now()
            for _ in range(1000):
                logger.info("test message")
            elapsed_time = (datetime.now() - start_time).total_seconds()

            assert elapsed_time < 1.0  # 1000次日志记录应该在1秒内完成
            assert mock_logger.info.call_count == 1000

    def test_context_performance(self):
        """测试上下文性能"""
        with patch("src.core.unified_logging.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            logger = UnifiedLogger("test_module")

            start_time = datetime.now()
            for _ in range(1000):
                with logger.context("test_op", "test_comp"):
                    logger.info("test message")
            elapsed_time = (datetime.now() - start_time).total_seconds()

            assert elapsed_time < 1.0  # 1000次上下文操作应该在1秒内完成
            assert mock_logger.info.call_count == 1000


if __name__ == "__main__":
    pytest.main([__file__])
