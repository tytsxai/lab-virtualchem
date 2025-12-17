# VirtualChemLab API 文档

## 概述

VirtualChemLab API 提供了完整的 RESTful 接口，支持实验管理、用户管理、数据记录等功能。

## 基础信息

- **基础URL**: <http://localhost:8000>
- **API版本**: 2.0.0
- **认证方式**: API Key（`X-API-Key` / `Authorization: Bearer`）
- **数据格式**: JSON

## 认证

所有 API 请求都需要在请求头中包含有效的 API Key（推荐使用 `X-API-Key`）：

```text
X-API-Key: <your-api-key>
```

也支持使用 `Authorization` 头：

```text
Authorization: Bearer <your-api-key>
```

### 获取 API Key

- 生产/CI：显式设置环境变量 `VCL_API_KEYS="key1,key2"`（逗号分隔，可配置多把）。
- 本机开发：首次启动 API 服务时，如果未配置 `VCL_API_KEYS`，会自动生成并写入 `~/.virtualchemlab/api_key.txt`。

## 端点列表

### 实验管理

#### GET /api/experiments

获取实验列表

**参数**:

- `page` (integer, optional): 页码，默认1
- `size` (integer, optional): 每页大小，默认10
- `level` (string, optional): 难度等级过滤
- `status` (string, optional): 状态过滤

**响应**:

```json
{
  "success": true,
  "data": {
    "experiments": [
      {
        "id": "exp_001",
        "name": "pH滴定实验",
        "description": "测试pH值",
        "level": "basic",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 10,
      "total": 100,
      "pages": 10
    }
  },
  "message": "获取成功"
}
```

#### POST /api/experiments

创建新实验

**请求体**:

```json
{
  "name": "pH滴定实验",
  "description": "测试pH值",
  "level": "basic",
  "template_id": "template_001"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "id": "exp_001",
    "name": "pH滴定实验",
    "description": "测试pH值",
    "level": "basic",
    "status": "draft",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "message": "创建成功"
}
```

#### GET /api/experiments/{id}

获取实验详情

**参数**:

- `id` (string, required): 实验ID

**响应**:

```json
{
  "success": true,
  "data": {
    "id": "exp_001",
    "name": "pH滴定实验",
    "description": "测试pH值",
    "level": "basic",
    "status": "active",
    "steps": [
      {
        "id": "step_1",
        "text": "准备试剂",
        "order": 1,
        "completed": false
      }
    ],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "message": "获取成功"
}
```

#### PUT /api/experiments/{id}

更新实验

**参数**:

- `id` (string, required): 实验ID

**请求体**:

```json
{
  "name": "更新的实验名称",
  "description": "更新的描述",
  "level": "intermediate"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "id": "exp_001",
    "name": "更新的实验名称",
    "description": "更新的描述",
    "level": "intermediate",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "message": "更新成功"
}
```

#### DELETE /api/experiments/{id}

删除实验

**参数**:

- `id` (string, required): 实验ID

**响应**:

```json
{
  "success": true,
  "message": "删除成功"
}
```

### 实验执行

#### POST /api/experiments/{id}/start

开始实验

**参数**:

- `id` (string, required): 实验ID

**响应**:

```json
{
  "success": true,
  "data": {
    "session_id": "session_001",
    "current_step": 1,
    "total_steps": 5,
    "started_at": "2024-01-01T00:00:00Z"
  },
  "message": "实验已开始"
}
```

#### POST /api/experiments/{id}/steps/{step_id}/submit

提交实验步骤

**参数**:

- `id` (string, required): 实验ID
- `step_id` (string, required): 步骤ID

**请求体**:

```json
{
  "data": {
    "volume": 25.0,
    "confirmed": true
  }
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "passed": true,
    "message": "步骤完成",
    "next_step": 2
  },
  "message": "提交成功"
}
```

#### POST /api/experiments/{id}/complete

完成实验

**参数**:

- `id` (string, required): 实验ID

**响应**:

```json
{
  "success": true,
  "data": {
    "score": 85,
    "completion_time": "00:45:30",
    "mistakes": 2,
    "completed_at": "2024-01-01T00:45:30Z"
  },
  "message": "实验完成"
}
```

### 用户管理

#### GET /api/users

获取用户列表

**参数**:

- `page` (integer, optional): 页码，默认1
- `size` (integer, optional): 每页大小，默认10
- `role` (string, optional): 角色过滤

**响应**:

```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "user_001",
        "username": "testuser",
        "email": "test@example.com",
        "role": "student",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 10,
      "total": 50,
      "pages": 5
    }
  },
  "message": "获取成功"
}
```

#### POST /api/users

创建新用户

**请求体**:

```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "role": "student"
}
```

**响应**:

```json
{
  "success": true,
  "data": {
    "id": "user_002",
    "username": "newuser",
    "email": "newuser@example.com",
    "role": "student",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "message": "创建成功"
}
```

#### GET /api/users/{id}

获取用户详情

**参数**:

- `id` (string, required): 用户ID

**响应**:

```json
{
  "success": true,
  "data": {
    "id": "user_001",
    "username": "testuser",
    "email": "test@example.com",
    "role": "student",
    "experiments_count": 10,
    "created_at": "2024-01-01T00:00:00Z"
  },
  "message": "获取成功"
}
```

### 实验记录

#### GET /api/records

获取实验记录

**参数**:

