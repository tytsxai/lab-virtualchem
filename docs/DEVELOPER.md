# VirtualChemLab 开发者文档

## 概述

本文档面向 VirtualChemLab 的开发者，提供详细的技术架构、开发指南和最佳实践。

> 默认定位：本地桌面单机应用（macOS/Windows/Linux）。REST API 与管理后台为可选组件，通常只在本机或内网启用。

## 技术架构

### 整体架构

VirtualChemLab 采用现代化的微服务架构，包含以下核心组件：

- **前端**: PySide6 (Qt) 桌面应用
- **后端**: Python 异步服务
- **数据库**: SQLite/PostgreSQL
- **缓存**: Redis
- **消息队列**: 内置事件总线
- **API**: RESTful API

### 核心模块

#### 1. 安全模块 (src/core/security/)

**功能**: 提供完整的安全保障

**组件**:

- `InputValidator`: 输入验证和清理
- `RBACManager`: 基于角色的访问控制
- `DataEncryption`: 数据加密
- `PasswordManager`: 密码管理
- `SecureToken`: 安全令牌

**使用示例**:

```python
from src.core.security import input_validator, rbac_manager

# 输入验证
is_valid, error, cleaned_data = input_validator.validate_and_sanitize_input(
    data, "experiment"
)

# 权限检查
user = rbac_manager.get_user_from_session(session_id)
if rbac_manager.has_permission(user, Permission.CREATE_EXPERIMENT):
    # 执行操作
    pass
```

#### 2. 异步服务 (src/core/async_service.py)

**功能**: 提供异步任务处理能力

**组件**:

- `AsyncServiceManager`: 异步服务管理器
- `AsyncCache`: 异步缓存
- `AsyncRateLimiter`: 速率限制器

**使用示例**:

```python
from src.core.async_service import async_service_manager

# 提交异步任务
task_id = async_service_manager.submit_task(process_data, data)
result = async_service_manager.wait_for_task(task_id)
```

#### 3. 缓存管理 (src/core/cache_manager.py)

**功能**: 智能缓存管理

**特性**:

- 多种缓存策略 (LRU, LFU, TTL)
- Redis 支持
- 自动过期清理
- 性能监控

**使用示例**:

```python
from src.core.cache_manager import cache_manager

# 设置缓存
cache_manager.set("key", data, ttl=3600)

# 获取缓存
data = cache_manager.get("key")
```

#### 4. 数据库连接池 (src/core/database_pool.py)

**功能**: 高效的数据库连接管理

**特性**:

- 连接池管理
- 事务支持
- 性能监控
- 多数据库支持

**使用示例**:

```python
from src.core.database_pool import db_manager

# 执行查询
results = db_manager.execute_query(
    "SELECT * FROM experiments WHERE id = ?",
    (experiment_id,)
)
```

#### 5. 事件驱动架构 (src/core/event_driven.py)

**功能**: 事件驱动的系统通信

**组件**:

- `EventBus`: 事件总线
- `EventStore`: 事件存储
- `EventSaga`: 分布式事务

**使用示例**:

```python
from src.core.event_driven import publish_event, EventType

# 发布事件
publish_event(
    EventType.EXPERIMENT_CREATED,
    {"experiment_id": "exp_001", "user_id": "user_001"}
)
```

#### 6. CQRS架构 (src/core/cqrs.py)

**功能**: 命令查询职责分离

**组件**:

- `CommandBus`: 命令总线
- `QueryBus`: 查询总线
- `CQRSManager`: CQRS管理器

**使用示例**:

```python
from src.core.cqrs import cqrs_manager, Command

# 发送命令
command = Command(data={"name": "新实验"})
result = cqrs_manager.send_command_sync(command, "create_experiment")
```

#### 7. 微服务架构 (src/core/microservices.py)

**功能**: 微服务管理

**组件**:

- `ServiceRegistry`: 服务注册中心
- `ServiceDiscovery`: 服务发现
- `ServiceGateway`: 服务网关

**使用示例**:

```python
from src.core.microservices import microservices_manager, BaseService

# 创建服务
class MyService(BaseService):
    async def start(self):
        # 服务启动逻辑
        pass

# 注册服务
service = MyService(service_info, registry)
microservices_manager.register_service(service)
```

## 开发指南

### 环境设置

#### 1. 开发环境要求

- Python 3.10+（推荐 3.11）
- Git
- IDE (推荐 PyCharm 或 VS Code)
- 数据库 (SQLite/PostgreSQL)
- Redis (可选)

#### 2. 项目设置

