# VirtualChemLab 重构后系统使用指南

## 📖 概述

本指南介绍如何使用重构后的VirtualChemLab系统，包括统一错误处理、事件总线、配置管理、性能监控等核心功能。

## 🚀 快速开始

### 启动重构后的应用

```bash
python main_refactored.py
```

### 基本导入

```python
from src.core.common_exceptions import VirtualChemLabError, ConfigurationError
from src.core.error_handler import get_error_handler, safe_execute
from src.core.enhanced_event_bus import get_event_bus, publish_event, subscribe_event
from src.core.unified_config_manager import get_config_manager, get_config, set_config
from src.core.unified_performance_monitor import get_performance_monitor, measure_performance
```

## 🔧 核心功能

### 1. 统一错误处理

#### 基本错误类型

```python
from src.core.common_exceptions import (
    VirtualChemLabError,
    ConfigurationError,
    ValidationError,
    NetworkError,
    UIError,
    PerformanceError,
    ErrorCategory,
    ErrorSeverity
)

# 创建错误
error = ConfigurationError(
    message="配置文件格式错误",
    config_key="app.debug",
    details={"line": 10, "column": 5}
)

# 错误信息
print(error.message)  # "配置文件格式错误"
print(error.category)  # ErrorCategory.CONFIGURATION
print(error.severity)  # ErrorSeverity.HIGH
print(error.details)   # {"config_key": "app.debug", "line": 10, "column": 5}
```

#### 错误处理装饰器

```python
from src.core.common_exceptions import handle_errors, recoverable_error

# 基本错误处理
@handle_errors()
def risky_function():
    raise ValueError("这是一个风险函数")

# 可恢复错误处理
@recoverable_error(fallback_value="默认值", retry_count=3)
def unreliable_function():
    if random.random() < 0.5:
        raise NetworkError("网络连接失败")
    return "成功结果"

# 安全执行
from src.core.error_handler import safe_execute

result = safe_execute(
    potentially_failing_function,
    error_class=ValidationError,
    fallback_value="验证失败，使用默认值"
)
```

#### 错误上下文管理

```python
from src.core.error_handler import error_context, log_and_continue, log_and_raise

# 错误上下文
with error_context(ErrorCategory.SYSTEM, ErrorSeverity.HIGH):
    try:
        raise RuntimeError("系统错误")
    except Exception as e:
        log_and_raise(e, UIError)

# 记录错误但继续执行
try:
    risky_operation()
except Exception as e:
    log_and_continue(e, "操作失败但继续执行")
```

### 2. 事件总线系统

#### 基本事件操作

```python
from src.core.enhanced_event_bus import (
    get_event_bus,
    Event,
    EventPriority,
    publish_event,
    subscribe_event
)

# 获取事件总线
event_bus = get_event_bus()

# 事件处理器
def event_handler(event: Event):
    print(f"收到事件: {event.name}, 数据: {event.data}")

# 订阅事件
subscription = subscribe_event("user_action", event_handler)

# 发布事件
publish_event("user_action", {"action": "click", "button": "submit"})

# 取消订阅
event_bus.unsubscribe(subscription)
```

#### 高级事件功能

```python
# 带标签过滤的事件订阅
def important_handler(event: Event):
    print(f"重要事件: {event.name}")

subscribe_event(
    "system_event",
    important_handler,
    tags_filter={"priority": "high"}
)

# 发布带标签的事件
publish_event(
    "system_event",
    {"message": "系统启动"},
    tags={"priority": "high"}
)

# 一次性订阅
def one_time_handler(event: Event):
    print(f"一次性事件: {event.name}")

subscribe_event("startup_complete", one_time_handler, once=True)

# 全局事件订阅
def global_handler(event: Event):
    print(f"全局事件: {event.name}")

event_bus.subscribe_global(global_handler)
```

### 3. 配置管理

#### 基本配置操作

```python
from src.core.unified_config_manager import (
    get_config_manager,
    get_config,
    set_config,
    has_config,
    remove_config
)

# 获取配置管理器
config_manager = get_config_manager()
config_manager.initialize()

# 设置配置
set_config("app.name", "VirtualChemLab")
set_config("app.debug", True)
set_config("ui.theme", "dark")
set_config("performance.cache_size", 1000)

# 获取配置
app_name = get_config("app.name")
debug_mode = get_config("app.debug")
theme = get_config("ui.theme")

# 检查配置存在性
if has_config("app.name"):
    print("应用名称配置存在")

# 移除配置
remove_config("app.debug")
```

#### 配置节管理

```python
# 添加新配置节
config_manager.add_section("experiment")

# 设置节内配置
set_config("experiment.auto_save", True)
set_config("experiment.save_interval", 30)

# 获取配置节
experiment_section = config_manager.get_section("experiment")
if experiment_section:
    print(f"实验配置: {experiment_section.data}")

# 配置验证
is_valid = config_manager.validate_all()
print(f"配置验证结果: {is_valid}")

# 保存配置
config_manager.save_config("my_config.json")
```