- `page` (integer, optional): 页码，默认1
- `size` (integer, optional): 每页大小，默认10
- `user_id` (string, optional): 用户ID过滤
- `experiment_id` (string, optional): 实验ID过滤

**响应**:

```json
{
  "success": true,
  "data": {
    "records": [
      {
        "id": "record_001",
        "user_id": "user_001",
        "experiment_id": "exp_001",
        "score": 85,
        "completion_rate": 0.9,
        "duration": "00:45:30",
        "completed_at": "2024-01-01T00:45:30Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 10,
      "total": 200,
      "pages": 20
    }
  },
  "message": "获取成功"
}
```

#### GET /api/records/{id}

获取实验记录详情

**参数**:

- `id` (string, required): 记录ID

**响应**:

```json
{
  "success": true,
  "data": {
    "id": "record_001",
    "user_id": "user_001",
    "experiment_id": "exp_001",
    "score": 85,
    "completion_rate": 0.9,
    "duration": "00:45:30",
    "mistakes": [
      {
        "step_id": "step_2",
        "error_type": "validation_failed",
        "description": "体积超出范围",
        "severity": "warning"
      }
    ],
    "step_records": [
      {
        "step_id": "step_1",
        "passed": true,
        "attempts": 1,
        "completed_at": "2024-01-01T00:10:00Z"
      }
    ],
    "completed_at": "2024-01-01T00:45:30Z"
  },
  "message": "获取成功"
}
```

### 系统管理

#### GET /api/health

健康检查

**响应**:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "2.0.0",
    "services": {
      "database": "healthy",
      "cache": "healthy",
      "queue": "healthy"
    }
  },
  "message": "系统健康"
}
```

#### GET /api/metrics

获取系统指标

**响应**:

```json
{
  "success": true,
  "data": {
    "requests_total": 1000,
    "requests_per_second": 10.5,
    "response_time_avg": 150.2,
    "error_rate": 0.02,
    "active_users": 25,
    "memory_usage": 0.65,
    "cpu_usage": 0.45
  },
  "message": "获取成功"
}
```

#### GET /api/logs

获取系统日志

**参数**:

- `level` (string, optional): 日志级别
- `limit` (integer, optional): 限制数量，默认100

**响应**:

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2024-01-01T00:00:00Z",
        "level": "INFO",
        "message": "用户登录成功",
        "user_id": "user_001",
        "ip": "192.168.1.100"
      }
    ],
    "total": 1000
  },
  "message": "获取成功"
}
```

## 数据模式

### Experiment

实验信息

| 属性名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| id | string | 是 | 实验ID |
| name | string | 是 | 实验名称 |
| description | string | 否 | 实验描述 |
| level | string | 是 | 难度等级 |
| status | string | 否 | 实验状态 |
| created_at | string | 否 | 创建时间 |
| updated_at | string | 否 | 更新时间 |

**示例**:

```json
{
  "id": "exp_001",
  "name": "pH滴定实验",
  "description": "测试pH值",
  "level": "basic",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### User

用户信息

| 属性名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| id | string | 是 | 用户ID |
| username | string | 是 | 用户名 |
| email | string | 是 | 邮箱 |
| role | string | 否 | 用户角色 |
| created_at | string | 否 | 创建时间 |

**示例**:

```json
{
  "id": "user_001",
  "username": "testuser",
  "email": "test@example.com",
  "role": "student",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Record

实验记录

| 属性名 | 类型 | 必需 | 描述 |
|--------|------|------|------|
| id | string | 是 | 记录ID |
| user_id | string | 是 | 用户ID |
| experiment_id | string | 是 | 实验ID |
| score | integer | 否 | 得分 |
| completion_rate | float | 否 | 完成率 |
| duration | string | 否 | 持续时间 |
| completed_at | string | 否 | 完成时间 |

**示例**:

```json
{
  "id": "record_001",
  "user_id": "user_001",
  "experiment_id": "exp_001",
  "score": 85,
  "completion_rate": 0.9,
  "duration": "00:45:30",
  "completed_at": "2024-01-01T00:45:30Z"
}
```

## 错误代码

| 代码 | 描述 |
|------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源未找到 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 500 | 服务器内部错误 |

## 示例

### 创建实验

```bash
curl -X POST "http://localhost:8000/api/experiments" \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "pH滴定实验",
    "description": "测试pH值",
    "level": "basic",
    "template_id": "template_001"
  }'
```

### 获取实验列表

```bash
curl -X GET "http://localhost:8000/api/experiments?page=1&size=10&level=basic" \
  -H "X-API-Key: <your-api-key>"
```

### 开始实验

```bash
curl -X POST "http://localhost:8000/api/experiments/exp_001/start" \
  -H "X-API-Key: <your-api-key>"
```

### 提交实验步骤

```bash
curl -X POST "http://localhost:8000/api/experiments/exp_001/steps/step_1/submit" \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "volume": 25.0,
      "confirmed": true
    }
  }'
```

### 完成实验

```bash
curl -X POST "http://localhost:8000/api/experiments/exp_001/complete" \
  -H "X-API-Key: <your-api-key>"
```

## 更新日志

### v2.0.0 (2024-01-01)

- 初始版本发布
- 支持实验管理
- 支持用户管理
- 支持数据记录
- 支持系统监控

## 支持

如果您在使用API时遇到问题，请：

1. 查看本文档
2. 检查错误代码
3. 联系技术支持: <support@virtualchemlab.com>
