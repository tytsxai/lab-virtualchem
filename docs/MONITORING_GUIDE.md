# 🔍 VirtualChemLab 监控与可观测性指南

> 完整的监控与可观测性解决方案

## 📋 目录

1. [系统概述](#系统概述)
2. [核心功能](#核心功能)
3. [快速开始](#快速开始)
4. [前端监控](#前端监控)
5. [后端监控](#后端监控)
6. [分布式追踪](#分布式追踪)
7. [告警系统](#告警系统)
8. [监控仪表板](#监控仪表板)
9. [配置说明](#配置说明)
10. [最佳实践](#最佳实践)

---

## 系统概述

VirtualChemLab监控系统提供全方位的可观测性支持，帮助快速定位问题并持续优化系统性能。

### 架构图

```
┌─────────────────────────────────────────────┐
│           监控与可观测性系统                 │
├─────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐           │
│  │  前端监控    │  │  后端监控    │           │
│  │             │  │             │           │
│  │ • 错误追踪   │  │ • APM指标   │           │
│  │ • 用户行为   │  │ • 资源监控   │           │
│  │ • 点击流     │  │ • 健康检查   │           │
│  └─────────────┘  └─────────────┘           │
│                                             │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ 分布式追踪   │  │  告警系统    │           │
│  │             │  │             │           │
│  │ • Trace ID  │  │ • 规则引擎   │           │
│  │ • Span管理  │  │ • 多渠道     │           │
│  │ • 调用链     │  │ • 聚合抑制   │           │
│  └─────────────┘  └─────────────┘           │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │        监控仪表板                │        │
│  │  • 实时数据  • HTML报告  • JSON  │        │
│  └─────────────────────────────────┘        │
└─────────────────────────────────────────────┘
```

### 核心特性

- ✅ **前端监控** - 错误追踪、用户行为分析
- ✅ **后端监控** - APM指标、资源监控、健康检查
- ✅ **全链路追踪** - Trace ID、分布式追踪
- ✅ **智能告警** - 阈值配置、多渠道通知
- ✅ **可视化仪表板** - 实时数据、HTML/JSON报告

---

## 核心功能

### 1. 前端监控

#### 错误追踪 (类似Sentry)

```python
from src.monitoring.frontend_monitor import FrontendMonitor, ErrorLevel

monitor = FrontendMonitor()

try:
    # 你的代码
    result = risky_operation()
except Exception as e:
    monitor.capture_exception(
        e,
        level=ErrorLevel.ERROR,
        user_id="user123",
        session_id="session456",
        component="ExperimentController",
        action="execute_step"
    )
```

**功能特性:**
- 自动捕获异常堆栈
- 错误分类和聚合
- 错误趋势分析
- 上下文信息记录

#### 用户行为埋点

```python
from src.monitoring.frontend_monitor import UserBehaviorTracker, EventType

tracker = UserBehaviorTracker()

# 追踪点击
tracker.track_click(
    component="ExperimentList",
    element="start_button",
    experiment_id="exp001"
)

# 追踪页面访问
tracker.track_view(
    component="HomePage",
    duration_ms=3500
)

# 追踪导航
tracker.track_navigation(
    from_page="HomePage",
    to_page="ExperimentPage"
)
```

#### 点击流分析

```python
# 分析用户路径
clickstream = tracker.analyze_clickstream(session_id="session123")

print(f"总步骤: {clickstream['total_steps']}")
print(f"路径: {clickstream['path']}")
print(f"常见转换: {clickstream['common_transitions']}")
```

### 2. 后端监控

#### APM性能监控

```python
from src.monitoring.backend_monitor import BackendMonitor

monitor = BackendMonitor()

# 计数器
monitor.apm.increment_counter("api.requests", value=1, endpoint="/api/experiment")

# 仪表
monitor.apm.set_gauge("active_users", 42)

# 直方图
monitor.apm.record_histogram("api.latency", duration_ms, endpoint="/api/experiment")

# 装饰器自动计时
@monitor.apm.time_operation("process_experiment")
def process_experiment(data):
    # 自动记录执行时间和成功/失败
    return result
```

#### 资源监控

```python
# 自动启动资源监控 (每60秒)
monitor = BackendMonitor(enable_resource_monitoring=True)

# 监控指标自动记录:
# - system.cpu.percent
# - system.memory.percent
# - system.disk.percent
# - process.cpu.percent
# - process.memory.rss_mb
```

#### 健康检查

```python
health = monitor.get_health_status()

print(f"状态: {health['status']}")  # healthy/unhealthy
print(f"CPU: {health['metrics']['cpu_percent']}%")
print(f"内存: {health['metrics']['memory_percent']}%")
print(f"问题: {health['issues']}")
```

### 3. 分布式追踪

#### 基础追踪

```python
from src.monitoring.distributed_tracing import TraceManager

trace_mgr = TraceManager()

# 使用上下文管理器
with trace_mgr.trace("handle_request") as ctx:
    print(f"Trace ID: {ctx.trace_id}")

    # 子操作
    with trace_mgr.trace("validate_input", context=ctx) as ctx1:
        trace_mgr.set_tag("user_id", "user123", ctx1)
        trace_mgr.log_event("validation_passed", ctx1)

    # 另一个子操作
    with trace_mgr.trace("process_data", context=ctx) as ctx2:
        # 处理逻辑
        pass
```

#### 跨服务追踪

```python
# 服务A: 创建追踪
ctx = trace_mgr.start_trace("service_a_operation")

# 传递到服务B (通过HTTP头)
headers = ctx.to_headers()
# headers = {"X-Trace-Id": "...", "X-Span-Id": "..."}

# 服务B: 继续追踪
from src.monitoring.distributed_tracing import TracingContext

incoming_ctx = TracingContext.from_headers(request.headers)
with trace_mgr.trace("service_b_operation", context=incoming_ctx):
    # 处理逻辑
    pass
```

#### 追踪分析

```python
# 获取追踪树
trace_tree = trace_mgr.get_trace_tree(trace_id)
print(f"总持续时间: {trace_tree['total_duration_ms']} ms")

# 获取统计
stats = trace_mgr.get_statistics(since_minutes=60)
print(f"总追踪: {stats['total_traces']}")
print(f"按操作统计: {stats['by_operation']}")
```

### 4. 告警系统

#### 创建告警规则

```python
from src.monitoring.alerting import (
    AlertManager, AlertRule, AlertSeverity,
    create_threshold_rule
)

alert_mgr = AlertManager()

# 方式1: 使用工厂函数
cpu_rule = create_threshold_rule(
    name="high_cpu",
    metric_getter=lambda: psutil.cpu_percent(),
    threshold=85,
    operator=">",
    severity=AlertSeverity.CRITICAL,
    message="CPU使用率超过85%",
    duration_seconds=120,  # 持续2分钟
    cooldown_seconds=300   # 冷却5分钟
)

alert_mgr.add_rule(cpu_rule)

# 方式2: 自定义规则
memory_rule = AlertRule(
    name="high_memory",
    condition=lambda: psutil.virtual_memory().percent > 90,
    severity=AlertSeverity.WARNING,
    message="内存使用率超过90%",
    duration_seconds=60
)

alert_mgr.add_rule(memory_rule)
```

#### 手动触发告警

```python
alert = alert_mgr.fire_alert(
    rule_name="custom_alert",
    severity=AlertSeverity.ERROR,
    message="检测到异常情况",
    component="ExperimentService"
)
```

#### 告警渠道

```python
from src.monitoring.alerting import (
    ConsoleAlertChannel,
    FileAlertChannel,
    WebhookAlertChannel,
    EmailAlertChannel
)

# 控制台 (默认)
alert_mgr.add_channel(ConsoleAlertChannel())

# 文件
alert_mgr.add_channel(FileAlertChannel(log_dir="logs/alerts"))

# Webhook
alert_mgr.add_channel(WebhookAlertChannel(
    webhook_url="https://your-webhook.com/alerts"
))

# 邮件
alert_mgr.add_channel(EmailAlertChannel(
    smtp_host="smtp.example.com",
    smtp_port=587,
    username="alerts@example.com",
    password="password",
    from_addr="alerts@example.com",
    to_addrs=["admin@example.com"]
))
```

### 5. 监控仪表板

#### 生成报告

```python
from src.monitoring.dashboard import MonitoringDashboard

dashboard = MonitoringDashboard()

# 获取总览
overview = dashboard.get_overview()

# 生成HTML报告
dashboard.generate_html_report(Path("reports/dashboard.html"))

# 导出JSON数据
dashboard.export_json_report(Path("reports/data.json"))
```

#### 实时查询

```python
# 系统指标
metrics = dashboard.get_system_metrics()

# 错误摘要
errors = dashboard.get_error_summary(limit=100)

# 追踪摘要
traces = dashboard.get_trace_summary(since_minutes=60)

# 告警摘要
alerts = dashboard.get_alert_summary()
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install psutil  # 系统监控 (必需)
pip install requests  # Webhook告警 (可选)
```

### 2. 基础配置

创建配置文件 `config/monitoring_config.json`:

```json
{
  "monitoring": {
    "enabled": true,
    "app_name": "VirtualChemLab",
    "frontend": {
      "error_tracking": {"enabled": true},
      "behavior_tracking": {"enabled": true}
    },
    "backend": {
      "apm": {"enabled": true},
      "resource_monitoring": {"enabled": true, "interval_seconds": 60}
    },
    "tracing": {"enabled": true},
    "alerting": {"enabled": true, "auto_check": true}
  }
}
```

### 3. 初始化监控

```python
from src.monitoring import (
    FrontendMonitor, UserBehaviorTracker,
    BackendMonitor, get_trace_manager,
    AlertManager
)

# 初始化所有监控组件
frontend_monitor = FrontendMonitor()
behavior_tracker = UserBehaviorTracker()
backend_monitor = BackendMonitor()
trace_manager = get_trace_manager()
alert_manager = AlertManager()

print("✅ 监控系统已启动")
```

### 4. 运行演示

```bash
python examples/monitoring_demo.py
```

---

## 配置说明

### 完整配置示例

```json
{
  "monitoring": {
    "enabled": true,
    "app_name": "VirtualChemLab",

    "frontend": {
      "error_tracking": {
        "enabled": true,
        "max_errors": 1000,
        "log_dir": "logs/frontend"
      },
      "behavior_tracking": {
        "enabled": true,
        "max_events": 10000,
        "log_dir": "logs/behavior"
      }
    },

    "backend": {
      "apm": {
        "enabled": true,
        "log_dir": "logs/apm"
      },
      "resource_monitoring": {
        "enabled": true,
        "interval_seconds": 60
      },
      "health_check": {
        "enabled": true,
        "thresholds": {
          "cpu_warning": 70,
          "cpu_critical": 85,
          "memory_warning": 80,
          "memory_critical": 90,
          "disk_warning": 80,
          "disk_critical": 90
        }
      }
    },

    "tracing": {
      "enabled": true,
      "service_name": "VirtualChemLab",
      "log_dir": "logs/traces",
      "sample_rate": 1.0
    },

    "alerting": {
      "enabled": true,
      "auto_check": true,
      "check_interval_seconds": 60,

      "rules": [
        {
          "name": "high_cpu_usage",
          "metric": "system.cpu.percent",
          "threshold": 85,
          "operator": ">",
          "severity": "critical",
          "duration_seconds": 120,
          "cooldown_seconds": 300
        }
      ]
    },

    "retention": {
      "metrics_days": 30,
      "traces_days": 7,
      "logs_days": 30,
      "alerts_days": 90
    }
  }
}
```

---

## 最佳实践

### 1. 错误追踪最佳实践

```python
# ✅ 好的做法: 提供完整上下文
monitor.capture_exception(
    exception,
    level=ErrorLevel.ERROR,
    user_id=current_user.id,
    session_id=request.session_id,
    component="ExperimentController",
    action="execute_step",
    experiment_id=experiment.id,
    step_number=step_num
)

# ❌ 不好的做法: 缺少上下文
monitor.capture_exception(exception)
```

### 2. 行为追踪最佳实践

```python
# ✅ 使用一致的命名规范
tracker.track_click(
    component="ExperimentList",      # 组件名: PascalCase
    element="start_experiment_btn",  # 元素名: snake_case
    action="click"                   # 动作名: 小写
)

# ✅ 记录重要属性
tracker.track_event(
    EventType.CUSTOM,
    component="Experiment",
    action="step_completed",
    step_number=3,
    duration_ms=1500,
    success=True
)
```

### 3. 性能监控最佳实践

```python
# ✅ 使用装饰器自动监控
@backend_monitor.apm.time_operation("database_query", table="experiments")
def query_experiments(filter_params):
    return db.query(Experiment).filter(**filter_params).all()

# ✅ 为指标添加标签
monitor.apm.increment_counter(
    "api.requests",
    endpoint="/api/experiments",
    method="POST",
    status_code=200
)
```

### 4. 追踪最佳实践

```python
# ✅ 使用有意义的操作名
with trace_mgr.trace("experiment.execute") as ctx:
    # 明确的操作名
    pass

# ✅ 添加关键标签
trace_mgr.set_tag("user_id", user.id)
trace_mgr.set_tag("experiment_type", "titration")

# ✅ 记录关键事件
trace_mgr.log_event("validation_completed", items_validated=10)
```

### 5. 告警最佳实践

```python
# ✅ 设置合理的阈值
cpu_rule = create_threshold_rule(
    name="high_cpu",
    metric_getter=get_cpu_usage,
    threshold=85,              # 不要太低
    duration_seconds=120,      # 避免误报
    cooldown_seconds=300       # 避免告警风暴
)

# ✅ 使用分级告警
# WARNING -> ERROR -> CRITICAL

# ✅ 提供可操作的消息
alert_mgr.fire_alert(
    rule_name="high_error_rate",
    severity=AlertSeverity.ERROR,
    message="错误率超过10%，请检查日志: /logs/errors/",
    dashboard_url="http://monitoring.example.com/errors"
)
```

---

## 日志文件结构

```
logs/
├── frontend/
│   └── errors_20251006.jsonl         # 前端错误日志
├── behavior/
│   └── events_20251006.jsonl         # 用户行为日志
├── apm/
│   └── metrics_20251006.jsonl        # APM指标日志
├── traces/
│   └── traces_20251006.jsonl         # 追踪日志
└── alerts/
    └── alerts_20251006.jsonl         # 告警日志
```

每个日志文件都是JSONL格式 (每行一个JSON对象)，便于分析和处理。

---

## 常见问题

### Q1: 如何减少日志文件大小？

A: 调整配置中的保留天数:

```json
"retention": {
  "metrics_days": 7,   // 减少到7天
  "traces_days": 3,    // 追踪只保留3天
  "logs_days": 7
}
```

### Q2: 如何集成到现有代码？

A: 使用装饰器最简单:

```python
from src.monitoring.backend_monitor import backend_monitor

@backend_monitor.apm.time_operation("my_function")
def my_function():
    # 自动记录性能指标
    pass
```

### Q3: 如何自定义告警渠道?

A: 继承 `AlertChannel` 类:

```python
from src.monitoring.alerting import AlertChannel, Alert

class CustomAlertChannel(AlertChannel):
    def send(self, alert: Alert) -> bool:
        # 实现你的发送逻辑
        return True

alert_mgr.add_channel(CustomAlertChannel())
```

---

## 性能影响

监控系统设计为轻量级，对应用性能影响极小:

- **前端监控**: < 1ms 开销
- **后端监控**: < 5ms 开销
- **追踪系统**: < 2ms 开销
- **告警检查**: 后台线程,不影响主流程
- **资源监控**: 60秒间隔,可配置

---

## 总结

VirtualChemLab监控系统提供了:

✅ **全方位监控** - 前端、后端、全链路
✅ **实时告警** - 多渠道、智能阈值
✅ **可视化仪表板** - HTML报告、JSON数据
✅ **易于集成** - 装饰器、上下文管理器
✅ **生产就绪** - 高性能、低开销

开始使用监控系统，快速定位问题，持续优化性能！

---

**文档版本**: v1.0.0
**更新时间**: 2025-10-06
**维护团队**: VirtualChemLab Team
