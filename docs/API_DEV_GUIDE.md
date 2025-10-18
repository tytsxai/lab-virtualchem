# VirtualChemLab 开发接口文档

## 概述

VirtualChemLab 提供了三种开发接口:

1. **Python API** - 直接调用Python模块
2. **REST API** - HTTP接口用于外部系统集成
3. **CLI工具** - 命令行开发工具

---

## 1. Python API

### 快速开始

```python
from src.core import TemplateEngine, ExperimentController
from src.storage import JSONStore

# 初始化组件
engine = TemplateEngine("assets/templates")
store = JSONStore("data/records")

# 加载实验
template = engine.load_experiment_by_id("titration_naoh_hcl")

# 运行实验
controller = ExperimentController(template, user_id="student_001")
controller.start_experiment()

# 提交步骤
passed, message, score = controller.submit_step({"confirmed": True})

if passed:
    controller.next_step()

# 完成实验
record = controller.finish_experiment()
store.save(record)

print(f"最终得分: {record.final_score}")
```

### 核心模块

#### 1.1 模板引擎 (TemplateEngine)

```python
from src.core.template_engine import TemplateEngine

engine = TemplateEngine(template_dir="assets/templates")

# 列出所有实验
experiments = engine.list_experiments()

# 加载特定实验
template = engine.load_experiment_by_id("exp_id")

# 验证模板
is_valid = engine.validate_template(template)
```

#### 1.2 实验控制器 (ExperimentController)

```python
from src.core.experiment_controller import ExperimentController

controller = ExperimentController(template, user_id="user_001")

# 开始实验
controller.start_experiment()

# 获取当前步骤
step = controller.get_current_step()

# 提交步骤数据
passed, message, score = controller.submit_step({
    "confirmed": True  # 确认型
    # "value": "25.0"  # 输入型
    # "selected": "option"  # 选择型
    # "sequence": ["a", "b", "c"]  # 顺序型
})

# 导航
controller.next_step()
controller.previous_step()

# 获取进度
progress = controller.get_progress()
# {
#     "total_steps": 10,
#     "current_step": 3,
#     "completed_steps": 3,
#     "progress_percent": 30.0
# }

# 完成实验
record = controller.finish_experiment()
```

#### 1.3 数据存储 (JSONStore)

```python
from src.storage.json_store import JSONStore

store = JSONStore(data_dir="data/records")

# 保存记录
store.save(record)

# 加载记录
record = store.load_by_id("record_id")

# 查询
records = store.find_by_user("user_id")
records = store.find_by_experiment("exp_id")
all_records = store.list_all()

# 删除
store.delete("record_id")
```

#### 1.4 报告生成 (HTMLGenerator)

```python
from src.reporter.html_generator import HTMLGenerator

generator = HTMLGenerator()

# 生成HTML报告
html_content = generator.generate(
    record=record,
    template=template,
    output_path="reports/report.html"
)
```

#### 1.5 曲线生成 (CurveGenerator)

```python
from src.core.curve_generator import CurveGenerator

gen = CurveGenerator()

# 滴定曲线
V, pH = gen.generate_titration_curve(
    acid_type="strong",
    acid_M=0.1,
    acid_V_ml=25.0,
    base_M=0.1
)

# 温度曲线
time, temp = gen.generate_temperature_curve(
    curve_type="heating",
    T0=25.0,
    T_target=100.0,
    k=0.05,
    duration_min=10.0
)

# 压力曲线
time, pressure = gen.generate_pressure_curve(
    T0=25.0,
    T_target=100.0,
    V_L=1.0,
    n_mol=0.1,
    k=0.05,
    duration_min=10.0
)
```

#### 1.6 安全检查 (HazardChecker)

```python
from src.knowledge.hazard_checker import HazardChecker

checker = HazardChecker()

# 温度检查
warnings = checker.check_temperature("乙醇", 85)

# 混合检查
warnings = checker.check_mixing(["H2SO4", "NaOH"])

# 防护检查
missing = checker.check_protection(
    required=["护目镜", "实验服"],
    worn=["护目镜"]
)
```

---

## 2. REST API

### 启动API服务器

```bash
# 方法1: 直接运行
python -m src.api.server

# 方法2: 使用CLI工具
python tools/dev_cli.py api start

# 服务器将运行在 http://localhost:8080
```

### API端点

#### 2.1 健康检查

```http
GET /api/health
```

