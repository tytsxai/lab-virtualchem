# 🔌 VirtualChemLab 接口与事件协议规范

> 前后端通信的契约与标准化规则

**版本**: v2.0.0
**状态**: ⚠️ 历史材料 / 规划性协议（可能与当前实现不一致）
**最后更新**: 2025年10月6日

---

## ⚠️ 维护安全提示

本文档包含 REST / 事件 / WebSocket 等“协议规划”。当前仓库的对外 HTTP 接口以 `docs/API.md`
为准（对齐 `src/api/server.py`、`src/api/admin_api.py`）。其中 WebSocket 在当前实现中为占位逻辑
（`src/api/server.py` 的升级处理返回 501），因此本文件的 WebSocket 章节不应被当作生产契约。

文档事实来源边界请参考：`docs/DOCS_STATUS.md`。

---

## 📋 目录

- [1. 协议概述](#1-协议概述)
- [2. 通信方式](#2-通信方式)
- [3. REST API 接口规范](#3-rest-api-接口规范)
- [4. 事件驱动协议](#4-事件驱动协议)
- [5. WebSocket 实时通信](#5-websocket-实时通信)
- [6. 数据格式规范](#6-数据格式规范)
- [7. 错误码体系](#7-错误码体系)
- [8. 版本控制策略](#8-版本控制策略)
- [9. 安全与认证](#9-安全与认证)
- [10. 最佳实践](#10-最佳实践)

---

## 1. 协议概述

### 1.1 设计原则

| 原则 | 说明 | 实现方式 |
|------|------|---------|
| **统一性** | 所有接口遵循统一规范 | REST + 事件总线 |
| **可扩展性** | 支持版本演进 | API版本控制 |
| **安全性** | 数据传输安全 | JWT + HTTPS |
| **性能** | 高效数据传输 | 压缩 + 缓存 |
| **可靠性** | 容错与重试机制 | 熔断器 + 重试 |

### 1.2 协议层次

```
┌─────────────────────────────────────┐
│     应用层 (Application Layer)      │
│   - 业务逻辑                        │
│   - 数据处理                        │
└─────────────────────────────────────┘
              ▲
              │
┌─────────────────────────────────────┐
│     协议层 (Protocol Layer)         │
│   - REST API (同步)                 │
│   - Event Bus (异步)                │
│   - WebSocket (实时)                │
└─────────────────────────────────────┘
              ▲
              │
┌─────────────────────────────────────┐
│     传输层 (Transport Layer)        │
│   - HTTP/HTTPS                      │
│   - WebSocket                       │
│   - 消息队列                        │
└─────────────────────────────────────┘
```

---

## 2. 通信方式

### 2.1 通信方式对比

| 方式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **REST API** | CRUD操作、资源管理 | 简单、标准化、易缓存 | 实时性差 |
| **Event Bus** | 模块解耦、异步处理 | 松耦合、可扩展 | 调试复杂 |
| **WebSocket** | 实时通信、推送 | 双向通信、低延迟 | 资源消耗高 |
| **Message Queue** | 异步任务、后台处理 | 可靠性高、削峰填谷 | 复杂度高 |

### 2.2 选择决策树

```
需要实时双向通信？
├─ 是 → 使用 WebSocket
└─ 否 → 需要异步处理？
    ├─ 是 → 模块内部？
    │   ├─ 是 → Event Bus
    │   └─ 否 → Message Queue
    └─ 否 → REST API
```

---

## 3. REST API 接口规范

### 3.1 基础规范

#### 3.1.1 URL 设计

**命名规则**:
```
格式: /api/{version}/{resource}/{id}/{sub-resource}
示例: /api/v1/experiments/exp_001/steps
```

**规范**:
- ✅ 使用复数名词: `/experiments` 而非 `/experiment`
- ✅ 使用小写字母和连字符: `/experiment-templates`
- ✅ 资源嵌套最多3层
- ❌ 避免动词: `/getExperiment` (错误)

#### 3.1.2 HTTP 方法

| 方法 | 用途 | 幂等性 | 示例 |
|------|------|--------|------|
| `GET` | 获取资源 | ✅ | `GET /api/v1/experiments` |
| `POST` | 创建资源 | ❌ | `POST /api/v1/experiments` |
| `PUT` | 完整更新 | ✅ | `PUT /api/v1/experiments/123` |
| `PATCH` | 部分更新 | ❌ | `PATCH /api/v1/experiments/123` |
| `DELETE` | 删除资源 | ✅ | `DELETE /api/v1/experiments/123` |

#### 3.1.3 状态码规范

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| `200` | 成功 | GET、PUT、PATCH成功 |
| `201` | 已创建 | POST成功创建资源 |
| `204` | 无内容 | DELETE成功 |
| `400` | 错误请求 | 参数验证失败 |
| `401` | 未认证 | Token缺失或无效 |
| `403` | 禁止访问 | 权限不足 |
| `404` | 未找到 | 资源不存在 |
| `409` | 冲突 | 资源状态冲突 |
| `422` | 不可处理 | 语义错误 |
| `429` | 请求过多 | 触发限流 |
| `500` | 服务器错误 | 内部错误 |
| `503` | 服务不可用 | 维护或过载 |

### 3.2 请求格式

#### 3.2.1 请求头

```http
POST /api/v1/experiments HTTP/1.1
Host: api.virtualchemlab.com
Content-Type: application/json
Accept: application/json
Accept-Language: zh-CN
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
X-Client-Version: 2.0.0
```

**必需头部**:
- `Content-Type`: 请求体格式
- `Accept`: 期望响应格式
- `Authorization`: 认证令牌 (需要认证的接口)

**可选头部**:
- `X-Request-ID`: 请求追踪ID
- `X-Client-Version`: 客户端版本
- `Accept-Language`: 语言偏好

#### 3.2.2 请求体

**标准格式**:
```json
{
  "data": {
    "type": "experiment",
    "attributes": {
      "template_id": "titration_naoh_hcl",
      "user_id": "student_001",
      "parameters": {
        "concentration": 0.1
      }
    }
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-06T10:30:00Z"
  }
}
```

### 3.3 响应格式

#### 3.3.1 成功响应

**单个资源**:
```json
{
  "success": true,
  "data": {
    "id": "exp_12345",
    "type": "experiment",
    "attributes": {
      "template_id": "titration_naoh_hcl",
      "status": "running",
      "created_at": "2025-10-06T10:30:00Z"
    },
    "relationships": {
      "user": {
        "data": {
          "id": "student_001",
          "type": "user"
        }
      }
    }
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-06T10:30:01Z",
    "version": "v1"
  }
}
```

**资源列表**:
```json
{
  "success": true,
  "data": [
    {
      "id": "exp_001",
      "type": "experiment",
      "attributes": { /* ... */ }
    },
    {
      "id": "exp_002",
      "type": "experiment",
      "attributes": { /* ... */ }
    }
  ],
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

#### 3.3.2 错误响应

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "实验参数验证失败",
    "details": [
      {
        "field": "parameters.concentration",
        "issue": "必须大于0",
        "value": -0.1
      }
    ],
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "meta": {
    "timestamp": "2025-10-06T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### 3.4 API 端点定义

#### 3.4.1 实验管理 API

**列出实验模板**
```http
GET /api/v1/experiment-templates
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": "titration_naoh_hcl",
      "name": "酸碱滴定实验",
      "category": "titration",
      "difficulty": "beginner",
      "duration_minutes": 30
    }
  ]
}
```

**开始实验**
```http
POST /api/v1/experiments/start
```

**请求体**:
```json
{
  "template_id": "titration_naoh_hcl",
  "user_id": "student_001",
  "parameters": {
    "concentration": 0.1
  }
}
```

**提交步骤**
```http
POST /api/v1/experiments/{session_id}/steps
```

**完成实验**
```http
POST /api/v1/experiments/{session_id}/finish
```

#### 3.4.2 记录管理 API

**查询记录**
```http
GET /api/v1/records?user_id={user_id}&page={page}&page_size={size}
```

**获取记录详情**
```http
GET /api/v1/records/{record_id}
```

**删除记录**
```http
DELETE /api/v1/records/{record_id}
```

#### 3.4.3 报告生成 API

**生成报告**
```http
POST /api/v1/reports/generate
```

**请求体**:
```json
{
  "record_id": "rec_12345",
  "format": "html",
  "options": {
    "include_charts": true,
    "include_raw_data": false
  }
}
```

---

## 4. 事件驱动协议

### 4.1 事件总线架构

```python
from src.core.event_bus import EventBus, Event, EventPriority

# 初始化事件总线
bus = EventBus()

# 订阅事件
bus.subscribe("experiment.started", on_experiment_started)
bus.subscribe("experiment.step_completed", on_step_completed)
bus.subscribe("experiment.completed", on_experiment_completed)

# 发布事件
event = Event(
    name="experiment.started",
    data={"session_id": "exp_001", "user_id": "student_001"},
    priority=EventPriority.HIGH
)
bus.publish(event)
```

### 4.2 事件命名规范

**格式**: `{domain}.{entity}.{action}`

**示例**:
```
实验领域:
- experiment.started          # 实验开始
- experiment.step_completed   # 步骤完成
- experiment.completed        # 实验完成
- experiment.failed           # 实验失败

用户领域:
- user.login                  # 用户登录
- user.logout                 # 用户登出
- user.profile_updated        # 用户信息更新

系统领域:
- system.health_check         # 健康检查
- system.cache_cleared        # 缓存清理
- system.backup_created       # 备份创建
```

### 4.3 事件数据结构

```python
@dataclass
class Event:
    """事件基类"""
    name: str                           # 事件名称
    data: Dict[str, Any]                # 事件数据
    timestamp: datetime                 # 时间戳
    priority: EventPriority             # 优先级
    source: Optional[str] = None        # 来源
    correlation_id: Optional[str] = None  # 关联ID
```

**事件优先级**:
```python
class EventPriority(Enum):
    CRITICAL = 3  # 关键事件 (立即处理)
    HIGH = 2      # 高优先级 (优先处理)
    NORMAL = 1    # 普通事件 (正常处理)
    LOW = 0       # 低优先级 (延后处理)
```

### 4.4 事件订阅模式

#### 4.4.1 同步订阅

```python
def on_experiment_started(event: Event):
    """同步处理实验开始事件"""
    session_id = event.data['session_id']
    logger.info(f"实验已开始: {session_id}")

bus.subscribe("experiment.started", on_experiment_started)
```

#### 4.4.2 异步订阅

```python
async def on_data_processed(event: Event):
    """异步处理数据"""
    await asyncio.sleep(0.1)
    result = await process_data(event.data)
    return result

bus.subscribe("data.processed", on_data_processed)
# 使用 publish_async 发布
await bus.publish_async(event)
```

#### 4.4.3 模式匹配订阅

```python
# 订阅所有实验相关事件
bus.subscribe("experiment.*", on_any_experiment_event)

# 订阅所有事件
bus.subscribe("*", on_any_event)
```

#### 4.4.4 带过滤器订阅

```python
def important_experiments_filter(event: Event) -> bool:
    """只处理重要实验"""
    return event.data.get('priority') == 'high'

bus.subscribe(
    "experiment.started",
    on_important_experiment,
    filter_func=important_experiments_filter
)
```

### 4.5 事件中间件

```python
def logging_middleware(event: Event) -> Event:
    """日志中间件"""
    logger.info(f"事件发布: {event.name}")
    return event

def validation_middleware(event: Event) -> Event:
    """验证中间件"""
    if not event.data:
        return None  # 拦截无效事件
    return event

bus.use_middleware(logging_middleware)
bus.use_middleware(validation_middleware)
```

### 4.6 标准事件列表

#### 4.6.1 实验生命周期事件

| 事件名称 | 触发时机 | 数据字段 |
|---------|---------|---------|
| `experiment.initialized` | 实验初始化完成 | `session_id`, `template_id`, `user_id` |
| `experiment.started` | 实验开始 | `session_id`, `start_time` |
| `experiment.step_completed` | 步骤完成 | `session_id`, `step_index`, `step_data` |
| `experiment.paused` | 实验暂停 | `session_id`, `pause_reason` |
| `experiment.resumed` | 实验恢复 | `session_id` |
| `experiment.completed` | 实验完成 | `session_id`, `record_id`, `score` |
| `experiment.failed` | 实验失败 | `session_id`, `error`, `reason` |

#### 4.6.2 数据事件

| 事件名称 | 触发时机 | 数据字段 |
|---------|---------|---------|
| `data.saved` | 数据保存 | `record_id`, `data_type` |
| `data.updated` | 数据更新 | `record_id`, `changes` |
| `data.deleted` | 数据删除 | `record_id` |
| `data.validated` | 数据验证 | `data`, `validation_result` |

#### 4.6.3 系统事件

| 事件名称 | 触发时机 | 数据字段 |
|---------|---------|---------|
| `system.startup` | 系统启动 | `version`, `config` |
| `system.shutdown` | 系统关闭 | `reason` |
| `system.error` | 系统错误 | `error`, `severity`, `context` |
| `system.health_check` | 健康检查 | `status`, `metrics` |

---

## 5. WebSocket 实时通信

### 5.1 连接协议

**连接URL**:
```
ws://localhost:8080/ws?token={jwt_token}&session_id={session_id}
```

**握手流程**:
```javascript
// 客户端连接
const ws = new WebSocket('ws://localhost:8080/ws?token=xxx');

ws.onopen = () => {
    // 发送认证消息
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'jwt_token_here'
    }));
};
```

### 5.2 消息格式

#### 5.2.1 客户端 → 服务器

```json
{
  "type": "message_type",
  "action": "action_name",
  "data": {
    "key": "value"
  },
  "message_id": "msg_12345",
  "timestamp": "2025-10-06T10:30:00Z"
}
```

#### 5.2.2 服务器 → 客户端

```json
{
  "type": "event",
  "event": "experiment.step_completed",
  "data": {
    "step_index": 2,
    "result": "success"
  },
  "message_id": "msg_12346",
  "timestamp": "2025-10-06T10:30:01Z"
}
```

### 5.3 消息类型

| 类型 | 方向 | 说明 | 示例 |
|------|------|------|------|
| `auth` | C→S | 认证 | 发送JWT令牌 |
| `ping` | C↔S | 心跳 | 保持连接 |
| `subscribe` | C→S | 订阅事件 | 订阅实验事件 |
| `unsubscribe` | C→S | 取消订阅 | 取消订阅 |
| `event` | S→C | 事件推送 | 实验状态变化 |
| `error` | S→C | 错误通知 | 连接错误 |

### 5.4 实时事件推送

```python
# 服务器端发布事件到WebSocket
async def on_experiment_event(event: Event):
    """将事件推送到WebSocket客户端"""
    ws_message = {
        "type": "event",
        "event": event.name,
        "data": event.data,
        "timestamp": event.timestamp.isoformat()
    }

    # 推送给订阅的客户端
    await websocket_server.broadcast(ws_message)
```

### 5.5 心跳机制

```javascript
// 客户端心跳
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000); // 30秒一次

// 服务器响应
ws.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
    }
});
```

---

## 6. 数据格式规范

### 6.1 字段命名规则

| 规则 | 格式 | 示例 | 说明 |
|------|------|------|------|
| **JSON字段** | snake_case | `user_id`, `created_at` | 小写+下划线 |
| **URL参数** | snake_case | `?user_id=123&page_size=20` | 小写+下划线 |
| **HTTP Header** | Kebab-Case | `X-Request-ID` | 首字母大写+连字符 |
| **类名** | PascalCase | `ExperimentController` | 首字母大写 |
| **常量** | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` | 全大写+下划线 |

