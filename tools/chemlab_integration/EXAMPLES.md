# 📖 ChemLab 集成使用示例

本文档提供 ChemLab 集成工具的实际使用示例。

---

## 基础使用

### 1. 快速导入所有数据

```bash
cd tools/chemlab_integration

# 安装依赖
pip install -r requirements.txt

# 一键导入
python scripts/import_all.py
```

**输出示例**:
```
🧪 ChemLab 数据导入工具
配置文件: tools/chemlab_integration/config.yaml

✅ 备份实验模板到: tools/chemlab_integration/backups/20250106_120000/templates
✅ 备份知识库到: tools/chemlab_integration/backups/20250106_120000/knowledge

📦 仓库路径: tools/chemlab_integration/temp/chemlab
  url: https://github.com/chemlab/chemlab.git
  branch: master
  commit: abc1234

============================================================
开始导入实验数据...
============================================================
找到 15 个示例文件
✅ 解析成功: Water Molecule Visualization
✅ 解析成功: Benzene Structure
...
✅ 成功导入 12 个实验模板到: ../../data/templates

============================================================
开始导入知识库数据...
============================================================
找到 20 个数据文件
📊 数据统计:
  reagent: 35 条
  apparatus: 8 条
  procedure: 5 条
✅ 成功导入 48 个知识卡片到: ../../data/knowledge

============================================================
✅ 导入完成!
============================================================
实验模板: 12 个
知识卡片: 48 个
总计: 60 个数据文件
```

---

## 高级用法

### 2. 仅导入实验

```bash
python scripts/import_experiments.py
```

### 3. 仅导入知识库

```bash
python scripts/import_knowledge.py
```

### 4. 更新到最新数据

```bash
# 自动拉取最新 chemlab 代码并重新导入
python scripts/import_all.py --update
```

### 5. 强制覆盖已存在文件

```bash
# 不询问,直接覆盖
python scripts/import_all.py --force
```

### 6. 详细输出模式

```bash
# 查看详细日志
python scripts/import_all.py --verbose
```

---

## 数据验证

### 7. 验证实验模板

```bash
python scripts/validate_output.py ../../data/templates
```

**输出**:
```
🔍 验证: ../../data/templates
类型: auto

✅ chemlab_exp_water_molecule.yaml: 验证通过
✅ chemlab_exp_benzene_structure.yaml: 验证通过
❌ chemlab_exp_invalid.yaml: 验证失败
  - steps: field required

验证完成: ✅ 11 个成功, ❌ 1 个失败
```

### 8. 验证知识库

```bash
python scripts/validate_output.py ../../data/knowledge
```

### 9. 保存验证报告

```bash
python scripts/validate_output.py ../../data/templates --output validation_report.json
```

---

## 配置自定义

### 10. 修改输出路径

编辑 `config.yaml`:

```yaml
output:
  experiments_dir: "../../data/templates_custom"
  knowledge_dir: "../../data/knowledge_custom"
```

### 11. 过滤实验级别

```yaml
filters:
  experiments:
    include_levels: ["basic"]  # 仅导入基础级别
    min_steps: 3
    max_steps: 10
```

### 12. 自定义转换选项

```yaml
conversion:
  experiments:
    default_duration: 60  # 改为 60 分钟
    auto_generate_scoring: true
    add_safety_hints: true
```

---

## Python API 使用

### 13. 编程式使用

```python
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from src.fetcher import ChemLabFetcher
from src.parsers.experiment_parser import ExperimentParser
from src.converters.template_converter import TemplateConverter

# 1. 获取数据
fetcher = ChemLabFetcher("config.yaml")
fetcher.clone_or_update()
example_files = fetcher.list_examples()

# 2. 解析实验
parser = ExperimentParser()
experiments = parser.parse_batch(example_files[:5])

# 3. 转换为模板
converter = TemplateConverter()
repo_info = fetcher.get_repo_info()

for exp in experiments:
    template = converter.convert(exp, repo_info)
    print(f"生成模板: {template['id']}")
    converter.save_template(template, Path("output"))
```

### 14. 单个实验转换

```python
from src.converters.template_converter import TemplateConverter

# 模拟实验数据
experiment_data = {
    "source_file": "my_experiment.py",
    "title": "我的实验",
    "description": "这是一个测试实验",
    "steps": ["准备试剂", "混合溶液", "观察反应"],
    "code_info": {
        "molecules": ["water", "salt"],
        "operations": ["mix", "heat"],
    }
}

# 转换
converter = TemplateConverter()
template = converter.convert(experiment_data)

# 查看结果
import yaml
print(yaml.dump(template, allow_unicode=True))
```

### 15. 知识卡片转换

```python
from src.converters.card_converter import CardConverter

# 试剂数据
reagent_data = {
    "name": "盐酸",
    "formula": "HCl",
    "cas": "7647-01-0",
    "molecular_weight": 36.46,
    "density": 1.2,
    "boiling_point": -85,
    "hazard": "腐蚀性物质,避免接触皮肤"
}

# 转换
converter = CardConverter()
card = converter.convert_reagent(reagent_data)

# 保存
from pathlib import Path
converter.save_card(card, Path("output/reagent"))
```

