# VirtualChemLab 文档

欢迎使用 VirtualChemLab 虚拟化学实验室！

## 目录

- [快速开始](#快速开始) — 最小可行的环境搭建步骤与快捷链接
- [用户指南](#用户指南) — 实验、模板和权限等常见操作
- [开发者文档](#开发者文档) — 模块结构、编码规范和测试方式
- [API文档](#api文档) — REST API 概览与示例
- [部署指南](#部署指南) — Docker/K8s/传统部署与配置要点
- [故障排除](#故障排除) — 常见问题、日志分析与支持渠道
- [文档维护状态](DOCS_STATUS.md) — 哪些文档是当前事实来源

## 快速开始

> ✅ TL;DR：阅读根目录下的 `QUICK_START.md`（English）或 `README_快速开始.md`（中文），并使用 `QUICK_START_GUIDE.md` + `QUICK_START_COMPLETION.md` 获得全流程指引与检查清单。

### 系统要求

- Python 3.10+（推荐 3.11）
- Windows 10/11, macOS 10.15+, 或 Linux
- 至少 4GB RAM
- 1GB 可用磁盘空间

### 安装

1. 克隆项目

   ```bash
   git clone https://github.com/tytsxai/VirtualChemLab.git
   cd VirtualChemLab
   ```

2. 创建虚拟环境

   ```bash
   python3.11 -m venv venv311
   source venv311/bin/activate     # Linux/macOS
   # 或
   venv311\Scripts\activate        # Windows
   ```

3. 安装依赖

   ```bash
   pip install -r requirements.lock
   # 若需刷新依赖，可切换为 requirements.txt
   ```

4. 初始化配置并检查目录

   ```bash
   cp env.example .env
   python config/schemas/app_config.py
   ```

5. 运行应用

   ```bash
   python main.py --env development
   ```

6. 运行测试

   ```bash
   pytest -q
   ```

   > 💡 在无显示环境（CI/纯终端）运行测试如遇 Qt 崩溃，可使用：`QT_QPA_PLATFORM=offscreen pytest -q` 或直接执行 `make test-fast`。

如需更详细的按需安装策略，请参阅根目录下的 `INSTALL.md`。

### 首次使用

1. 启动应用后，您将看到主界面
2. 点击"新建实验"开始您的第一个实验
3. 选择实验模板
4. 按照步骤指导完成实验

## 用户指南

### 实验管理

#### 创建实验

1. 点击"新建实验"按钮
2. 选择实验模板
3. 填写实验信息：
   - 实验名称
   - 实验描述
   - 难度等级
4. 点击"创建"按钮

#### 执行实验

1. 在实验列表中选择要执行的实验
2. 点击"开始实验"
3. 按照步骤指导进行操作
4. 系统会实时验证您的操作
5. 完成所有步骤后查看结果

#### 实验记录

- 所有实验操作都会自动记录
- 可以查看实验历史
- 支持导出实验报告

### 用户管理

#### 用户角色

- **学生**: 可以创建和执行实验
- **管理员**: 拥有所有权限

#### 权限说明

- 学生只能查看自己的实验记录
- 管理员可以管理系统设置

### 实验模板

#### 内置模板

系统提供多种预定义实验模板：

- **基础实验**: pH滴定、酸碱中和
- **中级实验**: 氧化还原反应、配位化合物
- **高级实验**: 有机合成、分析化学

#### 自定义模板

管理员可以创建自定义实验模板：

1. 点击"模板管理"
2. 选择"新建模板"
3. 设计实验步骤
4. 设置验证规则
5. 保存模板

## 开发者文档

### 项目结构

```text
src/
├── core/           # 核心功能模块
│   ├── security/  # 安全模块
│   ├── async_service.py
│   ├── cache_manager.py
│   ├── database_pool.py
│   ├── event_driven.py
│   ├── cqrs.py
│   └── microservices.py
├── models/         # 数据模型
├── ui/            # 用户界面
├── utils/         # 工具函数
└── main.py        # 应用入口
```

### 核心模块

#### 安全模块 (src/core/security/)

- **输入验证**: 确保用户输入的安全性
- **权限管理**: 基于角色的访问控制
- **数据加密**: 敏感数据保护

#### 异步服务 (src/core/async_service.py)

- **任务管理**: 异步任务执行
- **缓存系统**: 智能缓存管理
- **速率限制**: 防止系统过载

#### 数据库连接池 (src/core/database_pool.py)

- **连接管理**: 高效的数据库连接管理
- **事务支持**: 完整的事务处理
- **性能监控**: 数据库性能监控

#### 事件驱动架构 (src/core/event_driven.py)

- **事件总线**: 系统间通信
- **事件存储**: 事件历史记录
- **Saga模式**: 分布式事务处理

#### CQRS架构 (src/core/cqrs.py)

- **命令查询分离**: 读写分离架构
- **命令总线**: 命令处理
- **查询总线**: 查询处理

#### 微服务架构 (src/core/microservices.py)

- **服务注册**: 服务发现
- **服务网关**: 统一入口
- **负载均衡**: 请求分发

### 开发指南

#### 添加新功能

1. 在相应的模块中创建新类
2. 实现必要的接口
3. 添加单元测试
4. 更新文档

#### 代码规范

- 使用Python类型提示
- 遵循PEP 8编码规范
- 添加详细的文档字符串
- 编写单元测试

#### 测试

运行全部测试：

```bash
pytest -q
```

> 💡 在无显示环境（CI/纯终端）运行测试如遇 Qt 崩溃，可使用：`QT_QPA_PLATFORM=offscreen pytest -q` 或直接执行 `make test-fast`。

运行特定测试套件：

```bash
pytest tests/security -q
pytest tests/performance -q
pytest tests/integration -q
```

## API文档

### 概述

VirtualChemLab API提供了完整的RESTful接口，支持：

- 实验管理
- 用户管理
- 数据记录
- 系统监控

### 认证

所有 API 请求都需要 API Key（推荐使用 `X-API-Key`）：

```bash
curl -H "X-API-Key: <your-api-key>" \
     http://localhost:8000/api/experiments
```

### 端点列表

#### 实验API

1. `GET /api/experiments` - 获取实验列表
2. `POST /api/experiments` - 创建新实验
3. `GET /api/experiments/{id}` - 获取实验详情
4. `PUT /api/experiments/{id}` - 更新实验
5. `DELETE /api/experiments/{id}` - 删除实验

#### 用户API

1. `GET /api/users` - 获取用户列表
2. `POST /api/users` - 创建新用户
3. `GET /api/users/{id}` - 获取用户详情
4. `PUT /api/users/{id}` - 更新用户
5. `DELETE /api/users/{id}` - 删除用户

#### 系统管理

1. `GET /api/health` - 健康检查
2. `GET /api/metrics` - 系统指标
3. `GET /api/logs` - 系统日志

### 响应格式

所有API响应都遵循统一格式：

```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 错误处理

错误响应格式：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": {...}
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 部署指南

### 开发环境

1. 按照[快速开始](#快速开始)指南设置开发环境
2. 运行测试确保一切正常
3. 启动开发服务器

### 生产环境

#### Docker部署

1. 构建镜像

```bash
docker build -t virtualchemlab .
```

1. 运行容器

```bash
docker run -d -p 8000:8000 --name virtualchemlab virtualchemlab
```

#### Kubernetes部署

1. 应用配置

```bash
kubectl apply -f k8s/
```

1. 检查状态

```bash
kubectl get pods
kubectl get services
```

#### 传统部署

1. 安装 Python 3.11 并创建虚拟环境
2. 安装依赖（推荐使用 `requirements.lock`）
3. 配置数据库与 `.env`
4. 运行 `python main.py --env production`

### 环境配置

#### 环境变量

- `DATABASE_URL`: 数据库连接字符串
- `REDIS_URL`: Redis连接字符串
- `JWT_SECRET`: JWT密钥
- `LOG_LEVEL`: 日志级别

#### 配置文件

配置文件位于 `config/` 目录：

- `development.yaml`: 开发环境配置
- `production.yaml`: 生产环境配置
- `testing.yaml`: 测试环境配置

## 故障排除

### 常见问题

#### 应用启动失败

**问题**: 应用无法启动

**解决方案**:

1. 检查Python版本是否为3.11（至少 3.10+）
2. 确认所有依赖已安装
3. 查看错误日志
4. 检查端口是否被占用

#### 数据库连接失败

**问题**: 无法连接到数据库

**解决方案**:

1. 检查数据库服务是否运行
2. 验证连接字符串
3. 检查网络连接
4. 确认数据库权限

#### 性能问题

**问题**: 应用运行缓慢

**解决方案**:

1. 检查系统资源使用情况
2. 优化数据库查询
3. 启用缓存
4. 调整连接池配置

### 日志分析

#### 日志位置

- 应用日志: `logs/app.log`
- 错误日志: `logs/error.log`
- 访问日志: `logs/access.log`

#### 日志级别

- `DEBUG`: 调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 性能监控

#### 系统指标

- CPU使用率
- 内存使用率
- 磁盘I/O
- 网络I/O

#### 应用指标

- 请求响应时间
- 错误率
- 并发用户数
- 数据库连接数

### 支持

如果您遇到问题，可以通过以下方式获取帮助：

1. 查看[FAQ](FAQ.md) 或 [故障排除指南](TROUBLESHOOTING.md)
2. 提交[Issue](https://github.com/tytsxai/VirtualChemLab/issues)
3. 联系技术支持: <support@virtualchemlab.com>

## 更新日志

更新日志以根目录 `CHANGELOG.md` 为准：

- `CHANGELOG.md`

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](../LICENSE) 文件。

## 贡献

我们欢迎社区贡献！请参阅 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解如何参与项目开发。

## 致谢

感谢所有为 VirtualChemLab 项目做出贡献的开发者和用户！
