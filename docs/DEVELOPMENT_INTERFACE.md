# VirtualChemLab 开发和测试接口

## 📋 概述

VirtualChemLab 提供了完整的开发和测试接口,包括:

- **REST API** - HTTP接口用于外部系统集成
- **Python API** - 直接调用Python模块
- **CLI工具** - 命令行开发和测试工具
- **测试工具集** - 自动化测试辅助工具
- **集成测试** - 完整的端到端测试

---

## 🚀 快速开始

### 1. 启动API服务器

```bash
# 启动REST API服务器
python start_api_server.py

# 自定义端口
python start_api_server.py --port 9000

# 服务器运行在 http://localhost:8080
```

### 2. 使用CLI工具

```bash
# 列出所有实验模板
python tools/dev_cli.py templates list

# 运行交互式实验
python tools/dev_cli.py experiment run titration_naoh_hcl

# 自动测试实验
python tools/dev_cli.py experiment run titration_naoh_hcl --auto

# 查看实验记录
python tools/dev_cli.py records list
```

### 3. 运行集成测试

```bash
# 运行所有集成测试
pytest tests/integration/ -v

# 运行特定测试
pytest tests/integration/test_experiment_flow.py -v

# 生成覆盖率报告
python tools/dev_cli.py test coverage
```

---

## 🔌 REST API

### API端点

#### 健康检查
```http
GET /api/health
```

#### 实验管理
```http
GET  /api/experiments           # 列出所有实验
GET  /api/experiments/{id}      # 获取实验详情
POST /api/experiments/start     # 开始实验
POST /api/experiments/submit    # 提交步骤
POST /api/experiments/finish    # 完成实验
```

#### 记录管理
```http
GET  /api/records              # 列出记录
GET  /api/records/{id}         # 获取记录详情
```

#### 报告生成
```http
POST /api/reports/generate     # 生成报告
```

### 使用Python客户端

```python
from src.api.client import VirtualChemLabClient

# 创建客户端
client = VirtualChemLabClient("http://localhost:8080")

# 列出实验
experiments = client.list_experiments()

# 运行实验
result = client.run_experiment(
    experiment_id="titration_naoh_hcl",
    steps_data=[
        {"confirmed": True},
        {"value": "25.0"},
        {"selected": "酚酞"}
    ],
    user_id="student_001"
)

print(f"最终得分: {result['final_score']}")
```

### 使用curl

```bash
# 健康检查
curl http://localhost:8080/api/health

# 列出实验
curl http://localhost:8080/api/experiments

# 开始实验
curl -X POST http://localhost:8080/api/experiments/start \
  -H "Content-Type: application/json" \
  -d '{"experiment_id": "titration_naoh_hcl", "user_id": "student_001"}'
```

完整API文档: [API_DEV_GUIDE.md](API_DEV_GUIDE.md)

---

## 🛠️ CLI开发工具

### 模板管理

```bash
# 列出所有模板
python tools/dev_cli.py templates list

# 验证模板
python tools/dev_cli.py templates validate titration_naoh_hcl

# 显示模板详情
python tools/dev_cli.py templates show titration_naoh_hcl
```

### 实验运行

```bash
# 交互式运行实验
python tools/dev_cli.py experiment run titration_naoh_hcl

# 自动运行(使用正确答案)
python tools/dev_cli.py experiment run titration_naoh_hcl --auto

# 指定用户
python tools/dev_cli.py experiment run titration_naoh_hcl --user student_001
```

### 记录管理

```bash
# 列出所有记录
python tools/dev_cli.py records list

# 列出特定用户记录
python tools/dev_cli.py records list --user student_001

# 显示记录详情
python tools/dev_cli.py records show <record_id>

# 导出记录到JSON
python tools/dev_cli.py records export output.json
```

### 测试工具

```bash
# 运行所有测试
python tools/dev_cli.py test run

# 运行特定测试
python tools/dev_cli.py test run --pattern test_experiment

# 检查代码覆盖率
python tools/dev_cli.py test coverage
```

---