### 4. 性能监控

#### 基本性能监控

```python
from src.core.unified_performance_monitor import (
    get_performance_monitor,
    PerformanceMetric,
    MetricType,
    measure_performance,
    measure_context,
    record_fps,
    record_frame_time
)

# 获取性能监控器
monitor = get_performance_monitor()

# 使用性能装饰器
@measure_performance("my_function")
def my_function():
    time.sleep(0.01)  # 模拟工作
    return "完成"

result = my_function()

# 使用性能上下文
with measure_context("my_context"):
    time.sleep(0.01)  # 模拟工作
    print("上下文执行完成")

# 手动记录性能指标
record_fps(60.0)
record_frame_time(16.67)
```

#### 性能数据分析

```python
# 获取性能指标历史
fps_history = monitor.get_metric_history(MetricType.FPS.value)
frame_time_history = monitor.get_metric_history(MetricType.FRAME_TIME.value)

# 获取性能统计
fps_stats = monitor.get_metric_stats(MetricType.FPS.value)
if fps_stats:
    print(f"FPS 统计: {fps_stats}")
    print(f"平均FPS: {fps_stats['avg']}")
    print(f"最高FPS: {fps_stats['max']}")
    print(f"最低FPS: {fps_stats['min']}")

# 获取性能报告
report = monitor.get_performance_report()
print(f"性能报告: {report}")

# 清除性能数据
monitor.clear_metrics(MetricType.FPS.value)
```

### 5. 错误恢复系统

#### 基本错误恢复

```python
from src.core.enhanced_error_recovery import (
    get_error_recovery,
    RecoveryRule,
    RecoveryStrategy,
    recover_error
)

# 获取错误恢复系统
recovery = get_error_recovery()

# 添加重试规则
retry_rule = RecoveryRule(
    error_type=NetworkError,
    strategy=RecoveryStrategy.RETRY,
    max_attempts=3,
    delay=1.0,
    backoff_multiplier=2.0
)
recovery.add_recovery_rule(NetworkError, retry_rule)

# 尝试恢复错误
try:
    raise NetworkError("网络连接失败", url="http://api.example.com")
except NetworkError as e:
    recovered = recover_error(e)
    print(f"错误恢复结果: {recovered}")
```

#### 高级恢复策略

```python
# 回退策略
def fallback_function(error: VirtualChemLabError, context):
    return f"回退结果: {error.message}"

fallback_rule = RecoveryRule(
    error_type=ValidationError,
    strategy=RecoveryStrategy.FALLBACK,
    fallback_function=fallback_function
)
recovery.add_recovery_rule(ValidationError, fallback_rule)

# 熔断器策略
circuit_breaker_rule = RecoveryRule(
    error_type=PerformanceError,
    strategy=RecoveryStrategy.CIRCUIT_BREAKER,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=5.0
)
recovery.add_recovery_rule(PerformanceError, circuit_breaker_rule)

# 优雅降级策略
graceful_degradation_rule = RecoveryRule(
    error_type=UIError,
    strategy=RecoveryStrategy.GRACEFUL_DEGRADATION
)
recovery.add_recovery_rule(UIError, graceful_degradation_rule)
```

### 6. 性能告警系统

#### 基本告警功能

```python
from src.core.performance_alerting import (
    get_performance_alerting,
    AlertRule,
    AlertSeverity,
    check_performance_metric
)

# 获取性能告警系统
alerting = get_performance_alerting()

# 添加告警规则
cpu_rule = AlertRule(
    name="high_cpu_usage",
    metric_name="cpu_usage",
    threshold=80.0,
    comparison="gt",
    severity=AlertSeverity.WARNING,
    description="CPU使用率过高"
)
alerting.add_rule(cpu_rule)

# 检查性能指标
from src.core.unified_performance_monitor import PerformanceMetric
metric = PerformanceMetric("cpu_usage", 85.0, time.time())
check_performance_metric(metric)

# 获取活跃告警
active_alerts = alerting.get_active_alerts()
for alert_name, alert in active_alerts.items():
    print(f"告警: {alert_name} - {alert.description}")
    print(f"当前值: {alert.current_value}")
    print(f"阈值: {alert.threshold}")
    print(f"严重程度: {alert.severity.value}")

# 确认告警
if active_alerts:
    alert_name = list(active_alerts.keys())[0]
    success = alerting.acknowledge_alert(alert_name, "user123")
    print(f"告警确认结果: {success}")
```

#### 高级告警功能

```python
# 抑制告警
success = alerting.suppress_alert("high_cpu_usage", "系统维护中")
print(f"告警抑制结果: {success}")

# 获取告警历史
alert_history = alerting.get_alert_history(limit=10)
for alert in alert_history:
    print(f"历史告警: {alert.rule_name} - {alert.state.value}")

# 获取告警统计
stats = alerting.get_stats()
print(f"告警统计: {stats}")

# 自定义告警动作
def custom_alert_action(alert):
    print(f"自定义告警动作: {alert.rule_name}")

from src.core.performance_alerting import AlertAction
custom_action = AlertAction(
    name="custom_action",
    action_type="notification",
    action_function=custom_alert_action,
    conditions={"severity": ["warning", "error"]}
)
alerting.add_action(custom_action)
```

