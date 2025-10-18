# VirtualChemLab 增强功能指南

## 概述

VirtualChemLab 经过重构和增强，新增了多项企业级功能，包括可观测性、智能缓存、插件系统、国际化支持、安全防护和API网关。本指南将详细介绍这些功能的使用方法。

## 目录

- [可观测性系统](#可观测性系统)
- [智能缓存管理](#智能缓存管理)
- [插件系统](#插件系统)
- [国际化支持](#国际化支持)
- [安全防护](#安全防护)
- [API网关](#api网关)
- [功能集成](#功能集成)
- [最佳实践](#最佳实践)

## 可观测性系统

### 功能特性

- **统一日志管理**: 结构化日志记录，支持多级别和上下文信息
- **分布式追踪**: 请求链路追踪，支持跨组件调用链分析
- **指标收集**: 性能指标、业务指标和自定义指标收集
- **实时监控**: 系统状态实时监控和告警

### 基本使用

```python
from src.core.enhanced_observability import (
    get_observability, LogLevel, TraceType, trace_span,
    record_metric, increment_counter, record_histogram, record_gauge
)

# 获取可观测性系统实例
observability = get_observability()

# 记录日志
observability.log(LogLevel.INFO, "操作开始", module="MyModule", function="my_function")

# 使用追踪
with trace_span("业务操作", TraceType.BUSINESS) as span_id:
    # 添加追踪日志
    observability.add_trace_log(span_id, LogLevel.INFO, "执行步骤1")

    # 执行业务逻辑
    result = perform_business_logic()

    observability.add_trace_log(span_id, LogLevel.INFO, "执行完成")

# 记录指标
record_metric("operation_duration", 0.5, unit="seconds")
increment_counter("operations_count")
record_histogram("response_time", 0.1)
record_gauge("active_connections", 10)

# 获取统计信息
stats = observability.get_stats()
```

### 高级功能

```python
# 自定义追踪标签
with trace_span("数据库查询", TraceType.DATABASE, table="users", operation="select") as span_id:
    # 执行数据库查询
    pass

# 导出数据
observability.export_data(Path("logs/observability"))
```

## 智能缓存管理

### 功能特性

- **多级缓存**: L1内存缓存 + L2磁盘缓存 + L3分布式缓存
- **智能淘汰**: LRU、LFU、TTL等多种淘汰策略
- **缓存预热**: 支持缓存预热和预加载
- **性能监控**: 缓存命中率、响应时间等指标监控

### 基本使用

```python
from src.core.smart_cache_manager import (
    get_cache_manager, cache_get, cache_set, cache_get_or_set, cache_preload
)

# 获取缓存管理器
cache_manager = get_cache_manager()

# 设置缓存
cache_set("user:123", {"name": "张三", "email": "zhangsan@example.com"}, ttl=3600)

# 获取缓存
user_data = cache_get("user:123")

# 获取或设置缓存
def fetch_user_data(user_id):
    # 模拟从数据库获取数据
    return {"name": "用户", "id": user_id}

user_data = cache_get_or_set("user:456", lambda: fetch_user_data("456"), ttl=1800)

# 预热缓存
def preload_users():
    return {"users": ["user1", "user2", "user3"]}

cache_preload(["users"])
```

### 高级功能

```python
# 多级缓存设置
cache_manager.set("key", "value", ttl=300, levels=[CacheLevel.L1, CacheLevel.L2])

# 获取缓存统计
stats = cache_manager.get_stats()
print(f"缓存命中率: {stats['hit_rate']:.2%}")

# 导出缓存数据
cache_manager.export_cache(Path("outputs/cache"))
```

## 插件系统

### 功能特性

- **动态加载**: 支持运行时动态加载和卸载插件
- **生命周期管理**: 完整的插件生命周期管理
- **依赖管理**: 插件间依赖关系管理
- **事件通信**: 插件间通过事件总线通信

### 创建插件

```python
from src.core.plugin_system import PluginInterface, PluginInfo, PluginType

class MyPlugin(PluginInterface):
    def initialize(self, config: dict) -> None:
        """初始化插件"""
        self.config = config
        print("插件初始化完成")

    def start(self) -> None:
        """启动插件"""
        print("插件启动")

    def stop(self) -> None:
        """停止插件"""
        print("插件停止")

    def cleanup(self) -> None:
        """清理插件"""
        print("插件清理")

    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name="MyPlugin",
            version="1.0.0",
            description="我的插件",
            author="开发者",
            plugin_type=PluginType.FEATURE
        )
```

### 使用插件

```python
from src.core.plugin_system import get_plugin_manager

# 获取插件管理器
plugin_manager = get_plugin_manager()

# 注册插件类
plugin_manager._register_plugin_class(MyPlugin)

# 加载插件
success = plugin_manager.load_plugin("MyPlugin", config={"setting": "value"})

if success:
    # 初始化插件
    plugin_manager.initialize_plugin("MyPlugin")

    # 启动插件
    plugin_manager.start_plugin("MyPlugin")

    # 获取插件实例
    plugin = plugin_manager.get_plugin("MyPlugin")

    # 停止插件
    plugin_manager.stop_plugin("MyPlugin")

    # 卸载插件
    plugin_manager.unload_plugin("MyPlugin")
```

## 国际化支持

### 功能特性

- **多语言支持**: 支持10种主要语言
- **动态切换**: 运行时动态语言切换
- **复数形式**: 支持复数形式翻译
- **上下文翻译**: 支持上下文相关的翻译

### 基本使用

```python
from src.core.enhanced_i18n_manager import (
    get_i18n_manager, LanguageCode, t, tp, set_language
)

# 获取国际化管理器
i18n_manager = get_i18n_manager()

# 添加翻译
i18n_manager.add_translation("hello", "Hello", LanguageCode.EN, "greetings")
i18n_manager.add_translation("hello", "你好", LanguageCode.ZH_CN, "greetings")
i18n_manager.add_translation("welcome", "Welcome, {name}!", LanguageCode.EN, "greetings")
i18n_manager.add_translation("welcome", "欢迎，{name}！", LanguageCode.ZH_CN, "greetings")

# 设置语言
set_language(LanguageCode.ZH_CN)

# 翻译文本
hello_text = t("hello", "greetings")
welcome_text = t("welcome", "greetings", name="用户")

# 复数形式翻译
i18n_manager.add_translation("item:one", "1 item", LanguageCode.EN, "inventory")
i18n_manager.add_translation("item:other", "{count} items", LanguageCode.EN, "inventory")

item_text = tp("item", 5, "inventory", count=5)  # "5 items"
```

### 高级功能

```python
# 获取支持的语言
languages = i18n_manager.get_supported_languages()
for lang in languages:
    print(f"{lang.name} ({lang.native_name})")

# 导出翻译数据
i18n_manager.export_translations(Path("outputs/i18n"))

# 从文件加载翻译
i18n_manager.load_resource_directory(Path("assets/i18n"))
```

## 安全防护

### 功能特性

- **身份认证**: 用户身份验证和会话管理
- **权限控制**: 基于角色的权限控制
- **数据加密**: 敏感数据加密存储
- **威胁检测**: 安全威胁检测和响应

### 基本使用

```python
from src.core.security_manager import (
    get_security_manager, Permission, authenticate_user, validate_session
)

# 获取安全管理器
security_manager = get_security_manager()

# 用户认证
session_id = authenticate_user("username", "password", "127.0.0.1")

if session_id:
    # 验证会话
    user_id = validate_session(session_id)

    if user_id:
        # 检查权限
        has_admin = security_manager.check_permission(user_id, Permission.ADMIN)
        has_read = security_manager.check_permission(user_id, Permission.READ)

        # 获取用户信息
        user = security_manager.get_user(user_id)

        # 登出
        security_manager.logout_user(session_id)

# 数据加密
original_data = "敏感数据"
key = "secret_key"
encrypted = security_manager.encrypt_data(original_data, key)
decrypted = security_manager.decrypt_data(encrypted, key)
```

### 高级功能

```python
# 威胁检测
security_manager.detect_threat(
    "brute_force",
    "检测到暴力破解攻击",
    ip_address="192.168.1.100",
    attempts=10
)

# 获取安全事件
events = security_manager.get_security_events(limit=10)
for event in events:
    print(f"安全事件: {event.description}")

# 导出安全数据
security_manager.export_security_data(Path("outputs/security"))
```

## API网关

### 功能特性

- **RESTful API**: 标准RESTful API接口
- **请求路由**: 智能请求路由和负载均衡
- **认证授权**: 集成身份认证和权限控制
- **限流控制**: 请求频率限制和流量控制

### 创建API端点

```python
from src.core.api_gateway import (
    get_api_gateway, HttpMethod, ApiRequest, ApiResponse,
    ApiResponseStatus, register_api_route, Permission
)

# 获取API网关
api_gateway = get_api_gateway()

# 定义API处理器
def user_handler(request: ApiRequest) -> ApiResponse:
    """用户API处理器"""
    if request.method == HttpMethod.GET:
        # 获取用户列表
        users = get_users()
        return ApiResponse(
            status=ApiResponseStatus.SUCCESS,
            data={"users": users},
            message="获取用户列表成功"
        )
    elif request.method == HttpMethod.POST:
        # 创建用户
        user_data = request.body
        new_user = create_user(user_data)
        return ApiResponse(
            status=ApiResponseStatus.SUCCESS,
            data={"user": new_user},
            message="创建用户成功",
            status_code=201
        )
    else:
        return ApiResponse(
            status=ApiResponseStatus.ERROR,
            message="不支持的HTTP方法",
            status_code=405
        )

# 注册API路由
register_api_route(
    HttpMethod.GET,
    "/api/users",
    user_handler,
    permissions=[Permission.READ],
    description="获取用户列表"
)

register_api_route(
    HttpMethod.POST,
    "/api/users",
    user_handler,
    permissions=[Permission.WRITE],
    description="创建用户"
)
```

### 使用API

```python
# 创建API请求
request = ApiRequest(
    method=HttpMethod.GET,
    path="/api/users",
    headers={"Authorization": "Bearer token"},
    query_params={"page": "1", "limit": "10"},
    user_id="user123",
    ip_address="127.0.0.1"
)

# 处理请求
response = api_gateway.handle_request(request)

# 检查响应
if response.status == ApiResponseStatus.SUCCESS:
    print(f"成功: {response.message}")
    print(f"数据: {response.data}")
else:
    print(f"错误: {response.message}")
    print(f"错误代码: {response.error_code}")
```

## 功能集成

### 集成示例

```python
def integrated_operation():
    """集成操作示例"""
    # 使用追踪包装整个操作
    with trace_span("集成操作", TraceType.BUSINESS) as span_id:
        observability = get_observability()
        observability.add_trace_log(span_id, LogLevel.INFO, "开始集成操作")

        # 1. 用户认证
        session_id = authenticate_user("admin", "password")
        if not session_id:
            raise Exception("认证失败")

        # 2. 权限检查
        user_id = validate_session(session_id)
        if not security_manager.check_permission(user_id, Permission.READ):
            raise Exception("权限不足")

        # 3. 缓存查询
        cache_key = f"user_data:{user_id}"
        user_data = cache_get(cache_key)

        if not user_data:
            # 4. 数据库查询（模拟）
            user_data = fetch_user_from_database(user_id)
            cache_set(cache_key, user_data, ttl=3600)

        # 5. 国际化处理
        welcome_message = t("welcome", "ui", name=user_data["name"])

        # 6. API响应
        response = ApiResponse(
            status=ApiResponseStatus.SUCCESS,
            data={"user": user_data, "message": welcome_message},
            message="操作成功"
        )

        # 7. 记录指标
        record_metric("integrated_operation_duration", 0.5)
        increment_counter("integrated_operations_count")

        observability.add_trace_log(span_id, LogLevel.INFO, "集成操作完成")

        return response
```

## 最佳实践

### 1. 错误处理

```python
from src.core.error_handler import safe_execute
from src.core.common_exceptions import SystemError

def safe_operation():
    """安全操作示例"""
    def operation():
        # 可能出错的操作
        return risky_operation()

    result = safe_execute(
        operation,
        error_class=SystemError,
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.MEDIUM
    )

    return result
```

### 2. 性能监控

```python
def monitored_operation():
    """性能监控示例"""
    start_time = time.time()

    try:
        # 执行业务逻辑
        result = business_logic()

        # 记录成功指标
        record_metric("operation_success_rate", 1.0)
        increment_counter("successful_operations")

        return result
    except Exception as e:
        # 记录失败指标
        record_metric("operation_success_rate", 0.0)
        increment_counter("failed_operations")
        raise
    finally:
        # 记录耗时
        duration = time.time() - start_time
        record_histogram("operation_duration", duration)
```

### 3. 缓存策略

```python
def smart_cache_usage():
    """智能缓存使用示例"""
    def fetch_data():
        # 模拟数据库查询
        time.sleep(0.1)
        return {"data": "expensive_computation"}

    # 使用缓存
    data = cache_get_or_set(
        "expensive_data",
        fetch_data,
        ttl=300  # 5分钟缓存
    )

    return data
```

### 4. 安全实践

```python
def secure_operation(user_id: str, operation: str):
    """安全操作示例"""
    # 验证会话
    if not validate_session(user_id):
        raise SecurityError("无效会话")

    # 检查权限
    if not security_manager.check_permission(user_id, Permission.ADMIN):
        raise SecurityError("权限不足")

    # 记录安全事件
    security_manager._log_security_event(
        "admin_operation",
        SecurityLevel.MEDIUM,
        user_id,
        f"管理员执行操作: {operation}"
    )

    # 执行操作
    return perform_operation(operation)
```

## 总结

VirtualChemLab 的增强功能提供了企业级的可观测性、缓存、插件、国际化、安全和API能力。通过合理使用这些功能，可以构建出更加健壮、可扩展和可维护的应用程序。

建议在实际使用中：

1. **逐步集成**: 不要一次性集成所有功能，根据实际需求逐步添加
2. **性能考虑**: 注意监控系统性能，避免过度使用缓存或日志
3. **安全优先**: 始终将安全放在首位，及时更新安全策略
4. **文档维护**: 保持文档更新，记录配置变更和最佳实践

更多详细信息请参考各模块的源代码和示例文件。
