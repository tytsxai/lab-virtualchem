# VirtualChemLab API 参考文档

## 概述

本文档提供 VirtualChemLab 核心 API 的详细说明,面向希望扩展或集成该系统的开发者。

---

## 核心模块

### 1. 模板引擎 (TemplateEngine)

**位置**: `src/core/template_engine.py`

#### 初始化

```python
from src.core import TemplateEngine

engine = TemplateEngine(templates_dir="assets/templates")
```

#### 主要方法

##### `load_experiment_by_id(experiment_id: str) -> ExperimentTemplate`

根据ID加载实验模板。

**参数**:
- `experiment_id` (str): 实验唯一标识符

**返回**: `ExperimentTemplate` 对象

**异常**:
- `FileNotFoundError`: 模板文件不存在
- `ValidationError`: 模板格式错误

**示例**:
```python
template = engine.load_experiment_by_id("titration_naoh_hcl_v1")
print(template.title)  # "NaOH滴定HCl实验"
```

##### `list_available_experiments() -> List[dict[str, str]]`

列出所有可用实验的摘要信息（用于列表/选择器），不会返回完整模板对象。

**返回**: 字典列表（字段以当前实现为准），例如：
- `id`
- `title` / `title_en`
- `level`
- `duration_min`
- `version`

**示例**:
```python
experiments = engine.list_available_experiments()
for exp in experiments:
    print(f"{exp['id']}: {exp['title']}")
```

##### `validate_template(template_path: Path) -> tuple[bool, list[str]]`

验证模板文件的完整性和正确性（包含结构/字段与部分业务规则校验）。

**参数**:
- `template_path` (Path): 模板文件路径

**返回**: `(ok, errors)`
- `ok`：是否通过
- `errors`：错误信息列表（为空表示无错误）

---

### 2. 实验控制器 (ExperimentController)

**位置**: `src/core/experiment_controller.py`

#### 初始化

```python
from src.core import ExperimentController

controller = ExperimentController(
    template=template,
    user_id="student_001"
)
```

#### 主要方法

##### `start_experiment() -> None`

开始实验,初始化记录。

**示例**:
```python
controller.start_experiment()
print(f"当前步骤: {controller.get_current_step().title}")
```

##### `submit_step(user_input: dict) -> StepResult`

提交当前步骤的用户数据进行验证。

**参数**:
- `user_input` (dict): 用户提交的数据
  - 确认型: `{"confirmed": bool}`
  - 输入型: `{"value": str}`
  - 选择型: `{"selected": str}` 或 `{"selected": List[str]}`
  - 顺序型: `{"sequence": List[str]}`

**返回**: `StepResult`（可当作对象使用，也兼容旧代码的 tuple 解包）
- `result.is_valid`：是否通过检查
- `result.message`：反馈消息
- `result.mistake`：错误详情（可选）
- `result.errors` / `result.warnings`：错误/警告列表

**示例**:
```python
result = controller.submit_step({"confirmed": True})
if result.is_valid:
    print("通过!")
else:
    print(f"失败: {result.message}")
```

##### `next_step() -> bool`

前进到下一步。

**返回**: 是否成功前进

##### `previous_step() -> bool`

返回上一步。

**返回**: 是否成功返回

##### `complete_experiment() -> UserRecord`

完成实验,计算最终得分。

**返回**: `UserRecord` 对象,包含完整实验记录

##### `get_progress() -> dict`

获取当前进度信息。

**返回**: 字典
```python
{
    "total_steps": int,
    "current_step": int,
    "completed_steps": int,
    "progress_percent": float
}
```

---

### 3. 规则验证器 (RuleValidator)

**位置**: `src/core/rule_validator.py`

#### 主要方法

##### `check(checkpoint: CheckPoint, user_data: dict) -> Tuple[bool, str]`

验证用户数据是否满足检查点要求。

**参数**:
- `checkpoint` (CheckPoint): 检查点对象
- `user_data` (dict): 用户数据

**返回**: `(passed, message)` 元组