### 6.2 数据类型规范

| 类型 | JSON类型 | 格式 | 示例 |
|------|---------|------|------|
| **ID** | string | 前缀+下划线+数字/UUID | `exp_12345`, `usr_001` |
| **时间戳** | string | ISO 8601 | `2025-10-06T10:30:00Z` |
| **布尔值** | boolean | true/false | `true` |
| **枚举** | string | 小写+下划线 | `running`, `completed` |
| **金额** | number | 小数点2位 | `99.99` |
| **百分比** | number | 0-100 | `85.5` |

### 6.3 通用数据模型

#### 6.3.1 分页数据

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
    "prev": null,
    "first": "/api/v1/experiments?page=1",
    "last": "/api/v1/experiments?page=8"
  }
}
```

#### 6.3.2 时间戳

```json
{
  "created_at": "2025-10-06T10:30:00Z",
  "updated_at": "2025-10-06T11:00:00Z",
  "deleted_at": null
}
```

#### 6.3.3 关系数据

```json
{
  "id": "exp_001",
  "relationships": {
    "user": {
      "data": { "id": "usr_001", "type": "user" }
    },
    "template": {
      "data": { "id": "tpl_001", "type": "template" }
    }
  }
}
```

---

## 7. 错误码体系

### 7.1 错误码结构

**格式**: `{DOMAIN}_{ERROR_TYPE}_{SPECIFIC}`

```
示例:
- EXP_VAL_001: 实验验证错误001
- AUTH_TOKEN_EXPIRED: 认证令牌过期
- SYS_DB_CONNECTION: 系统数据库连接错误
```

### 7.2 错误码分类

#### 7.2.1 通用错误 (1000-1999)

| 错误码 | 英文 | 中文 | HTTP状态 |
|--------|------|------|---------|
| `1000` | `UNKNOWN_ERROR` | 未知错误 | 500 |
| `1001` | `INVALID_REQUEST` | 无效请求 | 400 |
| `1002` | `MISSING_PARAMETER` | 缺少参数 | 400 |
| `1003` | `INVALID_PARAMETER` | 参数无效 | 400 |
| `1004` | `RESOURCE_NOT_FOUND` | 资源不存在 | 404 |
| `1005` | `RESOURCE_CONFLICT` | 资源冲突 | 409 |
| `1006` | `RATE_LIMIT_EXCEEDED` | 超过限流 | 429 |

#### 7.2.2 认证错误 (2000-2999)

| 错误码 | 英文 | 中文 | HTTP状态 |
|--------|------|------|---------|
| `2000` | `AUTH_REQUIRED` | 需要认证 | 401 |
| `2001` | `AUTH_INVALID_TOKEN` | 令牌无效 | 401 |
| `2002` | `AUTH_TOKEN_EXPIRED` | 令牌过期 | 401 |
| `2003` | `AUTH_INSUFFICIENT_PERMISSION` | 权限不足 | 403 |
| `2004` | `AUTH_USER_NOT_FOUND` | 用户不存在 | 404 |
| `2005` | `AUTH_INVALID_CREDENTIALS` | 凭证无效 | 401 |

#### 7.2.3 实验错误 (3000-3999)

| 错误码 | 英文 | 中文 | HTTP状态 |
|--------|------|------|---------|
| `3000` | `EXP_TEMPLATE_NOT_FOUND` | 模板不存在 | 404 |
| `3001` | `EXP_INVALID_STATE` | 实验状态无效 | 400 |
| `3002` | `EXP_STEP_VALIDATION_FAILED` | 步骤验证失败 | 422 |
| `3003` | `EXP_SAFETY_VIOLATION` | 安全规则违反 | 400 |
| `3004` | `EXP_SESSION_EXPIRED` | 会话过期 | 410 |
| `3005` | `EXP_ALREADY_COMPLETED` | 实验已完成 | 409 |

#### 7.2.4 数据错误 (4000-4999)

| 错误码 | 英文 | 中文 | HTTP状态 |
|--------|------|------|---------|
| `4000` | `DATA_VALIDATION_FAILED` | 数据验证失败 | 422 |
| `4001` | `DATA_SAVE_FAILED` | 数据保存失败 | 500 |
| `4002` | `DATA_CORRUPTED` | 数据损坏 | 500 |
| `4003` | `DATA_DUPLICATE` | 数据重复 | 409 |

#### 7.2.5 系统错误 (5000-5999)

| 错误码 | 英文 | 中文 | HTTP状态 |
|--------|------|------|---------|
| `5000` | `SYS_INTERNAL_ERROR` | 内部错误 | 500 |
| `5001` | `SYS_SERVICE_UNAVAILABLE` | 服务不可用 | 503 |
| `5002` | `SYS_DATABASE_ERROR` | 数据库错误 | 500 |
| `5003` | `SYS_TIMEOUT` | 请求超时 | 504 |

### 7.3 错误响应格式

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
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-06T10:30:00Z",
    "help_url": "https://docs.virtualchemlab.com/errors/3002"
  }
}
```