**响应:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-06T10:30:00"
}
```

#### 2.2 列出实验

```http
GET /api/experiments
```

**响应:**
```json
{
  "experiments": [
    {
      "id": "titration_naoh_hcl",
      "title": "NaOH滴定HCl实验",
      "description": "强酸强碱滴定",
      "difficulty": "beginner",
      "duration_minutes": 30,
      "tags": ["titration", "acid-base"]
    }
  ],
  "count": 1
}
```

#### 2.3 获取实验详情

```http
GET /api/experiments/{experiment_id}
```

**响应:**
```json
{
  "experiment": {
    "id": "titration_naoh_hcl",
    "title": "NaOH滴定HCl实验",
    "steps": [
      {
        "id": "step1",
        "title": "准备工作",
        "instruction": "准备实验器材",
        "checkpoint_type": "confirm"
      }
    ],
    "score_rule": {
      "total_score": 100,
      "formula": "100 - total_mistakes * 5"
    }
  }
}
```

#### 2.4 开始实验

```http
POST /api/experiments/start
Content-Type: application/json

{
  "experiment_id": "titration_naoh_hcl",
  "user_id": "student_001"
}
```

**响应:**
```json
{
  "session_id": "student_001_titration_naoh_hcl_1696595400",
  "experiment_id": "titration_naoh_hcl",
  "current_step": {
    "id": "step1",
    "title": "准备工作",
    "instruction": "准备实验器材",
    "checkpoint_type": "confirm"
  },
  "progress": {
    "total_steps": 10,
    "current_step": 0,
    "completed_steps": 0,
    "progress_percent": 0.0
  }
}
```

#### 2.5 提交步骤

```http
POST /api/experiments/submit
Content-Type: application/json

{
  "session_id": "student_001_titration_naoh_hcl_1696595400",
  "data": {
    "confirmed": true
  }
}
```

**响应:**
```json
{
  "passed": true,
  "message": "确认成功!",
  "score": 10.0,
  "has_next_step": true,
  "current_step": {
    "id": "step2",
    "title": "下一步骤",
    ...
  },
  "progress": {
    "total_steps": 10,
    "current_step": 1,
    "completed_steps": 1,
    "progress_percent": 10.0
  }
}
```

#### 2.6 完成实验

```http
POST /api/experiments/finish
Content-Type: application/json

{
  "session_id": "student_001_titration_naoh_hcl_1696595400"
}
```

**响应:**
```json
{
  "record_id": "rec_1696595500_abc123",
  "final_score": 95.0,
  "total_mistakes": 1,
  "duration_seconds": 450.5
}
```

#### 2.7 列出记录

```http
GET /api/records?user_id=student_001
```

**响应:**
```json
{
  "records": [
    {
      "id": "rec_1696595500_abc123",
      "user_id": "student_001",
      "experiment_id": "titration_naoh_hcl",
      "final_score": 95.0,
      "start_time": "2025-10-06T10:30:00",
      "end_time": "2025-10-06T10:37:30"
    }
  ],
  "count": 1
}
```

#### 2.8 生成报告

```http
POST /api/reports/generate
Content-Type: application/json

{
  "record_id": "rec_1696595500_abc123",
  "format": "html"
}
```

**响应:**
```json
{
  "record_id": "rec_1696595500_abc123",
  "format": "html",
  "content": "<html>...</html>",
  "url": "/reports/rec_1696595500_abc123.html"
}
```

### 使用Python客户端

```python
from src.api.client import VirtualChemLabClient

# 创建客户端
client = VirtualChemLabClient("http://localhost:8080")

# 健康检查
health = client.health_check()

# 列出实验
experiments = client.list_experiments()

# 开始实验
session = client.start_experiment("titration_naoh_hcl", "student_001")

# 提交步骤
result = client.submit_step({"confirmed": True})

# 完成实验
final_result = client.finish_experiment()

# 生成报告
report = client.generate_report(final_result['record_id'])
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

# 提交步骤
curl -X POST http://localhost:8080/api/experiments/submit \
  -H "Content-Type: application/json" \
  -d '{"session_id": "xxx", "data": {"confirmed": true}}'
```

---

## 3. CLI开发工具

### 安装

```bash
# 确保工具可执行
chmod +x tools/dev_cli.py

# 创建别名(可选)
alias vcl-dev="python tools/dev_cli.py"
```

### 模板管理

```bash
# 列出所有模板
python tools/dev_cli.py templates list

# 验证模板
python tools/dev_cli.py templates validate titration_naoh_hcl

# 显示模板详情
python tools/dev_cli.py templates show titration_naoh_hcl
```

### 运行实验

```bash
# 交互式运行
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

# 导出记录
python tools/dev_cli.py records export output.json
python tools/dev_cli.py records export output.json --user student_001
```

### 测试工具

```bash
# 运行所有测试
python tools/dev_cli.py test run

