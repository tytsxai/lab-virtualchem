# 📚 接口与事件协议 - 文档索引

> VirtualChemLab 通信协议完整文档导航

**版本**: v2.0.0
**最后更新**: 2025年12月17日

---

## ⚠️ 重要说明（维护安全）

本仓库同时存在两类“协议/接口”文档：

1. **当前实现对齐的权威说明**（推荐优先阅读）
   - `docs/API.md`：HTTP REST / Admin API（与 `src/api/server.py`、`src/api/admin_api.py` 对齐）
2. **历史材料 / 规划性协议**（可能与当前实现不一致）
   - `docs/API_EVENT_PROTOCOL.md`
   - `docs/API_PROTOCOL_QUICK_REFERENCE.md`

特别注意：当前 `src/api/server.py` 中 WebSocket 升级处理为占位实现（返回 501），因此任何 WebSocket 章节不应被视为生产契约。

---

## 🎯 快速导航

### 新手入门 (5分钟)

1. **[快速参考卡](./API_PROTOCOL_QUICK_REFERENCE.md)** ⭐ 推荐
   - 最常用的API和事件
   - 快速查找表
   - 代码片段

2. **[使用示例](./API_USAGE_EXAMPLES.md)**
   - 可阅读的示例代码
   - 常见调用模式
   - 错误处理与最佳实践

### 深入学习 (30分钟)

3. **[完整协议规范](./API_EVENT_PROTOCOL.md)** 📖 详细
   - REST API规范
   - 事件驱动协议
   - WebSocket 实时通信（规划/历史材料）
   - 错误码体系
   - 版本控制策略

---

## 📂 文档结构

```
docs/
├── API_EVENT_PROTOCOL.md              # 完整协议规范 (主文档)
├── API_PROTOCOL_QUICK_REFERENCE.md    # 快速参考卡
├── PROTOCOL_INDEX.md                  # 本文档 (索引)
├── API_REFERENCE.md                   # API接口参考
├── API_USAGE_EXAMPLES.md              # API 使用示例
├── EVENT_CATALOG.md                   # 事件目录
├── ERROR_CODES.md                     # 错误码完整列表
└── SECURITY_GUIDE.md                  # 安全指南
```

---

## 📖 核心文档

### 1. 完整协议规范 📘

**文件**: [API_EVENT_PROTOCOL.md](./API_EVENT_PROTOCOL.md)

**内容**:
- ✅ 协议概述与设计原则
- ✅ 通信方式对比与选择
- ✅ REST API完整规范
- ✅ 事件驱动协议
- ✅ WebSocket实时通信
- ✅ 数据格式规范
- ✅ 错误码体系
- ✅ 版本控制策略
- ✅ 安全与认证
- ✅ 最佳实践

**阅读时间**: 30-60分钟
**适合人群**: 开发者、架构师

