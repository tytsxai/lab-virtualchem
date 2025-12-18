# VirtualChemLab HTTP API（REST / Admin）

> 本文档对齐当前代码实现：`src/api/server.py`（REST API）与 `src/api/admin_api.py`（管理后台 API）。
> 如需查看 OpenAPI JSON，可访问 REST API 的 `/api/docs`。

## 1. REST API（实验/记录/报告）

### 1.1 基础信息

- 默认地址：`http://127.0.0.1:8080`
- 启动方式：`python -m src.api.server`
- 监听地址：通过环境变量 `VCL_API_HOST` 指定（默认 `127.0.0.1`）
- 认证：API Key（`X-API-Key` 或 `Authorization: Bearer`）
- CORS：默认仅允许本机回环来源（见 1.3）

> 说明：当前 REST API 基于 Python 标准库 `HTTPServer` 实现，适合本机集成与开发调试；如需生产级对外服务，建议在反向代理/容器编排下运行并补齐进程管理、TLS、限流与观测，或迁移到 FastAPI/Flask 等更适合服务化的框架。

### 1.2 认证（API Key）

除以下端点外，其余均需要 API Key：

- `GET /api/health`
- `GET /api/ready`
- `GET /healthz`
- `GET /readyz`
- `GET /api/docs`

请求头任选一种：

```text
X-API-Key: <your-api-key>
```

或：

```text
Authorization: Bearer <your-api-key>
```

获取/配置 API Key：

- 生产/CI：必须显式提供 API Key（推荐环境变量 `VCL_API_KEYS="key1,key2"`，逗号分隔可多把）；缺失时服务会拒绝启动（避免多副本密钥漂移）。实现上也支持通过用户配置文件 `~/.virtualchemlab/config.json` 的 `security.api_key` 提供，但不建议在生产将密钥落盘到可被打包/镜像/备份带走的位置。
- 本机开发：首次启动 API 服务时，如果未配置 `VCL_API_KEYS`，会自动生成并写入 `~/.virtualchemlab/api_key.txt`（同时写入 `~/.virtualchemlab/config.json`）。

### 1.3 CORS（浏览器跨域访问）

安全默认值：REST API 仅允许本机回环来源（`localhost/127.0.0.1/::1`）。

如需浏览器跨域调用，请显式配置：

- `VCL_API_CORS_ORIGINS`：逗号分隔允许列表，例如：
  - `VCL_API_CORS_ORIGINS=https://app.example.com,https://admin.example.com`

未配置时，非本机回环 Origin 的请求会因缺少 `Access-Control-Allow-Origin` 而被浏览器拦截。

### 1.4 端点一览

#### 健康检查 / 文档（无需认证）

- `GET /api/health`
- `GET /api/ready`（就绪：模板/存储可用性；失败返回 503）
- `GET /healthz`（部署探针：包含构建信息与磁盘可写探测；失败返回 503）
- `GET /readyz`（部署探针：可选探测 DB/缓存；失败返回 503）
- `GET /api/docs`（OpenAPI JSON）

#### 监控（默认需要认证）

- `GET /metrics`：Prometheus 文本格式指标（建议在反向代理/采集侧统一做鉴权与访问控制）

示例：

```bash
curl http://127.0.0.1:8080/api/health
curl http://127.0.0.1:8080/api/docs
```

#### 实验

- `GET /api/experiments`：列出可用实验模板
- `GET /api/experiments/{experiment_id}`：获取实验详情（含步骤与评分规则）
- `POST /api/experiments/start`：开始实验会话
- `POST /api/experiments/submit`：提交当前步骤
- `POST /api/experiments/finish`：完成实验并生成记录

示例：列出实验

```bash
curl -H "X-API-Key: <key>" \
  http://127.0.0.1:8080/api/experiments
```

示例：开始实验

```bash
curl -X POST \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"experiment_id":"exp_001","user_id":"alice"}' \
  http://127.0.0.1:8080/api/experiments/start
```

示例：提交步骤

```bash
curl -X POST \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","data":{"confirmed":true}}' \
  http://127.0.0.1:8080/api/experiments/submit
```

响应关键字段：

- `passed`：是否通过
- `message`：提示信息
- `has_next_step`：是否已进入下一步（失败或最后一步会为 `false`）
- `current_step`：当前步骤（实验完成时为 `null`）
- `progress`：进度信息

示例：完成实验

```bash
curl -X POST \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>"}' \
  http://127.0.0.1:8080/api/experiments/finish
```

#### 记录

- `GET /api/records?user_id=<optional>`：列出记录（可选按 user 过滤）
- `GET /api/records/{record_id}?user_id=<optional>`：获取记录详情

> 建议：如果你已知 `user_id`，在查询单条记录时携带 `?user_id=...` 可以避免全量扫描。

示例：列出记录

```bash
curl -H "X-API-Key: <key>" \
  "http://127.0.0.1:8080/api/records?user_id=alice"
```

示例：获取记录详情

```bash
curl -H "X-API-Key: <key>" \
  "http://127.0.0.1:8080/api/records/<record_id>?user_id=alice"
```

#### 报告

- `POST /api/reports/generate`：生成报告（当前支持 `html`）

请求体：

```json
{
  "record_id": "<record_id>",
  "format": "html"
}
```

行为：

- 默认会将报告写入 `reports/<record_id>.html`
- 同时在响应中返回 `content`（HTML 字符串）与 `path`
- 响应中的 `url` 是一个**相对路径提示**（`/reports/<record_id>.html`）。当前 stdlib `HTTPServer` 实现不会自动托管 `reports/` 静态文件：如需通过浏览器访问，请自行在反向代理/静态服务器中映射该目录，或直接打开 `path` 指向的本地文件。

示例：

```bash
curl -X POST \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"record_id":"<record_id>","format":"html"}' \
  http://127.0.0.1:8080/api/reports/generate
```

### 1.5 错误响应

错误时返回统一结构（示例）：

```json
{
  "success": false,
  "error": {
    "message": "未授权: 无效的API密钥",
    "status": 401,
    "timestamp": "2025-12-18T12:00:00.000000"
  }
}
```

---

## 2. 管理后台 API（许可证/设备/审计）

管理后台后端实现：`src/api/admin_api.py`，启动脚本：`python tools/admin_server_start.py`。

### 2.1 认证

管理后台敏感接口需要提供共享密钥：

- `X-Admin-Secret: <secret>`
- 或 `Authorization: Bearer <secret>`

密钥来源：

- 生产环境：必须设置 `VCL_ADMIN_SECRET_KEY`（建议长度 >= 32）。
- 开发环境：若未设置，启动脚本会生成临时密钥并写入 `~/.virtualchemlab/admin_secret.txt`（不会在日志中打印明文）。

### 2.2 CORS

管理后台 API 默认不启用 CORS（安全默认值）。

如需浏览器跨域访问，请显式设置：

- `VCL_ADMIN_CORS_ORIGINS`：逗号分隔允许列表（开发环境可用 `*`，不建议生产使用）
