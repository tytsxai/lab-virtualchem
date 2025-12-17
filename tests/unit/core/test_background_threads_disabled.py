from src.core.enhanced_performance import (
    EnhancedPerformanceManager,
    performance_manager,
)
from src.core.high_performance_cache import HighPerformanceLRUCache
from src.monitoring.backend_monitor import BackendMonitor, backend_monitor


def test_backend_monitor_does_not_start_thread_under_pytest() -> None:
    monitor = BackendMonitor(enable_resource_monitoring=True)
    assert monitor._resource_monitor_running is False
    assert monitor._resource_monitor_thread is None


def test_global_backend_monitor_does_not_start_thread_under_pytest() -> None:
    assert backend_monitor._resource_monitor_running is False


def test_enhanced_performance_manager_does_not_start_thread_under_pytest() -> None:
    manager = EnhancedPerformanceManager()
    assert manager.monitor.monitoring_active is False
    assert manager.monitor.monitor_thread is None


def test_global_performance_manager_does_not_start_thread_under_pytest() -> None:
    assert performance_manager.monitor.monitoring_active is False


def test_high_performance_cache_does_not_start_thread_under_pytest() -> None:
    cache = HighPerformanceLRUCache()
    assert cache.auto_cleanup is False
    assert cache._cleanup_thread is None