**章节导航**:
1. [协议概述](#1-协议概述)
2. [通信方式](#2-通信方式)
3. [REST API 接口规范](#3-rest-api-接口规范)
4. [事件驱动协议](#4-事件驱动协议)
5. [WebSocket 实时通信](#5-websocket-实时通信)
6. [数据格式规范](#6-数据格式规范)
7. [错误码体系](#7-错误码体系)
8. [版本控制策略](#8-版本控制策略)
9. [安全与认证](#9-安全与认证)
10. [最佳实践](#10-最佳实践)

---

### 2. 快速参考卡 📋

**文件**: [API_PROTOCOL_QUICK_REFERENCE.md](./API_PROTOCOL_QUICK_REFERENCE.md)

**内容**:
- ✅ 快速开始代码
- ✅ 通信方式对照表
- ✅ REST API速查表
- ✅ 事件总线速查表
- ✅ 错误码速查表
- ✅ 认证速查表
- ✅ 数据格式速查表
- ✅ 版本控制速查表
- ✅ WebSocket速查表
- ✅ 最佳实践检查清单

**阅读时间**: 5-10分钟
**适合人群**: 所有开发者

**快速查找**:
- [REST API速查](#rest-api-速查)
- [事件总线速查](#事件总线速查)
- [错误码速查](#错误码速查)
- [认证速查](#认证速查)

---

### 3. 示例与联调入口 💻

**推荐入口**:

1. `docs/API_USAGE_EXAMPLES.md`（可直接阅读）
2. `examples/api_integration_example.py`（更接近可运行示例，需依赖已安装）

---

## 🔍 按主题查找

### REST API

| 主题 | 文档位置 | 页面 |
|------|---------|------|
| URL设计规范 | 完整协议 - 3.1.1 | p.5 |
| HTTP方法 | 完整协议 - 3.1.2 | p.5 |
| 状态码规范 | 完整协议 - 3.1.3 | p.6 |
| 请求格式 | 完整协议 - 3.2 | p.7 |
| 响应格式 | 完整协议 - 3.3 | p.8 |
| API端点 | 完整协议 - 3.4 | p.10 |
| 快速参考 | 快速参考 - REST API | p.2 |

### 事件总线

| 主题 | 文档位置 | 页面 |
|------|---------|------|
| 事件架构 | 完整协议 - 4.1 | p.12 |
| 命名规范 | 完整协议 - 4.2 | p.13 |
| 数据结构 | 完整协议 - 4.3 | p.14 |
| 订阅模式 | 完整协议 - 4.4 | p.15 |
| 中间件 | 完整协议 - 4.5 | p.17 |
| 标准事件 | 完整协议 - 4.6 | p.18 |
| 快速参考 | 快速参考 - 事件总线 | p.3 |

### 错误处理

| 主题 | 文档位置 | 页面 |
|------|---------|------|
| 错误码结构 | 完整协议 - 7.1 | p.22 |
| 错误码分类 | 完整协议 - 7.2 | p.22 |
| 错误响应格式 | 完整协议 - 7.3 | p.25 |
| 处理最佳实践 | 完整协议 - 7.4 | p.26 |
| 快速参考 | 快速参考 - 错误码 | p.4 |

### 认证与安全

| 主题 | 文档位置 | 页面 |
|------|---------|------|
| JWT认证 | 完整协议 - 9.1 | p.28 |
| 权限控制 | 完整协议 - 9.2 | p.29 |
| 安全最佳实践 | 完整协议 - 9.3 | p.30 |
| 快速参考 | 快速参考 - 认证 | p.5 |

### WebSocket

| 主题 | 文档位置 | 页面 |
|------|---------|------|
| 连接协议 | 完整协议 - 5.1 | p.19 |
| 消息格式 | 完整协议 - 5.2 | p.19 |
| 消息类型 | 完整协议 - 5.3 | p.20 |
| 事件推送 | 完整协议 - 5.4 | p.20 |
| 心跳机制 | 完整协议 - 5.5 | p.21 |
| 快速参考 | 快速参考 - WebSocket | p.6 |

---

## 💡 常见任务

### 如何...

#### 1. 调用REST API?

**参考**: [完整协议 - 3.4](./API_EVENT_PROTOCOL.md#34-api-端点定义) 或 [快速参考](./API_PROTOCOL_QUICK_REFERENCE.md#rest-api-速查)

```python
from src.api.client import VirtualChemLabClient

client = VirtualChemLabClient("http://localhost:8080")
experiments = client.list_experiments()
```

#### 2. 订阅事件?

**参考**: [完整协议 - 4.4](./API_EVENT_PROTOCOL.md#44-事件订阅模式) 或 [快速参考](./API_PROTOCOL_QUICK_REFERENCE.md#事件总线速查)

```python
from src.core.event_bus import get_event_bus

bus = get_event_bus()
bus.subscribe("experiment.started", handler)
```

#### 3. 处理错误?

**参考**: [完整协议 - 7](./API_EVENT_PROTOCOL.md#7-错误码体系) 或 [快速参考](./API_PROTOCOL_QUICK_REFERENCE.md#错误码速查)

```python
from src.utils.error_handler import safe_execute, ValidationError

@safe_execute(context="操作", default_return=None)
def my_function():
    # 你的代码
    pass
```

#### 4. 实现认证?

**参考**: [完整协议 - 9](./API_EVENT_PROTOCOL.md#9-安全与认证) 或 [快速参考](./API_PROTOCOL_QUICK_REFERENCE.md#认证速查)

```python
from src.core.auth import require_auth, create_token

token = create_token({"user_id": "123", "role": "student"})

@require_auth
def protected_endpoint(auth_context):
    # 受保护的端点
    pass
```

#### 5. 使用WebSocket?

**参考**: [完整协议 - 5](./API_EVENT_PROTOCOL.md#5-websocket-实时通信) 或 [快速参考](./API_PROTOCOL_QUICK_REFERENCE.md#websocket速查)

```javascript
const ws = new WebSocket('ws://localhost:8080/ws?token=xxx');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到:', data);
};
```

---

## 🎓 学习路径

### 初学者 (第1天)

**目标**: 了解基本概念，能够调用API和订阅事件

1. ✅ 阅读 [快速参考卡](./API_PROTOCOL_QUICK_REFERENCE.md) (10分钟)
2. ✅ 浏览 [API 使用示例](./API_USAGE_EXAMPLES.md) (10分钟)
3. ✅ 浏览 REST API章节 (15分钟)
4. ✅ 浏览 事件总线章节 (15分钟)
5. ✅ 练习基本API调用 (30分钟)

**预期成果**:
- 理解REST API基本概念
- 会订阅和发布事件
- 能调用简单接口

### 中级开发者 (第2-3天)

**目标**: 掌握完整协议，能够处理错误和实现认证

1. ✅ 精读 [完整协议规范](./API_EVENT_PROTOCOL.md) (60分钟)
2. ✅ 学习错误处理 (30分钟)
3. ✅ 学习认证授权 (30分钟)
4. ✅ 实践异步事件 (60分钟)
5. ✅ 实现完整流程 (120分钟)

**预期成果**:
- 能够设计符合规范的API
- 掌握事件驱动架构
- 能够处理各种错误场景
- 实现安全认证

### 高级开发者 (第4-5天)

**目标**: 深入理解协议设计，能够扩展和优化

1. ✅ 研究版本控制策略 (60分钟)
2. ✅ 学习WebSocket实现 (60分钟)
3. ✅ 性能优化实践 (120分钟)
4. ✅ 设计新接口 (180分钟)
5. ✅ 代码审查和重构 (120分钟)

**预期成果**:
- 能够设计高性能API
- 理解版本演进策略
- 掌握WebSocket实时通信
- 能够进行架构优化

---

## 📚 相关资源

### 项目内部文档

| 文档 | 说明 |
|------|------|
| [架构文档](./ARCHITECTURE.md) | 系统架构设计 |
| [开发者指南](./DEVELOPER.md) | 开发流程与实践 |
| [高级特性](./ADVANCED_FEATURES.md) | 高级功能文档 |
| [故障排除](./TROUBLESHOOTING.md) | 常见问题与排障 |

### 外部参考

| 资源 | 链接 | 说明 |
|------|------|------|
| REST API设计 | [REST API Tutorial](https://restfulapi.net/) | REST最佳实践 |
| 事件驱动架构 | [Martin Fowler](https://martinfowler.com/articles/201701-event-driven.html) | 事件驱动设计 |
| JWT认证 | [JWT.io](https://jwt.io/) | JWT官方文档 |
| WebSocket | [MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket) | WebSocket文档 |

### 代码示例

| 示例 | 文件 | 说明 |
|------|------|------|
| API 集成 | [api_integration_example.py](../examples/api_integration_example.py) | API 调用示例 |
| 系统示例 | [refactored_system_examples.py](../examples/refactored_system_examples.py) | 模块调用示例 |
| API客户端 | [src/api/client.py](../src/api/client.py) | API客户端实现 |
| API服务器 | [src/api/server.py](../src/api/server.py) | API服务器实现 |

---

## 🔄 文档更新记录

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v2.0.0 | 2025-10-06 | 初始版本，完整协议规范 |
| | | - REST API规范 |
| | | - 事件驱动协议 |
| | | - WebSocket通信 |
| | | - 错误码体系 |
| | | - 版本控制策略 |
| | | - 安全与认证 |

---

## 📞 获取帮助

### 文档问题

如果文档有不清楚的地方:

1. 查看 [快速参考卡](./API_PROTOCOL_QUICK_REFERENCE.md)
2. 阅读 [API 使用示例](./API_USAGE_EXAMPLES.md)
3. 查阅 [完整协议规范](./API_EVENT_PROTOCOL.md)
4. 提交 Issue

### 技术支持

- 📧 Email: support@virtualchemlab.com
- 📚 文档: https://docs.virtualchemlab.com
- 💬 Issues: https://github.com/virtualchemlab/issues

---

## ✅ 快速检查清单

### REST API实现

- [ ] URL遵循命名规范
- [ ] 使用正确的HTTP方法
- [ ] 返回正确的状态码
- [ ] 实现标准响应格式
- [ ] 添加错误处理
- [ ] 实现认证授权
- [ ] 添加API版本控制
- [ ] 实现分页
- [ ] 添加缓存
- [ ] 实现限流

### 事件总线使用

- [ ] 使用清晰的事件命名
- [ ] 提供充分的上下文数据
- [ ] 设置合适的优先级
- [ ] 避免循环依赖
- [ ] 处理异步错误
- [ ] 记录事件日志
- [ ] 使用中间件
- [ ] 清理事件历史

### 错误处理

- [ ] 使用标准错误码
- [ ] 提供详细错误信息
- [ ] 包含trace_id
- [ ] 记录错误日志
- [ ] 返回合适的HTTP状态码
- [ ] 提供帮助链接

---

**文档维护者**: VirtualChemLab团队
**创建日期**: 2025年10月6日
**文档版本**: v2.0.0

---

## 🎯 下一步

1. **新手**: 阅读 [快速参考卡](./API_PROTOCOL_QUICK_REFERENCE.md)
2. **开发者**: 精读 [完整协议规范](./API_EVENT_PROTOCOL.md)
3. **实践**: 运行 [API 集成示例](../examples/api_integration_example.py)
4. **深入**: 研究相关架构与故障排除文档

**祝学习愉快!** 🚀
