# VirtualChemLab 插件系统文档

## 概述

VirtualChemLab 采用插件化架构，核心功能保持轻量，高级功能通过可选插件实现。这样的设计使得：

- **轻量安装**：基础版本只需要核心依赖
- **按需扩展**：根据实际需求安装特定插件
- **优雅降级**：插件不可用时自动使用回退实现
- **许可兼容**：不同许可证的库作为可选插件

## 可用插件

### 1. RDKit - 化学结构渲染

**功能**：分子结构可视化、化学属性计算、格式转换

**安装**：
```bash
pip install rdkit
```

**使用示例**：
```python
from src.plugins.chem_render import get_renderer

renderer = get_renderer()

# 渲染SMILES为图片
img_data = renderer.smiles_to_image('CCO', width=400, height=400)

# 获取分子属性
props = renderer.get_mol_properties('CCO')
print(f"分子量: {props['molecular_weight']}")
print(f"分子式: {props['formula']}")

# 验证SMILES
valid, error = renderer.validate_smiles('CCO')

# 格式转换
inchi = renderer.smiles_to_inchi('CCO')
```

**回退行为**：返回占位图片和空属性

---

### 2. PyQtGraph - 交互式图表

**功能**：高性能交互式科学图表

**安装**：
```bash
pip install pyqtgraph
```

**使用示例**：
```python
from src.plugins.advanced_plots import get_plotter
import numpy as np

plotter = get_plotter()

# 创建交互式图表
plot_widget = plotter.create_interactive_plot(
    parent=self,
    title="实验数据",
    x_label="时间 (s)",
    y_label="温度 (°C)"
)

# 绘制曲线
x = np.linspace(0, 10, 100)
y = np.sin(x)
plotter.plot_curve(plot_widget, x, y, name="正弦波", color='b')

# 多曲线图
data_sets = [
    (x1, y1, "曲线1"),
    (x2, y2, "曲线2"),
]
plot_widget = plotter.create_multi_curve_plot(data_sets)

# 实时更新图表
plot, curve, buffer = plotter.create_realtime_plot()
plotter.update_realtime_plot(curve, buffer, new_x, new_y)
```

**回退行为**：返回 None，使用项目自带的 matplotlib

---

### 3. ReportLab / WeasyPrint - PDF报告

**功能**：生成专业的实验报告PDF

**安装**：
```bash
# 方案1：ReportLab（推荐）
pip install reportlab

# 方案2：WeasyPrint（更强大，需要更多依赖）
pip install weasyprint
```

**使用示例**：
```python
from src.plugins.pdf_export import get_exporter
from pathlib import Path

exporter = get_exporter()

# 结构化数据导出（ReportLab）
content = [
    {'type': 'heading', 'data': '实验结果'},
    {'type': 'text', 'data': '本次实验测得...'},
    {'type': 'image', 'path': 'chart.png', 'width': 400, 'caption': '温度曲线'},
    {'type': 'table', 'data': [
        ['时间', '温度', '压力'],
        ['0s', '25°C', '1atm'],
        ['10s', '50°C', '1.2atm'],
    ]},
]

exporter.export_with_reportlab(
    Path('report.pdf'),
    title='酸碱中和实验报告',
    content=content,
    metadata={'author': '张三'}
)

# HTML转PDF（WeasyPrint）
html = "<html><body><h1>实验报告</h1><p>内容...</p></body></html>"
exporter.export_with_weasyprint(Path('report.pdf'), html)

# 自动选择可用方法
exporter.export(Path('report.pdf'), content, method='auto')
```

**回退行为**：导出为纯文本文件 (.txt)

---

### 4. Cantera - 热力学与动力学（高级）

**功能**：高精度化学反应计算、燃烧模拟

**注意**：这是一个可选的高级功能，大多数用户不需要

**安装**：
```bash
pip install cantera
```

**使用示例**：
```python
from src.plugins.thermo_kinetics import get_calculator

calc = get_calculator()

# 初始化气体
calc.initialize_gas('gri30.yaml')

# 计算化学平衡
result = calc.calculate_equilibrium(
    temperature=1000,  # K
    pressure=101325,   # Pa
    composition={'H2': 0.5, 'O2': 0.25, 'N2': 0.25}
)

print(f"平衡温度: {result['temperature']} K")
print(f"平衡组分: {result['composition']}")

# 模拟自燃
trajectory = calc.simulate_ignition(
    temperature=1200,
    pressure=101325,
    composition={'CH4': 0.1, 'O2': 0.2, 'N2': 0.7},
    time_span=(0, 0.1)
)
```

**回退行为**：返回简化计算结果（不进行真实平衡计算）

---

### 5. OpenMM - 分子动力学（高级）

**功能**：分子动力学模拟和动画

**注意**：这是一个可选的高级功能，需要较大的计算资源

**安装**：
```bash
# 推荐使用conda安装
conda install -c conda-forge openmm
```

