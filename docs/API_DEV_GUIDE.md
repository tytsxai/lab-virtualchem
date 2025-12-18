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
from src.core.experiment_controller import ExperimentController
from src.core.template_engine import TemplateEngine
from src.storage import JSONStore

# 初始化组件
engine = TemplateEngine("assets/templates")
store = JSONStore("data/records")

# 加载实验
template = engine.load_experiment_by_id("titration_naoh_hcl")

# 运行实验
controller = ExperimentController(template, user_id="student_001", storage=store)
controller.start_experiment()

# 提交步骤（通过时会自动进入下一步）
result = controller.submit_step({"confirmed": True})

if not result.is_valid:
    raise RuntimeError(result.message)

# ... 继续提交后续步骤直到全部通过 ...

# 完成实验并保存记录
record = controller.complete_experiment()
store.save_record(record)

print(f"最终得分: {record.final_score}")
```

### 核心模块

#### 1.1 模板引擎 (TemplateEngine)

```python
from pathlib import Path

from src.core.template_engine import TemplateEngine

engine = TemplateEngine(templates_dir="assets/templates")

# 列出所有实验
experiments = engine.list_available_experiments()

# 加载特定实验
template = engine.load_experiment_by_id("exp_id")

# 验证模板文件（返回 ok, errors）
ok, errors = engine.validate_template(Path("assets/templates/exp_id.yaml"))
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
result = controller.submit_step({
    "confirmed": True  # 确认型
    # "value": "25.0"  # 输入型
    # "selected": "option"  # 选择型
    # "sequence": ["a", "b", "c"]  # 顺序型
})

# 通过时会自动进入下一步；需要手动导航时可使用：
# controller.next_step()
# controller.previous_step()

# 获取进度
progress = controller.get_progress()
# {
#     "total_steps": 10,
#     "current_step": 3,
#     "completed_steps": 3,
#     "progress_percent": 30.0
# }

# 完成实验
record = controller.complete_experiment()
```

#### 1.3 数据存储 (JSONStore)

```python
from src.storage.json_store import JSONStore

store = JSONStore(base_dir="data/records")

# 保存记录
store.save_record(record)

# 列出记录索引（可按 user_id 过滤）
entries = store.list_records(user_id="user_id", limit=20)

# 加载记录
record = store.load_record(user_id="user_id", record_id=entries[0]["record_id"])

# 删除
store.delete_record(user_id="user_id", record_id=record.record_id)
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

> 说明：REST API 的接口契约与安全默认值请以 `docs/API.md` 与 `/api/docs`（OpenAPI JSON）为准；
> 本章节只提供开发调用示例，避免多处维护导致文档与实现漂移。

### 启动 API 服务器

```bash
# 方法1: 直接运行（默认绑定 127.0.0.1:8080）
python -m src.api.server

# 方法2: 使用CLI工具
python tools/dev_cli.py api start

# 如需对外监听请显式配置
VCL_API_HOST=0.0.0.0 python -m src.api.server
```

### 认证（API Key）

- 默认除 `GET /api/health` 与 `GET /api/docs` 外，均需要 API Key。
- 请求头任选一种：

```text
X-API-Key: <your-api-key>
```

或：

```text
Authorization: Bearer <your-api-key>
```

> 开发环境：未设置 `VCL_API_KEYS` 时，服务会自动生成 key 并写入 `~/.virtualchemlab/api_key.txt`；
> 生产环境：必须显式配置 `VCL_API_KEYS`，否则服务会拒绝启动（避免容器/多副本密钥漂移）。

### CORS（浏览器跨域）

安全默认值：仅允许本机回环 Origin。跨域访问需显式配置 `VCL_API_CORS_ORIGINS`。

### 常用调用示例（curl）

```bash
# 健康检查（无需认证）
curl http://127.0.0.1:8080/api/health

# 就绪检查（无需认证；失败返回 503）
curl http://127.0.0.1:8080/api/ready

# 部署探针（无需认证；含构建信息/磁盘探测）
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/readyz

# OpenAPI 文档（无需认证）
curl http://127.0.0.1:8080/api/docs

# 列出实验（需要 API Key）
curl -H "X-API-Key: <key>" http://127.0.0.1:8080/api/experiments

# 开始实验
curl -X POST http://127.0.0.1:8080/api/experiments/start \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"experiment_id":"titration_naoh_hcl","user_id":"student_001"}'

# 提交步骤
curl -X POST http://127.0.0.1:8080/api/experiments/submit \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","data":{"confirmed":true}}'

# 完成实验并生成记录
curl -X POST http://127.0.0.1:8080/api/experiments/finish \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>"}'

# 列出记录（可选按 user_id 过滤）
curl -H "X-API-Key: <key>" "http://127.0.0.1:8080/api/records?user_id=student_001"

# 获取单条记录（建议携带 user_id 以避免全量扫描）
curl -H "X-API-Key: <key>" "http://127.0.0.1:8080/api/records/<record_id>?user_id=student_001"

# 生成报告（写入 reports/<record_id>.html，并返回 path/url）
curl -X POST http://127.0.0.1:8080/api/reports/generate \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"record_id":"<record_id>","format":"html"}'
```

### 使用 Python 客户端

```python
from src.api.client import VirtualChemLabClient

client = VirtualChemLabClient("http://127.0.0.1:8080", api_key="<key>")

health = client.health_check()
experiments = client.list_experiments()
session = client.start_experiment("titration_naoh_hcl", "student_001")
result = client.submit_step({"confirmed": True})
final_result = client.finish_experiment()
report = client.generate_report(final_result["record_id"])
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

# 默认仅绑定本机回环地址（127.0.0.1）；如需对外提供服务请显式设置：
VCL_API_HOST=0.0.0.0 python -m src.api.server
```

### 8.2 生产环境

```bash
# 当前 REST API 基于 Python 标准库 HTTPServer 实现（非 WSGI/ASGI），
# 因此不支持 `gunicorn ... src.api.server:app` / `waitress-serve ... src.api.server:app` 这种用法。
#
# 推荐做法：直接以进程方式运行，并交由 systemd/supervisor/容器编排 管理。
ENVIRONMENT=production VCL_API_HOST=0.0.0.0 python -m src.api.server
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