### 7.4 错误处理最佳实践

```python
from src.utils.error_handler import ValidationError, safe_execute

@safe_execute(context="实验步骤提交", raise_error=True)
def submit_step(step_data: dict):
    """提交实验步骤"""
    # 验证参数
    if not step_data:
        raise ValidationError(
            "步骤数据不能为空",
            code=3002,
            details={"field": "step_data", "issue": "不能为空"}
        )

    # 处理逻辑
    # ...

    return {"success": True}
```

---

## 8. 版本控制策略

### 8.1 版本格式

**语义化版本**: `MAJOR.MINOR.PATCH`

```
v1.2.3
│ │ │
│ │ └─ 补丁版本 (向后兼容的bug修复)
│ └─── 次版本 (向后兼容的新功能)
└───── 主版本 (破坏性变更)
```

### 8.2 API版本策略

#### 8.2.1 URL版本控制

```
/api/v1/experiments      # 版本 1
/api/v2/experiments      # 版本 2
```

#### 8.2.2 Header版本控制

```http
GET /api/experiments HTTP/1.1
Accept: application/vnd.virtualchemlab.v2+json
```

#### 8.2.3 版本生命周期

| 阶段 | 说明 | 时长 | 支持级别 |
|------|------|------|---------|
| **开发中** | 功能开发和测试 | - | 不稳定 |
| **Beta** | 公开测试 | 1-3个月 | 有限支持 |
| **稳定版** | 生产就绪 | 12个月+ | 完全支持 |
| **已废弃** | 不推荐使用 | 6个月 | 维护支持 |
| **已停用** | 不再支持 | - | 无支持 |

