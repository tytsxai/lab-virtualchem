# 🧪 ChemLab 集成工具

## 概述

本工具用于将 [chemlab/chemlab](https://github.com/chemlab/chemlab) 开源库中的化学实验案例和知识库数据集成到 VirtualChemLab 项目中。

## 功能特性

- ✅ **实验案例转换**: 将 chemlab 实验转换为 VirtualChemLab YAML 模板格式
- ✅ **知识库导入**: 提取化学知识(试剂、装置等)并生成知识卡片
- ✅ **许可证隔离**: 独立工具形式,不污染主程序的 MIT 许可
- ✅ **自动化处理**: 一键导入最新数据
- ✅ **数据验证**: 确保生成的数据符合 VirtualChemLab 标准

## 许可证说明

**重要**: 本工具仅作为**数据导入工具**使用,独立于 VirtualChemLab 主程序:

- ✅ VirtualChemLab 主程序: **MIT License**
- ✅ ChemLab 源库: **BSD License** (兼容)
- ✅ 本导入工具: **BSD License** (与 chemlab 保持一致)
- ✅ 生成的数据文件: 继承源数据许可

**使用本工具生成的数据时,请遵守 chemlab 的 BSD 许可证要求(保留版权声明)。**

## 目录结构

```
tools/chemlab_integration/
├── README.md                 # 本文件
├── LICENSE                   # BSD 许可证
├── requirements.txt          # 依赖包
├── config.yaml              # 配置文件
├── src/
│   ├── __init__.py
│   ├── fetcher.py           # 数据获取模块
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── experiment_parser.py    # 实验解析器
│   │   └── knowledge_parser.py     # 知识解析器
│   ├── converters/
│   │   ├── __init__.py
│   │   ├── template_converter.py   # 模板转换器
│   │   └── card_converter.py       # 知识卡片转换器
│   └── validators/
│       ├── __init__.py
│       └── schema_validator.py     # 数据验证器
├── scripts/
│   ├── import_all.py        # 一键导入脚本
│   ├── import_experiments.py    # 导入实验
│   ├── import_knowledge.py      # 导入知识库
│   └── validate_output.py       # 验证输出
└── tests/
    ├── __init__.py
    └── test_converters.py   # 单元测试
```

## 快速开始

### 1. 安装依赖

```bash
cd tools/chemlab_integration
pip install -r requirements.txt
```

### 2. 配置参数

编辑 `config.yaml` 设置输出路径和过滤规则。

### 3. 一键导入

```bash
# 导入所有数据(实验 + 知识库)
python scripts/import_all.py

# 仅导入实验模板
python scripts/import_experiments.py

# 仅导入知识库
python scripts/import_knowledge.py
```

### 4. 验证数据

```bash
python scripts/validate_output.py
```

## 配置说明

### config.yaml 示例

```yaml
# ChemLab 源配置
source:
  repository: "https://github.com/chemlab/chemlab.git"
  branch: "master"
  clone_path: "./temp/chemlab"

# 输出配置
output:
  experiments_dir: "../../data/templates"  # 实验模板输出目录
  knowledge_dir: "../../data/knowledge"    # 知识库输出目录
  backup: true                             # 是否备份旧数据

# 过滤规则
filters:
  experiments:
    include_levels: ["basic", "intermediate", "advanced"]
    exclude_tags: []
  knowledge:
    include_types: ["reagent", "apparatus", "procedure"]

# 转换选项
conversion:
  add_metadata: true          # 添加元数据(来源、版本等)
  validate_on_save: true      # 保存时验证
  skip_existing: false        # 是否跳过已存在文件
```

## 数据映射

### 实验案例 → YAML 模板

| ChemLab 字段 | VirtualChemLab 字段 | 转换规则 |
|-------------|-------------------|---------|
| name | title | 直接映射 |
| description | 嵌入 steps[0].text | 作为第一步说明 |
| materials | reagents | 提取试剂列表 |
| procedure | steps | 拆分为多个步骤 |
| safety_notes | 生成 Hazard | 创建安全提示 |

### 化学知识 → 知识卡片

| ChemLab 数据 | 知识卡片类型 | 字段映射 |
|-------------|------------|---------|
| Molecule 数据 | reagent | formula, properties |
| Apparatus 数据 | apparatus | title, content |
| Protocol 数据 | procedure | steps, hints |

## 使用示例

### Python API

```python
from src.fetcher import ChemLabFetcher
from src.converters.template_converter import TemplateConverter

# 1. 获取 chemlab 数据
fetcher = ChemLabFetcher(config_path="config.yaml")
experiments = fetcher.fetch_experiments()

# 2. 转换为模板
converter = TemplateConverter()
for exp in experiments:
    template = converter.convert(exp)
    template.save("../../data/templates")

# 3. 验证
from src.validators.schema_validator import validate_template
is_valid, errors = validate_template(template)
```

### CLI 使用

```bash
# 查看可用实验
python scripts/import_experiments.py --list

# 导入指定实验
python scripts/import_experiments.py --id titration_001

# 批量导入(带过滤)
python scripts/import_experiments.py --level basic --tag acid-base

# 强制覆盖已存在文件
python scripts/import_all.py --force
```

## 数据验证

工具会自动验证:

- ✅ YAML 语法正确性
- ✅ Pydantic 模型验证
- ✅ 必填字段完整性
- ✅ 引用关系正确性
- ✅ 数值范围合理性

验证失败的数据会:
1. 记录到日志文件 `logs/import_errors.log`
2. 生成错误报告 `output/validation_report.json`
3. 不会写入输出目录

## 常见问题

### Q1: 导入的数据会覆盖现有数据吗?

A: 默认情况下,如果文件已存在会跳过。使用 `--force` 标志可强制覆盖。建议先备份。

### Q2: 如何确保许可证合规?

A: 本工具会在生成的每个文件中添加元数据,标注数据来源和原始许可证。VirtualChemLab 主程序不包含 chemlab 代码,仅使用转换后的数据。

### Q3: chemlab 更新后如何同步?

A: 重新运行 `python scripts/import_all.py --update` 即可拉取最新数据并转换。

### Q4: 可以自定义转换规则吗?

A: 可以。编辑 `src/converters/` 下的转换器类,或在 `config.yaml` 中配置映射规则。

## 维护与更新

### 定期更新流程

```bash
# 1. 拉取最新 chemlab 数据
cd tools/chemlab_integration
python scripts/import_all.py --update

# 2. 验证新数据
python scripts/validate_output.py

# 3. 在 VirtualChemLab 中测试
cd ../../
python -m pytest tests/test_templates.py
```

### 贡献指南

欢迎贡献改进!请遵循:

1. Fork 项目并创建分支
2. 添加/修改转换规则
3. 编写测试用例
4. 提交 Pull Request

## 技术支持

- 🐛 报告问题: GitHub Issues
- 📧 联系邮箱: <your-email>
- 📖 详细文档: [docs/CHEMLAB_INTEGRATION.md](../../docs/CHEMLAB_INTEGRATION.md)

## 更新日志

### v1.0.0 (2025-10-06)
- ✅ 初始版本
- ✅ 支持实验案例转换
- ✅ 支持知识库导入
- ✅ 数据验证功能
- ✅ CLI 工具

---

**⚠️ 重要提示**: 本工具生成的数据文件需遵守 chemlab 的 BSD 许可证。在商业使用前请仔细阅读许可证条款。
