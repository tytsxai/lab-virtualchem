# 错误处理系统使用指南

## 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [错误码系统](#错误码系统)
4. [异常类体系](#异常类体系)
5. [错误处理](#错误处理)
6. [错误恢复](#错误恢复)
7. [错误报告](#错误报告)
8. [错误拦截](#错误拦截)
9. [错误分析](#错误分析)
10. [最佳实践](#最佳实践)

---

## 系统概述

VirtualChemLab 的错误处理系统提供了完整的错误管理解决方案，包括：

- ✅ **统一的错误码系统**：标准化的错误代码和消息
- ✅ **完整的异常类体系**：结构化的异常定义
- ✅ **自动错误处理**：装饰器和上下文管理器
- ✅ **错误恢复策略**：自动重试、降级等
- ✅ **错误报告系统**：多渠道通知
- ✅ **全局错误拦截**：捕获所有未处理异常
- ✅ **错误监控分析**：实时监控和趋势分析

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                   应用程序代码                            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────┐
│              错误拦截器 (Interceptor)                     │
│  • 全局异常钩子                                           │
│  • Qt事件异常捕获                                         │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────┐
│              错误处理器 (Handler)                         │
│  • 异常转换                                               │
│  • 日志记录                                               │
│  • 历史保存                                               │
└─────┬─────────────┴──────────────┬──────────────────────┘
      │                            │
      ↓                            ↓
┌──────────────────┐      ┌────────────────────┐
│  错误报告器       │      │  错误恢复管理器      │
│  • 生成报告       │      │  • 重试策略          │
│  • 多渠道通知     │      │  • 降级策略          │
└──────────────────┘      └────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────────────┐
│              错误分析器 (Analytics)                       │
│  • 错误趋势分析                                           │
│  • 热点错误识别                                           │
│  • 监控告警                                               │
└─────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 安装错误拦截器

在应用程序启动时安装全局错误拦截器：

```python
from PyQt6.QtWidgets import QApplication
from src.core.error_system import install_error_interceptor

# 创建Qt应用
app = QApplication([])

# 安装错误拦截器
interceptor = install_error_interceptor(
    app=app,
    show_error_dialog=True,  # 显示错误对话框
    auto_recovery=True,      # 启用自动恢复
)

# 运行应用
app.exec()
```

### 2. 使用装饰器保护函数

```python
from src.core.error_system import safe_execute, retry

# 基础用法
@safe_execute(context="加载实验数据")
def load_experiment_data(exp_id):
    # 可能抛出异常的代码
    data = fetch_data(exp_id)
    return process_data(data)

# 带重试的用法
@retry(max_retries=3, retry_delay=2.0)
def fetch_remote_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

### 3. 抛出自定义异常

```python
from src.core.error_system import (
    DataValidationError,
    ErrorCodeRegistry,
)

def validate_input(data):
    if not data.get("name"):
        raise DataValidationError(
            message="实验名称不能为空",
            error_code=ErrorCodeRegistry.VALIDATION_REQUIRED_FIELD,
            field="name",
            value=data.get("name"),
        )
```

---

## 错误码系统

### 错误码分类

错误码按功能分类，使用数字范围区分：

| 范围 | 分类 | 说明 |
|------|------|------|
| 1000-1999 | GENERAL | 通用错误 |
| 2000-2999 | AUTH | 认证错误 |
| 3000-3999 | EXPERIMENT | 实验错误 |
| 4000-4999 | DATA | 数据错误 |
| 5000-5999 | SYSTEM | 系统错误 |
| 6000-6999 | NETWORK | 网络错误 |
| 7000-7999 | LICENSE | 许可证错误 |
| 8000-8999 | TEMPLATE | 模板错误 |
| 9000-9999 | VALIDATION | 验证错误 |

### 常用错误码

```python
from src.core.error_system import ErrorCodeRegistry

# 通用错误
ErrorCodeRegistry.INVALID_PARAMETER      # 1003: 参数无效
ErrorCodeRegistry.RESOURCE_NOT_FOUND     # 1004: 资源不存在

# 认证错误
ErrorCodeRegistry.AUTH_TOKEN_EXPIRED     # 2002: 令牌过期
ErrorCodeRegistry.AUTH_INSUFFICIENT_PERMISSION  # 2003: 权限不足

# 实验错误
ErrorCodeRegistry.EXP_TEMPLATE_NOT_FOUND # 3000: 实验模板不存在
ErrorCodeRegistry.EXP_STEP_VALIDATION_FAILED  # 3002: 步骤验证失败

# 数据错误
ErrorCodeRegistry.DATA_VALIDATION_FAILED # 4000: 数据验证失败
ErrorCodeRegistry.DATA_SAVE_FAILED       # 4001: 数据保存失败

# 系统错误
ErrorCodeRegistry.SYS_FILE_NOT_FOUND     # 5004: 文件不存在
ErrorCodeRegistry.SYS_PERMISSION_DENIED  # 5005: 权限被拒绝
```

### 自定义错误码

```python
from src.core.error_system import ErrorCode, ErrorCategory, ErrorCodeRegistry

# 定义自定义错误码
CUSTOM_ERROR = ErrorCode(
    code=9100,
    category=ErrorCategory.VALIDATION,
    name="CUSTOM_VALIDATION_ERROR",
    message_zh="自定义验证错误",
    message_en="Custom validation error",
    http_status=400,
    recoverable=True,
    severity="warning",
    help_url="https://docs.example.com/errors/9100",
)

# 注册错误码
ErrorCodeRegistry.register(CUSTOM_ERROR)
```

---

## 异常类体系

### 基础异常类

所有应用异常都继承自 `BaseAppException`：

```python
from src.core.error_system import BaseAppException, ErrorCodeRegistry

try:
    # 可能抛出异常的代码
    result = risky_operation()
except Exception as e:
    # 创建应用异常
    app_error = BaseAppException(
        message="操作失败",
        error_code=ErrorCodeRegistry.SYS_INTERNAL_ERROR,
        details={"operation": "risky_operation", "input": data},
        original_exception=e,
        user_message="操作执行失败，请稍后重试",
        recovery_hint="检查输入数据是否正确",
    )
    raise app_error
```

### 专用异常类

系统提供了多种专用异常类：

```python
from src.core.error_system import (
    AuthenticationError,
    AuthorizationError,
    DataValidationError,
    ResourceNotFoundError,
    ExperimentError,
    TemplateError,
    ConfigurationError,
    LicenseError,
    NetworkError,
    SystemError as AppSystemError,
)

# 认证错误
raise AuthenticationError(
    message="用户未登录",
    error_code=ErrorCodeRegistry.AUTH_REQUIRED,
)

# 数据验证错误
raise DataValidationError(
    message="温度值超出范围",
    field="temperature",
    value=150,
)

# 资源不存在错误
raise ResourceNotFoundError(
    message="实验模板不存在",
    resource_type="experiment_template",
    resource_id="exp_001",
)

# 实验错误
raise ExperimentError(
    message="实验步骤执行失败",
    experiment_id="exp_001",
    step_id="step_5",
)
```

### 从标准异常转换

```python
from src.core.error_system import from_standard_exception

try:
    file_content = open("data.json").read()
except Exception as e:
    # 自动转换为应用异常
    app_error = from_standard_exception(e, context="读取数据文件")
    raise app_error
```

---

## 错误处理

### 装饰器方式

#### 1. safe_execute - 安全执行

```python
from src.core.error_system import safe_execute

@safe_execute(
    context="加载用户数据",
    default_return=None,  # 发生错误时的返回值
    reraise=False,        # 是否重新抛出异常
)
def load_user_data(user_id):
    # 可能抛出异常的代码
    return database.get_user(user_id)
```

#### 2. async_safe_execute - 异步安全执行

```python
from src.core.error_system import async_safe_execute

@async_safe_execute(context="异步获取数据")
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### 上下文管理器方式

```python
from src.core.error_system import safe_context

# 基础用法
with safe_context(context="数据保存", reraise=True):
    save_data_to_database(data)

# 带用户信息
with safe_context(
    context="用户操作",
    user_id="user_001",
    session_id="session_123",
):
    perform_user_action()
```

### 手动错误处理

```python
from src.core.error_system import error_handler

try:
    result = risky_operation()
except Exception as e:
    # 手动处理异常
    app_error = error_handler.handle_exception(
        exception=e,
        context="执行风险操作",
        user_id="user_001",
        session_id="session_123",
        reraise=False,  # 不重新抛出
    )
    # 使用默认值
    result = default_value
```

### 获取错误历史

```python
from src.core.error_system import error_handler

# 获取最近的错误
recent_errors = error_handler.get_error_history(limit=50)

# 获取特定严重程度的错误
critical_errors = error_handler.get_error_history(
    limit=100,
    severity="critical",
)

# 获取错误统计
stats = error_handler.get_error_stats()
print(f"总错误数: {stats['total_errors']}")
print(f"严重错误数: {stats['critical_count']}")
print(f"可恢复错误数: {stats['recoverable_count']}")
```

---

## 错误恢复

### 恢复策略

系统提供多种恢复策略：

```python
from src.core.error_system import RecoveryAction, RecoveryStrategy

# 重试策略
retry_strategy = RecoveryStrategy(
    action=RecoveryAction.RETRY,
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0,  # 指数退避
    recovery_hint="正在重试...",
)

# 降级策略
fallback_strategy = RecoveryStrategy(
    action=RecoveryAction.FALLBACK,
    fallback_value=[],  # 降级值
    recovery_hint="使用默认值",
)

# 跳过策略
skip_strategy = RecoveryStrategy(
    action=RecoveryAction.SKIP,
    recovery_hint="跳过此错误继续执行",
)

# 人工介入策略
manual_strategy = RecoveryStrategy(
    action=RecoveryAction.MANUAL,
    auto_recover=False,
    recovery_hint="请人工处理",
)
```

### 注册自定义恢复策略

```python
from src.core.error_system import (
    recovery_manager,
    ErrorCodeRegistry,
    RecoveryStrategy,
    RecoveryAction,
)

# 为特定错误码注册策略
recovery_manager.register_strategy(
    error_code=ErrorCodeRegistry.NET_CONNECTION_FAILED.code,
    strategy=RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=5,
        retry_delay=3.0,
    ),
)
```

### 自动恢复装饰器

```python
from src.core.error_system import auto_recover, RecoveryStrategy, RecoveryAction

# 使用默认策略
@auto_recover(context="加载配置")
def load_config():
    return load_from_file("config.json")

# 使用自定义策略
@auto_recover(
    context="连接数据库",
    strategy=RecoveryStrategy(
        action=RecoveryAction.RETRY,
        max_retries=5,
        retry_delay=2.0,
    ),
)
def connect_database():
    return db.connect()
```

### 便捷装饰器

#### retry - 重试装饰器

```python
from src.core.error_system import retry

@retry(
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0,
    exceptions=(ConnectionError, TimeoutError),
)
def fetch_remote_data(url):
    response = requests.get(url, timeout=5)
    return response.json()
```

#### fallback - 降级装饰器

```python
from src.core.error_system import fallback

@fallback(default_value=[])
def get_items_from_cache():
    return cache.get("items")
```

---

## 错误报告

### 生成错误报告

```python
from src.core.error_system import error_reporter, NotificationChannel

try:
    perform_operation()
except Exception as e:
    # 生成错误报告
    report = error_reporter.report_error(
        exception=e,
        context="执行关键操作",
        user_id="user_001",
        session_id="session_123",
        notify=True,
        notification_channels=[
            NotificationChannel.LOG,
            NotificationChannel.CONSOLE,
        ],
    )

    print(f"错误报告ID: {report.report_id}")
```

### 自定义通知处理器

```python
from src.core.error_system import (
    error_reporter,
    NotificationChannel,
    NotificationLevel,
)

def email_notification_handler(report, level):
    """邮件通知处理器"""
    if level in (NotificationLevel.CRITICAL, NotificationLevel.ERROR):
        send_email(
            to="admin@example.com",
            subject=f"错误告警: {report.error_type}",
            body=f"错误消息: {report.message}\n时间: {report.timestamp}",
        )

# 注册通知处理器
error_reporter.register_notification_handler(
    channel=NotificationChannel.EMAIL,
    handler=email_notification_handler,
)
```

### 导出错误报告

```python
from src.core.error_system import error_reporter

# 导出为JSON
error_reporter.export_reports("error_report.json", format="json")

# 导出为CSV
error_reporter.export_reports("error_report.csv", format="csv")

# 导出为HTML
error_reporter.export_reports("error_report.html", format="html")
```

---

## 错误拦截

### Qt应用程序

```python
from PyQt6.QtWidgets import QApplication
from src.core.error_system import install_error_interceptor

app = QApplication([])

# 安装拦截器
interceptor = install_error_interceptor(
    app=app,
    show_error_dialog=True,
    auto_recovery=True,
)

# 监听错误信号
def on_error_occurred(exception, context):
    print(f"捕获到错误: {exception} in {context}")

interceptor.error_occurred.connect(on_error_occurred)

app.exec()
```

### 控制台应用程序

```python
from src.core.error_system import install_console_error_interceptor

# 安装控制台拦截器
interceptor = install_console_error_interceptor()

# 现在所有未捕获的异常都会被处理
def main():
    # 应用程序代码
    pass

if __name__ == "__main__":
    main()
```

### 手动安装异常钩子

```python
from src.core.error_system import install_global_exception_hook

# 安装全局异常钩子（不依赖Qt）
install_global_exception_hook()
```

---

## 错误分析

### 获取错误指标

```python
from src.core.error_system import error_handler, ErrorAnalytics

# 创建分析器
analytics = ErrorAnalytics(error_handler.error_history)

# 获取指标
metrics = analytics.get_metrics()
print(f"总错误数: {metrics.total_errors}")
print(f"错误率: {metrics.error_rate:.2f} 个/小时")
print(f"最频繁错误: {metrics.most_frequent_error}")
print(f"严重错误数: {metrics.critical_errors}")
```

### 错误趋势分析

```python
from datetime import timedelta
from src.core.error_system import ErrorAnalytics

analytics = ErrorAnalytics(error_handler.error_history)

# 获取24小时内的错误趋势（每小时统计）
trends = analytics.get_error_trends(
    time_window=timedelta(hours=24),
    interval=timedelta(hours=1),
)

for trend in trends:
    print(f"{trend['timestamp']}: {trend['error_count']} 个错误")
```

### 热点错误识别

```python
# 获取最频繁的10个错误
hot_errors = analytics.get_hot_errors(top_n=10)

for i, error in enumerate(hot_errors, 1):
    print(f"{i}. {error['error_type']}: {error['count']} 次")
```

### 生成分析报告

```python
from pathlib import Path

# 生成并保存报告
report = analytics.generate_report(
    output_path=Path("logs/error_analysis_report.txt")
)

# 打印报告
print(report)
```

### 实时错误监控

```python
from src.core.error_system import error_monitor

# 配置监控器
error_monitor.alert_threshold = 10  # 告警阈值
error_monitor.time_window = 60      # 时间窗口（秒）

# 注册自定义告警处理器
def my_alert_handler(alert_data):
    print(f"⚠️ 告警: {alert_data['error_count']} 个错误!")
    # 发送邮件、短信等

error_monitor.register_alert_callback(my_alert_handler)

# 记录错误（通常由系统自动调用）
error_monitor.record_error({
    "error_code": 5000,
    "error_type": "SYS_INTERNAL_ERROR",
    "message": "系统内部错误",
})
```

---

## 最佳实践

### 1. 始终使用具体的异常类

❌ **不推荐：**

```python
raise Exception("数据验证失败")
```

✅ **推荐：**

```python
from src.core.error_system import DataValidationError, ErrorCodeRegistry

raise DataValidationError(
    message="温度值超出范围",
    error_code=ErrorCodeRegistry.VALIDATION_OUT_OF_RANGE,
    field="temperature",
    value=150,
    details={"valid_range": "0-100"},
)
```

### 2. 为关键操作添加错误处理

❌ **不推荐：**

```python
def save_data(data):
    database.save(data)
```

✅ **推荐：**

```python
from src.core.error_system import safe_execute, retry

@retry(max_retries=3)
@safe_execute(context="保存数据", reraise=True)
def save_data(data):
    database.save(data)
```

### 3. 提供有意义的错误上下文

❌ **不推荐：**

```python
try:
    process_data(data)
except Exception as e:
    logger.error(str(e))
```

✅ **推荐：**

```python
from src.core.error_system import error_handler

try:
    process_data(data)
except Exception as e:
    error_handler.handle_exception(
        exception=e,
        context=f"处理数据: user={user_id}, data_size={len(data)}",
        user_id=user_id,
        session_id=session_id,
    )
```

### 4. 为用户提供友好的错误消息

❌ **不推荐：**

```python
raise DataValidationError("Invalid input: expected int, got str")
```

✅ **推荐：**

```python
raise DataValidationError(
    message="输入数据类型错误：期望整数，实际为字符串",
    user_message="请输入有效的数字",
    recovery_hint="检查输入是否为纯数字，不要包含字母或特殊字符",
    field="count",
    value=input_value,
)
```

### 5. 使用恢复策略处理临时性错误

❌ **不推荐：**

```python
def fetch_data(url):
    return requests.get(url).json()  # 网络错误时直接失败
```

✅ **推荐：**

```python
from src.core.error_system import retry, fallback

@fallback(default_value=None)
@retry(max_retries=3, retry_delay=2.0, exceptions=(ConnectionError,))
def fetch_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

### 6. 定期分析错误日志

```python
from src.core.error_system import error_handler, ErrorAnalytics
from pathlib import Path

# 每天生成错误分析报告
def generate_daily_report():
    analytics = ErrorAnalytics(error_handler.error_history)
    report_path = Path(f"logs/daily_report_{datetime.now():%Y%m%d}.txt")
    analytics.generate_report(output_path=report_path)
```

### 7. 为不同环境使用不同的错误处理策略

```python
import os
from src.core.error_system import install_error_interceptor

# 开发环境：显示详细错误
if os.getenv("ENV") == "development":
    interceptor = install_error_interceptor(
        app=app,
        show_error_dialog=True,
        auto_recovery=False,  # 不自动恢复，方便调试
    )

# 生产环境：自动恢复，记录详细日志
else:
    interceptor = install_error_interceptor(
        app=app,
        show_error_dialog=False,  # 不显示技术细节
        auto_recovery=True,       # 尝试自动恢复
    )
```

---

## 完整示例

### 示例1：实验管理系统

```python
from src.core.error_system import (
    safe_execute,
    retry,
    ExperimentError,
    DataValidationError,
    ErrorCodeRegistry,
)

class ExperimentManager:
    @safe_execute(context="加载实验模板")
    def load_template(self, template_id):
        """加载实验模板"""
        template = self.db.get_template(template_id)

        if not template:
            raise ExperimentError(
                message=f"实验模板不存在: {template_id}",
                error_code=ErrorCodeRegistry.EXP_TEMPLATE_NOT_FOUND,
                experiment_id=template_id,
                user_message="找不到指定的实验模板",
                recovery_hint="请检查模板ID是否正确",
            )

        return template

    @retry(max_retries=3, exceptions=(ValidationError,))
    def validate_step(self, step_data):
        """验证实验步骤"""
        if not step_data.get("action"):
            raise DataValidationError(
                message="步骤缺少必要的action字段",
                error_code=ErrorCodeRegistry.VALIDATION_REQUIRED_FIELD,
                field="action",
                value=None,
                user_message="实验步骤配置不完整",
            )

        return True

    @safe_execute(context="执行实验步骤", reraise=True)
    def execute_step(self, step):
        """执行实验步骤"""
        # 验证
        self.validate_step(step)

        # 执行
        result = self.engine.execute(step)

        # 保存结果
        self.save_result(result)

        return result
```

### 示例2：数据导入系统

```python
from src.core.error_system import (
    safe_execute,
    retry,
    fallback,
    DataValidationError,
    SystemError as AppSystemError,
)

class DataImporter:
    @retry(max_retries=3, retry_delay=1.0)
    @safe_execute(context="读取数据文件")
    def read_file(self, filepath):
        """读取数据文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise AppSystemError(
                message=f"文件不存在: {filepath}",
                error_code=ErrorCodeRegistry.SYS_FILE_NOT_FOUND,
                details={"filepath": filepath},
                user_message="找不到要导入的文件",
                recovery_hint="请检查文件路径是否正确",
            )

    @fallback(default_value=[])
    def parse_data(self, content):
        """解析数据"""
        try:
            data = json.loads(content)
            self.validate_data(data)
            return data
        except json.JSONDecodeError as e:
            raise DataValidationError(
                message="数据格式错误：无效的JSON",
                original_exception=e,
                user_message="文件内容格式不正确",
                recovery_hint="请确保文件是有效的JSON格式",
            )

    @safe_execute(context="导入数据", reraise=True)
    def import_data(self, filepath):
        """导入数据"""
        # 读取文件
        content = self.read_file(filepath)

        # 解析数据
        data = self.parse_data(content)

        # 保存到数据库
        for item in data:
            self.save_item(item)

        return len(data)
```

---

## 总结

VirtualChemLab 的错误处理系统提供了：

1. **标准化**：统一的错误码和异常类
2. **自动化**：装饰器和拦截器自动处理错误
3. **智能化**：自动恢复和重试机制
4. **可观测**：完整的日志、报告和分析
5. **用户友好**：清晰的错误消息和恢复建议

通过合理使用这套系统，可以大大提高应用的健壮性和用户体验。
