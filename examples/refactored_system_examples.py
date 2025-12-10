"""
重构后系统的使用示例
展示如何使用重构后的各种组件和功能
"""

import asyncio
import time
from pathlib import Path

from src import __version__ as APP_VERSION
# 导入重构后的核心组件
from src.core.common_exceptions import (
    VirtualChemLabError,
    ConfigurationError,
    ValidationError,
    NetworkError,
    UIError,
    PerformanceError,
    ErrorCategory,
    ErrorSeverity,
    handle_errors,
    recoverable_error,
)
from src.core.error_handler import (
    get_error_handler,
    safe_execute,
    error_context,
    log_and_continue,
    log_and_raise,
)
from src.core.enhanced_event_bus import (
    get_event_bus,
    Event,
    EventPriority,
    publish_event,
    subscribe_event,
)
from src.core.enhanced_error_recovery import (
    get_error_recovery,
    RecoveryRule,
    RecoveryStrategy,
    recover_error,
)
from src.core.unified_config_manager import (
    get_config_manager,
    get_config,
    set_config,
    has_config,
    remove_config,
)
from src.core.unified_performance_monitor import (
    get_performance_monitor,
    PerformanceMetric,
    MetricType,
    measure_performance,
    measure_context,
    record_fps,
    record_frame_time,
)
from src.core.performance_alerting import (
    get_performance_alerting,
    AlertRule,
    AlertSeverity,
    check_performance_metric,
)
from src.core.config_migration import (
    get_config_migration_manager,
    migrate_config,
    detect_config_version,
)


def example_error_handling():
    """错误处理示例"""
    print("=== 错误处理示例 ===")

    # 1. 基本错误处理
    try:
        raise ConfigurationError("配置文件格式错误", config_key="app.debug")
    except VirtualChemLabError as e:
        print(f"捕获到错误: {e}")
        print(f"错误详情: {e.to_dict()}")

    # 2. 使用错误处理装饰器
    @handle_errors()
    def risky_function():
        raise ValueError("这是一个风险函数")

    try:
        risky_function()
    except VirtualChemLabError as e:
        print(f"装饰器捕获的错误: {e}")

    # 3. 使用可恢复错误装饰器
    @recoverable_error(fallback_value="默认值", retry_count=2)
    def unreliable_function():
        if time.time() % 2 < 1:
            raise NetworkError("网络连接失败", url="http://example.com")
        return "成功结果"

    result = unreliable_function()
    print(f"可恢复函数结果: {result}")

    # 4. 使用安全执行
    def potentially_failing_function():
        raise ValidationError("验证失败", field="email")

    result = safe_execute(
        potentially_failing_function,
        error_class=ValidationError,
        fallback_value="验证失败，使用默认值"
    )
    print(f"安全执行结果: {result}")

    # 5. 使用错误上下文
    with error_context(ErrorCategory.SYSTEM, ErrorSeverity.HIGH):
        try:
            raise RuntimeError("系统错误")
        except Exception as e:
            log_and_raise(e, UIError)


def example_event_bus():
    """事件总线示例"""
    print("\n=== 事件总线示例 ===")

    # 获取事件总线
    event_bus = get_event_bus()

    # 1. 基本事件发布和订阅
    def event_handler(event: Event):
        print(f"收到事件: {event.name}, 数据: {event.data}")

    # 订阅事件
    subscription = subscribe_event("user_action", event_handler)

    # 发布事件
    publish_event("user_action", {"action": "click", "button": "submit"})

    # 2. 带标签的事件过滤
    def important_handler(event: Event):
        print(f"重要事件: {event.name}")

    def normal_handler(event: Event):
        print(f"普通事件: {event.name}")

    # 订阅带标签过滤的事件
    subscribe_event("system_event", important_handler, tags_filter={"priority": "high"})
    subscribe_event("system_event", normal_handler)

    # 发布不同优先级的事件
    publish_event("system_event", {"message": "系统启动"}, tags={"priority": "high"})
    publish_event("system_event", {"message": "系统运行"}, tags={"priority": "normal"})

    # 3. 一次性订阅
    def one_time_handler(event: Event):
        print(f"一次性事件: {event.name}")

    subscribe_event("startup_complete", one_time_handler, once=True)

    # 发布事件（只会触发一次）
    publish_event("startup_complete", {"status": "ready"})
    publish_event("startup_complete", {"status": "ready"})  # 不会再次触发

    # 4. 取消订阅
    event_bus.unsubscribe(subscription)
    publish_event("user_action", {"action": "click"})  # 不会触发


