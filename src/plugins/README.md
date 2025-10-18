# 插件系统

## 快速开始

### 1. 检查插件状态

```bash
python -m src.plugins.manager status
```

### 2. 安装推荐插件

```bash
python -m src.plugins.manager install --recommended
```

或手动安装：

```bash
pip install rdkit reportlab
```

### 3. 在代码中使用

```python
# 化学渲染
from src.plugins.chem_render import get_renderer
renderer = get_renderer()
img = renderer.smiles_to_image('CCO')

# PDF导出
from src.plugins.pdf_export import get_exporter
exporter = get_exporter()
exporter.export(Path('report.pdf'), content)
```

### 4. 运行演示

```bash
python examples/plugin_demo.py
```

## 可用插件

- **rdkit**: 化学结构渲染和属性计算
- **pyqtgraph**: 交互式科学图表
- **reportlab**: PDF报告生成
- **weasyprint**: HTML转PDF
- **cantera**: 热力学计算（高级）
- **openmm**: 分子动力学（高级）

## 详细文档

查看 [docs/PLUGINS.md](../../docs/PLUGINS.md) 获取完整文档。

## 架构

```
src/plugins/
├── __init__.py          # 核心注册表
├── manager.py           # 命令行工具
├── chem_render.py       # RDKit 适配
├── advanced_plots.py    # PyQtGraph 适配
├── pdf_export.py        # ReportLab/WeasyPrint 适配
├── thermo_kinetics.py   # Cantera 适配
└── molecule_animator.py # OpenMM 适配
```

每个插件都有：
- 主功能实现
- 回退函数（插件不可用时）
- 自动注册和状态管理
