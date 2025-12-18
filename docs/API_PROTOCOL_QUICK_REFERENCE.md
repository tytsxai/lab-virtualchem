# 📋 接口与事件协议 - 快速参考

> VirtualChemLab 前后端通信快速参考卡

---

## ⚠️ 维护安全提示

本文件为“协议速查卡”，包含部分历史/规划内容（例如 WebSocket）。当前仓库对外 HTTP 接口以
`docs/API.md` 为准（对齐 `src/api/server.py`、`src/api/admin_api.py`）。如你在这里看到与实际
实现不一致的端点/认证方式，请优先相信 `docs/API.md`，并参考 `docs/DOCS_STATUS.md` 的来源边界。

---

## 🚀 快速开始

### REST API

```python
# 导入客户端
from src.api.client import VirtualChemLabClient

# 创建客户端
client = VirtualChemLabClient("http://localhost:8080")

# 开始实验
result = client.run_experiment(
    experiment_id="titration_naoh_hcl",
    user_id="student_001",
    steps_data=[{"confirmed": True}, {"value": "25.0"}]
)
```

### 事件总线

```python
# 导入事件总线
from src.core.event_bus import get_event_bus, Event

# 获取实例
bus = get_event_bus()

# 订阅事件
bus.subscribe("experiment.completed", handler)

# 发布事件
bus.publish(Event(name="experiment.started", data={...}))
```

---

## 📊 通信方式对照表

| 场景 | 推荐方式 | 原因 |
|------|---------|------|
| 查询数据 | REST GET | 简单、可缓存 |
| 创建资源 | REST POST | 标准化 |
| 更新资源 | REST PUT/PATCH | 幂等性 |
| 删除资源 | REST DELETE | 幂等性 |
| 模块解耦 | Event Bus | 松耦合 |
| 异步任务 | Message Queue | 可靠性 |
| 实时推送 | WebSocket | 低延迟 |

---

## 🔌 REST API 速查

### HTTP方法

| 方法 | 用途 | 幂等 | 示例 |
|------|------|-----|------|
| GET | 查询 | ✅ | `GET /experiments` |
| POST | 创建 | ❌ | `POST /experiments` |
| PUT | 完整更新 | ✅ | `PUT /experiments/123` |
| PATCH | 部分更新 | ❌ | `PATCH /experiments/123` |
| DELETE | 删除 | ✅ | `DELETE /experiments/123` |

### 常用状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| 200 | 成功 | GET/PUT/PATCH成功 |
| 201 | 已创建 | POST成功 |
| 204 | 无内容 | DELETE成功 |
| 400 | 错误请求 | 参数错误 |
| 401 | 未认证 | 需要登录 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 500 | 服务器错误 | 内部错误 |

### API端点

```
# 实验管理
GET    /api/v1/experiments              # 列出实验
GET    /api/v1/experiments/{id}         # 获取实验
POST   /api/v1/experiments/start        # 开始实验
POST   /api/v1/experiments/{id}/steps   # 提交步骤
POST   /api/v1/experiments/{id}/finish  # 完成实验

# 记录管理
GET    /api/v1/records                  # 查询记录
GET    /api/v1/records/{id}             # 获取记录
DELETE /api/v1/records/{id}             # 删除记录

# 报告生成
POST   /api/v1/reports/generate         # 生成报告

# 系统
GET    /api/v1/health                   # 健康检查
```

### 请求示例

```http
POST /api/v1/experiments/start HTTP/1.1
Host: api.virtualchemlab.com
Content-Type: application/json
Authorization: Bearer eyJhbGci...

{
  "template_id": "titration_naoh_hcl",
  "user_id": "student_001",
  "parameters": {
    "concentration": 0.1
  }
}
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "session_id": "exp_12345",
    "status": "running",
    "created_at": "2025-10-06T10:30:00Z"
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-06T10:30:01Z"
  }
}
```

---

## 🎯 事件总线速查

### 事件命名

**格式**: `{domain}.{action}`

```
experiment.started          # 实验开始
experiment.step_completed   # 步骤完成
experiment.completed        # 实验完成
user.login                  # 用户登录
system.error               # 系统错误
```

### 订阅模式

```python
# 1. 订阅特定事件
bus.subscribe("experiment.started", handler)

# 2. 订阅所有实验事件
bus.subscribe("experiment.*", handler)

# 3. 订阅所有事件
bus.subscribe("*", handler)

# 4. 带优先级
bus.subscribe("critical.event", handler, priority=EventPriority.HIGH)

# 5. 带过滤器
bus.subscribe("order.*", handler,
    filter_func=lambda e: e.data.get('amount') > 100)
```

### 事件优先级

```python
class EventPriority(Enum):
    CRITICAL = 3  # 关键 - 立即处理
    HIGH = 2      # 高优先级 - 优先处理
    NORMAL = 1    # 普通 - 正常处理
    LOW = 0       # 低优先级 - 延后处理
```

### 标准事件

| 事件名称 | 触发时机 | 数据字段 |
|---------|---------|---------|
| `experiment.started` | 实验开始 | `session_id`, `user_id` |
| `experiment.step_completed` | 步骤完成 | `session_id`, `step_index` |
| `experiment.completed` | 实验完成 | `session_id`, `record_id` |
| `experiment.failed` | 实验失败 | `session_id`, `error` |
| `data.saved` | 数据保存 | `record_id`, `data_type` |
| `system.error` | 系统错误 | `error`, `severity` |

### 发布事件

```python
from src.core.event_bus import Event, EventPriority

# 同步发布
event = Event(
    name="experiment.completed",
    data={"session_id": "exp_001", "record_id": "rec_001"},
    priority=EventPriority.HIGH
)
bus.publish(event)

# 异步发布
await bus.publish_async(event)
```

