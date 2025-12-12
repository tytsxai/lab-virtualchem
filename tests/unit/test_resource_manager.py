"""资源管理器测试"""

import threading
import time
from unittest.mock import Mock

import pytest

from src.core.resource_manager import (
    _resource_lock,
    _resources,
    cleanup_resources,
    register_resource,
    unregister_resource,
)


class TestResourceManager:
    """资源管理器测试类"""

    def setup_method(self):
        """测试前准备"""
        # 清理所有资源
        cleanup_resources()

    def teardown_method(self):
        """测试后清理"""
        # 清理所有资源
        cleanup_resources()

    def test_register_resource(self):
        """测试注册资源"""
        # 模拟资源
        mock_resource = Mock()
        mock_cleanup = Mock()

        # 注册资源
        register_resource("test_resource", mock_resource, mock_cleanup)

        # 检查资源是否已注册
        assert "test_resource" in _resources
        resource, cleanup_func = _resources["test_resource"]
        assert resource is mock_resource
        assert cleanup_func is mock_cleanup

    def test_register_resource_override(self):
        """测试注册资源覆盖"""
        # 注册第一个资源
        mock_resource1 = Mock()
        mock_cleanup1 = Mock()
        register_resource("test_resource", mock_resource1, mock_cleanup1)

        # 注册同名资源（应该覆盖）
        mock_resource2 = Mock()
        mock_cleanup2 = Mock()
        register_resource("test_resource", mock_resource2, mock_cleanup2)

        # 检查资源是否被覆盖
        assert "test_resource" in _resources
        resource, cleanup_func = _resources["test_resource"]
        assert resource is mock_resource2
        assert cleanup_func is mock_cleanup2

    def test_unregister_resource(self):
        """测试注销资源"""
        # 注册资源
        mock_resource = Mock()
        mock_cleanup = Mock()
        register_resource("test_resource", mock_resource, mock_cleanup)

        # 注销资源
        unregister_resource("test_resource")

        # 检查资源是否已注销
        assert "test_resource" not in _resources

    def test_unregister_nonexistent_resource(self):
        """测试注销不存在的资源"""
        # 尝试注销不存在的资源
        unregister_resource("nonexistent_resource")

        # 应该不会抛出异常
        assert "nonexistent_resource" not in _resources

    def test_cleanup_resources(self):
        """测试清理资源"""
        # 注册多个资源
        mock_resource1 = Mock()
        mock_cleanup1 = Mock()
        register_resource("resource1", mock_resource1, mock_cleanup1)

        mock_resource2 = Mock()
        mock_cleanup2 = Mock()
        register_resource("resource2", mock_resource2, mock_cleanup2)

        # 清理资源
        cleanup_resources()

        # 检查清理函数是否被调用
        mock_cleanup1.assert_called_once_with(mock_resource1)
        mock_cleanup2.assert_called_once_with(mock_resource2)

        # 检查资源是否已清理
        assert len(_resources) == 0

    def test_cleanup_resources_with_none_resource(self):
        """测试清理资源（资源为None）"""
        # 注册资源为None的资源
        mock_cleanup = Mock()
        register_resource("test_resource", None, mock_cleanup)

        # 清理资源
        cleanup_resources()

        # 检查清理函数是否被调用（无参数）
        mock_cleanup.assert_called_once_with()

        # 检查资源是否已清理
        assert len(_resources) == 0

    def test_cleanup_resources_with_exception(self):
        """测试清理资源时出现异常"""
        # 注册会抛出异常的资源
        mock_resource = Mock()
        mock_cleanup = Mock(side_effect=Exception("Cleanup failed"))
        register_resource("test_resource", mock_resource, mock_cleanup)

        # 清理资源（不应该抛出异常）
        cleanup_resources()

        # 检查清理函数是否被调用
        mock_cleanup.assert_called_once_with(mock_resource)

        # 检查资源是否已清理
        assert len(_resources) == 0

    def test_cleanup_resources_reverse_order(self):
        """测试清理资源的反向顺序"""
        # 注册多个资源
        cleanup_order = []

        def create_cleanup(name):
            def cleanup(resource):
                cleanup_order.append(name)
            return cleanup

        register_resource("resource1", Mock(), create_cleanup("resource1"))
        register_resource("resource2", Mock(), create_cleanup("resource2"))
        register_resource("resource3", Mock(), create_cleanup("resource3"))

        # 清理资源
        cleanup_resources()

        # 检查清理顺序（应该是反向的）
        assert cleanup_order == ["resource3", "resource2", "resource1"]

    def test_thread_safety(self):
        """测试线程安全性"""
        results = []

        def worker(thread_id):
            # 注册资源
            mock_resource = Mock()
            mock_cleanup = Mock()
            register_resource(f"resource_{thread_id}", mock_resource, mock_cleanup)

            # 注销资源
            unregister_resource(f"resource_{thread_id}")

            results.append(thread_id)

        # 创建多个线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查所有线程都成功完成
        assert len(results) == 10
        assert set(results) == set(range(10))

    def test_resource_locking(self):
        """测试资源锁定"""
        # 测试锁是否正确工作
        assert _resource_lock.locked() is False

        with _resource_lock:
            assert _resource_lock.locked() is True

        assert _resource_lock.locked() is False

    def test_multiple_cleanup_calls(self):
        """测试多次清理调用"""
        # 注册资源
        mock_resource = Mock()
        mock_cleanup = Mock()
        register_resource("test_resource", mock_resource, mock_cleanup)

        # 多次清理
        cleanup_resources()
        cleanup_resources()
        cleanup_resources()

        # 清理函数应该只被调用一次
        mock_cleanup.assert_called_once_with(mock_resource)

    def test_resource_registration_during_cleanup(self):
        """测试清理期间注册资源"""
        # 注册一个会在清理时注册新资源的资源
        def cleanup_with_registration(resource):
            # 在清理时注册新资源
            register_resource("new_resource", Mock(), Mock())

        register_resource("test_resource", Mock(), cleanup_with_registration)

        # 清理资源
        cleanup_resources()

        # 新注册的资源不应该被清理
        assert "new_resource" in _resources

    def test_complex_resource_scenario(self):
        """测试复杂资源场景"""
        # 模拟数据库连接
        db_connection = Mock()
        db_cleanup = Mock()
        register_resource("database", db_connection, db_cleanup)

        # 模拟缓存管理器
        cache_manager = Mock()
        cache_cleanup = Mock()
        register_resource("cache", cache_manager, cache_cleanup)

        # 模拟事件总线
        event_bus = Mock()
        event_cleanup = Mock()
        register_resource("event_bus", event_bus, event_cleanup)

        # 检查所有资源都已注册
        assert len(_resources) == 3

        # 清理资源
        cleanup_resources()

        # 检查所有清理函数都被调用
        db_cleanup.assert_called_once_with(db_connection)
        cache_cleanup.assert_called_once_with(cache_manager)
        event_cleanup.assert_called_once_with(event_bus)

        # 检查资源已清理
        assert len(_resources) == 0

    def test_resource_cleanup_with_context_manager(self):
        """测试资源清理的上下文管理器"""
        # 模拟支持上下文管理器的资源
        class ContextResource:
            def __init__(self):
                self.closed = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.closed = True

        resource = ContextResource()

        def cleanup(resource):
            if hasattr(resource, '__exit__'):
                resource.__exit__(None, None, None)

        register_resource("context_resource", resource, cleanup)

        # 清理资源
        cleanup_resources()

        # 检查资源是否被正确关闭
        assert resource.closed is True

    def test_performance(self):
        """测试性能"""

        # 测试注册性能
        start_time = time.time()
        for i in range(1000):
            register_resource(f"resource_{i}", Mock(), Mock())
        register_time = time.time() - start_time

        # 测试注销性能
        start_time = time.time()
        for i in range(1000):
            unregister_resource(f"resource_{i}")
        unregister_time = time.time() - start_time

        # 测试清理性能
        # 重新注册一些资源
        for i in range(100):
            register_resource(f"resource_{i}", Mock(), Mock())

        start_time = time.time()
        cleanup_resources()
        cleanup_time = time.time() - start_time

        # 性能应该合理
        assert register_time < 1.0  # 1000次注册应该在1秒内
        assert unregister_time < 1.0  # 1000次注销应该在1秒内
        assert cleanup_time < 0.1  # 100次清理应该在0.1秒内

        print(f"Register performance: {register_time:.3f}s for 1000 operations")
        print(f"Unregister performance: {unregister_time:.3f}s for 1000 operations")
        print(f"Cleanup performance: {cleanup_time:.3f}s for 100 operations")

    def test_error_handling(self):
        """测试错误处理"""
        # 测试注册None名称
        with pytest.raises(ValueError):
            register_resource(None, Mock(), Mock())

        # 测试注册空名称
        with pytest.raises(ValueError):
            register_resource("", Mock(), Mock())

        # 测试注册None清理函数
        with pytest.raises(ValueError):
            register_resource("test", Mock(), None)

    def test_resource_manager_integration(self):
        """测试资源管理器集成"""
        # 模拟完整的应用程序资源管理场景

        # 1. 注册数据库连接
        db_connection = Mock()
        def db_cleanup(conn):
            conn.close()
        register_resource("database", db_connection, db_cleanup)

        # 2. 注册缓存管理器
        cache_manager = Mock()
        def cache_cleanup(cache):
            cache.close()
        register_resource("cache", cache_manager, cache_cleanup)

        # 3. 注册事件总线
        event_bus = Mock()
        def event_cleanup(bus):
            bus.close()
        register_resource("event_bus", event_bus, event_cleanup)

        # 4. 注册日志系统
        logger = Mock()
        def logger_cleanup(log):
            log.shutdown()
        register_resource("logger", logger, logger_cleanup)

        # 检查所有资源都已注册
        assert len(_resources) == 4

        # 模拟应用程序关闭，清理所有资源
        cleanup_resources()

        # 检查所有资源都被正确清理
        assert len(_resources) == 0

        # 检查清理函数都被调用
        db_connection.close.assert_called_once()
        cache_manager.close.assert_called_once()
        event_bus.close.assert_called_once()
        logger.shutdown.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