### 7. 配置迁移

#### 基本配置迁移

```python
from src.core.config_migration import (
    get_config_migration_manager,
    migrate_config,
    detect_config_version
)

# 获取配置迁移管理器
migration = get_config_migration_manager()

# 检测配置版本
v1_config = {
    "app": {
        "name": "VirtualChemLab",
        "version": "1.0.0",
        "environment": "development"
    }
}

version = detect_config_version(v1_config)
print(f"检测到配置版本: {version}")

# 迁移配置
migrated_config = migrate_config(v1_config, "2.0.0")
print(f"迁移后的配置: {migrated_config}")

# 获取版本历史
version_history = migration.get_version_history()
print(f"支持的版本: {version_history}")

# 获取迁移信息
migration_info = migration.get_migration_info("1.0.0", "2.0.0")
print(f"迁移信息: {migration_info}")
```

#### 高级配置迁移

```python
# 备份配置
from pathlib import Path
backup_path = Path("config_backup.json")
migration.backup_config(v1_config, backup_path)

# 恢复配置
restored_config = migration.restore_config(backup_path)
print(f"恢复的配置: {restored_config}")

# 验证配置版本
is_valid = migration.validate_config_version(migrated_config)
print(f"配置验证结果: {is_valid}")

# 获取迁移统计
stats = migration.get_stats()
print(f"迁移统计: {stats}")
```

## 🔗 集成使用

### 组件间通信

```python
# 错误处理 + 事件总线
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
```

### 性能监控 + 告警

```python
# 性能监控 + 告警
@measure_performance("integration_function")
def integration_function():
    time.sleep(0.02)  # 模拟工作
    return "集成测试完成"

result = integration_function()

# 检查性能指标
monitor = get_performance_monitor()
function_time_history = monitor.get_metric_history(MetricType.FUNCTION_TIME.value)

if function_time_history:
    latest_metric = function_time_history[-1]
    check_performance_metric(latest_metric)
```

### 配置管理 + 迁移

```python
# 配置管理 + 迁移
old_config = {
    "app": {
        "name": "VirtualChemLab",
        "version": "1.0.0",
        "environment": "development"
    }
}

# 迁移配置
new_config = migrate_config(old_config, "2.0.0")

# 使用新配置
config_manager = get_config_manager()
config_manager.initialize()

# 设置迁移后的配置
for section_name, section_data in new_config.items():
    for key, value in section_data.items():
        set_config(f"{section_name}.{key}", value)
```

## 📊 最佳实践

### 1. 错误处理最佳实践

- **使用特定错误类型**: 根据错误性质选择合适的错误类型
- **提供详细上下文**: 在错误中包含足够的上下文信息
- **实现错误恢复**: 为可恢复的错误实现恢复机制
- **记录错误日志**: 使用统一的日志格式记录错误

### 2. 事件总线最佳实践

- **使用有意义的事件名称**: 事件名称应该清晰描述事件内容
- **合理使用标签**: 使用标签进行事件分类和过滤
- **避免事件循环**: 注意避免事件处理中的循环依赖
- **及时取消订阅**: 在组件销毁时及时取消事件订阅

### 3. 配置管理最佳实践

- **使用配置节**: 将相关配置组织到配置节中
- **验证配置格式**: 使用Schema验证配置格式
- **支持配置迁移**: 为配置变更提供迁移路径
- **备份重要配置**: 定期备份重要配置文件

### 4. 性能监控最佳实践

- **选择合适的指标**: 监控对系统性能有重要影响的指标
- **设置合理阈值**: 根据系统特性设置合理的告警阈值
- **定期清理数据**: 定期清理过期的性能数据
- **分析性能趋势**: 定期分析性能数据趋势

## 🐛 故障排除

### 常见问题

1. **导入错误**: 确保所有依赖模块已正确安装
2. **配置错误**: 检查配置文件格式和Schema定义
3. **性能问题**: 监控系统资源使用情况
4. **事件循环**: 检查事件订阅和取消订阅逻辑

### 调试技巧

1. **启用详细日志**: 设置日志级别为DEBUG
2. **使用性能监控**: 监控系统性能指标
3. **检查错误统计**: 查看错误处理统计信息
4. **分析事件流**: 跟踪事件发布和订阅

## 📚 参考资源

- [重构报告（历史材料）](../archive/v2.0.0-reports/REFACTORING_REPORT.md)
- [代码质量报告（历史材料）](../archive/v2.0.0-reports/CODE_QUALITY_REPORT.md)
- [测试示例](../examples/refactored_system_examples.py)
- [测试用例](../tests/test_refactored_system.py)

---

*最后更新: 2025-01-09*
*VirtualChemLab v2.0.0 - 虚拟化学实验室*
