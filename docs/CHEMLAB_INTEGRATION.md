# 🧪 ChemLab 数据集成指南

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [详细说明](#详细说明)
- [配置参考](#配置参考)
- [数据映射](#数据映射)
- [常见问题](#常见问题)
- [许可证合规](#许可证合规)

---

## 概述

本文档介绍如何将开源项目 [chemlab/chemlab](https://github.com/chemlab/chemlab) 中的化学实验案例和知识库数据集成到 VirtualChemLab 项目中。

### 为什么集成 ChemLab?

- ✅ **丰富实验案例**: ChemLab 提供了多个化学实验示例
- ✅ **标准化数据**: 包含分子数据、物理性质等结构化信息
- ✅ **开源友好**: BSD 许可证,与 MIT 兼容
- ✅ **教育资源**: 适合化学教学和实验模拟

### 架构设计

```
┌─────────────────────────────────────────┐
│         VirtualChemLab (MIT)            │
│  ┌───────────────────────────────────┐  │
│  │    核心程序 (不包含 chemlab 代码)  │  │
│  └───────────────────────────────────┘  │
│                  ▲                       │
│                  │ 使用                  │
│  ┌───────────────────────────────────┐  │
│  │    生成的数据文件 (YAML/JSON)      │  │
│  │    - 实验模板                      │  │
│  │    - 知识卡片                      │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                   ▲
                   │ 生成
┌─────────────────────────────────────────┐
│  ChemLab 集成工具 (BSD, 独立)           │
│  ┌───────────────────────────────────┐  │
│  │  数据获取 → 解析 → 转换 → 验证     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                   ▲
                   │ 读取
┌─────────────────────────────────────────┐
│      ChemLab 仓库 (BSD)                 │
│      github.com/chemlab/chemlab         │
└─────────────────────────────────────────┘
```

**关键点**:
- 集成工具与主程序**完全隔离**
- 主程序仅使用**生成的数据文件**,不包含 chemlab 代码
- 许可证清晰分离: 主程序 MIT, 工具 BSD, 数据继承源许可

---

## 快速开始

### 1. 安装依赖

```bash
cd tools/chemlab_integration
pip install -r requirements.txt
```

### 2. 配置工具

编辑 `tools/chemlab_integration/config.yaml`,设置输出路径等参数。

默认配置已适配 VirtualChemLab,通常无需修改。

### 3. 一键导入

```bash
# 导入所有数据 (实验 + 知识库)
python scripts/import_all.py

# 仅导入实验
python scripts/import_experiments.py

# 仅导入知识库
python scripts/import_knowledge.py
```

### 4. 验证数据

```bash
# 验证所有导入的数据
python scripts/validate_output.py ../../data/templates
python scripts/validate_output.py ../../data/knowledge
```

### 5. 在 VirtualChemLab 中使用

导入成功后,新的实验模板和知识卡片会自动出现在 VirtualChemLab 中。

```bash
cd ../../
python main.py
```

---

## 详细说明

### 工作流程

1. **数据获取**
   - 克隆/更新 chemlab GitHub 仓库
   - 定位示例文件和数据文件

2. **数据解析**
   - 解析 Python 示例代码
   - 提取实验步骤和分子信息
   - 解析数据库文件 (JSON/YAML/Python)

3. **数据转换**
   - 实验案例 → VirtualChemLab YAML 模板
   - 化学知识 → VirtualChemLab 知识卡片
   - 添加元数据 (来源、版本、许可证)

4. **数据验证**
   - Pydantic 模型验证
   - YAML 语法检查
   - 引用关系检查

5. **保存输出**
   - 实验模板保存到 `data/templates/`
   - 知识卡片保存到 `data/knowledge/`

### 目录结构

```
tools/chemlab_integration/
├── README.md              # 工具说明
├── LICENSE                # BSD 许可证
├── requirements.txt       # 依赖包
├── config.yaml           # 配置文件
│
├── src/                  # 源代码
│   ├── fetcher.py           # 数据获取
│   ├── parsers/             # 解析器
│   │   ├── experiment_parser.py
│   │   └── knowledge_parser.py
│   ├── converters/          # 转换器
│   │   ├── template_converter.py
│   │   └── card_converter.py
│   └── validators/          # 验证器
│       └── schema_validator.py
│
├── scripts/              # 执行脚本
│   ├── import_all.py        # 一键导入
│   ├── import_experiments.py
│   ├── import_knowledge.py
│   └── validate_output.py
│
├── tests/                # 单元测试
│   └── test_converters.py
│
├── temp/                 # 临时文件 (自动生成)
│   └── chemlab/            # 克隆的仓库
│
└── backups/              # 备份目录 (自动生成)
    └── 20250106_120000/
```

---

## 配置参考

### 核心配置项

#### 1. 源配置

```yaml
source:
  repository: "https://github.com/chemlab/chemlab.git"
  branch: "master"
  clone_path: "./temp/chemlab"
  auto_update: true
```

#### 2. 输出配置

```yaml
output:
  experiments_dir: "../../data/templates"
  knowledge_dir: "../../data/knowledge"
  backup:
    enabled: true
    backup_dir: "./backups"
    max_backups: 5
```

#### 3. 过滤规则

```yaml
filters:
  experiments:
    include_levels: ["basic", "intermediate", "advanced"]
    min_steps: 3
    max_steps: 50
  knowledge:
    include_types: ["reagent", "apparatus", "procedure"]
```

#### 4. 转换选项

```yaml
conversion:
  experiments:
    add_metadata: true
    auto_generate_scoring: true
    default_duration: 45
  knowledge:
    add_metadata: true
    query_pubchem: false  # 可选:查询 PubChem 获取更多数据
```

### 完整配置

完整配置请参考 `tools/chemlab_integration/config.yaml`。

---

## 数据映射

### 实验案例 → YAML 模板

| ChemLab 数据 | VirtualChemLab 字段 | 转换规则 |
|-------------|-------------------|---------|
| 文件名 | `id` | 生成唯一 ID: `chemlab_exp_<filename>` |
| 文档字符串第一行 | `title` | 提取为实验标题 |
| 文档字符串 | 嵌入 `steps[0].text` | 作为实验说明 |
| Python 代码 | `steps` | 解析操作流程为步骤 |
| 导入的分子 | `reagents` | 提取分子列表为试剂 |
| 可视化操作 | `curves` | 生成曲线配置 |
| 步骤数量 | `score_rules` | 自动生成评分规则 |

### 化学知识 → 知识卡片

| ChemLab 数据 | 卡片字段 | 转换规则 |
|-------------|---------|---------|
| `name` | `title` | 直接映射 |
| `formula` | `formula` | 化学式 |
| `cas` | `cas` | CAS 号 |
| `mw` / `molecular_weight` | `properties.molecular_weight` | 分子量 |
| `density` / `rho` | `properties.density` | 密度 |
| `bp` / `boiling_point` | `properties.boiling_point` | 沸点 |
| `mp` / `melting_point` | `properties.melting_point` | 熔点 |
| `hazard` / `hazards` | `hazards[]` | 危害信息 |

### 示例

#### 输入: ChemLab 示例

```python
"""Water Molecule Visualization

This example shows how to visualize a water molecule.
"""
from chemlab import Molecule

# Create water molecule
water = Molecule.from_formula("H2O")

# Render it
water.render()
```

#### 输出: VirtualChemLab 模板

```yaml
id: chemlab_exp_water_molecule
title: Water Molecule Visualization
title_en: Water Molecule Visualization
level: basic
duration_min: 45

steps:
  - id: step_1
    text: "Create water molecule"
    check:
      type: confirm
  - id: step_2
    text: "Render the structure"
    check:
      type: confirm

reagents:
  - id: reagent_1
    name: Water
    amount: "适量"
    hazard_level: info

metadata:
  source: chemlab
  source_file: water_molecule.py
  source_commit: abc1234
  license: BSD-3-Clause (from chemlab)
```

---

## 常见问题

### Q1: 导入的数据会覆盖现有数据吗?

**A**: 默认情况下:
- ✅ 自动备份现有数据到 `tools/chemlab_integration/backups/`
- ✅ 如果文件名相同会覆盖
- ✅ 使用 `--force` 强制覆盖

建议在导入前手动备份重要数据。

### Q2: 如何确保许可证合规?

**A**: 工具设计已充分考虑许可证问题:

1. **主程序保持 MIT**: VirtualChemLab 核心代码不包含任何 chemlab 代码
2. **工具独立 BSD**: 集成工具使用 BSD 许可,与 chemlab 一致
3. **数据标注来源**: 所有生成的数据文件都包含元数据,标注来源和许可证
4. **文档明确说明**: README 和文档中明确说明许可证要求

使用流程:
- ✅ 使用工具导入数据 (遵守 BSD)
- ✅ VirtualChemLab 使用数据文件 (MIT + 数据使用声明)
- ✅ 分发时保留数据来源声明

### Q3: chemlab 更新后如何同步?

**A**: 非常简单:

```bash
python scripts/import_all.py --update
```

工具会:
1. 拉取最新 chemlab 代码
2. 重新解析和转换
3. 更新数据文件

### Q4: 如何自定义转换规则?

**A**: 有两种方式:

**方式 1: 修改配置文件**

编辑 `config.yaml`:

```yaml
conversion:
  experiments:
    default_duration: 60  # 改为 60 分钟
    add_safety_hints: true
```

**方式 2: 修改转换器代码**

编辑转换器类:
- `src/converters/template_converter.py` - 实验转换
- `src/converters/card_converter.py` - 知识卡片转换

### Q5: 导入失败怎么办?

**A**: 故障排查步骤:

1. **查看日志**
   ```bash
   python scripts/import_all.py --verbose
   ```

2. **检查网络连接**
   - 确保能访问 GitHub
   - 必要时使用代理

3. **验证依赖**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **手动验证数据**
   ```bash
   python scripts/validate_output.py <输出目录>
   ```

### Q6: 可以只导入特定实验吗?

**A**: 可以通过配置过滤:

```yaml
filters:
  experiments:
    include_levels: ["basic"]  # 仅导入基础级别
    min_steps: 5              # 至少 5 个步骤
    exclude_tags: ["advanced"] # 排除高级实验
```

或直接修改代码在解析后过滤。

---

## 许可证合规

### 重要声明

⚠️ **使用本工具生成的数据时,必须遵守以下要求:**

1. **保留版权声明**
   - 所有生成的数据文件都包含元数据,标注来源为 ChemLab
   - 不要删除或修改这些元数据

2. **分发时的说明**
   - 如果分发 VirtualChemLab 包含 ChemLab 数据,需在文档中说明:
     > "本软件使用的部分实验数据和化学知识来源于 ChemLab 项目 (https://github.com/chemlab/chemlab),  
     > 该项目使用 BSD 3-Clause 许可证。"

3. **商业使用**
   - VirtualChemLab 主程序: MIT 许可,可自由商业使用
   - ChemLab 数据: BSD 许可,需保留版权声明
   - 建议: 在商业产品中明确区分自有数据和 ChemLab 数据

### 许可证兼容性

| 组件 | 许可证 | 说明 |
|-----|-------|------|
| VirtualChemLab 主程序 | MIT | 核心代码,不含 chemlab 代码 |
| ChemLab 集成工具 | BSD-3-Clause | 独立工具,与源保持一致 |
| 生成的数据文件 | BSD-3-Clause (来源标注) | 继承源数据许可 |
| ChemLab 原项目 | BSD-3-Clause | 上游项目 |

**结论**: MIT 和 BSD 许可证兼容,可安全集成使用。

### 最佳实践

✅ **推荐做法**:

1. 在 VirtualChemLab 的 README 中添加致谢:
   ```markdown
   ## 致谢
   
   本项目使用的部分化学数据来源于 [ChemLab](https://github.com/chemlab/chemlab) 项目。
   ```

2. 在关于页面中列出数据来源

3. 保留所有元数据字段

4. 定期更新数据并标注版本

---

## 技术支持

### 报告问题

如遇到问题,请提供:

1. 错误日志 (使用 `--verbose` 运行)
2. 配置文件 `config.yaml`
3. VirtualChemLab 版本
4. Python 版本和操作系统

提交 Issue: [GitHub Issues](https://github.com/your-repo/issues)

### 贡献改进

欢迎贡献:

- 🐛 修复 Bug
- ✨ 添加新功能
- 📝 改进文档
- 🧪 添加测试

请遵循项目贡献指南。

### 联系方式

- 📧 邮箱: <your-email>
- 💬 讨论: [GitHub Discussions](https://github.com/your-repo/discussions)

---

## 更新日志

### v1.0.0 (2025-10-06)

- ✅ 初始版本发布
- ✅ 支持实验案例导入
- ✅ 支持知识库导入
- ✅ 数据验证功能
- ✅ CLI 工具
- ✅ 完整文档

---

**最后更新**: 2025年10月6日  
**维护者**: VirtualChemLab Team

