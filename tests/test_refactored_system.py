"""
重构后系统的综合测试
测试所有重构后的核心组件和功能
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.core.common_exceptions import (
    VirtualChemLabError,
    ConfigurationError,
    ValidationError,
    NetworkError,
    UIError,
    PerformanceError,
    ErrorCategory,
    ErrorSeverity,
)
from src.core.error_handler import ErrorHandler, get_error_handler
from src.core.enhanced_event_bus import (
    EnhancedEventBus,
    Event,
    EventPriority,
    get_event_bus,
    publish_event,
    subscribe_event,
)
from src.core.enhanced_error_recovery import (
    EnhancedErrorRecovery,
    RecoveryRule,
    RecoveryStrategy,
    get_error_recovery,
)
from src.core.unified_config_manager import (
    UnifiedConfigManager,
    get_config_manager,
    get_config,
    set_config,
)
from src.core.unified_performance_monitor import (
    UnifiedPerformanceMonitor,
    PerformanceMetric,
    MetricType,
    get_performance_monitor,
)
from src.core.performance_alerting import (
    PerformanceAlerting,
    AlertRule,
    AlertSeverity,
    get_performance_alerting,
)
from src.core.config_migration import (
    ConfigMigrationManager,
    get_config_migration_manager,
    migrate_config,
)


class TestCommonExceptions:
    """测试统一异常系统"""

    def test_virtualchemlab_error_creation(self):
        """测试基础异常创建"""
        error = VirtualChemLabError(
            message="Test error",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.MEDIUM
        )

        assert error.message == "Test error"
        assert error.category == ErrorCategory.SYSTEM
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.error_code is None
        assert error.details == {}
        assert error.cause is None

    def test_error_with_details(self):
        """测试带详情的异常"""
        error = VirtualChemLabError(
            message="Test error",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            error_code="TEST_ERROR",
            details={"key": "value"},
            cause=ValueError("Original error")
        )

        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert isinstance(error.cause, ValueError)

    def test_error_to_dict(self):
        """测试异常转字典"""
        error = VirtualChemLabError(
            message="Test error",
            category=ErrorCategory.UI,
            severity=ErrorSeverity.LOW
        )

        error_dict = error.to_dict()

        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "ui"
        assert error_dict["severity"] == "low"
        assert "timestamp" in error_dict

    def test_specific_error_types(self):
        """测试特定错误类型"""
        # 配置错误
        config_error = ConfigurationError("Config error", config_key="test_key")
        assert config_error.category == ErrorCategory.CONFIGURATION
        assert config_error.severity == ErrorSeverity.HIGH
        assert config_error.details["config_key"] == "test_key"

        # 验证错误
        validation_error = ValidationError("Validation error", field="test_field")
        assert validation_error.category == ErrorCategory.VALIDATION
        assert validation_error.details["field"] == "test_field"

        # 网络错误
        network_error = NetworkError("Network error", url="http://test.com")
        assert network_error.category == ErrorCategory.NETWORK
        assert network_error.details["url"] == "http://test.com"

        # UI错误
        ui_error = UIError("UI error", widget="test_widget")
        assert ui_error.category == ErrorCategory.UI
        assert ui_error.details["widget"] == "test_widget"

        # 性能错误
        perf_error = PerformanceError("Performance error", metric="cpu_usage")
        assert perf_error.category == ErrorCategory.PERFORMANCE
        assert perf_error.details["metric"] == "cpu_usage"


class TestErrorHandler:
    """测试错误处理器"""

    def test_error_handler_creation(self):
        """测试错误处理器创建"""
        handler = ErrorHandler()
        assert isinstance(handler, ErrorHandler)

    def test_error_callback_registration(self):
        """测试错误回调注册"""
        handler = ErrorHandler()
        callback = Mock()

        handler.register_callback(ErrorCategory.SYSTEM, callback)

        # 模拟错误处理
        error = VirtualChemLabError("Test error", ErrorCategory.SYSTEM)
        handler.handle_error(error)

        callback.assert_called_once_with(error)

    def test_error_recovery_strategy(self):
        """测试错误恢复策略"""
        handler = ErrorHandler()
        strategy = Mock(return_value="recovered")

        handler.register_recovery_strategy(VirtualChemLabError, strategy)

        error = VirtualChemLabError("Test error")
        result = handler.handle_error(error)

        strategy.assert_called_once_with(error)
        assert result == "recovered"

    def test_error_stats(self):
        """测试错误统计"""
        handler = ErrorHandler()

        # 处理几个错误
        handler.handle_error(VirtualChemLabError("Error 1", ErrorCategory.SYSTEM))
        handler.handle_error(VirtualChemLabError("Error 2", ErrorCategory.UI))

        stats = handler.get_error_stats()

        assert stats["system_medium"] == 1
        assert stats["ui_medium"] == 1


class TestEnhancedEventBus:
    """测试增强事件总线"""

    def test_event_bus_creation(self):
        """测试事件总线创建"""
        bus = EnhancedEventBus()
        assert isinstance(bus, EnhancedEventBus)

    def test_event_creation(self):
        """测试事件创建"""
        event = Event(
            name="test_event",
            data={"key": "value"},
            source="test_source",
            priority=EventPriority.HIGH
        )

        assert event.name == "test_event"
        assert event.data == {"key": "value"}
        assert event.source == "test_source"
        assert event.priority == EventPriority.HIGH

    def test_event_subscription(self):
        """测试事件订阅"""
        bus = EnhancedEventBus()
        callback = Mock()

        subscription = bus.subscribe("test_event", callback)

        assert subscription.callback == callback
        assert subscription.event_name == "test_event"

    def test_event_publishing(self):
        """测试事件发布"""
        bus = EnhancedEventBus()
        callback = Mock()

        bus.subscribe("test_event", callback)
        bus.publish_sync("test_event", {"data": "test"})

        callback.assert_called_once()
        called_event = callback.call_args[0][0]
        assert called_event.name == "test_event"
        assert called_event.data == {"data": "test"}

    def test_event_filtering(self):
        """测试事件过滤"""
        bus = EnhancedEventBus()
        callback1 = Mock()
        callback2 = Mock()

        # 订阅特定标签的事件
        bus.subscribe("test_event", callback1, tags_filter={"type": "important"})
        bus.subscribe("test_event", callback2)

        # 发布带标签的事件
        bus.publish_sync("test_event", {"data": "test"}, tags={"type": "important"})

        # 两个回调都应该被调用
        callback1.assert_called_once()
        callback2.assert_called_once()

        # 发布不带标签的事件
        bus.publish_sync("test_event", {"data": "test2"})

        # 只有第二个回调被调用
        assert callback1.call_count == 1
        assert callback2.call_count == 2


class TestEnhancedErrorRecovery:
    """测试增强错误恢复"""

    def test_error_recovery_creation(self):
        """测试错误恢复系统创建"""
        recovery = EnhancedErrorRecovery()
        assert isinstance(recovery, EnhancedErrorRecovery)

    def test_recovery_rule_registration(self):
        """测试恢复规则注册"""
        recovery = EnhancedErrorRecovery()
        rule = RecoveryRule(
            error_type=VirtualChemLabError,
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3
        )

        recovery.add_recovery_rule(VirtualChemLabError, rule)

        retrieved_rule = recovery.get_recovery_rule(VirtualChemLabError("test"))
        assert retrieved_rule == rule

    def test_retry_strategy(self):
        """测试重试策略"""
        recovery = EnhancedErrorRecovery()
        rule = RecoveryRule(
            error_type=VirtualChemLabError,
            strategy=RecoveryStrategy.RETRY,
            max_attempts=2,
            delay=0.1
        )

        recovery.add_recovery_rule(VirtualChemLabError, rule)

        error = VirtualChemLabError("Test error")
        result = recovery.recover_error(error)

        assert result == "retry"

    def test_fallback_strategy(self):
        """测试回退策略"""
        recovery = EnhancedErrorRecovery()
        fallback_func = Mock(return_value="fallback_result")

        rule = RecoveryRule(
            error_type=VirtualChemLabError,
            strategy=RecoveryStrategy.FALLBACK,
            fallback_function=fallback_func
        )

        recovery.add_recovery_rule(VirtualChemLabError, rule)

        error = VirtualChemLabError("Test error")
        result = recovery.recover_error(error)

        assert result == "fallback_result"
        fallback_func.assert_called_once_with(error, None)

    def test_circuit_breaker_strategy(self):
        """测试熔断器策略"""
        recovery = EnhancedErrorRecovery()
        rule = RecoveryRule(
            error_type=VirtualChemLabError,
            strategy=RecoveryStrategy.CIRCUIT_BREAKER,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=1.0
        )

        recovery.add_recovery_rule(VirtualChemLabError, rule)

        error = VirtualChemLabError("Test error")

        # 第一次应该通过
        result1 = recovery.recover_error(error)
        assert result1 == "circuit_breaker_check_passed"

        # 模拟多次失败
        for _ in range(3):
            recovery.recover_error(error)

        # 现在应该被熔断
        result2 = recovery.recover_error(error)
        assert result2 is None


class TestUnifiedConfigManager:
    """测试统一配置管理器"""

    def test_config_manager_creation(self):
        """测试配置管理器创建"""
        manager = UnifiedConfigManager()
        assert isinstance(manager, UnifiedConfigManager)

    def test_config_manager_initialization(self):
        """测试配置管理器初始化"""
        manager = UnifiedConfigManager()
        manager.initialize()

        assert manager.is_initialized()
        assert manager.has("app.name")
        assert manager.get("app.name") == "VirtualChemLab"

    def test_config_get_set(self):
        """测试配置获取和设置"""
        manager = UnifiedConfigManager()
        manager.initialize()

        # 设置配置
        manager.set("test.key", "test_value")

        # 获取配置
        value = manager.get("test.key")
        assert value == "test_value"

        # 检查存在性
        assert manager.has("test.key")
        assert not manager.has("nonexistent.key")

    def test_config_validation(self):
        """测试配置验证"""
        manager = UnifiedConfigManager()
        manager.initialize()

        # 验证所有配置
        is_valid = manager.validate_all()
        assert is_valid

    def test_config_section_management(self):
        """测试配置节管理"""
        manager = UnifiedConfigManager()
        manager.initialize()

        # 添加新节
        manager.add_section("test_section")

        # 设置节内配置
        manager.set("test_section.key1", "value1")
        manager.set("test_section.key2", "value2")

        # 获取节
        section = manager.get_section("test_section")
        assert section is not None
        assert section.name == "test_section"
        assert section.get("key1") == "value1"
        assert section.get("key2") == "value2"


class TestUnifiedPerformanceMonitor:
    """测试统一性能监控器"""

    def test_performance_monitor_creation(self):
        """测试性能监控器创建"""
        monitor = UnifiedPerformanceMonitor()
        assert isinstance(monitor, UnifiedPerformanceMonitor)

    def test_performance_metric_creation(self):
        """测试性能指标创建"""
        metric = PerformanceMetric(
            name="test_metric",
            value=42.0,
            timestamp=time.time(),
            unit="ms"
        )

        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.unit == "ms"

    def test_metric_collection(self):
        """测试指标收集"""
        monitor = UnifiedPerformanceMonitor()

        # 收集指标
        metric = PerformanceMetric(
            name="test_metric",
            value=42.0,
            timestamp=time.time()
        )

        monitor._collector.collect_metric(metric)

        # 获取历史
        history = monitor.get_metric_history("test_metric")
        assert len(history) == 1
        assert history[0].value == 42.0

    def test_performance_decorator(self):
        """测试性能装饰器"""
        monitor = UnifiedPerformanceMonitor()

        @monitor.measure_function("test_function")
        def test_function():
            time.sleep(0.01)  # 模拟工作
            return "result"

        result = test_function()
        assert result == "result"

        # 检查是否记录了性能指标
        history = monitor.get_metric_history(MetricType.FUNCTION_TIME.value)
        assert len(history) > 0

    def test_performance_context(self):
        """测试性能上下文"""
        monitor = UnifiedPerformanceMonitor()

        with monitor.measure_context("test_context"):
            time.sleep(0.01)  # 模拟工作

        # 检查是否记录了性能指标
        history = monitor.get_metric_history(MetricType.FUNCTION_TIME.value)
        assert len(history) > 0

    def test_performance_report(self):
        """测试性能报告"""
        monitor = UnifiedPerformanceMonitor()

        # 记录一些指标
        monitor.record_fps(60.0)
        monitor.record_frame_time(16.67)

        report = monitor.get_performance_report()

        assert "timestamp" in report
        assert "metrics" in report
        assert "monitoring" in report


class TestPerformanceAlerting:
    """测试性能告警系统"""

    def test_performance_alerting_creation(self):
        """测试性能告警系统创建"""
        alerting = PerformanceAlerting()
        assert isinstance(alerting, PerformanceAlerting)

    def test_alert_rule_management(self):
        """测试告警规则管理"""
        alerting = PerformanceAlerting()

        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            threshold=80.0,
            comparison="gt",
            severity=AlertSeverity.WARNING
        )

        alerting.add_rule(rule)

        retrieved_rule = alerting.get_rule("test_rule")
        assert retrieved_rule == rule

        alerting.remove_rule("test_rule")
        assert alerting.get_rule("test_rule") is None

    def test_alert_triggering(self):
        """测试告警触发"""
        alerting = PerformanceAlerting()

        # 添加测试规则
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            threshold=50.0,
            comparison="gt",
            severity=AlertSeverity.WARNING
        )
        alerting.add_rule(rule)

        # 创建超过阈值的指标
        metric = PerformanceMetric(
            name="test_metric",
            value=60.0,
            timestamp=time.time()
        )

        # 检查指标
        alerting.check_metric(metric)

        # 检查是否触发了告警
        active_alerts = alerting.get_active_alerts()
        assert "test_rule" in active_alerts

    def test_alert_acknowledgment(self):
        """测试告警确认"""
        alerting = PerformanceAlerting()

        # 触发告警
        rule = AlertRule(
            name="test_rule",
            metric_name="test_metric",
            threshold=50.0,
            comparison="gt",
            severity=AlertSeverity.WARNING
        )
        alerting.add_rule(rule)

        metric = PerformanceMetric(
            name="test_metric",
            value=60.0,
            timestamp=time.time()
        )
        alerting.check_metric(metric)

        # 确认告警
        success = alerting.acknowledge_alert("test_rule", "test_user")
        assert success

        # 检查告警状态
        active_alerts = alerting.get_active_alerts()
        assert "test_rule" not in active_alerts


class TestConfigMigration:
    """测试配置迁移"""

    def test_config_migration_creation(self):
        """测试配置迁移系统创建"""
        migration = ConfigMigrationManager(Mock())
        assert isinstance(migration, ConfigMigrationManager)

    def test_version_detection(self):
        """测试版本检测"""
        migration = ConfigMigrationManager(Mock())

        # 测试v1.0.0配置
        v1_config = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "environment": "development"
            }
        }

        version = migration.detect_config_version(v1_config)
        assert version == "1.0.0"

        # 测试v2.0.0配置
        v2_config = {
            "app": {
                "name": "TestApp",
                "version": "2.0.0",
                "environment": "development"
            },
            "ui": {
                "theme": "dark"
            }
        }

        version = migration.detect_config_version(v2_config)
        assert version == "2.0.0"

    def test_config_migration(self):
        """测试配置迁移"""
        migration = ConfigMigrationManager(Mock())

        # v1.0.0配置
        v1_config = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "environment": "development"
            }
        }

        # 迁移到v2.0.0
        migrated_config = migration.migrate_config(v1_config, "2.0.0")

        assert "ui" in migrated_config
        assert "performance" in migrated_config
        assert migrated_config["app"]["version"] == "2.0.0"
        assert migrated_config["app"]["debug"] is False
        assert migrated_config["app"]["log_level"] == "INFO"


class TestIntegration:
    """集成测试"""

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 创建错误
        error = ConfigurationError("Test config error", config_key="test_key")

        # 使用错误处理器
        handler = get_error_handler()
        result = handler.handle_error(error)

        # 检查错误统计
        stats = handler.get_error_stats()
        assert "configuration_high" in stats

    def test_event_bus_integration(self):
        """测试事件总线集成"""
        bus = get_event_bus()
        callback = Mock()

        # 订阅事件
        bus.subscribe("test_event", callback)

        # 发布事件
        bus.publish_sync("test_event", {"data": "test"})

        # 检查回调是否被调用
        callback.assert_called_once()

    def test_performance_monitoring_integration(self):
        """测试性能监控集成"""
        monitor = get_performance_monitor()

        # 记录性能指标
        monitor.record_fps(60.0)
        monitor.record_frame_time(16.67)

        # 获取性能报告
        report = monitor.get_performance_report()

        assert "metrics" in report
        assert "fps" in report["metrics"]
        assert "frame_time" in report["metrics"]

    def test_config_management_integration(self):
        """测试配置管理集成"""
        manager = get_config_manager()
        manager.initialize()

        # 设置配置
        set_config("test.integration", "value")

        # 获取配置
        value = get_config("test.integration")
        assert value == "value"

        # 检查存在性
        assert has_config("test.integration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