## 🧪 测试工具集

### 创建测试模板

```python
from tools.test_harness import TestHarness

# 创建简单测试模板
template = TestHarness.create_simple_template(
    exp_id="test_exp",
    num_steps=5
)
```

### 自动完成实验

```python
from tools.test_harness import TestHarness

# 创建控制器
controller = TestHarness.create_test_controller(template, "test_user")

# 自动完成(无错误)
record = TestHarness.auto_complete_experiment(controller)

# 自动完成(故意犯错)
record = TestHarness.auto_complete_experiment(controller, make_mistakes=True)
```

### 运行实验场景

```python
from tools.test_harness import TestHarness

# 定义场景
steps_data = [
    {"confirmed": True},
    {"value": "25.0"},
    {"selected": "酚酞"}
]

# 运行场景
result = TestHarness.run_experiment_scenario(
    template=template,
    steps_data=steps_data,
    user_id="scenario_user"
)
```

### 性能基准测试

```python
from tools.test_harness import TestHarness

# 运行基准测试
stats = TestHarness.benchmark_experiment(template, num_runs=100)

print(f"平均时间: {stats['avg_time']*1000:.2f}ms")
print(f"最快: {stats['min_time']*1000:.2f}ms")
print(f"最慢: {stats['max_time']*1000:.2f}ms")
```

### 验证模板文件

```bash
# 使用CLI工具
python tools/test_harness.py validate assets/templates/titration_naoh_hcl.yaml

# 使用Python
from tools.test_harness import TestHarness

result = TestHarness.validate_template_file("path/to/template.yaml")

if result["valid"]:
    print("✅ 模板有效")
else:
    print("❌ 错误:", result["errors"])
```

---

## 🔬 集成测试

### 完整实验流程测试

```python
# tests/integration/test_experiment_flow.py

def test_complete_successful_experiment(template_engine, storage):
    """测试完整的成功实验流程"""

    # 1. 加载模板
    template = template_engine.load_experiment_by_id("test_exp_001")

    # 2. 创建控制器
    controller = ExperimentController(template, "test_user")
    controller.start_experiment()

    # 3. 完成所有步骤
    for i, step in enumerate(template.steps):
        current_step = controller.get_current_step()

        # 提交正确答案
        if step.checkpoint.type == "confirm":
            passed, msg, score = controller.submit_step({"confirmed": True})
        elif step.checkpoint.type == "input":
            passed, msg, score = controller.submit_step({"value": str(step.checkpoint.expected)})
        # ...

        assert passed is True
        controller.next_step()

    # 4. 完成实验
    record = controller.finish_experiment()

    # 5. 验证结果
    assert record.final_score == 100
    assert len(record.mistakes) == 0

    # 6. 保存和验证
    storage.save(record)
    loaded_record = storage.load_by_id(record.id)
    assert loaded_record.final_score == record.final_score
```

### 运行集成测试

```bash
# 运行所有集成测试
pytest tests/integration/ -v

# 运行特定测试类
pytest tests/integration/test_experiment_flow.py::TestExperimentFlow -v

# 运行特定测试
pytest tests/integration/test_experiment_flow.py::TestExperimentFlow::test_complete_successful_experiment -v
```

---

## 📊 性能测试

### 运行性能测试

```bash
# 运行性能测试套件
pytest tests/performance/test_performance.py -v

# 生成性能报告
python tools/dev_cli.py experiment run titration_naoh_hcl --auto
```

### 自定义性能测试

```python
import time
from tools.test_harness import TestHarness

def test_experiment_performance():
    """测试实验性能"""
    template = TestHarness.create_simple_template(num_steps=10)

    # 测试100次运行
    durations = []

    for i in range(100):
        controller = TestHarness.create_test_controller(template, f"user_{i}")

        start = time.time()
        TestHarness.auto_complete_experiment(controller)
        duration = time.time() - start

        durations.append(duration)

    # 分析结果
    avg_time = sum(durations) / len(durations)
    assert avg_time < 0.1  # 平均时间应小于100ms
```

---

