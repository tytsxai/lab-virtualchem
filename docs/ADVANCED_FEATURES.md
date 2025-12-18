# 🚀 VirtualChemLab 高级特性文档

> 企业级架构的高级功能和最佳实践

> 说明：本页包含“最佳实践 + 能力清单”。其中部分能力在当前仓库可能属于可选依赖或实验性实现，
> 不应被视为对外稳定契约。对外接口与运行方式请以 `docs/API.md`、`docs/ARCHITECTURE.md`、
> `docs/CONFIGURATION_REFERENCE.md` 为准；文档事实边界见 `docs/DOCS_STATUS.md`。

---

## 📑 目录

1. [高级缓存系统](#高级缓存系统)
2. [消息队列系统](#消息队列系统)
3. [认证授权](#认证授权)
4. [数据验证框架](#数据验证框架)
5. [结构化日志](#结构化日志)
6. [最佳实践](#最佳实践)

---

## 🗄️ 高级缓存系统

### 概述

提供多种缓存策略和分布式缓存支持，显著提升应用性能。

### 核心特性

- ✅ **多种缓存策略**: LRU、LFU、FIFO、TTL
- ✅ **分布式缓存**: Redis支持（可降级到本地缓存）
- ✅ **多级缓存**: L1/L2/L3 缓存架构
- ✅ **缓存预热**: 自动预加载热数据
- ✅ **装饰器支持**: 简化缓存使用

### 快速开始

```python
from src.core.cache import MemoryCache, cached, get_cache_manager

# 1. 创建缓存
cache = MemoryCache[str](max_size=1000, strategy=CacheStrategy.LRU)

# 2. 基本使用
cache.set("key", "value", ttl=3600)
value = cache.get("key")

# 3. 使用装饰器
@cached(ttl=300)
def expensive_calculation(x: int) -> int:
    return x * x

# 4. 多级缓存
from src.core.cache import MultiLevelCache

l1 = MemoryCache(max_size=100)   # 快速本地缓存
l2 = MemoryCache(max_size=1000)  # 较大本地缓存
multi = MultiLevelCache(l1, l2)
```

### 缓存策略对比

| 策略 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| LRU | 一般用途 | 简单高效 | 可能淘汰重要数据 |
| LFU | 热点数据 | 保留常用数据 | 冷启动慢 |
| FIFO | 顺序访问 | 实现简单 | 不考虑访问频率 |
| TTL | 时效数据 | 自动过期 | 需要设置合理TTL |

### 最佳实践

**✅ 推荐**

```python
# 使用装饰器
@cached(ttl=600, cache_name="experiments")
def get_experiment(exp_id: str) -> Experiment:
    return expensive_db_query(exp_id)

# 多级缓存提升性能
l1 = MemoryCache(max_size=100)  # 热数据
l2 = RedisCache(host="localhost", port=6379)  # 共享缓存（Redis）
cache = MultiLevelCache(l1, l2)
```

**❌ 避免**

```python
# 不要缓存不可序列化的对象
cache.set("key", file_handle)  # ❌

# 不要设置过长的TTL
cache.set("key", value, ttl=86400*365)  # ❌ 一年太长

# 不要缓存敏感数据
cache.set("password", user_password)  # ❌ 安全问题
```

---

## 📨 消息队列系统

### 概述

异步任务处理、消息重试、死信队列等企业级消息队列功能。

### 核心特性

- ✅ **优先级队列**: 4个优先级(CRITICAL/HIGH/NORMAL/LOW)
- ✅ **自动重试**: 指数退避策略
- ✅ **死信队列**: 失败消息收集
- ✅ **延迟消息**: 定时任务支持
- ✅ **多工作线程**: 并发处理

### 快速开始

```python
from src.core.message_queue import InMemoryMessageQueue, Message, MessagePriority

# 1. 创建队列
queue = InMemoryMessageQueue(worker_count=4)

# 2. 订阅主题
from src.core.message_queue import BaseMessageHandler

class MyHandler(BaseMessageHandler):
    async def handle(self, message):
        print(f"处理消息: {message.data}")

await queue.subscribe("my.topic", MyHandler())

# 3. 启动队列
await queue.start()

# 4. 发布消息
message = Message(
    topic="my.topic",
    data={"key": "value"},
    priority=MessagePriority.HIGH
)
await queue.publish(message)

# 5. 延迟消息
delayed_msg = Message(
    topic="my.topic",
    data={"key": "value"},
    delay=60  # 60秒后执行
)
await queue.publish(delayed_msg)
```

### 使用场景

| 场景 | 优先级 | 重试 | 说明 |
|------|--------|------|------|
| 报告生成 | LOW | 3次 | 可以稍后处理 |
| 实验数据保存 | NORMAL | 5次 | 重要但不紧急 |
| 用户通知 | HIGH | 3次 | 需要及时送达 |
| 安全告警 | CRITICAL | 10次 | 必须处理 |

### 最佳实践

**✅ 推荐**

```python
# 使用专门的处理器
class ReportHandler(BaseMessageHandler):
    async def handle(self, message):
        # 生成报告
        report = await generate_report(message.data)
        await save_report(report)

    async def on_error(self, message, error):
        # 错误处理
        logger.error(f"报告生成失败: {error}")
        await notify_admin(message, error)

# 合理设置重试次数
message = Message(
    topic="report.generate",
    data=data,
    max_retries=3  # 重试3次
)
```

**❌ 避免**

```python
# 不要在处理器中执行耗时操作
async def handle(self, message):
    time.sleep(100)  # ❌ 阻塞工作线程

# 不要忽略错误
async def on_error(self, message, error):
    pass  # ❌ 应该记录日志

# 不要设置过多重试
message.max_retries = 100  # ❌ 太多了
```

---

## 🔐 认证授权

### 概述

基于JWT的认证和RBAC权限控制系统。

### 核心特性

- ✅ **JWT认证**: 无状态令牌认证
- ✅ **RBAC**: 基于角色的访问控制
- ✅ **密码加密**: PBKDF2哈希
- ✅ **令牌刷新**: 支持访问令牌刷新
- ✅ **黑名单**: 令牌撤销支持

### 快速开始

```python
from src.core.auth import (
    AuthService, JWTManager, RBACManager,
    User, Role, Permission
)

# 1. 初始化
jwt_manager = JWTManager(secret_key="your-secret-key")
rbac_manager = RBACManager()
auth_service = AuthService(jwt_manager, rbac_manager, user_repo)

# 2. 用户认证
context = auth_service.authenticate("username", "password")
if context:
    print(f"令牌: {context.token.access_token}")
    print(f"权限: {len(context.permissions)}")

# 3. 令牌验证
context = auth_service.authorize(access_token)

# 4. 检查权限
if context.has_permission(Permission.EXPERIMENT_CREATE):
    create_experiment()

# 5. 使用装饰器
from src.core.auth import require_permission, require_role

@require_role(Role.ADMIN)
def admin_function():
    pass

@require_permission(Permission.EXPERIMENT_DELETE)
def delete_experiment(exp_id: str):
    pass
```

### 角色权限矩阵

| 权限 | ADMIN | STUDENT | GUEST |
|------|-------|---------|-------|
| 创建实验 | ✅ | ❌ | ❌ |
| 运行实验 | ✅ | ✅ | ❌ |
| 删除实验 | ✅ | ❌ | ❌ |
| 查看报告 | ✅ | ✅ | ✅ |
| 导出报告 | ✅ | ❌ | ❌ |
| 系统配置 | ✅ | ❌ | ❌ |

### 最佳实践

**✅ 推荐**

```python
# 使用环境变量存储密钥
import os
jwt_manager = JWTManager(
    secret_key=os.getenv("JWT_SECRET_KEY"),
    access_token_expire=3600  # 1小时
)

# 定期刷新令牌
if token_expires_soon():
    new_token = auth_service.refresh_token(refresh_token)

# 登出时撤销令牌
auth_service.logout(access_token)
```

**❌ 避免**

```python
# 不要在代码中硬编码密钥
jwt_manager = JWTManager(secret_key="123456")  # ❌

# 不要设置过长的过期时间
access_token_expire=86400*365  # ❌ 一年太长

# 不要在URL中传递令牌
url = f"/api?token={access_token}"  # ❌ 使用Header
```

---

## ✅ 数据验证框架

### 概述

强大的数据验证框架，支持多种验证器和规则链。

### 核心特性

- ✅ **多种验证器**: 类型、范围、长度、模式等
- ✅ **验证器链**: 组合多个验证规则
- ✅ **Pydantic集成**: 支持Pydantic模型
- ✅ **自定义验证**: 灵活的自定义规则
- ✅ **错误收集**: 完整的错误信息

### 快速开始

```python
from src.core.validation import (
    ValidationRule, ValidatorChain, SchemaValidator
)

# 1. 基础验证器
email_validator = ValidationRule.email("email")
result = email_validator.validate("test@example.com")
print(f"有效: {result.is_valid}")

# 2. 验证器链
password_chain = ValidatorChain()
password_chain.add(ValidationRule.required("password"))
password_chain.add(ValidationRule.length(min_length=8, field_name="password"))
password_chain.add(ValidationRule.pattern(
    r'[A-Z]',  # 必须包含大写字母
    "password"
))

# 3. 模式验证器
class UserValidator(SchemaValidator):
    def __init__(self):
        super().__init__()

        self.field("username").add(
            ValidationRule.required("username")
        ).add(
            ValidationRule.length(min_length=3, max_length=20, field_name="username")
        )

        self.field("email").add(
            ValidationRule.email("email")
        )

        self.field("age").add(
            ValidationRule.range(min_value=0, max_value=150, field_name="age")
        )

# 4. 使用
validator = UserValidator()
result = validator.validate({
    "username": "john_doe",
    "email": "john@example.com",
    "age": 25
})

if not result.is_valid:
    for error in result.errors:
        print(f"{error.field}: {error.message}")
```

### 内置验证器

| 验证器 | 用途 | 示例 |
|--------|------|------|
| RequiredValidator | 必填检查 | `ValidationRule.required("name")` |
| TypeValidator | 类型检查 | `ValidationRule.type_of(int, "age")` |
| RangeValidator | 数值范围 | `ValidationRule.range(0, 100, "score")` |
| LengthValidator | 字符串长度 | `ValidationRule.length(min_length=3)` |
| PatternValidator | 正则匹配 | `ValidationRule.pattern(r'\d+')` |
| EmailValidator | 邮箱格式 | `ValidationRule.email()` |
| URLValidator | URL格式 | `ValidationRule.url()` |
| CustomValidator | 自定义规则 | `ValidationRule.custom(func, msg)` |

### 最佳实践

**✅ 推荐**

```python
# 为不同实体创建专门的验证器
class ExperimentValidator(SchemaValidator):
    def __init__(self):
        super().__init__()
        # 定义所有字段的验证规则
        self.field("temperature").add(
            ValidationRule.range(-273.15, 1000, "temperature")
        )

# 组合验证器
def validate_experiment_data(data):
    # 结构验证
    struct_result = ExperimentValidator().validate(data)

    # 业务逻辑验证
    business_result = validate_business_rules(data)

    # 合并结果
    struct_result.merge(business_result)
    return struct_result
```

**❌ 避免**

```python
# 不要跳过验证
def create_user(data):
    user = User(**data)  # ❌ 没有验证

# 不要忽略验证错误
result = validator.validate(data)
# 继续处理... ❌ 应该检查result.is_valid
```

---

## 📊 结构化日志

### 概述

企业级结构化日志系统，支持上下文追踪、性能分析、审计日志。

### 核心特性

- ✅ **结构化输出**: JSON格式日志
- ✅ **上下文追踪**: 请求ID、用户ID等
- ✅ **性能测量**: 自动记录操作耗时
- ✅ **审计日志**: 用户操作审计
- ✅ **彩色输出**: 控制台友好显示

### 快速开始

```python
from src.core.structured_logging import (
    LoggerFactory, set_context, PerformanceLogger, AuditLogger
)

# 1. 配置日志系统
LoggerFactory.configure(
    log_level="INFO",
    log_file="app.log",
    console=True,
    json_format=False  # 控制台彩色输出
)

# 2. 获取日志记录器
logger = LoggerFactory.get_logger("VirtualChemLab")

# 3. 基础日志
logger.info("应用启动", version="2.0.0")
logger.debug("调试信息", data={"key": "value"})
logger.error("错误发生", exc_info=True)

# 4. 设置上下文
set_context(
    request_id="req_12345",
    user_id="user_001",
    experiment_id="exp_789"
)

logger.info("用户操作")  # 自动包含上下文

# 5. 临时上下文
with logger.context(session_id="session_abc"):
    logger.info("会话中的操作")

# 6. 性能日志
perf_logger = PerformanceLogger(logger)

with perf_logger.measure("数据库查询", table="experiments"):
    results = db.query("SELECT * FROM experiments")
# 自动记录耗时

# 7. 审计日志
audit_logger = AuditLogger(logger)

audit_logger.log_action(
    action="create_experiment",
    resource="experiment:exp_001",
    user_id="user_001",
    result="success",
    ip_address="192.168.1.100"
)

audit_logger.log_access(
    resource="report:rep_001",
    user_id="user_001",
    granted=True
)
```

### 日志级别使用指南

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| DEBUG | 开发调试 | 变量值、函数调用 |
| INFO | 正常信息 | 操作成功、状态变化 |
| WARNING | 警告信息 | 慢查询、降级使用 |
| ERROR | 错误信息 | 操作失败、异常 |
| CRITICAL | 严重错误 | 系统崩溃、数据丢失 |

### 最佳实践

**✅ 推荐**

```python
# 使用结构化字段
logger.info(
    "实验完成",
    experiment_id="exp_001",
    duration_seconds=12.5,
    status="success"
)

# 性能监控
with perf_logger.measure("report_generation"):
    generate_report()

# 错误日志包含上下文
try:
    process_data()
except Exception as e:
    logger.exception(
        "数据处理失败",
        data_id=data_id,
        operation="process"
    )
```

**❌ 避免**

```python
# 不要使用字符串拼接
logger.info(f"User {user_id} did {action}")  # ❌
# 使用:
logger.info("User action", user_id=user_id, action=action)  # ✅

# 不要记录敏感信息
logger.info("Login", password=pwd)  # ❌

# 不要过度记录
for item in range(1000000):
    logger.debug(f"Processing {item}")  # ❌ 性能问题
```

---

## 🎯 最佳实践

### 整体架构建议

#### 1. 分层清晰

```
┌─────────────────┐
│   Presentation  │  FastAPI/Flask
├─────────────────┤
│    Application  │  业务逻辑
├─────────────────┤
│     Domain      │  领域模型
├─────────────────┤
│ Infrastructure  │  数据访问/缓存/消息队列
└─────────────────┘
```

#### 2. 依赖注入

```python
# 通过容器管理所有依赖
container = create_app()

# 服务自动解析依赖
experiment_service = container.resolve(IExperimentService)
```

#### 3. 配置外部化

```python
# config.json
{
  "cache": {
    "strategy": "LRU",
    "max_size": 1000
  },
  "jwt": {
    "secret_key": "${JWT_SECRET}",  # 从环境变量读取
    "expire": 3600
  }
}
```

### 性能优化

#### 1. 缓存策略

```python
# 多级缓存
l1 = MemoryCache(max_size=100)    # 热数据，速度最快
l2 = MemoryCache(max_size=1000)   # 温数据
l3 = RedisCache(host="localhost", port=6379)  # 冷数据，可共享（Redis）

cache = MultiLevelCache(l1, l2, l3)
```

#### 2. 异步处理

```python
# 耗时操作异步化
@async_cached(ttl=300)
async def generate_report(exp_id: str):
    # 异步生成报告
    report = await async_generate(exp_id)
    return report

# 使用消息队列
await queue.publish(Message(
    topic="report.generate",
    data={"experiment_id": exp_id}
))
```

#### 3. 数据库优化

```python
# 使用缓存减少数据库查询
@cached(ttl=600)
def get_experiment(exp_id: str):
    return db.query_experiment(exp_id)

# 批量操作
experiments = db.batch_query(experiment_ids)
```

### 安全建议

#### 1. 认证授权

```python
# 所有API都需要认证
@require_auth
@require_permission(Permission.EXPERIMENT_CREATE)
def create_experiment(data):
    pass
```

#### 2. 数据验证

```python
# 输入验证
validator = ExperimentValidator()
result = validator.validate(input_data)

if not result.is_valid:
    raise ValidationError(result.errors)
```

#### 3. 审计日志

```python
# 记录所有关键操作
audit_logger.log_action(
    action="delete_experiment",
    resource=f"experiment:{exp_id}",
    user_id=current_user.id,
    result="success"
)
```

### 监控与运维

#### 1. 健康检查

```python
def health_check():
    checks = {
        "database": check_database(),
        "cache": check_cache(),
        "queue": check_queue()
    }
    return all(checks.values())
```

#### 2. 性能监控

```python
# 记录所有操作耗时
with perf_logger.measure("experiment_run"):
    run_experiment(exp_id)
```

#### 3. 错误追踪

```python
# 使用请求ID追踪
set_context(request_id=generate_request_id())

# 所有日志自动包含request_id
logger.info("操作开始")
logger.error("操作失败")
```

---

## 📚 参考资源

### 文档

- [架构概览](ARCHITECTURE.md)
- [快速开始](../QUICK_START_GUIDE.md)
- [API文档](API.md)

### 示例代码

```bash
# 可运行示例（与当前仓库文件对齐）
python3 examples/api_integration_example.py
python3 examples/error_handling_examples.py
```

### 社区

- GitHub Issues
- 技术博客
- 开发者论坛

---

**版本**: v2.0.0
**最后更新**: 2025年10月6日

**✨ 使用这些高级特性，构建企业级应用！**
