# 错误处理系统 - 快速参考

## 快速开始

### 1. 安装错误拦截器（应用启动时）

```python
from src.core.error_system import install_error_interceptor
from PyQt6.QtWidgets import QApplication

app = QApplication([])
install_error_interceptor(app, show_error_dialog=True, auto_recovery=True)
app.exec()
```

### 2. 使用装饰器保护函数

```python
from src.core.error_system import safe_execute, retry

@safe_execute(context="操作描述")
def my_function():
    # 代码...
    pass

@retry(max_retries=3, retry_delay=2.0)
def network_function():
    # 网络请求...
    pass
```

### 3. 抛出异常

```python
from src.core.error_system import DataValidationError, ErrorCodeRegistry

raise DataValidationError(
    message="数据验证失败",
    error_code=ErrorCodeRegistry.DATA_VALIDATION_FAILED,
    field="temperature",
    value=150,
)
```

---

## 常用错误码

```python
from src.core.error_system import ErrorCodeRegistry

# 通用
ErrorCodeRegistry.INVALID_PARAMETER          # 1003
ErrorCodeRegistry.RESOURCE_NOT_FOUND         # 1004

# 认证
ErrorCodeRegistry.AUTH_REQUIRED              # 2000
ErrorCodeRegistry.AUTH_TOKEN_EXPIRED         # 2002

# 实验
ErrorCodeRegistry.EXP_TEMPLATE_NOT_FOUND     # 3000
ErrorCodeRegistry.EXP_STEP_VALIDATION_FAILED # 3002

# 数据
ErrorCodeRegistry.DATA_VALIDATION_FAILED     # 4000
ErrorCodeRegistry.DATA_SAVE_FAILED           # 4001

# 系统
ErrorCodeRegistry.SYS_FILE_NOT_FOUND         # 5004
ErrorCodeRegistry.SYS_PERMISSION_DENIED      # 5005
```

---

## 常用异常类

```python
from src.core.error_system import (
    BaseAppException,              # 基础异常
    AuthenticationError,           # 认证错误
    AuthorizationError,            # 授权错误
    DataValidationError,           # 数据验证错误
    ResourceNotFoundError,         # 资源不存在
    ExperimentError,               # 实验错误
    TemplateError,                 # 模板错误
    NetworkError,                  # 网络错误
    AppSystemError,                # 系统错误
)
```

---

## 装饰器

| 装饰器 | 用途 | 示例 |
|--------|------|------|
| `@safe_execute` | 捕获并记录异常 | `@safe_execute(context="操作")` |
| `@retry` | 自动重试 | `@retry(max_retries=3)` |
| `@fallback` | 失败时返回默认值 | `@fallback(default_value=[])` |
| `@auto_recover` | 自动恢复 | `@auto_recover(context="操作")` |

---

## 上下文管理器

```python
from src.core.error_system import safe_context

with safe_context(context="数据保存", reraise=True):
    save_data()
```

---

## 错误处理

```python
from src.core.error_system import error_handler

# 手动处理异常
try:
    risky_operation()
except Exception as e:
    error_handler.handle_exception(e, context="操作描述")

# 获取错误历史
errors = error_handler.get_error_history(limit=50)

# 获取统计
stats = error_handler.get_error_stats()
```

---

## 错误报告

```python
from src.core.error_system import error_reporter, NotificationChannel

# 生成报告
report = error_reporter.report_error(
    exception=e,
    context="操作描述",
    notify=True,
    notification_channels=[NotificationChannel.LOG],
)

# 导出报告
error_reporter.export_reports("report.json", format="json")
```

---

## 错误恢复

```python
from src.core.error_system import (
    recovery_manager,
    RecoveryStrategy,
    RecoveryAction,
)

# 注册自定义策略
recovery_manager.register_strategy(
    error_code=3000,
    strategy=RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=3,
    ),
)
```

---

## 错误分析

```python
from src.core.error_system import ErrorAnalytics, error_handler

# 创建分析器
analytics = ErrorAnalytics(error_handler.error_history)

# 获取指标
metrics = analytics.get_metrics()

# 获取趋势
trends = analytics.get_error_trends()

# 获取热点错误
hot_errors = analytics.get_hot_errors(top_n=10)

# 生成报告
report = analytics.generate_report(output_path="report.txt")
```

---

## 错误监控

```python
from src.core.error_system import error_monitor

# 配置告警
error_monitor.alert_threshold = 10
error_monitor.time_window = 60

# 注册告警处理器
def my_alert(alert_data):
    print(f"告警: {alert_data['error_count']} 个错误")

error_monitor.register_alert_callback(my_alert)

# 记录错误
error_monitor.record_error(error_record)
```

---

## 完整示例

```python
from src.core.error_system import (
    safe_execute,
    retry,
    DataValidationError,
    ErrorCodeRegistry,
)

class DataProcessor:
    @retry(max_retries=3, retry_delay=1.0)
    @safe_execute(context="加载数据")
    def load_data(self, filepath):
        with open(filepath, 'r') as f:
            return f.read()

    def validate_data(self, data):
        if not data:
            raise DataValidationError(
                message="数据不能为空",
                error_code=ErrorCodeRegistry.VALIDATION_REQUIRED_FIELD,
                field="data",
                value=data,
            )

    @safe_execute(context="处理数据", reraise=True)
    def process(self, filepath):
        data = self.load_data(filepath)
        self.validate_data(data)
        return self.transform(data)
```

---

## 最佳实践

1. ✅ 使用具体的异常类，不要使用通用的 `Exception`
2. ✅ 为关键操作添加 `@safe_execute` 或 `@retry`
3. ✅ 提供清晰的错误上下文和用户消息
4. ✅ 为临时性错误（网络、文件）使用重试机制
5. ✅ 定期分析错误日志，识别系统问题
6. ✅ 在应用启动时安装全局错误拦截器
7. ✅ 为不同环境配置不同的错误处理策略
