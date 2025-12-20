# 增强的实验交互UI组件文档

## 概述

VirtualChemLab新增了一套完整的实验交互UI组件库，提供更丰富的用户交互体验和数据可视化功能。

## 新增组件

### 1. 实验交互组件 (`experiment_widgets.py`)

#### ValueSlider - 数值滑块

带数值显示和单位的滑块组件，适合连续数值调节。

**功能特性：**

- 实时数值显示
- 自定义范围和精度
- 单位显示
- 平滑动画效果

**使用示例：**

```python
from src.ui.experiment_widgets import ValueSlider

# 创建温度滑块
temp_slider = ValueSlider(
    label="加热温度",
    min_value=0.0,
    max_value=100.0,
    default_value=25.0,
    unit="°C",
    decimals=1
)

# 监听值变化
temp_slider.value_changed.connect(on_temperature_changed)

# 获取当前值
current_temp = temp_slider.value()
```

#### NumericInput - 数值输入器

带增减按钮的数值输入框。

**功能特性：**

- 快捷增减按钮
- 精确数值输入
- 范围限制
- 步进控制

**使用示例：**

```python
from src.ui.experiment_widgets import NumericInput

volume_input = NumericInput(
    label="滴定体积",
    min_value=0.0,
    max_value=50.0,
    default_value=0.0,
    unit="mL",
    decimals=2,
    step=0.5
)
```

#### ColorPicker - 颜色选择器

用于溶液颜色选择和显示。

**功能特性：**

- 颜色预览
- 十六进制颜色码显示
- 颜色选择对话框

**使用示例：**

```python
from src.ui.experiment_widgets import ColorPicker
from PySide6.QtGui import QColor

color_picker = ColorPicker(label="溶液颜色", default_color=QColor(255, 0, 0))
color_picker.color_changed.connect(on_color_changed)
```

#### TemperatureGauge - 温度计组件

可视化温度显示组件，带动画效果。

**功能特性：**

- 温度计外观
- 动画过渡
- 颜色根据温度变化
- 刻度显示

**使用示例：**

```python
from src.ui.experiment_widgets import TemperatureGauge

temp_gauge = TemperatureGauge(min_temp=0.0, max_temp=100.0)
temp_gauge.setTemperature(75.5)  # 设置温度
```

#### PHIndicator - pH指示器

pH值可视化显示组件。

**功能特性：**

- pH颜色条
- 当前值指示器
- 0-14 pH范围
- 颜色渐变

**使用示例：**

```python
from src.ui.experiment_widgets import PHIndicator

ph_indicator = PHIndicator()
ph_indicator.setPH(7.5)  # 设置pH值
```

#### ReactionProgressBar - 反应进度条

显示化学反应进度。

**功能特性：**

- 渐变色进度条
- 百分比显示
- 动画效果

**使用示例：**

```python
from src.ui.experiment_widgets import ReactionProgressBar

progress = ReactionProgressBar(label="反应进度")
progress.setProgress(75.0)  # 设置进度 (0-100)
```

#### Timer - 计时器组件

实验计时器。

**功能特性：**

- 开始/暂停/重置
- 时分秒显示
- 时间更新信号

**使用示例：**

```python
from src.ui.experiment_widgets import Timer

timer = Timer(label="实验计时")
timer.start()  # 开始计时
timer.time_updated.connect(on_time_update)  # 监听时间更新
```

---

### 2. 器材详情面板 (`equipment_detail_panel.py`)

#### EquipmentDetailPanel - 器材详情面板

显示器材的详细信息。

**功能特性：**

- 器材图片展示
- 属性和规格显示
- 危险性警告
- 操作按钮

**使用示例：**

```python
from src.ui.equipment_detail_panel import EquipmentDetailPanel

detail_panel = EquipmentDetailPanel()

# 显示器材信息
equipment_data = {
    "name": "烧杯 (100mL)",
    "type": "beaker",
    "category": "玻璃器皿",
    "description": "用于盛放液体的玻璃容器",
    "capacity": "100 mL",
    "hazard_level": 0,
    "image": "path/to/beaker.png"
}

detail_panel.show_equipment("beaker_100ml", equipment_data)

# 连接信号
detail_panel.use_clicked.connect(on_equipment_used)
detail_panel.info_requested.connect(on_info_requested)
```

#### CompactEquipmentCard - 紧凑型器材卡片

用于器材库展示的小卡片。

**使用示例：**