### 8.3 兼容性保证

**向后兼容的变更**:
- ✅ 添加新端点
- ✅ 添加可选字段
- ✅ 添加响应字段
- ✅ 放宽验证规则

**破坏性变更** (需要新主版本):
- ❌ 删除端点
- ❌ 删除字段
- ❌ 修改字段类型
- ❌ 严格验证规则
- ❌ 改变行为

### 8.4 废弃流程

```http
GET /api/v1/experiments HTTP/1.1

HTTP/1.1 200 OK
Deprecation: version="v1", date="2025-12-31"
Sunset: Wed, 31 Dec 2025 23:59:59 GMT
Link: </api/v2/experiments>; rel="alternate"
```

---

## 9. 安全与认证

### 9.1 JWT认证

#### 9.1.1 令牌结构

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "student_001",
    "username": "张三",
    "role": "student",
    "permissions": ["experiment:read", "experiment:create"],
    "iat": 1728201000,
    "exp": 1728287400
  },
  "signature": "..."
}
```

#### 9.1.2 认证流程

```python
from src.core.auth import create_token, verify_token, require_auth

# 1. 登录获取令牌
token = create_token({
    "user_id": "student_001",
    "role": "student"
})

# 2. 请求时验证
@require_auth
def protected_endpoint(auth_context):
    user_id = auth_context.user_id
    # 处理请求