**示例**:
```python
from src.core import RuleValidator
from src.models.experiment import CheckPoint

validator = RuleValidator()
checkpoint = CheckPoint(
    type="input",
    expected="25.0",
    tolerance=0.5,
    message="输入体积"
)

passed, msg = validator.check(checkpoint, {"value": "25.2"})
# passed = True, msg = "输入正确!在允许范围内"
```

##### `evaluate_expression(expression: str, context: dict) -> Any`

安全求值表达式。

**参数**:
- `expression` (str): 数学表达式
- `context` (dict): 变量上下文

**返回**: 表达式结果

**示例**:
```python
result = validator.evaluate_expression(
    "pH >= 7.0 and pH <= 7.5",
    {"pH": 7.2}
)
# result = True
```

---

### 4. 曲线生成器 (CurveGenerator)

**位置**: `src/core/curve_generator.py`

#### 主要方法

##### `generate_titration_curve(...) -> Tuple[np.ndarray, np.ndarray]`

生成滴定曲线数据。

**参数**:
- `acid_type` (str): "strong" 或 "weak"
- `acid_M` (float): 酸的浓度 (mol/L)
- `acid_V_ml` (float): 酸的体积 (mL)
- `base_M` (float): 碱的浓度 (mol/L)
- `pKa` (float, 可选): 弱酸的pKa值

**返回**: `(V_base, pH_values)` 元组
- `V_base`: 加入碱的体积数组 (mL)
- `pH_values`: 对应的pH值数组

**示例**:
```python
from src.core import CurveGenerator

gen = CurveGenerator()
V, pH = gen.generate_titration_curve(
    acid_type="strong",
    acid_M=0.1,
    acid_V_ml=25.0,
    base_M=0.1
)

# 可用于绘图
import matplotlib.pyplot as plt
plt.plot(V, pH)
plt.xlabel("加入NaOH体积 (mL)")
plt.ylabel("pH")
plt.show()
```

##### `generate_temperature_curve(...) -> Tuple[np.ndarray, np.ndarray]`

生成温度变化曲线。

**参数**:
- `curve_type` (str): "heating" 或 "cooling"
- `T0` (float): 初始温度 (°C)
- `T_target` (float): 目标温度 (°C)
- `k` (float): 速率常数
- `duration_min` (float): 持续时间 (分钟)

**返回**: `(time_points, temp_values)` 元组

---

### 5. 危险检查器 (HazardChecker)

**位置**: `src/knowledge/hazard_checker.py`

#### 主要方法

##### `check_temperature(reagent: str, temperature: float) -> List[str]`

检查温度危险。

**返回**: 危险警告列表

##### `check_mixing(reagents: List[str]) -> List[str]`

检查试剂混合危险。

**返回**: 危险警告列表

##### `check_protection(required: List[str], worn: List[str]) -> List[str]`

检查防护装备。

**返回**: 缺失装备列表

**示例**:
```python
from src.knowledge import HazardChecker

checker = HazardChecker()

# 温度检查
warnings = checker.check_temperature("乙醇", 85)
# ["警告: 乙醇沸点为78°C,当前温度85°C过高!"]

# 混合检查
warnings = checker.check_mixing(["H2SO4", "NaOH"])
# ["危险: 强酸与强碱混合会剧烈放热!"]

# 防护检查
missing = checker.check_protection(
    required=["护目镜", "实验服"],
    worn=["护目镜"]
)
# ["实验服"]
```

---

### 6. 报告生成器 (HTMLGenerator)

**位置**: `src/reporter/html_generator.py`

#### 主要方法

##### `generate(record: UserRecord, template: ExperimentTemplate, output_path: str = None) -> str`

生成HTML实验报告。

**参数**:
- `record` (UserRecord): 实验记录
- `template` (ExperimentTemplate): 实验模板
- `output_path` (str, 可选): 输出文件路径

**返回**: HTML字符串

