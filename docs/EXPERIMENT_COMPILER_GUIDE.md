# 实验编译器使用指南

## 概述

实验编译器是 VirtualChemLab 的核心功能,用于将多种格式的实验描述编译为标准的实验模板。支持:

- ✅ YAML/JSON 格式
- ✅ 半结构化文本
- ✅ 自然语言描述 (需要AI助手)
- ✅ 字典对象
- ✅ 自动格式检测
- ✅ 错误检测和修复建议
- ✅ 向后兼容性

## 快速开始

### 1. 从YAML文件添加实验

```bash
# 使用实验管理工具
实验管理工具.bat add examples/new_experiment_example.yaml

# 或使用Python
python -c "from src.ai.experiment_compiler import compile_experiment; compile_experiment('examples/new_experiment_example.yaml')"
```

### 2. 从字典创建实验

```python
from src.ai.experiment_compiler import compile_experiment

exp_data = {
    "title": "我的实验",
    "steps": [
        {
            "text": "步骤1",
            "check": {"type": "confirm"}
        }
    ]
}

result = compile_experiment(exp_data, format_type="dict")

if result.success:
    print(f"成功! 实验ID: {result.template.id}")
```

### 3. 使用命令行工具

```bash
# 列出所有实验
实验管理工具.bat list

# 查看实验详情
实验管理工具.bat info titration_naoh_hcl_v1

# 验证实验
实验管理工具.bat validate titration_naoh_hcl_v1

# 编译实验
实验管理工具.bat compile examples/new_experiment_example.yaml -o output.yaml

# 获取统计信息
实验管理工具.bat stats

# 热重载实验
实验管理工具.bat reload
```

## 实验模板格式

### 完整示例

```yaml
experiment:
  id: "my_experiment_v1"              # 必需: 唯一标识符
  title: "实验标题"                    # 必需: 实验名称
  title_en: "Experiment Title"        # 可选: 英文标题
  description: "实验描述"              # 可选: 详细描述
  category: "无机化学"                 # 可选: 分类
  level: "basic"                       # 可选: basic/intermediate/advanced
  duration_min: 45                     # 可选: 预计时长(分钟)

  # 实验目标
  goals:
    - name: "目标描述"
      metric: "metric_name"            # 度量指标变量名
      lte: 0.5                         # 小于等于
      # gte: 10                        # 大于等于
      # eq: 25.0                       # 等于

  # 试剂列表
  reagents:
    - id: "reagent_1"
      name: "试剂名称"
      amount: "用量"
      hazard_level: "info"             # info/warning/severe/critical

  # 实验步骤 (必需)
  steps:
    - id: "step_1"                     # 必需: 步骤ID
      text: "步骤描述"                  # 必需: 步骤文本

      # 检查点配置
      check:
        type: "confirm"                # confirm/input/select/sequence
        fail_hint: "失败提示"

        # input类型的配置
        # input:
        #   key: "variable_name"
        #   label: "显示标签"
        #   input_type: "float"        # int/float/string/bool
        #   range: [0, 100]            # 数值范围
        #   unit: "mL"                 # 单位

        # select类型的配置
        # input:
        #   key: "choice"
        #   label: "选择标签"
        #   options:
        #     - value: "option1"
        #       label: "选项1"
        #       correct: true
        #     - value: "option2"
        #       label: "选项2"
        #       correct: false

        # sequence类型的配置
        # require: ["step_id_1", "step_id_2"]

      # 提示列表
      hints:
        - text: "提示内容"
        # trigger: "expression"        # 可选: 触发条件

      safety_level: "info"             # info/warning/severe/critical

  # 曲线配置
  curves:
    - id: "curve_1"
      type: "titration_ph"             # titration_ph/temp_time/volume_time/pressure_temp
      params:
        acid_M: 0.1
        acid_V_ml: 25.0
        base_M: 0.1
      x_label: "X轴标签"
      y_label: "Y轴标签"
      x_unit: "单位"
      y_unit: "单位"

  # 评分规则
  score_rules:
    - when: "expression"               # 条件表达式
      then: 50                         # 得分

  version: "1.0.0"                     # 版本号
```

### 检查点类型详解

#### 1. confirm - 确认类型

用于需要用户确认已完成某个操作的步骤。

```yaml
check:
  type: "confirm"
  fail_hint: "请确认已完成此步骤"
```

用户输入: `{"confirmed": true}`

#### 2. input - 输入类型

用于需要用户输入数值或文本的步骤。

```yaml
check:
  type: "input"
  input:
    key: "volume"                      # 变量名
    label: "体积"                       # 显示标签
    input_type: "float"                # 类型
    range: [0, 50]                     # 范围
    unit: "mL"                         # 单位
  correct_value: 25.0                  # 可选: 期望值
  fail_hint: "请输入正确的体积值"
```

用户输入: `{"volume": 25.0}`

#### 3. select - 选择类型

用于需要用户从选项中选择的步骤。

```yaml
check:
  type: "select"
  input:
    key: "indicator"
    label: "选择指示剂"
    options:
      - value: "phenolphthalein"
        label: "酚酞"
        correct: true
      - value: "methyl_orange"
        label: "甲基橙"
        correct: false
  fail_hint: "应选择酚酞指示剂"
```

用户输入: `{"indicator": "phenolphthalein"}`

#### 4. sequence - 依赖类型

用于需要先完成其他步骤的情况。

```yaml
check:
  type: "sequence"
  require: ["step_1", "step_2"]       # 前置步骤ID列表
  fail_hint: "请先完成前置步骤"
```

## 编译器API

### ExperimentCompiler 类