---

## ⚠️ 错误码速查

### 分类

| 范围 | 分类 | 示例 |
|------|------|------|
| 1000-1999 | 通用错误 | 1001: 无效请求 |
| 2000-2999 | 认证错误 | 2002: 令牌过期 |
| 3000-3999 | 实验错误 | 3002: 验证失败 |
| 4000-4999 | 数据错误 | 4000: 验证失败 |
| 5000-5999 | 系统错误 | 5000: 内部错误 |

### 常用错误码

| 错误码 | 类型 | 说明 | HTTP |
|--------|------|------|------|
| 1001 | `INVALID_REQUEST` | 无效请求 | 400 |
| 1004 | `RESOURCE_NOT_FOUND` | 资源不存在 | 404 |
| 2001 | `AUTH_INVALID_TOKEN` | 令牌无效 | 401 |
| 2002 | `AUTH_TOKEN_EXPIRED` | 令牌过期 | 401 |
| 2003 | `AUTH_INSUFFICIENT_PERMISSION` | 权限不足 | 403 |
| 3001 | `EXP_INVALID_STATE` | 状态无效 | 400 |
| 3002 | `EXP_STEP_VALIDATION_FAILED` | 验证失败 | 422 |
| 5000 | `SYS_INTERNAL_ERROR` | 内部错误 | 500 |

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": 3002,
    "type": "EXP_STEP_VALIDATION_FAILED",
    "message": "步骤验证失败",
    "details": [
      {
        "field": "volume",
        "issue": "必须在0-100之间",
        "value": 150
      }
    ],
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## 🔒 认证速查

### JWT认证流程

```python
from src.core.auth import create_token, verify_token, require_auth

# 1. 创建令牌
token = create_token({
    "user_id": "student_001",
    "role": "student"
})

# 2. 验证令牌
payload = verify_token(token)

# 3. 保护端点
@require_auth
def protected_endpoint(auth_context):
    user_id = auth_context.user_id
    # ...
```

### 权限控制

```python
from src.core.auth import require_permission, Permission

@require_auth
@require_permission(Permission.EXPERIMENT_CREATE)
def create_experiment(auth_context, data):
    # ...
```

### 权限列表

```python
class Permission(Enum):
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_UPDATE = "experiment:update"
    EXPERIMENT_DELETE = "experiment:delete"
    ADMIN_MANAGE = "admin:manage"
```

---

## 📝 数据格式速查

### 字段命名

| 类型 | 格式 | 示例 |
|------|------|------|
| JSON字段 | snake_case | `user_id`, `created_at` |
| URL参数 | snake_case | `?user_id=123` |
| HTTP Header | Kebab-Case | `X-Request-ID` |
| 类名 | PascalCase | `ExperimentController` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |

### 数据类型

| 类型 | 格式 | 示例 |
|------|------|------|
| ID | 前缀+下划线+数字 | `exp_12345` |
| 时间戳 | ISO 8601 | `2025-10-06T10:30:00Z` |
| 布尔值 | true/false | `true` |
| 枚举 | 小写+下划线 | `running` |

### 分页数据

```json
{
  "data": [...],
  "meta": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  },
  "links": {
    "self": "/api/v1/experiments?page=1",
    "next": "/api/v1/experiments?page=2",
    "last": "/api/v1/experiments?page=8"
  }
}
```

---

## 🔧 版本控制

### 版本格式

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ 补丁版本 (bug修复)
  │     └─────── 次版本 (新功能)
  └───────────── 主版本 (破坏性变更)
```

### API版本

```
# URL版本控制
/api/v1/experiments
/api/v2/experiments

# Header版本控制
Accept: application/vnd.virtualchemlab.v2+json
```

### 废弃通知

```http
HTTP/1.1 200 OK
Deprecation: version="v1", date="2025-12-31"
Sunset: Wed, 31 Dec 2025 23:59:59 GMT
Link: </api/v2/experiments>; rel="alternate"
```

---

## 🌐 WebSocket速查

### 连接

```javascript
const ws = new WebSocket('ws://localhost:8080/ws?token=xxx');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'jwt_token'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到:', data);
};
```

### 消息格式

```json
{
  "type": "event",
  "event": "experiment.step_completed",
  "data": {
    "step_index": 2,
    "result": "success"
  },
  "message_id": "msg_12345",
  "timestamp": "2025-10-06T10:30:00Z"
}
```

### 心跳

```javascript
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);
```

---

## ✅ 最佳实践检查清单

### REST API

- [ ] 使用正确的HTTP方法
- [ ] 遵循命名规范 (snake_case)
- [ ] 返回正确的状态码
- [ ] 提供清晰的错误信息
- [ ] 实现分页 (列表接口)
- [ ] 添加认证 (敏感接口)
- [ ] 使用版本控制
- [ ] 实现缓存 (GET请求)
- [ ] 添加限流保护
- [ ] 记录日志

### 事件总线

- [ ] 使用清晰的事件名称
- [ ] 提供充分的上下文数据
- [ ] 设置合适的优先级
- [ ] 避免循环依赖
- [ ] 处理异步事件错误
- [ ] 记录事件日志
- [ ] 避免同步订阅者阻塞

### 错误处理

- [ ] 使用标准错误码
- [ ] 提供详细错误信息
- [ ] 包含trace_id
- [ ] 记录错误日志
- [ ] 返回合适的HTTP状态码

---

## 📚 相关文档

- [完整协议文档](./API_EVENT_PROTOCOL.md)
- [REST API参考](./API_REFERENCE.md)
- [事件列表](./EVENT_CATALOG.md)
- [错误码完整列表](./ERROR_CODES.md)

---

**版本**: v2.0.0
**最后更新**: 2025年10月6日