**示例**:
```python
from src.reporter import HTMLGenerator

generator = HTMLGenerator()
html = generator.generate(
    record=controller.get_record(),
    template=template,
    output_path="reports/experiment_001.html"
)
```

---

## 数据模型

### ExperimentTemplate

实验模板数据模型。

**字段**:
```python
class ExperimentTemplate(BaseModel):
    id: str                         # 唯一标识符
    title: str                      # 标题
    description: str                # 描述
    difficulty: str                 # 难度: beginner/intermediate/advanced
    duration_minutes: int           # 预计用时(分钟)
    steps: List[Step]               # 步骤列表
    score_rule: ScoreRule           # 评分规则
    knowledge_cards: List[str] = [] # 知识点ID
    curves: List[Curve] = []        # 曲线配置
    hazards: List[dict] = []        # 危险项
    tags: List[str] = []            # 标签
    metadata: dict = {}             # 元数据
```

### Step

实验步骤。

**字段**:
```python
class Step(BaseModel):
    id: str                      # 步骤ID
    title: str                   # 标题
    instruction: str             # 说明
    checkpoint: CheckPoint       # 检查点
    hints: List[str] = []        # 提示
    knowledge_refs: List[str] = []  # 知识引用
```

### CheckPoint

检查点配置。

**字段**:
```python
class CheckPoint(BaseModel):
    type: str          # 类型: confirm/input/select/sequence
    expected: Any      # 期望值
    message: str       # 提示消息

    # 可选字段
    tolerance: float = None      # 容差(数值类型)
    unit: str = None             # 单位
    options: List[str] = None    # 选项(select类型)
    expression: str = None       # 验证表达式
```

### UserRecord

用户实验记录。

**字段**:
```python
class UserRecord(BaseModel):
    user_id: str
    experiment_id: str
    start_time: datetime
    end_time: datetime = None
    step_records: List[StepRecord] = []
    final_score: float = None
    metadata: dict = {}
```

---

## 扩展开发

### 1. 添加新的检查点类型

1. 在 `src/core/rule_validator.py` 的 `check()` 方法中添加新类型处理
2. 在 `src/models/experiment.py` 的 `CheckPoint` 模型中添加相关字段
3. 更新UI以支持新类型的输入

### 2. 添加新的曲线类型

1. 在 `src/core/curve_generator.py` 中添加新方法
2. 在实验模板YAML中配置曲线参数
3. 在UI的 `CurveWidget` 中添加绘制逻辑

### 3. 自定义评分规则

在YAML模板中使用 `score_rule.formula`:

```yaml
score_rule:
  total_score: 100
  formula: "100 - total_mistakes * 5 + bonus_points"
```

可用变量:
- `total_mistakes`: 总错误数
- `correct_count`: 正确步骤数
- `total_steps`: 总步骤数
- 自定义变量

---

## 常见问题

### Q: 如何添加自定义试剂?

A: 在 `assets/knowledge/reagents/` 下创建新的YAML文件:

```yaml
id: "my_reagent"
name: "我的试剂"
formula: "XYZ"
hazards:
  - type: "toxic"
    severity: "high"
    description: "有毒"
```

### Q: 如何集成到其他系统?

A: VirtualChemLab 提供 Python API,可通过以下方式集成:

```python
from src.core import TemplateEngine, ExperimentController

# 加载模板
engine = TemplateEngine("path/to/templates")
template = engine.load_experiment_by_id("exp_id")

# 运行实验
controller = ExperimentController(template, user_id="external_user")
controller.start_experiment()

# ... 与外部系统交互 ...

record = controller.complete_experiment()
# 将record导出到外部系统
```

---

## 版本历史

- **v1.0.0** (2025-10-06): 初始版本
  - 核心引擎
  - 基础UI
  - 滴定、重结晶、酯化实验模板

---

## 联系我们

- **GitHub**: https://github.com/yourorg/VirtualChemLab
- **文档**: https://virtualchemlab.readthedocs.io
- **问题反馈**: https://github.com/yourorg/VirtualChemLab/issues

---

*最后更新: 2025-10-06*