---

## 批处理脚本

### 16. Windows 批处理

创建 `quick_import.bat`:

```batch
@echo off
cd tools\chemlab_integration
python scripts\import_all.py --update --verbose
pause
```

### 17. Linux/macOS 脚本

创建 `quick_import.sh`:

```bash
#!/bin/bash
cd tools/chemlab_integration
python scripts/import_all.py --update --verbose
```

使其可执行:
```bash
chmod +x quick_import.sh
./quick_import.sh
```

---

## 定时任务

### 18. 定期更新数据 (Linux Cron)

```bash
# 编辑 crontab
crontab -e

# 每周日凌晨 2 点更新
0 2 * * 0 cd /path/to/VirtualChemLab && python tools/chemlab_integration/scripts/import_all.py --update
```

### 19. Windows 计划任务

1. 打开任务计划程序
2. 创建基本任务
3. 触发器: 每周
4. 操作: 启动程序
   - 程序: `python`
   - 参数: `tools\chemlab_integration\scripts\import_all.py --update`
   - 起始位置: `C:\path\to\VirtualChemLab`

---

## 故障排查

### 20. 检查依赖

```bash
python -c "import yaml, git, pydantic; print('✅ 所有依赖已安装')"
```

### 21. 测试连接

```bash
git ls-remote https://github.com/chemlab/chemlab.git
```

### 22. 手动克隆仓库

```bash
cd tools/chemlab_integration/temp
git clone https://github.com/chemlab/chemlab.git
```

### 23. 清理并重试

```bash
# 删除临时文件
rm -rf tools/chemlab_integration/temp
rm -rf tools/chemlab_integration/cache

# 重新导入
python scripts/import_all.py
```

---

## 集成到 VirtualChemLab

### 24. 使用导入的实验

```python
# 在 VirtualChemLab 主程序中
from src.core.experiment_controller import ExperimentController

# 加载实验
controller = ExperimentController()
controller.load_template("data/templates/chemlab_exp_water_molecule.yaml")

# 运行实验
controller.start_experiment()
```

### 25. 查询导入的知识卡片

```python
from src.knowledge.loader import KnowledgeLoader
from pathlib import Path

loader = KnowledgeLoader(Path("data/knowledge"))

# 搜索 chemlab 来源的试剂
cards = loader.search_cards("chemlab")
for card in cards:
    print(f"{card.title}: {card.metadata.get('source')}")
```

---

## 单元测试

### 26. 运行测试

```bash
cd tools/chemlab_integration
python -m pytest tests/
```

### 27. 测试覆盖率

```bash
pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 生产环境使用

### 28. 生产配置

创建 `config.prod.yaml`:

```yaml
source:
  auto_update: false  # 不自动更新,使用稳定版本

output:
  backup:
    enabled: true
    max_backups: 10

validation:
  strict_mode: true  # 严格验证

logging:
  level: "WARNING"  # 仅警告和错误
```

使用:
```bash
python scripts/import_all.py --config config.prod.yaml
```

### 29. CI/CD 集成

`.github/workflows/import-chemlab.yml`:

```yaml
name: Import ChemLab Data

on:
  schedule:
    - cron: '0 2 * * 0'  # 每周日凌晨 2 点
  workflow_dispatch:  # 手动触发

jobs:
  import:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          cd tools/chemlab_integration
          pip install -r requirements.txt

      - name: Import data
        run: |
          cd tools/chemlab_integration
          python scripts/import_all.py --update

      - name: Validate data
        run: |
          cd tools/chemlab_integration
          python scripts/validate_output.py ../../data/templates

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add data/
          git commit -m "Auto-import ChemLab data" || echo "No changes"
          git push
```

---

## 常见场景

### 30. 场景: 添加新实验

1. ChemLab 项目添加了新实验
2. 运行更新命令:
   ```bash
   python scripts/import_all.py --update
   ```
3. 新实验自动导入到 VirtualChemLab

### 31. 场景: 修复导入错误

1. 发现某个实验转换错误
2. 在 `src/converters/template_converter.py` 中修复逻辑
3. 重新导入:
   ```bash
   python scripts/import_all.py --force
   ```

### 32. 场景: 自定义数据源

1. 复制并修改 `src/parsers/experiment_parser.py`
2. 实现自己的解析逻辑
3. 在配置中指定自定义解析器

---

## 总结

本文档涵盖了 ChemLab 集成工具的各种使用场景,从基础导入到高级自定义,从开发测试到生产部署。

**核心命令速查**:

```bash
# 安装
pip install -r requirements.txt

# 导入
python scripts/import_all.py

# 更新
python scripts/import_all.py --update

# 验证
python scripts/validate_output.py <目录>

# 测试
python -m pytest tests/
```

更多信息请参考:
- 📖 [完整文档](../../docs/CHEMLAB_INTEGRATION.md)
- 🚀 [快速开始](QUICKSTART.md)
- 📝 [实施总结](IMPLEMENTATION_SUMMARY.md)

---

**最后更新**: 2025年10月6日