# 运行特定测试
python tools/dev_cli.py test run --pattern test_experiment

# 检查覆盖率
python tools/dev_cli.py test coverage
```

---

## 4. 测试框架

### 单元测试

```python
import pytest
from src.core.experiment_controller import ExperimentController

def test_experiment_controller():
    # 准备
    template = create_test_template()
    controller = ExperimentController(template, "test_user")

    # 执行
    controller.start_experiment()
    passed, msg, score = controller.submit_step({"confirmed": True})

    # 断言
    assert passed is True
    assert score > 0
```

### 集成测试

```python
from tests.integration.test_experiment_flow import TestExperimentFlow

# 运行集成测试
pytest tests/integration/test_experiment_flow.py -v
```

### 性能测试

```python
from tests.performance.test_performance import TestPerformance

# 运行性能测试
pytest tests/performance/test_performance.py -v
```

---

## 5. 开发最佳实践

### 5.1 错误处理

```python
from src.utils.error_handler import safe_execute, ExperimentError

@safe_execute(default_return=None)
def risky_operation():
    # 可能出错的代码
    ...

# 自定义错误
try:
    template = engine.load_experiment_by_id("invalid_id")
except FileNotFoundError as e:
    logger.error(f"Template not found: {e}")
```

### 5.2 日志记录

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### 5.3 配置管理

```python
from src.utils.config import Config

config = Config()

# 读取配置
templates_dir = config.get("paths.templates_dir")
log_level = config.get("logging.level", "INFO")

# 更新配置
config.set("paths.data_dir", "custom/data")
config.save()
```

### 5.4 类型注解

```python
from typing import List, Optional, Dict, Any
from src.models.experiment import ExperimentTemplate

def process_template(
    template: ExperimentTemplate,
    user_id: str,
    options: Optional[Dict[str, Any]] = None
) -> List[str]:
    """处理模板

    Args:
        template: 实验模板
        user_id: 用户ID
        options: 可选参数

    Returns:
        处理结果列表
    """
    ...
```

---

## 6. 调试技巧

### 6.1 启用详细日志

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 6.2 使用pdb调试

```python
import pdb

def problematic_function():
    pdb.set_trace()  # 设置断点
    # 代码...
```

### 6.3 检查数据结构

```python
from pprint import pprint

# 美化打印
pprint(template.model_dump())
pprint(controller.get_progress())
```

---

## 7. 扩展开发

### 7.1 添加新的检查点类型

1. 在 `src/models/experiment.py` 中定义新类型
2. 在 `src/core/rule_validator.py` 中添加验证逻辑
3. 在UI中添加对应的输入组件

### 7.2 添加新的曲线类型

1. 在 `src/core/curve_generator.py` 中添加生成方法
2. 在模板YAML中配置曲线参数
3. 在UI中添加显示逻辑

### 7.3 自定义评分规则

在模板中使用公式:

```yaml
score_rule:
  total_score: 100
  formula: "100 - total_mistakes * 5 + bonus_points"
  variables:
    bonus_points: 10
```

---

## 8. 部署指南

### 8.1 开发环境

```bash
# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 运行测试
pytest -v

# 启动开发服务器
python -m src.api.server
```

### 8.2 生产环境

```bash
# 使用gunicorn(Linux/Mac)
gunicorn -w 4 -b 0.0.0.0:8080 src.api.server:app

# 使用waitress(Windows)
waitress-serve --port=8080 src.api.server:app
```

---

## 9. 常见问题

### Q: 如何添加自定义试剂?

A: 在 `assets/knowledge/reagents.json` 中添加:

```json
{
  "id": "my_reagent",
  "name": "我的试剂",
  "formula": "XYZ",
  "hazards": [...]
}
```

### Q: 如何自定义报告模板?

A: 修改 `src/reporter/templates/report.html` 模板文件

### Q: 如何集成到LMS系统?

A: 使用REST API集成:

```python
# LMS系统中
from your_lms import create_assignment

response = requests.post("http://vcl-api:8080/api/experiments/start", json={
    "experiment_id": "exp_id",
    "user_id": lms_user_id
})

session_id = response.json()['session_id']
create_assignment(session_id)
```

---

## 10. 资源链接

- **源代码**: https://github.com/yourorg/VirtualChemLab
- **API文档**: http://localhost:8080/api/docs
- **问题追踪**: https://github.com/yourorg/VirtualChemLab/issues
- **开发指南**: docs/DEVELOPMENT_GUIDE.md

---

*最后更新: 2025-10-06*



