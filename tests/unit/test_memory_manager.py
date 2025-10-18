"""内存管理器测试"""

import pytest
import time
import gc
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.memory_manager import (
    MemoryManager,
    MemoryMetrics,
    MemoryThreshold,
    get_memory_manager,
    close_memory_manager,
)


class TestMemoryManager:
    """内存管理器测试类"""

    def setup_method(self):
        """测试前准备"""
        self.memory_manager = MemoryManager(
            check_interval=0.1,
            threshold_warning=50,
            threshold_critical=80
        )

    def teardown_method(self):
        """测试后清理"""
        self.memory_manager.close()

    def test_memory_manager_initialization(self):
        """测试内存管理器初始化"""
        assert self.memory_manager.check_interval == 0.1
        assert self.memory_manager.threshold_warning == 50
        assert self.memory_manager.threshold_critical == 80
        assert self.memory_manager.is_monitoring is False

    def test_start_monitoring(self):
        """测试开始监控"""
        self.memory_manager.start_monitoring()
        assert self.memory_manager.is_monitoring is True

        # 等待一段时间确保监控开始
        time.sleep(0.2)

        # 检查是否有监控数据
        assert len(self.memory_manager.metrics_history) > 0

    def test_stop_monitoring(self):
        """测试停止监控"""
        self.memory_manager.start_monitoring()
        assert self.memory_manager.is_monitoring is True

        self.memory_manager.stop_monitoring()
        assert self.memory_manager.is_monitoring is False

    def test_get_current_metrics(self):
        """测试获取当前指标"""
        metrics = self.memory_manager.get_current_metrics()

        assert isinstance(metrics, MemoryMetrics)
        assert metrics.timestamp is not None
        assert metrics.rss_mb >= 0
        assert metrics.vms_mb >= 0
        assert metrics.percent >= 0
        assert metrics.available_mb >= 0

    def test_get_memory_usage(self):
        """测试获取内存使用情况"""
        usage = self.memory_manager.get_memory_usage()

        assert isinstance(usage, dict)
        assert "rss_mb" in usage
        assert "vms_mb" in usage
        assert "percent" in usage
        assert "available_mb" in usage
        assert "timestamp" in usage

    def test_check_memory_threshold(self):
        """测试内存阈值检查"""
        # 模拟低内存使用
        with patch.object(self.memory_manager, 'get_current_metrics') as mock_metrics:
            mock_metrics.return_value = MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=100,
                vms_mb=200,
                percent=30,
                available_mb=1000
            )

            threshold = self.memory_manager.check_memory_threshold()
            assert threshold == MemoryThreshold.NORMAL

        # 模拟警告级别内存使用
        with patch.object(self.memory_manager, 'get_current_metrics') as mock_metrics:
            mock_metrics.return_value = MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=100,
                vms_mb=200,
                percent=60,
                available_mb=1000
            )

            threshold = self.memory_manager.check_memory_threshold()
            assert threshold == MemoryThreshold.WARNING

        # 模拟严重级别内存使用
        with patch.object(self.memory_manager, 'get_current_metrics') as mock_metrics:
            mock_metrics.return_value = MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=100,
                vms_mb=200,
                percent=90,
                available_mb=1000
            )

            threshold = self.memory_manager.check_memory_threshold()
            assert threshold == MemoryThreshold.CRITICAL

    def test_optimize_memory(self):
        """测试内存优化"""
        # 创建一些对象来占用内存
        data = []
        for i in range(1000):
            data.append([i] * 100)

        # 记录优化前的内存
        before_metrics = self.memory_manager.get_current_metrics()

        # 执行内存优化
        self.memory_manager.optimize_memory()

        # 记录优化后的内存
        after_metrics = self.memory_manager.get_current_metrics()

        # 内存使用应该有所改善
        assert after_metrics.rss_mb <= before_metrics.rss_mb

    def test_force_garbage_collection(self):
        """测试强制垃圾回收"""
        # 创建一些对象
        data = []
        for i in range(1000):
            data.append([i] * 100)

        # 删除引用
        del data

        # 强制垃圾回收
        self.memory_manager.force_garbage_collection()

        # 检查垃圾回收统计
        stats = self.memory_manager.get_gc_stats()
        assert stats["collections"] > 0

    def test_detect_memory_leak(self):
        """测试内存泄漏检测"""
        # 模拟正常内存使用
        with patch.object(self.memory_manager, 'get_current_metrics') as mock_metrics:
            mock_metrics.side_effect = [
                MemoryMetrics(datetime.now(), 100, 200, 50, 1000),
                MemoryMetrics(datetime.now(), 105, 205, 52, 1000),
                MemoryMetrics(datetime.now(), 110, 210, 54, 1000),
            ]

            # 添加多个指标到历史记录
            for _ in range(3):
                self.memory_manager._collect_metrics()

            # 检测内存泄漏
            is_leak = self.memory_manager.detect_memory_leak()
            assert isinstance(is_leak, bool)

    def test_get_memory_trend(self):
        """测试获取内存趋势"""
        # 添加一些模拟数据
        now = datetime.now()
        for i in range(10):
            metrics = MemoryMetrics(
                timestamp=now,
                rss_mb=100 + i * 5,
                vms_mb=200 + i * 5,
                percent=50 + i * 2,
                available_mb=1000 - i * 10
            )
            self.memory_manager.metrics_history.append(metrics)

        trend = self.memory_manager.get_memory_trend()

        assert isinstance(trend, dict)
        assert "direction" in trend
        assert "rate" in trend
        assert "confidence" in trend

    def test_get_fragmentation_rate(self):
        """测试获取碎片化率"""
        # 添加一些模拟数据
        now = datetime.now()
        for i in range(5):
            metrics = MemoryMetrics(
                timestamp=now,
                rss_mb=100 + i * 2,
                vms_mb=200 + i * 2,
                percent=50 + i,
                available_mb=1000 - i * 5
            )
            self.memory_manager.metrics_history.append(metrics)

        fragmentation_rate = self.memory_manager.get_fragmentation_rate()

        assert isinstance(fragmentation_rate, float)
        assert 0 <= fragmentation_rate <= 1

    def test_get_gc_stats(self):
        """测试获取垃圾回收统计"""
        # 执行一些垃圾回收
        gc.collect()

        stats = self.memory_manager.get_gc_stats()

        assert isinstance(stats, dict)
        assert "collections" in stats
        assert "collected" in stats
        assert "uncollectable" in stats

    def test_get_memory_alerts(self):
        """测试获取内存警报"""
        # 模拟高内存使用
        with patch.object(self.memory_manager, 'get_current_metrics') as mock_metrics:
            mock_metrics.return_value = MemoryMetrics(
                timestamp=datetime.now(),
                rss_mb=100,
                vms_mb=200,
                percent=85,
                available_mb=1000
            )

            alerts = self.memory_manager.get_memory_alerts()

            assert isinstance(alerts, list)
            if alerts:
                assert all(isinstance(alert, dict) for alert in alerts)

    def test_context_manager(self):
        """测试上下文管理器"""
        with MemoryManager() as memory:
            assert memory.is_monitoring is False
            memory.start_monitoring()
            assert memory.is_monitoring is True
        # 上下文退出后应该自动停止监控

    def test_singleton_pattern(self):
        """测试单例模式"""
        # 获取全局内存管理器
        memory1 = get_memory_manager()
        memory2 = get_memory_manager()

        # 应该是同一个实例
        assert memory1 is memory2

        # 清理
        close_memory_manager()

    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        import time

        results = []

        def worker(thread_id):
            for i in range(10):
                metrics = self.memory_manager.get_current_metrics()
                results.append((thread_id, i, metrics is not None))
                time.sleep(0.001)

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查所有操作都成功
        for thread_id, i, success in results:
            assert success, f"Thread {thread_id}, iteration {i} failed"

    def test_performance(self):
        """测试性能"""
        import time

        # 测试获取指标性能
        start_time = time.time()
        for i in range(100):
            self.memory_manager.get_current_metrics()
        get_time = time.time() - start_time

        # 测试内存优化性能
        start_time = time.time()
        for i in range(10):
            self.memory_manager.optimize_memory()
        optimize_time = time.time() - start_time

        # 性能应该合理
        assert get_time < 1.0  # 100次获取应该在1秒内
        assert optimize_time < 2.0  # 10次优化应该在2秒内

        print(f"Get metrics performance: {get_time:.3f}s for 100 operations")
        print(f"Optimize memory performance: {optimize_time:.3f}s for 10 operations")

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效阈值
        with pytest.raises(ValueError):
            MemoryManager(threshold_warning=-1)

        with pytest.raises(ValueError):
            MemoryManager(threshold_critical=101)

        with pytest.raises(ValueError):
            MemoryManager(threshold_warning=80, threshold_critical=50)

    def test_memory_metrics(self):
        """测试内存指标"""
        now = datetime.now()
        metrics = MemoryMetrics(
            timestamp=now,
            rss_mb=100.5,
            vms_mb=200.3,
            percent=75.2,
            available_mb=500.1
        )

        assert metrics.timestamp == now
        assert metrics.rss_mb == 100.5
        assert metrics.vms_mb == 200.3
        assert metrics.percent == 75.2
        assert metrics.available_mb == 500.1

    def test_memory_threshold_enum(self):
        """测试内存阈值枚举"""
        assert MemoryThreshold.NORMAL.value == "normal"
        assert MemoryThreshold.WARNING.value == "warning"
        assert MemoryThreshold.CRITICAL.value == "critical"

    def test_monitoring_callbacks(self):
        """测试监控回调"""
        callback_called = False

        def test_callback(metrics):
            nonlocal callback_called
            callback_called = True
            assert isinstance(metrics, MemoryMetrics)

        # 注册回调
        self.memory_manager.add_monitoring_callback(test_callback)

        # 开始监控
        self.memory_manager.start_monitoring()

        # 等待回调被调用
        time.sleep(0.2)

        # 检查回调是否被调用
        assert callback_called

        # 停止监控
        self.memory_manager.stop_monitoring()

    def test_memory_history_cleanup(self):
        """测试内存历史清理"""
        # 添加大量历史数据
        now = datetime.now()
        for i in range(1000):
            metrics = MemoryMetrics(
                timestamp=now,
                rss_mb=100 + i,
                vms_mb=200 + i,
                percent=50 + i * 0.1,
                available_mb=1000 - i
            )
            self.memory_manager.metrics_history.append(metrics)

        # 执行清理
        self.memory_manager._cleanup_history()

        # 检查历史记录数量是否合理
        assert len(self.memory_manager.metrics_history) <= self.memory_manager.max_history


if __name__ == "__main__":
    pytest.main([__file__])