```python
from src.ai.experiment_compiler import ExperimentCompiler

# 创建编译器
compiler = ExperimentCompiler(ai_assistant=None)

# 从字典编译
result = compiler.compile_from_dict(data_dict)

# 从YAML编译
result = compiler.compile_from_yaml(yaml_string)

# 从JSON编译
result = compiler.compile_from_json(json_string)

# 从文件编译
result = compiler.compile_from_file(Path("experiment.yaml"))

# 验证和修复
result = compiler.validate_and_fix(template)
```

### CompilationResult 结构

```python
@dataclass
class CompilationResult:
    success: bool                      # 是否成功
    template: ExperimentTemplate       # 编译后的模板
    warnings: list[str]                # 警告列表
    errors: list[str]                  # 错误列表
    suggestions: list[str]             # 改进建议
```

### 便捷函数

```python
from src.ai.experiment_compiler import compile_experiment, save_compiled_template

# 自动检测格式并编译
result = compile_experiment(source, format_type="auto")

# 保存编译结果
save_compiled_template(result, "output.yaml", format_type="yaml")
```

## 增强实验管理器

### EnhancedExperimentManager 类

```python
from src.core.enhanced_experiment_manager import EnhancedExperimentManager

# 创建管理器
manager = EnhancedExperimentManager(
    templates_dir="assets/templates",
    records_dir="data/records",
    ai_assistant=None
)

# 加载实验
template = manager.load_experiment("experiment_id")

# 添加实验
success, template, messages = manager.add_experiment(
    source="experiment.yaml",
    format_type="auto",
    save=True
)

# 更新实验
success, messages = manager.update_experiment(
    "experiment_id",
    {"duration_min": 60}
)

# 删除实验
success, messages = manager.delete_experiment(
    "experiment_id",
    force=False
)

# 列出实验
experiments = manager.list_experiments(
    category="无机化学",
    level="basic"
)

# 获取实验信息
info = manager.get_experiment_info("experiment_id")

# 开始实验会话
session_id, controller = manager.start_experiment_session(
    "experiment_id",
    "user_001"
)

# 获取会话
controller = manager.get_session(session_id)

# 结束会话
record = manager.end_experiment_session(session_id, save_record=True)

# 检查前置条件
satisfied, missing = manager.check_prerequisites(
    "experiment_id",
    "user_001"
)

# 获取统计信息
stats = manager.get_experiment_statistics()

# 检查更新
updated_ids = manager.check_for_updates()

# 热重载
count = manager.reload_updated_experiments()
```

## 错误处理

### ExperimentErrorHandler

```python
from src.core.experiment_error_handler import (
    get_error_handler,
    handle_validation_error,
    handle_template_error,
    handle_runtime_error,
)

# 获取错误处理器
error_handler = get_error_handler()

# 处理错误
error = handle_validation_error("输入值超出范围", step_id="step_1")

# 获取最近错误
recent_errors = error_handler.get_recent_errors(count=10)

# 获取错误摘要
summary = error_handler.get_error_summary()

# 清空历史
error_handler.clear_history()
```

## 兼容性说明

### 支持的旧格式字段

编译器自动转换以下旧格式字段:

- `difficulty` → `level`
- `duration_minutes` → `duration_min`
- `instruction` → `text` (步骤中)

示例:

```yaml
# 旧格式
experiment:
  difficulty: "basic"
  duration_minutes: 45
  steps:
    - instruction: "步骤描述"

# 自动转换为新格式
experiment:
  level: "basic"
  duration_min: 45
  steps:
    - text: "步骤描述"
```

## 最佳实践

### 1. 实验ID命名

- 使用描述性名称
- 包含版本号
- 使用下划线分隔
- 示例: `titration_naoh_hcl_v1`

### 2. 步骤设计

- 每个步骤应该清晰、具体
- 提供充分的提示和安全警告
- 合理设置检查点类型
- 标注安全级别

### 3. 评分规则

- 覆盖关键操作
- 平衡各项得分
- 总分通常为100
- 使用清晰的条件表达式

### 4. 错误处理

- 提供友好的失败提示
- 设置合理的输入范围
- 验证依赖关系
- 测试各种边界情况

## 常见问题

### Q: 如何使用AI编译自然语言描述?

A: 需要先启用AI助手:

```python
from src.ai.chemistry_assistant import ChemistryAI
from src.ai.experiment_compiler import ExperimentCompiler

ai = ChemistryAI()
compiler = ExperimentCompiler(ai_assistant=ai)

result = compiler.compile_from_text(natural_language_text)
```

### Q: 如何实现实验热重载?

A: 使用增强管理器的热重载功能:

```python
manager = EnhancedExperimentManager(...)

# 检查更新
updated = manager.check_for_updates()

# 重新加载
count = manager.reload_updated_experiments()
```

### Q: 如何处理编译错误?

A: 检查编译结果中的错误和建议:

```python
result = compile_experiment(source)

if not result.success:
    print("错误:")
    for error in result.errors:
        print(f"  - {error}")

    print("建议:")
    for suggestion in result.suggestions:
        print(f"  - {suggestion}")
```

### Q: 如何验证现有模板?

A: 使用验证功能:

```bash
# 命令行
实验管理工具.bat validate experiment_id

# Python
manager = EnhancedExperimentManager(...)
template = manager.load_experiment("experiment_id")
result = manager.compiler.validate_and_fix(template)
```

## 示例

完整示例请参考:

- `examples/new_experiment_example.yaml` - YAML格式实验
- `examples/natural_language_experiment.txt` - 自然语言描述
- `tests/test_experiment_compiler.py` - 测试用例
- `assets/templates/` - 现有实验模板

## 相关文档

- [API参考文档](API_REFERENCE.md)
- [开发者指南](API_DEV_GUIDE.md)
- [架构文档](ARCHITECTURE.md)