```python
from src.ui.equipment_detail_panel import CompactEquipmentCard

card = CompactEquipmentCard("beaker_100ml", equipment_data)
card.clicked.connect(on_card_clicked)
```

---

### 3. 实验工具栏 (`experiment_toolbar.py`)

#### ExperimentToolbar - 实验工具栏

完整功能的垂直工具栏。

**功能特性：**

- 分类工具展示
- 互斥工具选择
- 快捷操作按钮
- 工具提示

**使用示例：**

```python
from src.ui.experiment_toolbar import ExperimentToolbar

toolbar = ExperimentToolbar()

# 监听工具选择
toolbar.tool_selected.connect(on_tool_selected)

# 监听操作触发
toolbar.action_triggered.connect(on_action_triggered)

# 获取当前工具
current_tool = toolbar.get_current_tool()

# 设置工具
toolbar.set_tool("dropper")
```

#### CompactToolbar - 紧凑型工具栏

水平布局的精简工具栏。

**使用示例：**

```python
from src.ui.experiment_toolbar import CompactToolbar

compact_toolbar = CompactToolbar()
compact_toolbar.tool_selected.connect(on_tool_selected)
```

#### FloatingToolPalette - 浮动工具面板

可拖动的浮动工具面板。

**使用示例：**

```python
from src.ui.experiment_toolbar import FloatingToolPalette

palette = FloatingToolPalette()
palette.tool_selected.connect(on_tool_selected)
palette.show()
```

---

### 4. 实时数据可视化 (`realtime_chart_widgets.py`)

#### RealtimeLineChart - 实时折线图

用于显示时序数据。

**功能特性：**

- 实时数据更新
- 自动滚动
- 数据点显示
- 渐变填充

**使用示例：**

```python
from src.ui.realtime_chart_widgets import RealtimeLineChart

# 创建折线图
temp_chart = RealtimeLineChart(
    title="温度变化",
    y_label="温度(°C)",
    max_points=50,
    y_min=0.0,
    y_max=100.0
)

# 添加数据点
temp_chart.add_data_point(25.5, "1s")
temp_chart.add_data_point(26.2, "2s")

# 清空数据
temp_chart.clear_data()

# 设置Y轴范围
temp_chart.set_y_range(0.0, 150.0)
```

#### RealtimeBarChart - 实时柱状图

用于数据对比显示。

**使用示例：**

```python
from src.ui.realtime_chart_widgets import RealtimeBarChart
from PySide6.QtGui import QColor

bar_chart = RealtimeBarChart(title="数据对比", max_bars=10, y_max=100.0)

# 设置数据
bar_chart.set_data("试剂A", 75.5, QColor(0, 120, 212))
bar_chart.set_data("试剂B", 82.3, QColor(46, 204, 113))

# 清空数据
bar_chart.clear_data()
```

#### DataMonitorPanel - 数据监控面板

集成多个图表的监控面板。

**使用示例：**

```python
from src.ui.realtime_chart_widgets import DataMonitorPanel

monitor = DataMonitorPanel()

# 添加折线图
temp_chart = monitor.add_line_chart(
    "temperature",
    "温度变化",
    "温度(°C)",
    max_points=50,
    y_min=0.0,
    y_max=100.0
)

# 添加柱状图
comparison_chart = monitor.add_bar_chart(
    "comparison",
    "数据对比",
    max_bars=10,
    y_max=100.0
)

# 获取图表
chart = monitor.get_chart("temperature")

# 清空所有数据
monitor.clear_all_data()
```

#### GaugeWidget - 仪表盘组件

显示当前值的仪表盘。

**使用示例：**

```python
from src.ui.realtime_chart_widgets import GaugeWidget

gauge = GaugeWidget(
    title="温度",
    min_value=0.0,
    max_value=100.0,
    unit="°C"
)

gauge.setValue(75.5)
current_value = gauge.value()
```

---

### 5. 增强的交互场景 (`enhanced_interaction_scene.py`)

#### EnhancedInteractiveScene - 增强的交互式场景

带有更多反馈效果的交互场景。

**新增功能：**

- 粒子效果
- 发光效果
- 物品高亮
- 震动/弹跳动画
- 连接线
- 区域脉冲

**使用示例：**