## 🔗 外部系统集成

### LMS系统集成示例

```python
class MyLMSIntegration:
    """LMS系统集成"""

    def __init__(self, api_url: str):
        self.client = VirtualChemLabClient(api_url)

    def create_assignment(self, course_id: str, experiment_id: str):
        """创建作业"""
        experiment = self.client.get_experiment(experiment_id)

        assignment = {
            "course_id": course_id,
            "experiment_id": experiment_id,
            "title": experiment['title'],
            "duration_minutes": experiment['duration_minutes']
        }

        # 保存到LMS数据库
        self.save_to_lms(assignment)

        return assignment

    def submit_assignment(self, assignment_id: str, student_id: str):
        """学生提交作业"""
        # 从LMS获取作业
        assignment = self.get_from_lms(assignment_id)

        # 开始实验
        session = self.client.start_experiment(
            assignment['experiment_id'],
            student_id
        )

        # 返回会话ID给前端
        return session['session_id']

    def grade_assignment(self, record_id: str):
        """评分作业"""
        # 获取实验记录
        record = self.client.get_record(record_id)

        # 生成报告
        report = self.client.generate_report(record_id)

        # 保存成绩到LMS
        self.save_grade(record['user_id'], record['final_score'])

        return {
            "score": record['final_score'],
            "report_url": report['url']
        }
```

完整示例: [examples/api_integration_example.py](../examples/api_integration_example.py)

---

## 📝 最佳实践

### 1. 错误处理

```python
from src.utils.error_handler import safe_execute

@safe_execute(default_return=None)
def risky_operation():
    # 可能出错的代码
    pass

# 或使用try-except
try:
    result = client.submit_step(data)
except requests.HTTPError as e:
    logger.error(f"API错误: {e}")
```

### 2. 日志记录

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("开始实验")
logger.debug(f"步骤数据: {data}")
logger.error(f"提交失败: {error}")
```

### 3. 配置管理

```python
from src.utils.config import Config

config = Config()

# 读取配置
api_url = config.get("api.url", "http://localhost:8080")

# 更新配置
config.set("api.timeout", 30)
config.save()
```

### 4. 测试隔离

```python
import pytest

@pytest.fixture
def isolated_storage(tmp_path):
    """隔离的存储"""
    return JSONStore(str(tmp_path / "data"))

def test_with_isolation(isolated_storage):
    # 测试不会影响实际数据
    isolated_storage.save(record)
```

---

## 🐛 调试技巧

### 1. 启用详细日志

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG

# 或在代码中
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 使用pdb调试

```python
import pdb

def problematic_function():
    pdb.set_trace()  # 设置断点
    # 调试代码
```

### 3. 检查API响应

```python
# 使用详细模式
import requests

response = requests.get("http://localhost:8080/api/experiments")
print(response.status_code)
print(response.headers)
print(response.json())
```

### 4. 验证数据结构

```python
from pprint import pprint

# 美化打印
pprint(template.model_dump())
pprint(record.model_dump())
```

---

## 📚 相关文档

- [API开发指南](API_DEV_GUIDE.md) - 完整的API文档
- [API参考文档](API_REFERENCE.md) - Python API参考
- [插件开发](PLUGINS.md) - 插件系统文档
- [用户手册](USER_MANUAL.md) - 用户使用指南

---

## 🔧 故障排除

### API服务器无法启动

```bash
# 检查端口占用
netstat -ano | findstr :8080

# 使用不同端口
python start_api_server.py --port 9000
```

### 导入模块失败

```bash
# 设置PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Windows PowerShell
$env:PYTHONPATH = "$PWD"
```

### 测试失败

```bash
# 清理缓存
find . -type d -name __pycache__ -exec rm -rf {} +

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

---

## 💡 贡献指南

欢迎贡献新的开发工具和测试用例!

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/new-tool`)
3. 提交更改 (`git commit -am 'Add new tool'`)
4. 推送到分支 (`git push origin feature/new-tool`)
5. 创建Pull Request

---

*最后更新: 2025-10-06*