```bash
# 克隆项目
git clone https://github.com/tytsxai/virtualchemlab.git
cd virtualchemlab

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 3. 配置设置

复制配置文件：

```bash
cp config/development.yaml.example config/development.yaml
```

编辑配置文件：

```yaml
# config/development.yaml
app:
  name: "VirtualChemLab"
  version: "2.0.0"
  debug: true
  environment: "development"

database:
  type: "sqlite"
  url: "sqlite:///data/development.db"

cache:
  type: "memory"
  max_size: 1000
  ttl: 3600

security:
  jwt_secret: "your-secret-key"
  password_min_length: 8
```

### 代码规范

#### 1. Python代码规范

遵循 PEP 8 编码规范：

```python
# 导入顺序
import os
import sys
from typing import List, Dict, Optional

# 类定义
class MyClass:
    """类文档字符串"""

    def __init__(self, name: str):
        """初始化方法"""
        self.name = name

    def method(self, param: int) -> bool:
        """方法文档字符串

        Args:
            param: 参数描述

        Returns:
            返回值描述
        """
        return True
```

#### 2. 类型提示

使用类型提示提高代码可读性：

```python
from typing import List, Dict, Optional, Union

def process_data(
    data: List[Dict[str, Any]],
    options: Optional[Dict[str, Any]] = None
) -> Union[bool, str]:
    """处理数据"""
    pass
```

#### 3. 文档字符串

使用详细的文档字符串：

```python
def calculate_score(
    experiment_data: Dict[str, Any],
    user_input: Dict[str, Any],
    rules: List[Dict[str, Any]]
) -> int:
    """计算实验得分

    Args:
        experiment_data: 实验数据
        user_input: 用户输入
        rules: 评分规则

    Returns:
        计算得出的分数

    Raises:
        ValueError: 当输入数据无效时
        CalculationError: 当计算过程出错时

    Example:
        >>> data = {"steps": []}
        >>> input_data = {"volume": 25.0}
        >>> rules = [{"condition": "volume > 20", "score": 10}]
        >>> calculate_score(data, input_data, rules)
        10
    """
    pass
```

### 测试指南

#### 1. 测试框架

项目使用自定义测试框架，支持：

- 单元测试
- 集成测试
- 性能测试
- 并行测试

#### 2. 编写测试

```python
# tests/test_example.py
import unittest
from src.core.example import ExampleClass

class TestExample(unittest.TestCase):
    """示例测试类"""

    def setUp(self):
        """测试设置"""
        self.example = ExampleClass()

    def test_basic_functionality(self):
        """测试基本功能"""
        result = self.example.method(10)
        self.assertEqual(result, 20)

    def test_error_handling(self):
        """测试错误处理"""
        with self.assertRaises(ValueError):
            self.example.method(-1)
```

#### 3. 运行测试

```bash
# 运行所有测试
pytest -q

# 运行特定测试
pytest tests/security -q
pytest tests/performance -q
pytest tests/integration -q

# 详细输出
pytest -vv
```

### 性能优化

#### 1. 异步编程

使用异步编程提高性能：

```python
import asyncio
from src.core.async_service import async_service_manager

async def process_large_dataset(data):
    """处理大数据集"""
    tasks = []

    # 创建异步任务
    for chunk in data:
        task = async_service_manager.submit_task(process_chunk, chunk)
        tasks.append(task)

    # 等待所有任务完成
    results = await asyncio.gather(*tasks)
    return results
```

#### 2. 缓存策略

合理使用缓存：

```python
from src.core.cache_manager import cache_manager

@cache_manager.cached(ttl=3600)
def expensive_calculation(data):
    """昂贵的计算"""
    # 计算结果
    return result

# 使用缓存
result = expensive_calculation(data)
```

#### 3. 数据库优化

优化数据库查询：

```python
from src.core.database_pool import db_manager

# 使用索引
db_manager.execute_query("""
    CREATE INDEX idx_experiment_user ON experiments(user_id)
""")

# 批量操作
queries = [
    ("INSERT INTO experiments (id, name) VALUES (?, ?)", (id, name))
    for id, name in experiment_list
]
db_manager.execute_batch(queries)
```

### 错误处理

#### 1. 异常处理

```python
import logging
from src.core.error_handler import ValidationError

logger = logging.getLogger(__name__)