**使用示例**：
```python
from src.plugins.molecule_animator import get_animator
from pathlib import Path

animator = get_animator()

# 设置系统
animator.setup_simple_system(
    pdb_file=Path('molecule.pdb'),
    temperature=300.0,
    timestep=2.0
)

# 生成轨迹
trajectory = animator.generate_trajectory(num_frames=100)

# 获取能量
energy = animator.get_energy_components()
print(f"总能量: {energy['total']} kJ/mol")

# 保存轨迹
animator.save_trajectory(Path('output.dcd'), trajectory, format='dcd')
```

**回退行为**：生成随机运动轨迹（演示用）

---

## 插件管理

### 检查插件状态

```python
from src.plugins import registry

# 列出所有插件
plugins = registry.list_plugins()
for name, info in plugins.items():
    print(f"{name}: {info.status.value} (v{info.version or 'N/A'})")
    if info.error_msg:
        print(f"  错误: {info.error_msg}")

# 检查单个插件
if registry.is_available('rdkit'):
    print("RDKit 可用")
else:
    print("RDKit 不可用")

# 获取插件信息
info = registry.get_info('pyqtgraph')
print(f"描述: {info.description}")
print(f"许可证: {info.license}")
```

### 使用命令行工具

```bash
# 检查所有插件状态
python -m src.plugins.manager status

# 安装推荐插件
python -m src.plugins.manager install --recommended

# 安装所有插件
python -m src.plugins.manager install --all

# 安装特定插件
python -m src.plugins.manager install rdkit reportlab
```

---

## 开发自定义插件

### 1. 注册插件

```python
from src.plugins import registry

# 定义回退函数
def fallback_function(*args, **kwargs):
    return "插件不可用"

# 注册
registry.register(
    name='my_plugin',
    description='我的自定义插件',
    module_name='my_module',
    license='MIT',
    fallback=fallback_function
)
```

### 2. 使用装饰器

```python
from src.plugins import require_plugin

@require_plugin('my_plugin')
def my_function():
    import my_module
    return my_module.do_something()
```

### 3. 手动检查

```python
from src.plugins import registry

if registry.is_available('my_plugin'):
    module = registry.get_module('my_plugin')
    module.do_something()
else:
    fallback = registry.get_fallback('my_plugin')
    fallback()
```

---

## 安装建议

### 最小安装（仅核心功能）
```bash
pip install -r requirements.txt
```

### 推荐安装（常用功能）
```bash
pip install -r requirements.txt
pip install rdkit reportlab
```

### 完整安装（所有功能）
```bash
pip install -r requirements.txt
pip install -r requirements-optional.txt
```

### 按场景安装

**化学教学**：
```bash
pip install rdkit reportlab
```

**数据分析**：
```bash
pip install pyqtgraph reportlab
```

**高级研究**：
```bash
pip install rdkit pyqtgraph reportlab cantera
# OpenMM 建议用 conda 安装
conda install -c conda-forge openmm
```

---

## 许可证说明

| 插件 | 许可证 | 商业使用 |
|------|--------|----------|
| RDKit | BSD-3-Clause | ✅ 允许 |
| PyQtGraph | MIT | ✅ 允许 |
| ReportLab | BSD | ✅ 允许 |
| WeasyPrint | BSD | ✅ 允许 |
| Cantera | BSD-3-Clause | ✅ 允许 |
| OpenMM | MIT | ✅ 允许 |

所有可选插件均为宽松许可证，可安全用于商业项目。

---

## 常见问题

**Q: 为什么不把所有功能都做成必需依赖？**

A: 为了保持核心轻量、降低安装门槛、避免许可证冲突、支持多种使用场景。

**Q: 插件不可用时程序会崩溃吗？**

A: 不会。每个插件都有回退实现，保证基本功能可用。

**Q: 如何知道某个功能是否需要插件？**

A: 查看功能文档，或运行时会有日志提示。UI上也会标注需要特定插件的功能。

**Q: 可以只安装部分插件吗？**

A: 可以。根据实际需求选择性安装，不需要全部安装。

**Q: OpenMM 为什么推荐用 conda 安装？**

A: OpenMM 依赖复杂的编译库，conda 提供预编译版本更可靠。

---

## 技术细节

### 插件加载流程

1. 注册插件（定义元数据和回退函数）
2. 尝试导入模块
3. 成功：标记为 AVAILABLE，存储模块引用
4. 失败：标记为 NOT_INSTALLED，记录错误信息
5. 运行时通过装饰器或手动检查调用

### 状态枚举

- `AVAILABLE`: 已安装且可用
- `NOT_INSTALLED`: 未安装
- `ERROR`: 加载错误
- `DISABLED`: 已禁用（预留）

### 设计原则

- **非侵入性**：不影响核心代码
- **向后兼容**：始终提供回退方案
- **透明性**：清晰的状态反馈
- **可扩展性**：易于添加新插件