```

### 9.2 权限控制 (RBAC)

```python
from src.core.auth import require_permission, Permission

@require_auth
@require_permission(Permission.EXPERIMENT_CREATE)
def create_experiment(auth_context, data):
    """创建实验 (需要创建权限)"""
    pass
```

**权限定义**:
```python
class Permission(Enum):
    EXPERIMENT_READ = "experiment:read"
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_DELETE = "experiment:delete"
    ADMIN_MANAGE = "admin:manage"
```

### 9.3 安全最佳实践

| 实践 | 说明 | 实现 |
|------|------|------|
| **HTTPS** | 加密传输 | 生产环境强制 |
| **令牌过期** | 定期刷新 | 24小时过期 |
| **限流** | 防止滥用 | 100次/分钟 |
| **输入验证** | 防注入 | Pydantic验证 |
| **CORS** | 跨域控制 | 白名单机制 |
| **SQL注入** | 防SQL注入 | 参数化查询 |
| **XSS防护** | 防跨站脚本 | 输出转义 |

---

## 10. 最佳实践

### 10.1 接口设计原则

#### 10.1.1 RESTful 最佳实践

```python
# ✅ 好的设计
GET    /api/v1/experiments              # 列出实验
GET    /api/v1/experiments/{id}         # 获取实验
POST   /api/v1/experiments              # 创建实验
PUT    /api/v1/experiments/{id}         # 更新实验
DELETE /api/v1/experiments/{id}         # 删除实验