def process_user_input(data):
    """处理用户输入"""
    try:
        # 验证输入
        if not data:
            raise ValidationError("输入数据不能为空")

        # 处理数据
        result = process_data(data)
        return result

    except ValidationError as e:
        logger.warning(f"输入验证失败: {e}")
        raise
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise
```

#### 2. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

def important_operation():
    """重要操作"""
    logger.info("开始重要操作")

    try:
        # 执行操作
        result = perform_operation()
        logger.info("重要操作完成")
        return result

    except Exception as e:
        logger.error(f"重要操作失败: {e}")
        raise
```

### 部署指南

#### 1. Docker部署

创建 Dockerfile：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY src/ ./src/
COPY config/ ./config/

# 设置环境变量
ENV PYTHONPATH=/app

# 启动应用
CMD ["python", "src/main.py"]
```

构建和运行：

```bash
# 构建镜像
docker build -t virtualchemlab .

# 运行容器
docker run -d -p 8000:8000 --name virtualchemlab virtualchemlab
```

#### 2. Kubernetes部署

创建部署配置：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: virtualchemlab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: virtualchemlab
  template:
    metadata:
      labels:
        app: virtualchemlab
    spec:
      containers:
      - name: virtualchemlab
        image: virtualchemlab:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

部署：

```bash
kubectl apply -f k8s/
```

#### 3. 传统部署

```bash
# 安装依赖
pip install -r requirements.txt

# 配置数据库
python scripts/setup_database.py

# 启动服务
python main.py
```

### 监控和调试

#### 1. 性能监控

```python
from src.core.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()

@monitor.measure
def expensive_operation():
    """昂贵的操作"""
    # 执行操作
    pass

# 获取性能指标
metrics = monitor.get_metrics()
print(f"平均执行时间: {metrics['avg_duration']}ms")
```

#### 2. 健康检查

```python
from src.core.health import HealthChecker

health_checker = HealthChecker()

@health_checker.register_check("database")
def check_database():
    """检查数据库连接"""
    try:
        db_manager.execute_query("SELECT 1")
        return True
    except Exception:
        return False

# 执行健康检查
status = health_checker.check_all()
print(f"系统状态: {status}")
```

#### 3. 调试技巧

```python
import logging
import pdb

# 设置调试日志
logging.basicConfig(level=logging.DEBUG)

def debug_function():
    """调试函数"""
    # 设置断点
    pdb.set_trace()

    # 调试信息
    logger.debug("调试信息")

    # 执行操作
    pass
```

### 贡献指南

#### 1. 提交代码

```bash
# 创建分支
git checkout -b feature/new-feature

# 提交更改
git add .
git commit -m "feat: 添加新功能"

# 推送分支
git push origin feature/new-feature
```

#### 2. 代码审查

- 确保代码符合规范
- 添加必要的测试
- 更新文档
- 通过所有测试

#### 3. 发布流程

1. 更新版本号
2. 更新CHANGELOG.md
3. 创建发布标签
4. 构建发布包
5. 部署到生产环境

### 最佳实践

#### 1. 代码组织

- 按功能模块组织代码
- 使用清晰的命名
- 保持函数简洁
- 避免重复代码

#### 2. 错误处理

- 使用具体的异常类型
- 记录详细的错误信息
- 提供有意义的错误消息
- 实现适当的恢复机制

#### 3. 性能考虑

- 使用异步编程
- 合理使用缓存
- 优化数据库查询
- 监控性能指标

#### 4. 安全考虑

- 验证所有输入
- 使用参数化查询
- 实施适当的权限控制
- 记录安全事件

### 常见问题

#### 1. 性能问题

**问题**: 应用响应缓慢

**解决方案**:

- 检查数据库查询
- 启用缓存
- 使用异步处理
- 监控资源使用

#### 2. 内存泄漏

**问题**: 内存使用持续增长

**解决方案**:

- 检查循环引用
- 及时释放资源
- 使用弱引用
- 监控内存使用

#### 3. 并发问题

**问题**: 多线程数据竞争

**解决方案**:

- 使用锁机制
- 避免共享状态
- 使用线程安全的数据结构
- 实施适当的同步

### 支持

如果您在开发过程中遇到问题，可以通过以下方式获取帮助：

1. 查看本文档
2. 提交 Issue
3. 联系开发团队
4. 参与社区讨论

## 更新日志

### v2.0.0 (2024-01-01)

#### 新功能

- 微服务架构
- 事件驱动架构
- CQRS模式
- 异步服务支持
- 智能缓存系统

#### 改进

- 性能优化
- 安全性增强
- 测试覆盖提升
- 文档完善

#### 修复

- 修复内存泄漏问题
- 修复并发问题
- 修复数据库连接问题