def example_error_recovery():
    """错误恢复示例"""
    print("\n=== 错误恢复示例 ===")

    recovery = get_error_recovery()

    # 1. 重试策略
    def failing_network_call():
        if time.time() % 3 < 1:
            raise NetworkError("网络连接失败", url="http://api.example.com")
        return "成功响应"

    # 添加重试规则
    retry_rule = RecoveryRule(
        error_type=NetworkError,
        strategy=RecoveryStrategy.RETRY,
        max_attempts=3,
        delay=0.1,
        backoff_multiplier=2.0
    )
    recovery.add_recovery_rule(NetworkError, retry_rule)

    # 尝试执行可能失败的操作
    try:
        result = failing_network_call()
        print(f"网络调用成功: {result}")
    except NetworkError as e:
        recovered = recover_error(e)
        print(f"错误恢复结果: {recovered}")

    # 2. 回退策略
    def fallback_function(error: VirtualChemLabError, context):
        return f"回退结果: {error.message}"

    fallback_rule = RecoveryRule(
        error_type=ValidationError,
        strategy=RecoveryStrategy.FALLBACK,
        fallback_function=fallback_function
    )
    recovery.add_recovery_rule(ValidationError, fallback_rule)

    try:
        raise ValidationError("验证失败", field="password")
    except ValidationError as e:
        recovered = recover_error(e)
        print(f"回退恢复结果: {recovered}")

    # 3. 熔断器策略
    circuit_breaker_rule = RecoveryRule(
        error_type=PerformanceError,
        strategy=RecoveryStrategy.CIRCUIT_BREAKER,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=5.0
    )
    recovery.add_recovery_rule(PerformanceError, circuit_breaker_rule)

    # 模拟多次性能错误
    for i in range(5):
        try:
            raise PerformanceError("性能问题", metric="cpu_usage")
        except PerformanceError as e:
            recovered = recover_error(e)
            print(f"熔断器检查结果 {i+1}: {recovered}")


def example_config_management():
    """配置管理示例"""
    print("\n=== 配置管理示例 ===")

    # 获取配置管理器
    config_manager = get_config_manager()
    config_manager.initialize()

    # 1. 基本配置操作
    # 设置配置
    set_config("app.name", "VirtualChemLab")
    set_config("app.debug", True)
    set_config("ui.theme", "dark")
    set_config("performance.cache_size", 1000)

    # 获取配置
    app_name = get_config("app.name")
    debug_mode = get_config("app.debug")
    theme = get_config("ui.theme")
    cache_size = get_config("performance.cache_size")

    print(f"应用名称: {app_name}")
    print(f"调试模式: {debug_mode}")
    print(f"主题: {theme}")
    print(f"缓存大小: {cache_size}")

    # 2. 配置存在性检查
    print(f"app.name 存在: {has_config('app.name')}")
    print(f"nonexistent.key 存在: {has_config('nonexistent.key')}")

    # 3. 配置节管理
    # 添加新配置节
    config_manager.add_section("experiment")
    set_config("experiment.auto_save", True)
    set_config("experiment.save_interval", 30)

    # 获取配置节
    experiment_section = config_manager.get_section("experiment")
    if experiment_section:
        print(f"实验配置节: {experiment_section.data}")

    # 4. 配置验证
    is_valid = config_manager.validate_all()
    print(f"配置验证结果: {is_valid}")

    # 5. 配置保存
    config_manager.save_config("example_config.json")
    print("配置已保存到 example_config.json")


def example_performance_monitoring():
    """性能监控示例"""
    print("\n=== 性能监控示例 ===")

    # 获取性能监控器
    monitor = get_performance_monitor()

    # 1. 使用性能装饰器
    @measure_performance("example_function")
    def example_function():
        time.sleep(0.01)  # 模拟工作
        return "完成"

    result = example_function()
    print(f"函数执行结果: {result}")

    # 2. 使用性能上下文
    with measure_context("example_context"):
        time.sleep(0.01)  # 模拟工作
        print("上下文执行完成")

    # 3. 手动记录性能指标
    record_fps(60.0)
    record_frame_time(16.67)

    # 4. 获取性能指标历史
    fps_history = monitor.get_metric_history(MetricType.FPS.value)
    frame_time_history = monitor.get_metric_history(MetricType.FRAME_TIME.value)
    function_time_history = monitor.get_metric_history(MetricType.FUNCTION_TIME.value)

    print(f"FPS 历史记录数量: {len(fps_history)}")
    print(f"帧时间历史记录数量: {len(frame_time_history)}")
    print(f"函数时间历史记录数量: {len(function_time_history)}")

    # 5. 获取性能统计
    fps_stats = monitor.get_metric_stats(MetricType.FPS.value)
    if fps_stats:
        print(f"FPS 统计: {fps_stats}")

    # 6. 获取性能报告
    report = monitor.get_performance_report()
    print(f"性能报告: {report}")


