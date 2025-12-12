"""
错误处理器测试
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorContextManager,
    ErrorHandler,
    ErrorRecord,
    ErrorSeverity,
    get_error_handler,
    handle_error_func,
    safe_execute,
    safe_execute_with_default,
)


class TestErrorContext:
    """错误上下文测试"""

    def test_error_context_creation(self):
        """测试错误上下文创建"""
        context = ErrorContext(
            user_id="user123",
            session_id="session456",
            component="test_component",
            operation="test_operation",
            metadata={"key": "value"},
        )

        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.component == "test_component"
        assert context.operation == "test_operation"
        assert context.metadata == {"key": "value"}

    def test_error_context_defaults(self):
        """测试错误上下文默认值"""
        context = ErrorContext()

        assert context.user_id is None
        assert context.session_id is None
        assert context.component is None
        assert context.operation is None
        assert context.metadata == {}


class TestErrorRecord:
    """错误记录测试"""

    def test_error_record_creation(self):
        """测试错误记录创建"""
        context = ErrorContext(component="test")
        exception = ValueError("Test error")

        record = ErrorRecord(
            id="error_001",
            timestamp=time.time(),
            exception=exception,
            context=context,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            message="Test error message",
            traceback="Traceback info",
            recoverable=True,
            handled=False,
            recovery_attempts=0,
            max_recovery_attempts=3,
            metadata={"key": "value"},
        )

        assert record.id == "error_001"
        assert record.exception == exception
        assert record.context == context
        assert record.severity == ErrorSeverity.MEDIUM
        assert record.category == ErrorCategory.VALIDATION
        assert record.message == "Test error message"
        assert record.recoverable is True
        assert record.handled is False


class TestErrorHandler:
    """错误处理器测试"""

    def test_error_handler_creation(self):
        """测试错误处理器创建"""
        handler = ErrorHandler()

        # 错误处理器会自动注册默认处理器，所以不应该是空的
        assert len(handler.error_handlers) > 0
        assert handler.error_records == []
        assert handler.max_error_records == 1000

    def test_register_handler(self):
        """测试注册错误处理器"""
        handler = ErrorHandler()

        def test_handler(error, context):
            return True

        handler.register_handler(ValueError, test_handler)

        assert ValueError in handler.error_handlers
        assert handler.error_handlers[ValueError] == test_handler

    def test_unregister_handler(self):
        """测试注销错误处理器"""
        handler = ErrorHandler()

        def test_handler(error, context):
            return True

        handler.register_handler(ValueError, test_handler)
        assert ValueError in handler.error_handlers

        success = handler.unregister_handler(ValueError)
        assert success is True
        assert ValueError not in handler.error_handlers

    def test_handle_error_with_registered_handler(self):
        """测试使用注册的处理器处理错误"""
        handler = ErrorHandler()

        def test_handler(error, context):
            return True

        handler.register_handler(ValueError, test_handler)

        context = ErrorContext(component="test")
        error = ValueError("Test error")

        result = handler.handle_error(error, context)
        assert result is True

        # 检查错误记录
        records = handler.get_error_records()
        assert len(records) == 1
        assert records[0].handled is True

    def test_handle_error_without_handler(self):
        """测试处理没有注册处理器的错误"""
        handler = ErrorHandler()

        context = ErrorContext(component="test")
        error = ValueError("Test error")

        result = handler.handle_error(error, context)
        assert result is True  # 默认处理器应该返回True

        # 检查错误记录
        records = handler.get_error_records()
        assert len(records) == 1
        assert records[0].handled is True

    def test_error_records_limit(self):
        """测试错误记录数量限制"""
        handler = ErrorHandler()
        handler.max_error_records = 3

        # 添加超过限制的错误记录
        for i in range(5):
            context = ErrorContext(component="test")
            error = ValueError(f"Error {i}")
            handler.handle_error(error, context)

        records = handler.get_error_records()
        assert len(records) == 3  # 应该只保留最后3个记录

    def test_get_error_records_with_limit(self):
        """测试获取有限数量的错误记录"""
        handler = ErrorHandler()

        # 添加多个错误记录
        for i in range(5):
            context = ErrorContext(component="test")
            error = ValueError(f"Error {i}")
            handler.handle_error(error, context)

        records = handler.get_error_records(limit=3)
        assert len(records) == 3

    def test_error_statistics(self):
        """测试错误统计"""
        handler = ErrorHandler()

        # 添加不同类型的错误
        handler.handle_error(ValueError("Value error"), ErrorContext())
        handler.handle_error(TypeError("Type error"), ErrorContext())
        handler.handle_error(ValueError("Another value error"), ErrorContext())

        stats = handler.get_error_statistics()

        assert stats["total_errors"] == 3
        assert stats["handled_errors"] == 3
        assert stats["unhandled_errors"] == 0
        assert "ValueError" in stats["type_counts"]
        assert stats["type_counts"]["ValueError"] == 2
        assert stats["type_counts"]["TypeError"] == 1

    def test_emergency_save_state_creates_snapshot(self, tmp_path, monkeypatch):
        """紧急保存状态应生成快照文件"""
        handler = ErrorHandler()
        handler.handle_error(ValueError("Boom"), ErrorContext(component="core"))

        monkeypatch.setenv("VCL_EMERGENCY_STATE_DIR", str(tmp_path))

        handler._emergency_save_state()

        files = list(Path(tmp_path).glob("state_*.json"))
        assert files, "应生成紧急状态文件"

        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["recent_errors"]
        assert data["recent_errors"][0]["message"] == "Boom"

    def test_restart_critical_components_invokes_dependencies(self, monkeypatch):
        """重启关键组件应调用各依赖"""
        handler = ErrorHandler()
        calls: list[str] = []

        monkeypatch.setattr("src.core.error_handler.close_event_bus", lambda: calls.append("close_bus"))
        monkeypatch.setattr("src.core.error_handler.get_event_bus", lambda: calls.append("get_bus"))
        monkeypatch.setattr("src.core.error_handler.reset_container", lambda: calls.append("reset_container"))
        monkeypatch.setattr(
            "src.core.error_handler.get_configured_container", lambda: calls.append("configure_container")
        )

        handler._restart_critical_components()

        assert calls == ["close_bus", "get_bus", "reset_container", "configure_container"]

    def test_restart_critical_components_handles_missing(self, monkeypatch):
        """缺少依赖时仍安全执行"""
        handler = ErrorHandler()

        monkeypatch.setattr("src.core.error_handler.close_event_bus", None)
        monkeypatch.setattr("src.core.error_handler.get_event_bus", None)
        monkeypatch.setattr("src.core.error_handler.reset_container", None)
        monkeypatch.setattr("src.core.error_handler.get_configured_container", None)

        handler._restart_critical_components()  # 不应抛出异常


class TestErrorContextManager:
    """错误上下文管理器测试"""

    def test_error_context_manager_success(self):
        """测试错误上下文管理器成功情况"""
        with ErrorContextManager("test_component", "test_operation", user_id="123") as context:
            assert context.component == "test_component"
            assert context.operation == "test_operation"
            # user_id 在 metadata 中，不在直接属性中
            assert context.metadata["user_id"] == "123"
            # 正常执行，不应该有错误

    def test_error_context_manager_with_exception(self):
        """测试错误上下文管理器异常情况"""
        with patch('src.core.error_handler.handle_error_func') as mock_handle:
            try:
                with ErrorContextManager("test_component", "test_operation") as context:
                    raise ValueError("Test error")
            except ValueError:
                pass  # 异常会被重新抛出

            # 验证错误处理函数被调用
            mock_handle.assert_called_once()
            args = mock_handle.call_args[0]
            assert isinstance(args[0], ValueError)
            assert args[1].component == "test_component"
            assert args[1].operation == "test_operation"


class TestUtilityFunctions:
    """工具函数测试"""

    def test_safe_execute_success(self):
        """测试安全执行成功"""
        def test_func(x, y):
            return x + y

        result = safe_execute(test_func, 2, 3, default_return=0)
        assert result == 5

    def test_safe_execute_with_exception(self):
        """测试安全执行异常"""
        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, default_return="default")
        assert result == "default"

    def test_safe_execute_with_default_success(self):
        """测试带默认值的安全执行成功"""
        def test_func():
            return "success"

        result = safe_execute_with_default("default", test_func)
        assert result == "success"

    def test_safe_execute_with_default_exception(self):
        """测试带默认值的安全执行异常"""
        def test_func():
            raise ValueError("Test error")

        result = safe_execute_with_default("default", test_func)
        assert result == "default"

    def test_get_error_handler(self):
        """测试获取错误处理器"""
        handler = get_error_handler()
        assert isinstance(handler, ErrorHandler)

    def test_handle_error_func(self):
        """测试错误处理函数"""
        error = ValueError("Test error")
        context = ErrorContext(component="test")

        result = handle_error_func(error, context)
        assert result is True


class TestErrorSeverityAndCategory:
    """错误严重程度和分类测试"""

    def test_error_severity_values(self):
        """测试错误严重程度值"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_category_values(self):
        """测试错误分类值"""
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.USER.value == "user"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.FILE.value == "file"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.BUSINESS.value == "business"
        assert ErrorCategory.UNKNOWN.value == "unknown"


if __name__ == "__main__":
    pytest.main([__file__])
