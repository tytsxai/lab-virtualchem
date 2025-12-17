"""
公共错误处理模块测试
"""

import time
from unittest.mock import patch

import pytest

from src.core.common_error_handlers import (
    CommonErrorHandlers,
    auto_recover,
    fallback,
    handle_database_operation,
    handle_file_operation,
    handle_network_operation,
    retry,
    retry_on_failure,
    safe_execute_with_default,
)
from src.core.common_exceptions import ErrorCategory, ErrorSeverity, VirtualChemLabError


class TestCommonErrorHandlers:
    """测试公共错误处理器"""

    def test_safe_execute_with_default_success(self):
        """测试安全执行成功"""

        def test_func():
            return "success"

        result = CommonErrorHandlers.safe_execute_with_default(test_func, "default")
        assert result == "success"

    def test_safe_execute_with_default_failure(self):
        """测试安全执行失败"""

        def test_func():
            raise ValueError("test error")

        result = CommonErrorHandlers.safe_execute_with_default(test_func, "default")
        assert result == "default"

    def test_safe_execute_with_default_virtualchemlab_error(self):
        """测试VirtualChemLabError不被捕获"""

        def test_func():
            raise VirtualChemLabError(
                "VCL error", ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
            )

        with pytest.raises(VirtualChemLabError):
            CommonErrorHandlers.safe_execute_with_default(test_func, "default")

    def test_retry_on_failure_success(self):
        """测试重试装饰器成功"""

        @CommonErrorHandlers.retry_on_failure(max_retries=2, delay=0.1)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_retry_on_failure_eventual_success(self):
        """测试重试装饰器最终成功"""
        call_count = 0

        @CommonErrorHandlers.retry_on_failure(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_on_failure_max_retries_exceeded(self):
        """测试重试装饰器超过最大重试次数"""
        call_count = 0

        @CommonErrorHandlers.retry_on_failure(max_retries=2, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with pytest.raises(VirtualChemLabError):
            test_func()

        assert call_count == 3  # 初始调用 + 2次重试

    def test_log_and_continue(self):
        """测试记录错误但继续执行"""
        with patch("src.core.common_error_handlers.logger") as mock_logger:
            error = ValueError("test error")
            CommonErrorHandlers.log_and_continue(error, "test message")

            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == 30  # WARNING level
            assert "test message" in call_args[0][1]

    def test_log_and_raise(self):
        """测试记录错误并重新抛出"""
        with patch("src.core.common_error_handlers.logger") as mock_logger:
            error = ValueError("test error")

            with pytest.raises(VirtualChemLabError):
                CommonErrorHandlers.log_and_raise(error)

            mock_logger.error.assert_called_once()

    def test_handle_file_operation_success(self):
        """测试文件操作装饰器成功"""

        @CommonErrorHandlers.handle_file_operation("read", "/test/path")
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_handle_file_operation_file_not_found(self):
        """测试文件操作装饰器文件未找到"""

        @CommonErrorHandlers.handle_file_operation("read", "/test/path")
        def test_func():
            raise FileNotFoundError("file not found")

        with pytest.raises(VirtualChemLabError) as exc_info:
            test_func()

        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
        assert "File not found" in exc_info.value.message

    def test_handle_file_operation_permission_error(self):
        """测试文件操作装饰器权限错误"""

        @CommonErrorHandlers.handle_file_operation("write", "/test/path")
        def test_func():
            raise PermissionError("permission denied")

        with pytest.raises(VirtualChemLabError) as exc_info:
            test_func()

        assert exc_info.value.category == ErrorCategory.FILE_SYSTEM
        assert "Permission denied" in exc_info.value.message

    def test_handle_database_operation(self):
        """测试数据库操作装饰器"""

        @CommonErrorHandlers.handle_database_operation("query")
        def test_func():
            raise Exception("database error")

        with pytest.raises(VirtualChemLabError) as exc_info:
            test_func()

        assert exc_info.value.category == ErrorCategory.DATABASE
        assert "Database operation failed" in exc_info.value.message

    def test_handle_network_operation(self):
        """测试网络操作装饰器"""

        @CommonErrorHandlers.handle_network_operation("request", "http://example.com")
        def test_func():
            raise Exception("network error")

        with pytest.raises(VirtualChemLabError) as exc_info:
            test_func()

        assert exc_info.value.category == ErrorCategory.NETWORK
        assert "Network operation failed" in exc_info.value.message


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_safe_execute_with_default_function(self):
        """测试safe_execute_with_default函数"""

        def test_func():
            raise ValueError("test error")

        result = safe_execute_with_default(test_func, "default")
        assert result == "default"

    def test_retry_on_failure_function(self):
        """测试retry_on_failure函数"""
        call_count = 0

        @retry_on_failure(max_retries=2, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_handle_file_operation_function(self):
        """测试handle_file_operation函数"""

        @handle_file_operation("read", "/test/path")
        def test_func():
            raise FileNotFoundError("file not found")

        with pytest.raises(VirtualChemLabError):
            test_func()

    def test_handle_database_operation_function(self):
        """测试handle_database_operation函数"""

        @handle_database_operation("query")
        def test_func():
            raise Exception("database error")

        with pytest.raises(VirtualChemLabError):
            test_func()

    def test_handle_network_operation_function(self):
        """测试handle_network_operation函数"""

        @handle_network_operation("request", "http://example.com")
        def test_func():
            raise Exception("network error")

        with pytest.raises(VirtualChemLabError):
            test_func()

    def test_backward_compatibility_aliases(self):
        """测试向后兼容的别名"""

        def test_func():
            raise ValueError("test error")

        # 测试别名
        result1 = auto_recover(test_func, "default")
        result2 = fallback(test_func, "default")

        assert result1 == "default"
        assert result2 == "default"

        # 测试retry别名
        call_count = 0

        @retry(max_retries=1, delay=0.1)
        def test_func2():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary error")
            return "success"

        result = test_func2()
        assert result == "success"
        assert call_count == 2


class TestPerformance:
    """性能测试"""

    def test_retry_performance(self):
        """测试重试逻辑不会引入不必要等待"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary error")
            return "success"

        with patch("time.sleep") as mock_sleep:
            result = test_func()

        assert result == "success"
        assert call_count == 2
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == pytest.approx(0.01)

    def test_safe_execute_performance(self):
        """测试安全执行性能"""

        def test_func():
            return "success"

        start_time = time.time()
        for _ in range(1000):
            safe_execute_with_default(test_func, "default")
        elapsed_time = time.time() - start_time

        assert elapsed_time < 1.0  # 1000次调用应该在1秒内完成


if __name__ == "__main__":
    pytest.main([__file__])