def example_performance_alerting():
    """性能告警示例"""
    print("\n=== 性能告警示例 ===")

    # 获取性能告警系统
    alerting = get_performance_alerting()

    # 1. 添加自定义告警规则
    custom_rule = AlertRule(
        name="custom_cpu_alert",
        metric_name="custom_cpu_metric",
        threshold=70.0,
        comparison="gt",
        severity=AlertSeverity.WARNING,
        description="自定义CPU告警"
    )
    alerting.add_rule(custom_rule)

    # 2. 模拟性能指标
    metrics = [
        PerformanceMetric("custom_cpu_metric", 65.0, time.time()),
        PerformanceMetric("custom_cpu_metric", 75.0, time.time()),
        PerformanceMetric("custom_cpu_metric", 85.0, time.time()),
    ]

    # 3. 检查指标并触发告警
    for metric in metrics:
        check_performance_metric(metric)
        print(f"检查指标: {metric.name} = {metric.value}")

    # 4. 获取活跃告警
    active_alerts = alerting.get_active_alerts()
    print(f"活跃告警数量: {len(active_alerts)}")

    for alert_name, alert in active_alerts.items():
        print(f"告警: {alert_name} - {alert.description}")
        print(f"  当前值: {alert.current_value}")
        print(f"  阈值: {alert.threshold}")
        print(f"  严重程度: {alert.severity.value}")

    # 5. 确认告警
    if active_alerts:
        alert_name = list(active_alerts.keys())[0]
        success = alerting.acknowledge_alert(alert_name, "example_user")
        print(f"告警确认结果: {success}")

    # 6. 获取告警统计
    stats = alerting.get_stats()
    print(f"告警统计: {stats}")


def example_config_migration():
    """配置迁移示例"""
    print("\n=== 配置迁移示例 ===")

    # 获取配置迁移管理器
    migration = get_config_migration_manager()

    # 1. 检测配置版本
    v1_config = {
        "app": {
            "name": "VirtualChemLab",
            "version": "1.0.0",
            "environment": "development"
        }
    }

    version = detect_config_version(v1_config)
    print(f"检测到配置版本: {version}")

    # 2. 迁移配置
    migrated_config = migrate_config(v1_config, APP_VERSION)
    print(f"迁移后的配置: {migrated_config}")

    # 3. 验证迁移结果
    assert "ui" in migrated_config
    assert "performance" in migrated_config
    assert migrated_config["app"]["version"] == APP_VERSION
    assert migrated_config["app"]["debug"] is False
    assert migrated_config["app"]["log_level"] == "INFO"

    print("配置迁移验证通过")

    # 4. 获取版本历史
    version_history = migration.get_version_history()
    print(f"支持的版本: {version_history}")

    # 5. 获取迁移信息
    migration_info = migration.get_migration_info("1.0.0", APP_VERSION)
    print(f"迁移信息: {migration_info}")


def example_integration():
    """集成示例"""
    print("\n=== 集成示例 ===")

    # 1. 错误处理 + 事件总线
    def error_event_handler(event: Event):
        print(f"错误事件: {event.name} - {event.data}")

    subscribe_event("error_occurred", error_event_handler)

    try:
        raise ConfigurationError("集成测试错误", config_key="integration.test")
    except VirtualChemLabError as e:
        # 发布错误事件
        publish_event("error_occurred", e.to_dict(), priority=EventPriority.HIGH)

        # 处理错误
        handler = get_error_handler()
        handler.handle_error(e)

    # 2. 性能监控 + 告警
    @measure_performance("integration_function")
    def integration_function():
        time.sleep(0.02)  # 模拟工作
        return "集成测试完成"

    result = integration_function()
    print(f"集成函数结果: {result}")

    # 检查性能指标
    monitor = get_performance_monitor()
    function_time_history = monitor.get_metric_history(MetricType.FUNCTION_TIME.value)

    if function_time_history:
        latest_metric = function_time_history[-1]
        check_performance_metric(latest_metric)

    # 3. 配置管理 + 迁移
    # 创建旧版本配置
    old_config = {
        "app": {
            "name": "VirtualChemLab",
            "version": "1.0.0",
            "environment": "development"
        }
    }

    # 迁移配置
    new_config = migrate_config(old_config, APP_VERSION)

    # 使用新配置
    config_manager = get_config_manager()
    config_manager.initialize()

    # 设置迁移后的配置
    for section_name, section_data in new_config.items():
        for key, value in section_data.items():
            set_config(f"{section_name}.{key}", value)

    print("集成测试完成")


def main():
    """主函数"""
    print("VirtualChemLab 重构后系统使用示例")
    print("=" * 50)

    try:
        # 运行各种示例
        example_error_handling()
        example_event_bus()
        example_error_recovery()
        example_config_management()
        example_performance_monitoring()
        example_performance_alerting()
        example_config_migration()
        example_integration()

        print("\n" + "=" * 50)
        print("所有示例执行完成！")

    except Exception as e:
        print(f"示例执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