# ❌ 不好的设计
GET  /api/v1/getExperiments            # 使用了动词
POST /api/v1/experiment/create         # 使用了动词
GET  /api/v1/experiments?action=delete # 错误的HTTP方法
```

#### 10.1.2 事件设计原则

```python
# ✅ 好的事件设计
Event(
    name="experiment.step_completed",  # 清晰的名称
    data={                             # 充分的上下文
        "session_id": "exp_001",
        "step_index": 2,
        "step_name": "添加试剂",
        "result": "success",
        "timestamp": "2025-10-06T10:30:00Z"
    },
    priority=EventPriority.HIGH
)

# ❌ 不好的事件设计
Event(
    name="step",                       # 名称不清晰
    data={"i": 2},                     # 上下文不足
)
```

### 10.2 性能优化

#### 10.2.1 缓存策略

```http
# 响应头
Cache-Control: public, max-age=3600
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

#### 10.2.2 分页优化

```python
# 使用游标分页 (大数据集)
GET /api/v1/records?cursor=eyJpZCI6MTIzfQ&limit=20

# 使用页码分页 (小数据集)
GET /api/v1/records?page=1&page_size=20
```

#### 10.2.3 字段过滤

```python
# 只返回需要的字段
GET /api/v1/experiments?fields=id,name,status
```

