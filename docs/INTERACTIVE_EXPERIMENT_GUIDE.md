# 交互式实验系统使用指南

## 概述

VirtualChemLab现在支持交互式实验模式，用户可以通过拖拽、点击等操作与虚拟实验环境进行真实的交互。

## 功能特性

### 1. 交互式场景 (InteractiveExperimentScene)

- **可拖拽物品**：实验器材可以自由拖拽到不同位置
- **可点击物品**：试剂瓶、工具等可以点击使用
- **放置区域**：定义特定区域接收特定类型的物品
- **状态管理**：实时跟踪所有物品的位置和状态

### 2. 实验器材库 (EquipmentLibrary)

- **分类展示**：按玻璃器皿、试剂、指示剂等分类
- **可视化卡片**：每个器材都有图标和详细信息
- **快速选择**：点击器材卡片即可添加到实验场景

### 3. 交互反馈系统 (InteractionFeedback)

- **动画效果**：
  - 拾取物品：缩放效果
  - 放下物品：弹跳效果
  - 错误提示：抖动效果
  - 成功提示：高亮闪烁

- **视觉反馈**：
  - 鼠标悬停高亮
  - 拖拽时半透明
  - 区域匹配提示

- **音效反馈**（可选）：
  - 点击音效
  - 拾取/放下音效
  - 成功/失败音效

## 使用方法

### 创建交互式实验

1. **在实验模板中启用交互模式**：

```yaml
experiment:
  id: "EXP-001"
  title: "我的交互式实验"

  metadata:
    interactive_mode: true  # 启用交互模式
    scene_config:
      width: 800
      height: 600
      background_color: "#f9f9f9"

      # 定义可拖拽物品
      draggable_items:
        - id: "beaker_100ml"
          type: "beaker"
          position: [100, 400]
          size: [80, 100]
          image: "beaker.png"

      # 定义可点击物品
      clickable_items:
        - id: "reagent_hcl"
          type: "reagent"
          position: [50, 50]
          size: [60, 80]
          image: "reagent_bottle.png"

      # 定义放置区域
      drop_zones:
        - id: "work_area"
          rect: [250, 300, 300, 250]
          accepted_types: ["beaker", "flask"]
```

2. **在步骤中添加交互式检查点**：

```yaml
steps:
  - id: "setup_equipment"
    text: "将烧杯放置到工作区域"
    check:
      type: "confirm"
      # 交互式检查：需要将烧杯拖拽到工作区域
      interactive_check:
        type: "drop"
        item_id: "beaker_100ml"
        zone_id: "work_area"
      fail_hint: "请将烧杯拖拽到工作区域"
```

### 学生端：进行交互式实验

1. **启动实验**：
   - 打开VirtualChemLab
   - 选择标记为"交互式"的实验
   - 点击"开始实验"

2. **操作实验器材**：
   - **拖拽**：点击并拖动器材到目标位置
   - **点击**：点击试剂瓶、工具等使用它们
   - **查看提示**：鼠标悬停在物品上查看提示信息

3. **完成检查点**：
   - 按照步骤说明操作
   - 完成指定的交互动作
   - 系统会自动验证并反馈

## 预设场景

系统内置了几个常用的实验场景配置：

### 1. 滴定实验场景 (titration)

- 滴定管
- 锥形瓶
- 试剂瓶
- 滴定架

### 2. 蒸馏实验场景 (distillation)

- 蒸馏瓶
- 冷凝管
- 接收瓶
- 酒精灯

### 3. 沉淀实验场景 (precipitation)

- 烧杯
- 试剂瓶
- 漏斗
- 过滤装置

## 开发者指南

### 自定义场景

```python
from src.ui.interactive_scene import InteractiveExperimentScene, ExperimentSceneBuilder

# 方法1：从配置创建
config = {
    "width": 800,
    "height": 600,
    "draggable_items": [...],
    "clickable_items": [...],
    "drop_zones": [...]
}
scene = ExperimentSceneBuilder.build_from_config(config)

# 方法2：程序化创建
scene = InteractiveExperimentScene()
scene.add_draggable_item("beaker", "beaker", (100, 400))
scene.add_drop_zone("work_area", (250, 300, 300, 250))
```

### 自定义动画效果

```python
from src.ui.interaction_feedback import AnimationHelper, FeedbackManager

# 使用内置动画
AnimationHelper.bounce(widget)  # 弹跳
AnimationHelper.shake(widget)   # 抖动
AnimationHelper.fade_in(widget) # 淡入

# 使用反馈管理器
feedback = FeedbackManager()
feedback.on_success(widget)  # 成功反馈
feedback.on_error(widget)    # 错误反馈
```

### 扩展器材库

```python
from src.ui.equipment_library import EquipmentLibrary

# 自定义器材数据
equipment_data = {
    "my_equipment": {
        "name": "我的器材",
        "type": "custom",
        "category": "自定义分类",
        "spec": "规格说明",
        "amount": "数量",
    }
}

library = EquipmentLibrary(equipment_data)
library.equipment_selected.connect(on_equipment_selected)
```

## 示例实验

系统提供了一个完整的交互式滴定实验示例：

**文件位置**：`assets/templates/titration_interactive.yaml`

**包含功能**：

- 滴定管的拖拽放置
- 试剂瓶的点击使用
- 锥形瓶的移动
- 指示剂的选择
- 实时反馈和提示

## 注意事项

1. **图片资源**：
   - 器材图片应放在 `assets/images/equipment/` 目录
   - 支持格式：PNG, JPG
   - 建议尺寸：100x100 像素左右

2. **性能优化**：
   - 场景中物品数量建议不超过20个
   - 大图片会自动缩放
   - 动画效果可以通过配置禁用

3. **兼容性**：
   - 传统实验模板仍然可用
   - 交互模式是可选的增强功能
   - 可以在同一个实验中混用传统和交互式检查点

## 故障排除

### 问题：场景显示空白

**解决方案**：

1. 检查模板中 `interactive_mode` 是否为 `true`
2. 检查 `scene_config` 配置是否正确
3. 查看日志文件中的错误信息

### 问题：物品无法拖拽

**解决方案**：

1. 确认物品类型为 `draggable_items`
2. 检查物品是否被锁定 (`is_locked`)
3. 确认鼠标事件没有被其他组件拦截

### 问题：动画效果不流畅

**解决方案**：

1. 减少场景中的物品数量
2. 降低动画时长 (duration)
3. 禁用不必要的视觉效果

## 反馈与建议

如有问题或建议，请联系开发团队或在项目仓库提交Issue。

---

**版本**：v1.0.0
**最后更新**：2025-10-07
