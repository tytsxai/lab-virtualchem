# UI交互改进文档

本文档详细说明了虚拟化学实验室系统的UI交互改进功能。

## 📋 目录

- [改进概述](#改进概述)
- [进度对话框](#进度对话框)
- [输入验证组件](#输入验证组件)
- [拖拽操作增强](#拖拽操作增强)
- [布局管理器](#布局管理器)
- [工具提示增强](#工具提示增强)
- [使用示例](#使用示例)

---

## 改进概述

本次UI改进专注于提升用户体验，主要包括以下六个方面：

### ✅ 已完成的改进

1. **进度指示器** - 为耗时操作添加可视化进度反馈
2. **错误提示优化** - 使用用户友好的错误对话框
3. **输入验证** - 实时验证输入并提供视觉反馈
4. **拖拽反馈** - 增强拖拽操作的动画和视觉效果
5. **工具提示** - 为控件添加丰富的帮助信息
6. **布局切换** - 支持多种布局模式的动态切换

---

## 进度对话框

### 功能特点

- ✨ 实时进度显示
- ⏸️ 可选的取消功能
- 🎨 美观的现代化UI
- 🔄 后台线程执行，不阻塞UI

### 使用方法

#### 简单方式

```python
from src.ui.progress_dialog import SimpleProgressDialog

def my_task(progress_callback=None):
    """耗时任务"""
    for i in range(10):
        # 执行工作...
        if progress_callback:
            progress_callback((i + 1) * 10, f"处理步骤 {i + 1}")
    return "完成"

# 运行任务
success, message = SimpleProgressDialog.run(
    my_task,
    parent=self,
    title="数据处理",
    message="正在处理数据...",
    cancellable=True
)
```

#### 高级方式

```python
from src.ui.progress_dialog import ProgressDialog

dialog = ProgressDialog(
    parent=self,
    title="备份数据",
    message="正在备份实验数据...",
    cancellable=False,
    indeterminate=False  # False = 显示进度百分比
)

success = dialog.run_task(backup_function)
```

### 应用场景

- 📦 数据备份和恢复
- 📊 报告生成
- 📤 文件导入导出
- 🔄 批量数据处理
- 🗜️ 文件压缩解压

---

## 输入验证组件

### 功能特点

- ✓ 实时验证输入
- 🎨 视觉状态反馈（绿色=有效，红色=无效）
- 💡 智能错误提示
- ⚡ 延迟验证，提高性能
- 📝 预定义验证器

### 组件类型

#### 1. ValidatedLineEdit - 单行输入框

```python
from src.ui.validated_input import ValidatedLineEdit, Validators

# 邮箱输入
email_input = ValidatedLineEdit(
    validator=Validators.email,
    placeholder="请输入邮箱",
    required=True
)

# 检查是否有效
if email_input.is_valid():
    email = email_input.text()
```

#### 2. ValidatedNumberInput - 数字输入框

```python
from src.ui.validated_input import ValidatedNumberInput

temp_input = ValidatedNumberInput(
    min_value=0,
    max_value=100,
    decimals=1,
    unit="℃"
)

value = temp_input.value()  # 获取数值
```

#### 3. ValidatedComboBox - 下拉选择框

```python
from src.ui.validated_input import ValidatedComboBox

combo = ValidatedComboBox(
    required=True,
    placeholder="请选择..."
)
combo.addItem("选项1")
combo.addItem("选项2")

if combo.is_valid():
    selection = combo.currentText()
```

#### 4. InputWithLabel - 带标签的输入组

```python
from src.ui.validated_input import InputWithLabel

input_group = InputWithLabel(
    label="学生姓名",
    input_widget=name_input,
    required=True,
    help_text="请输入您的真实姓名"
)
```

### 预定义验证器

```python
from src.ui.validated_input import Validators

# 邮箱验证
email_validator = Validators.email

# 手机号验证
phone_validator = Validators.phone

# 数字范围验证
number_validator = Validators.number(min_val=0, max_val=100)

# 长度验证
min_length_validator = Validators.min_length(6)
max_length_validator = Validators.max_length(50)

# 正则表达式验证
pattern_validator = Validators.pattern(r'^[A-Z]\d{3}$', "格式: A123")
```

### 自定义验证器

```python
def custom_validator(text: str) -> tuple[bool, str]:
    """自定义验证逻辑

    Returns:
        (是否有效, 错误消息)
    """
    if len(text) < 3:
        return False, "至少需要3个字符"
    if not text.isalnum():
        return False, "只能包含字母和数字"
    return True, ""

input_field = ValidatedLineEdit(validator=custom_validator)
```

---

## 拖拽操作增强

### 功能特点

- 🎯 拖拽时物品放大和阴影效果
- ✨ 成功放入的闪烁动画
- 🔴 错误放入的抖动动画
- 🔙 自动返回原位动画
- 🌈 区域智能高亮（绿色=有效，红色=无效）
- 🎭 平滑的动画过渡

### 视觉反馈

#### 拖拽开始

```python
# 物品被拾起时:
- 透明度变为 0.8
- 缩放至 1.05 倍
- 显示阴影效果
- 光标变为抓取手型
```

#### 拖拽中

```python
# 物品在区域上悬停时:
- 有效区域显示绿色高亮
- 无效区域显示红色高亮
- 区域边框加粗
```

#### 放置成功

```python
# 成功放入区域时:
- 闪烁动画 (200ms)
- 恢复原始透明度
- 触发成功音效（可选）
```

#### 放置失败

```python
# 放入错误区域时:
- 左右抖动动画 (400ms)
- 保持在当前位置
- 或自动返回原位（可配置）
```

### 配置选项

```python
from src.ui.interactive_scene import DraggableItem

item = DraggableItem("beaker", "容器")

# 启用自动返回原位
item.snap_back_on_invalid_drop = True

# 锁定物品（禁止拖拽）
item.lock()

# 解锁物品
item.unlock()
```

---

## 布局管理器

### 功能特点

- 🎨 4种预设布局模式
- 💾 自动保存布局配置
- 🔄 平滑的布局切换
- 📐 智能调整组件大小
- 🎯 响应式设计

### 布局模式

#### 1. 经典布局 (Classic)

```
┌─────────┬──────────────────┐
│         │                  │
│ 实验列表  │   实验区域         │
│         │                  │
│         │                  │
└─────────┴──────────────────┘
侧边栏: 250px (25%)
实验区: 750px (75%)
```

#### 2. 现代布局 (Modern)

```
┌─────┬──────────────────────┐
│     │                      │
│列表 │   宽敞的实验区域       │
│     │                      │
│     │                      │
└─────┴──────────────────────┘
侧边栏: 200px (20%)
实验区: 800px (80%)
```

#### 3. 紧凑布局 (Compact)

```
┌─────────────────────────────┐
│                             │
│      全屏实验区域              │
│      (无侧边栏)               │
│                             │
└─────────────────────────────┘
实验区: 100%
隐藏工具栏和状态栏
```

#### 4. 宽屏布局 (Wide)

```
┌──────────┬─────────────────┐
│          │                 │
│  宽侧边栏 │   实验区域        │
│          │                 │
│          │                 │
└──────────┴─────────────────┘
侧边栏: 300px (30%)
实验区: 700px (70%)
```

### 使用方法

#### 在主窗口中集成

```python
from src.ui.layout_manager import LayoutManager, LayoutMode

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 创建布局管理器
        self.layout_manager = LayoutManager(self)

        # 切换布局
        self.layout_manager.switch_layout(LayoutMode.MODERN)

    def on_layout_menu_clicked(self, layout_type: str):
        """布局菜单点击"""
        self.layout_manager.switch_layout(layout_type)
```

#### 切换布局

```python
# 使用枚举
from src.ui.layout_manager import LayoutMode
layout_mgr.switch_layout(LayoutMode.CLASSIC)

# 使用字符串
layout_mgr.switch_layout("modern")

# 切换侧边栏显示
layout_mgr.toggle_sidebar()

# 切换工具栏显示
layout_mgr.toggle_toolbar()
```

### 布局配置

布局配置自动保存到：

- `QSettings`: 系统注册表/配置文件
- `data/layout_config.json`: JSON配置文件

配置内容：

```json
{
  "mode": "modern",
  "sidebar_width": 200,
  "toolbar_visible": true,
  "statusbar_visible": true,
  "sidebar_visible": true,
  "info_panel_height": 200
}
```

---

## 工具提示增强

### 功能特点

- 📝 富文本格式支持
- ⌨️ 自动显示快捷键
- 💡 智能提示和警告
- 🎨 美观的HTML样式
- 🔧 预定义常用提示

### 使用方法

#### 1. 简单增强

```python
from src.ui.tooltip_enhancer import TooltipEnhancer

# 使用预定义提示
button = QPushButton("保存")
TooltipEnhancer.enhance_widget(
    button,
    tooltip_key="save"  # 自动匹配预定义提示
)
```

#### 2. 带快捷键

```python
TooltipEnhancer.enhance_widget(
    save_button,
    tooltip_key="save",
    shortcut="Ctrl+S"
)
```

#### 3. 自定义提示

```python
TooltipEnhancer.enhance_widget(
    custom_button,
    custom_tooltip="这是自定义的工具提示\n支持多行文本"
)
```

#### 4. 批量增强

```python
# 自动增强容器中的所有控件
TooltipEnhancer.enhance_container(
    parent_widget,
    recursive=True
)
```

#### 5. 富文本提示

```python
from src.ui.tooltip_enhancer import RichTooltip

rich_tooltip = RichTooltip.create(
    title="高级功能",
    description="这是功能的详细描述",
    shortcuts=[
        ("保存", "Ctrl+S"),
        ("打开", "Ctrl+O")
    ],
    tips=[
        "可以使用拖拽操作",
        "支持批量处理"
    ],
    warnings=[
        "操作不可撤销",
        "请提前备份数据"
    ]
)

widget.setToolTip(rich_tooltip)
```

### 预定义提示

工具提示增强器包含60+个预定义的常用提示，涵盖：

- 🔘 按钮操作（开始、暂停、保存等）
- 🧪 实验操作（加热、冷却、搅拌等）
- ⚙️ 设置选项（语言、主题、通知等）
- 📝 输入字段（名称、学号、温度等）

### 全局样式

```python
# 设置全局工具提示样式
TooltipEnhancer.set_global_tooltip_style()
```

---

## 使用示例

### 完整示例：实验表单

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from src.ui.validated_input import ValidatedLineEdit, InputWithLabel, Validators
from src.ui.tooltip_enhancer import TooltipEnhancer
from src.ui.progress_dialog import SimpleProgressDialog

class ExperimentForm(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 带验证的输入
        self.name_input = ValidatedLineEdit(
            validator=Validators.min_length(2),
            placeholder="请输入姓名",
            required=True
        )
        name_group = InputWithLabel(
            "学生姓名",
            self.name_input,
            required=True,
            help_text="用于实验报告"
        )
        layout.addWidget(name_group)

        # 2. 提交按钮（带工具提示）
        submit_btn = QPushButton("提交实验")
        TooltipEnhancer.enhance_widget(
            submit_btn,
            custom_tooltip="提交实验数据并生成报告",
            shortcut="Ctrl+Enter"
        )
        submit_btn.clicked.connect(self.on_submit)
        layout.addWidget(submit_btn)

        # 3. 批量增强工具提示
        TooltipEnhancer.enhance_container(self)

    def on_submit(self):
        # 验证输入
        if not self.name_input.is_valid():
            return

        # 使用进度对话框处理提交
        def submit_task(progress_callback=None):
            # 验证数据
            if progress_callback:
                progress_callback(30, "验证数据...")
            time.sleep(1)

            # 生成报告
            if progress_callback:
                progress_callback(70, "生成报告...")
            time.sleep(1)

            # 保存
            if progress_callback:
                progress_callback(100, "保存完成")
            return "提交成功"

        success, msg = SimpleProgressDialog.run(
            submit_task,
            parent=self,
            title="提交实验",
            message="正在处理..."
        )
```

### 在主窗口中应用

```python
from src.ui.layout_manager import LayoutManager
from src.ui.tooltip_enhancer import TooltipEnhancer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. 初始化布局管理器
        self.layout_manager = LayoutManager(self)

        # 2. 设置全局工具提示样式
        TooltipEnhancer.set_global_tooltip_style()

        # 3. 创建UI
        self.init_ui()

        # 4. 批量增强所有控件
        TooltipEnhancer.enhance_container(self)

    def init_ui(self):
        # 创建菜单
        layout_menu = self.menuBar().addMenu("布局")

        layout_menu.addAction("经典布局").triggered.connect(
            lambda: self.layout_manager.switch_layout("classic")
        )
        layout_menu.addAction("现代布局").triggered.connect(
            lambda: self.layout_manager.switch_layout("modern")
        )
        layout_menu.addAction("紧凑布局").triggered.connect(
            lambda: self.layout_manager.switch_layout("compact")
        )
```

---

## 最佳实践

### 1. 进度指示器

✅ **推荐做法**

- 为所有超过1秒的操作添加进度指示
- 提供取消选项（如果操作可以安全中断）
- 显示有意义的状态消息

❌ **避免**

- 对瞬间完成的操作显示进度条
- 不提供任何状态更新

### 2. 输入验证

✅ **推荐做法**

- 使用延迟验证（300ms）避免频繁检查
- 提供清晰的错误消息
- 必填字段要明确标识

❌ **避免**

- 每次按键都立即验证
- 模糊的错误提示
- 隐藏必填字段要求

### 3. 拖拽操作

✅ **推荐做法**

- 提供清晰的视觉反馈
- 区分有效和无效的放置目标
- 考虑添加音效反馈

❌ **避免**

- 无动画的生硬操作
- 不明确的放置规则

### 4. 布局管理

✅ **推荐做法**

- 保存用户的布局偏好
- 提供布局预览
- 支持快捷键切换

❌ **避免**

- 频繁强制切换布局
- 不保存用户选择

### 5. 工具提示

✅ **推荐做法**

- 简洁明了的描述
- 包含快捷键信息
- 使用富文本增强可读性

❌ **避免**

- 过长的文本
- 重复按钮文本
- 纯技术术语

---

## 性能优化

### 输入验证性能

```python
# ✅ 使用延迟验证
validation_timer.start(300)  # 300ms延迟

# ❌ 避免立即验证
textChanged.connect(validate)  # 每次按键都验证
```

### 动画性能

```python
# ✅ 使用Qt动画框架
QPropertyAnimation(item, b"opacity")

# ✅ 保持动画引用
self._animations.append(animation)

# ❌ 避免过多同时动画
```

### 布局性能

```python
# ✅ 批量更新UI
self.setUpdatesEnabled(False)
# ... 进行多个更改 ...
self.setUpdatesEnabled(True)
```

---

## 故障排除

### 问题：进度对话框不显示

**原因**: 任务在主线程执行
**解决**: 使用 `ProgressWorker` 在后台线程运行

### 问题：输入验证不工作

**原因**: 验证器函数返回格式错误
**解决**: 确保返回 `tuple[bool, str]`

### 问题：拖拽动画卡顿

**原因**: 动画对象被垃圾回收
**解决**: 保存动画引用到实例变量

### 问题：布局切换没有效果

**原因**: 主窗口缺少必要的部件
**解决**: 确保主窗口有 `main_splitter`、`sidebar` 等属性

---

## 更新日志

### v2.0.0 (2024-10-08)

#### 新增

- ✨ 进度对话框组件
- ✨ 带验证的输入控件系列
- ✨ 拖拽操作视觉增强
- ✨ 布局管理器
- ✨ 工具提示增强系统

#### 改进

- 🎨 优化备份和恢复操作的用户体验
- 🎨 改进错误提示对话框
- 🎨 增强交互反馈动画

#### 文档

- 📚 添加完整的使用文档
- 📚 添加示例代码
- 📚 添加最佳实践指南

---

## 参考资源

- [Qt文档 - QGraphicsItem动画](https://doc.qt.io/qt-6/qgraphicsitem.html)
- [Qt文档 - 输入验证](https://doc.qt.io/qt-6/qvalidator.html)
- [Qt文档 - 布局管理](https://doc.qt.io/qt-6/layout.html)
- [示例代码](../examples/ui_improvements_demo.py)

---

## 联系支持

如有问题或建议，请：

- 📧 提交Issue
- 💬 联系开发团队
- 📖 查看完整文档

---

**文档版本**: 1.0.0
**最后更新**: 2024-10-08
**维护者**: VirtualChemLab开发团队