### 10.3 错误处理

```python
# 提供有用的错误信息
{
  "error": {
    "code": 3002,
    "message": "步骤验证失败",
    "details": [
      {
        "field": "volume",
        "issue": "必须在0-100之间",
        "value": 150,
        "suggested": 50
      }
    ],
    "help_url": "https://docs.virtualchemlab.com/errors/3002"
  }
}
```

### 10.4 文档规范

```python
def create_experiment(template_id: str, user_id: str) -> dict:
    """
    创建新实验

    Args:
        template_id: 实验模板ID
        user_id: 用户ID

    Returns:
        包含session_id的字典

    Raises:
        ValidationError: 参数验证失败
        ResourceNotFoundError: 模板不存在

    Example:
        >>> result = create_experiment("titration_naoh_hcl", "student_001")
        >>> print(result['session_id'])
        'exp_12345'
    """
    pass
```

---

## 附录

### A. 完整示例

#### A.1 REST API 完整流程

```python
import requests

# 1. 登录获取令牌
response = requests.post('http://localhost:8080/api/v1/auth/login', json={
    'username': 'student_001',
    'password': 'password'
})
token = response.json()['data']['token']

# 2. 创建实验
headers = {'Authorization': f'Bearer {token}'}
response = requests.post(
    'http://localhost:8080/api/v1/experiments',
    headers=headers,
    json={
        'template_id': 'titration_naoh_hcl',
        'user_id': 'student_001'
    }
)
session_id = response.json()['data']['session_id']

# 3. 提交步骤
response = requests.post(
    f'http://localhost:8080/api/v1/experiments/{session_id}/steps',
    headers=headers,
    json={'step_data': {'confirmed': True}}
)

# 4. 完成实验
response = requests.post(
    f'http://localhost:8080/api/v1/experiments/{session_id}/finish',
    headers=headers
)
record_id = response.json()['data']['record_id']
```

#### A.2 事件驱动完整流程

```python
from src.core.event_bus import EventBus, Event, EventPriority

# 初始化
bus = EventBus()

# 订阅事件
@bus.subscribe("experiment.step_completed")
def on_step_completed(event: Event):
    print(f"步骤{event.data['step_index']}完成")

@bus.subscribe("experiment.completed", priority=EventPriority.HIGH)
def on_experiment_completed(event: Event):
    print(f"实验完成，记录ID: {event.data['record_id']}")

# 发布事件
bus.publish(Event(
    name="experiment.step_completed",
    data={"step_index": 1, "session_id": "exp_001"}
))

bus.publish(Event(
    name="experiment.completed",
    data={"session_id": "exp_001", "record_id": "rec_001"}
))
```

### B. 相关文档

- [REST API参考](./API_REFERENCE.md)
- [事件列表](./EVENT_CATALOG.md)
- [错误码完整列表](./ERROR_CODES.md)
- [安全指南](./SECURITY_GUIDE.md)

---

**文档版本**: v2.0.0
**最后更新**: 2025年10月6日
**维护者**: VirtualChemLab团队

**📞 需要帮助?**
- 📧 Email: support@virtualchemlab.com
- 📚 文档: https://docs.virtualchemlab.com
- 💬 Issues: https://github.com/virtualchemlab/issues