```python
from src.ui.enhanced_interaction_scene import EnhancedInteractiveScene
from PySide6.QtCore import QPointF

# 创建场景
scene = EnhancedInteractiveScene(scene_config)

# 显示成功反馈
scene.show_success_feedback(QPointF(100, 100))

# 显示错误反馈
scene.show_error_feedback(QPointF(200, 200))

# 显示提示
scene.show_hint("请将烧杯放置到工作区", duration=3000)

# 高亮兼容区域
scene.highlight_compatible_zones(item)

# 验证放置
is_valid = scene.validate_drop("beaker_100ml")

# 物品动画
scene.shake_item("beaker_100ml")  # 震动
scene.bounce_item("flask_250ml")  # 弹跳
scene.pulse_zone("work_area")  # 区域脉冲

# 添加连接线
scene.add_connection_line("burette", "flask", QColor(100, 150, 255))

# 连接信号
scene.item_hovered.connect(on_item_hovered)
scene.zone_activated.connect(on_zone_activated)
scene.interaction_hint.connect(on_hint_changed)
```

#### EnhancedDraggableItem - 增强的可拖拽物品

带悬停效果和高亮的可拖拽物品。

**使用示例：**

```python
# 通过场景创建
item = scene.add_draggable_item(
    "beaker",
    "beaker",
    position=(100, 400),
    image_path="assets/images/beaker.png",
    size=(80, 100)
)

# 高亮物品
item.highlight(QColor(255, 215, 0))

# 取消高亮
item.unhighlight()
```

---

## 完整示例

查看 `examples/enhanced_interaction_demo.py` 获取完整的使用示例，包括：

1. 交互式场景的创建和使用
2. 所有UI组件的集成
3. 实时数据监控
4. 器材详情展示
5. 工具栏使用

### 运行示例

```bash
cd virtualchemlab开发
python examples/enhanced_interaction_demo.py
```

---

## 集成到现有实验

### 1. 在 ExperimentView 中使用新组件

```python
from src.ui.experiment_widgets import ValueSlider, Timer
from src.ui.realtime_chart_widgets import RealtimeLineChart

class MyExperimentView(ExperimentView):
    def init_ui(self):
        super().init_ui()

        # 添加温度滑块
        self.temp_slider = ValueSlider("温度", 0, 100, 25, "°C")
        self.step_layout.addWidget(self.temp_slider)

        # 添加计时器
        self.timer = Timer("计时")
        self.step_layout.addWidget(self.timer)

        # 添加数据图表
        self.chart = RealtimeLineChart("温度监测", "温度(°C)")
        self.step_layout.addWidget(self.chart)
```

### 2. 创建自定义交互场景

```python
from src.ui.enhanced_interaction_scene import EnhancedInteractiveScene
from src.ui.interactive_scene import InteractiveExperimentView

# 配置场景
scene_config = {
    "width": 800,
    "height": 600,
    "draggable_items": [...],
    "clickable_items": [...],
    "drop_zones": [...]
}

# 创建场景
scene = EnhancedInteractiveScene(scene_config)
view = InteractiveExperimentView(scene)

# 添加到布局
layout.addWidget(view)
```

---

## 样式自定义

所有组件都支持通过样式表自定义外观：

```python
component.setStyleSheet("""
    QWidget {
        background-color: #ffffff;
        border: 2px solid #dee2e6;
        border-radius: 8px;
    }
""")
```

---

## 性能优化建议

1. **图表更新频率**：控制数据更新频率，避免过于频繁的重绘
2. **粒子效果**：在低性能设备上可以禁用粒子效果
3. **动画**：根据需要启用/禁用动画效果
4. **数据点数量**：限制图表中的数据点数量

---

## 常见问题

### Q: 如何禁用粒子效果？

```python
scene.show_particles = False
```

### Q: 如何改变温度计的颜色范围？

温度计会根据温度自动改变颜色：

- 0-30%: 蓝色（冷）
- 30-70%: 黄色（温）
- 70-100%: 红色（热）

### Q: 如何实现自定义的交互反馈？

继承 `EnhancedInteractiveScene` 并重写相关方法：

```python
class MyScene(EnhancedInteractiveScene):
    def show_success_feedback(self, position):
        # 自定义成功反馈
        super().show_success_feedback(position)
        # 添加额外效果
```

---

## 更新日志

### v1.0.0 (2025-10-07)

- ✨ 新增实验交互组件库
- ✨ 新增器材详情面板
- ✨ 新增实验工具栏
- ✨ 新增实时数据可视化组件
- ✨ 增强交互式场景反馈效果
- 📝 添加完整使用示例

---

## 反馈与贡献

如有问题或建议，请提交Issue或Pull Request。
