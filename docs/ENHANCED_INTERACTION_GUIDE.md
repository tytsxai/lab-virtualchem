# 增强交互功能指南

## 📋 目录

1. [功能概览](#功能概览)
2. [手势交互系统](#手势交互系统)
3. [智能引导系统](#智能引导系统)
4. [增强反馈系统](#增强反馈系统)
5. [协作式实验](#协作式实验)
6. [录制与回放](#录制与回放)
7. [使用示例](#使用示例)
8. [最佳实践](#最佳实践)

---

## 功能概览

VirtualChemLab 2.0 引入了全面的交互增强功能，为用户提供更自然、更智能的实验操作体验。

### 核心特性

✨ **手势交互** - 支持多点触控和自定义手势  
🧠 **智能引导** - 上下文感知的实时帮助系统  
🎨 **增强反馈** - 视觉、音效和动画的综合反馈  
👥 **协作实验** - 多用户实时协作功能  
📹 **录制回放** - 操作录制和演示回放  

---

## 手势交互系统

### 支持的手势类型

#### 1. 基础手势

| 手势 | 操作 | 默认功能 | 说明 |
|------|------|----------|------|
| 单击 (Tap) | 单次点击 | 选择物品 | 快速选择实验器材 |
| 双击 (Double Tap) | 连续两次点击 | 确认/放大 | 确认选择或放大查看 |
| 长按 (Long Press) | 按住不放 | 上下文菜单 | 显示详细信息或选项 |

#### 2. 高级手势

| 手势 | 操作 | 默认功能 | 说明 |
|------|------|----------|------|
| 滑动 (Swipe) | 快速划过 | 切换/滚动 | 四个方向的快速导航 |
| 捏合 (Pinch) | 双指收缩/展开 | 缩放 | 缩放实验场景 |
| 旋转 (Rotate) | 双指旋转 | 旋转物体 | 调整器材角度 |
| 三指滑动 | 三指同时滑动 | 切换步骤 | 快速切换实验步骤 |

### 使用方法

#### Python 代码示例

```python
from src.ui.gesture_controller import GestureController, GestureType

# 创建手势控制器
gesture_controller = GestureController()

# 注册自定义动作处理器
def on_select_item(event):
    print(f"选择物品 @ {event.position}")

gesture_controller.register_action("select_item", on_select_item)

# 绑定手势到动作
gesture_controller.bind_gesture(GestureType.TAP, "select_item")

# 处理触摸事件
# gesture_controller.process_touch_event(touch_event)
```

#### 自定义手势绑定

```python
# 保存手势配置
gesture_controller.save_bindings("config/gestures.json")

# 加载手势配置
gesture_controller.load_bindings("config/gestures.json")
```

### 手势识别参数

可以调整以下参数来优化手势识别：

```python
recognizer = gesture_controller.recognizer

# 时间阈值（毫秒）
recognizer.tap_threshold = 200
recognizer.double_tap_threshold = 300
recognizer.long_press_threshold = 500

# 距离阈值（像素）
recognizer.swipe_threshold = 50
recognizer.pinch_threshold = 10

# 速度阈值（像素/秒）
recognizer.swipe_velocity_threshold = 100
```

---

## 智能引导系统

### 功能特点

1. **上下文感知** - 根据实验阶段和用户操作提供相关提示
2. **自适应学习** - 根据用户水平调整引导内容
3. **主动干预** - 检测困难时自动提供帮助
4. **多种引导类型** - 工具提示、教程、警告等

### 引导类型

#### GuideType 枚举

- `TOOLTIP` - 工具提示
- `HINT` - 提示信息
- `TUTORIAL` - 教程引导
- `WARNING` - 警告信息
- `SUCCESS` - 成功提示
- `ERROR` - 错误提示
- `INFO` - 一般信息

### 使用示例

#### 创建引导消息

```python
from src.ui.smart_guide_system import (
    SmartGuideSystem,
    GuideMessage,
    GuideType,
    GuidePriority
)

# 创建智能引导系统
guide_system = SmartGuideSystem()

# 创建引导消息
welcome_guide = GuideMessage(
    id="welcome",
    guide_type=GuideType.TUTORIAL,
    priority=GuidePriority.HIGH,
    title="欢迎使用虚拟化学实验室",
    content="这是您的第一个实验。我们将引导您完成每个步骤。",
    actions=[
        {"id": "start", "label": "开始"},
        {"id": "skip", "label": "跳过"}
    ],
    duration=0  # 0表示不自动关闭
)

# 显示引导
guide_system.show_guide(welcome_guide, parent_widget)
```

#### 添加引导规则

```python
# 添加基于条件的自动引导
guide_system.add_rule(
    rule_id="beginner_help",
    conditions={
        "user_level": "beginner",
        "step_type": "input"
    },
    guide=GuideMessage(
        id="input_help",
        guide_type=GuideType.HINT,
        priority=GuidePriority.NORMAL,
        title="数值输入提示",
        content="请输入准确的数值。系统会检查您的输入是否在允许范围内。",
        duration=5000
    )
)
```

#### 更新引导上下文

```python
# 更新上下文以触发相应引导
guide_system.update_context(
    experiment_id="EXP-001",
    step_index=3,
    step_type="input",
    user_level="beginner",
    user_mistakes=2
)
```

### 智能建议

```python
# 获取智能建议
current_state = {
    "step_time": 150,
    "mistakes": 3
}

suggestion = guide_system.get_suggestion(current_state)
if suggestion:
    print(suggestion)
    # 输出: "建议查看实验步骤详解或观看演示视频"
```

---

## 增强反馈系统

### 反馈类型

#### 1. 视觉反馈

- **缩放动画** (SCALE) - 放大缩小效果
- **淡入淡出** (FADE) - 透明度变化
- **抖动动画** (SHAKE) - 左右摇晃
- **弹跳动画** (BOUNCE) - 上下弹跳
- **发光效果** (GLOW) - 光晕效果
- **脉冲动画** (PULSE) - 颜色脉动
- **粒子效果** (PARTICLE) - 粒子爆发

#### 2. 音效反馈

- 成功提示音
- 错误提示音
- 警告音
- 操作音效
- 成就解锁音

### 使用示例

#### 基础反馈

```python
from src.ui.enhanced_feedback import (
    EnhancedFeedbackSystem,
    FeedbackType,
    AnimationType
)

# 创建反馈系统
feedback_system = EnhancedFeedbackSystem()

# 显示成功反馈
feedback_system.show_feedback(
    widget=button,
    feedback_type=FeedbackType.SUCCESS,
    animation_type=AnimationType.BOUNCE,
    duration=400,
    with_sound=True
)

# 显示错误反馈
feedback_system.show_feedback(
    widget=input_field,
    feedback_type=FeedbackType.ERROR,
    animation_type=AnimationType.SHAKE,
    duration=400,
    with_sound=True
)
```

#### 快捷方法

```python
# 成功效果（带消息）
feedback_system.show_success_effect(widget, "操作成功！")

# 错误效果（带消息）
feedback_system.show_error_effect(widget, "操作失败！")

# 成就效果（带粒子）
feedback_system.show_achievement_effect(
    widget,
    "完美实验",
    scene=graphics_scene
)
```

#### 粒子效果

```python
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

# 创建粒子效果
feedback_system.create_particle_effect(
    scene=graphics_scene,
    position=QPointF(200, 300),
    color=QColor(52, 152, 219),
    count=30,
    duration=1500
)
```

#### 音效控制

```python
# 启用/禁用音效
feedback_system.set_sound_enabled(True)

# 设置音量 (0.0-1.0)
feedback_system.set_sound_volume(0.7)

# 播放特定音效
feedback_system.play_sound(FeedbackType.SUCCESS)
```

---

## 协作式实验

### 功能特点

- **多用户角色** - 所有者、操作者、观察者、助手
- **实时同步** - 操作、光标、聊天同步
- **权限管理** - 基于角色的操作权限
- **实时聊天** - 内置聊天系统

### 用户角色

| 角色 | 权限 | 说明 |
|------|------|------|
| OWNER | 完全控制 | 实验创建者，拥有所有权限 |
| OPERATOR | 执行操作 | 可进行实验操作和数据输入 |
| OBSERVER | 仅观察 | 只能查看和聊天 |
| ASSISTANT | 协助操作 | 可协助操作但不能提交步骤 |

### 使用示例

#### 创建协作会话

```python
from src.ui.collaborative_experiment import (
    CollaborationManager,
    CollaboratorRole
)

# 创建管理器
collab_manager = CollaborationManager()

# 创建会话
session_id = collab_manager.create_session(
    owner_id="teacher_001",
    owner_name="张老师",
    experiment_id="EXP-001"
)

# 加入会话
collab_manager.join_session(
    session_id=session_id,
    user_id="student_001",
    user_name="学生A",
    role=CollaboratorRole.OPERATOR
)
```

#### 提交操作

```python
# 获取会话
session = collab_manager.get_session(session_id)

# 提交操作
session.submit_action(
    user_id="student_001",
    action_type=ActionType.ADD_EQUIPMENT,
    data={"equipment_id": "beaker_250ml", "position": (100, 200)}
)
```

#### 发送聊天消息

```python
# 发送消息
session.send_chat_message(
    user_id="student_001",
    message="我已经准备好器材了"
)
```

#### 创建协作界面

```python
from src.ui.collaborative_experiment import CollaborativeExperimentWidget

# 创建协作组件
collab_widget = CollaborativeExperimentWidget(
    session=session,
    current_user_id="student_001",
    parent=main_window
)

# 添加到布局
layout.addWidget(collab_widget)
```

---

## 录制与回放

### 功能特点

- **完整录制** - 记录所有用户操作
- **时间戳** - 精确的时间记录
- **可选截图** - 保存关键画面
- **回放控制** - 播放、暂停、快进、跳转
- **速度调节** - 0.25x - 2.0x 播放速度

### 录制功能

#### 开始录制

```python
from src.ui.experiment_recorder import ExperimentRecorder

# 创建录制器
recorder = ExperimentRecorder()

# 开始录制
recorder.start_recording(
    experiment_id="EXP-001",
    user_id="student_001",
    title="酸碱滴定实验",
    description="第一次完整录制"
)
```

#### 记录操作

```python
# 记录操作
recorder.record_action(
    action_type="click",
    target_id="beaker_001",
    data={"x": 100, "y": 200}
)

recorder.record_action(
    action_type="input",
    target_id="volume_input",
    data={"value": 25.0},
    user_input=25.0
)
```

#### 暂停和恢复

```python
# 暂停录制
recorder.pause_recording()

# 恢复录制
recorder.resume_recording()

# 停止录制
recording = recorder.stop_recording()
```

#### 保存录制

```python
from src.ui.experiment_recorder import save_recording

# 保存到文件
save_recording(recording, "recordings/titration_demo.json")
```

### 回放功能

#### 加载和播放

```python
from src.ui.experiment_recorder import (
    ExperimentPlayer,
    load_recording
)

# 创建播放器
player = ExperimentPlayer()

# 加载录制
recording = load_recording("recordings/titration_demo.json")
player.load_recording(recording)

# 开始播放
player.start_playback(speed=1.0)
```

#### 注册动作处理器

```python
# 注册处理器
def handle_click(action):
    print(f"点击: {action.target_id} @ {action.timestamp}")

player.register_action_handler("click", handle_click)
```

#### 播放控制

```python
# 暂停播放
player.pause_playback()

# 恢复播放
player.resume_playback()

# 停止播放
player.stop_playback()

# 跳转到指定位置 (0.0-1.0)
player.seek_to(0.5)  # 跳转到50%位置

# 设置播放速度
player.set_playback_speed(1.5)  # 1.5倍速
```

#### 创建播放界面

```python
from src.ui.experiment_recorder import PlayerControlWidget

# 创建播放控制组件
player_control = PlayerControlWidget(player)

# 添加到布局
layout.addWidget(player_control)
```

---

## 使用示例

### 完整实验流程

```python
from PySide6.QtWidgets import QApplication, QMainWindow
from src.ui.gesture_controller import GestureController
from src.ui.smart_guide_system import SmartGuideSystem
from src.ui.enhanced_feedback import EnhancedFeedbackSystem
from src.ui.experiment_recorder import ExperimentRecorder

class EnhancedExperimentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化所有系统
        self.gesture_controller = GestureController()
        self.guide_system = SmartGuideSystem()
        self.feedback_system = EnhancedFeedbackSystem()
        self.recorder = ExperimentRecorder()
        
        # 设置手势
        self.setup_gestures()
        
        # 设置引导
        self.setup_guides()
        
        # 开始录制
        self.recorder.start_recording(
            experiment_id="EXP-001",
            user_id="demo_user",
            title="演示实验"
        )
    
    def setup_gestures(self):
        # 注册动作处理器
        self.gesture_controller.register_action(
            "select_item",
            self.on_select_item
        )
        
        self.gesture_controller.register_action(
            "zoom",
            self.on_zoom
        )
    
    def setup_guides(self):
        # 设置引导上下文
        self.guide_system.update_context(
            experiment_id="EXP-001",
            step_index=0,
            step_type="confirm",
            user_level="beginner"
        )
    
    def on_select_item(self, event):
        # 记录操作
        self.recorder.record_action(
            "select",
            "item_001",
            {"position": (event.position.x(), event.position.y())}
        )
        
        # 显示反馈
        self.feedback_system.show_success_effect(
            self,
            "物品已选择"
        )
    
    def on_zoom(self, event):
        # 记录缩放
        self.recorder.record_action(
            "zoom",
            "scene",
            {"scale": event.scale}
        )

# 运行应用
app = QApplication([])
window = EnhancedExperimentWindow()
window.show()
app.exec()
```

### 实验模板配置

在 YAML 模板中启用交互功能：

```yaml
experiment:
  id: "EXP-001"
  title: "交互式实验"
  
  # 交互功能配置
  interaction:
    enable_gesture: true
    enable_smart_guide: true
    enable_feedback: true
    enable_recording: true
    enable_collaboration: true
  
  # 手势配置
  gestures:
    tap:
      - action: "select_equipment"
        description: "选择器材"
    swipe:
      - action: "switch_step"
        direction: "left"
        description: "下一步"
  
  # 引导配置
  smart_guide:
    user_level: "auto"
    show_welcome: true
    auto_hint_threshold: 3
    timeout_hint: 120
  
  # 反馈配置
  feedback:
    enable_sound: true
    enable_animation: true
    enable_particles: true
    success_animation: "bounce"
    error_animation: "shake"
```

---

## 最佳实践

### 1. 手势设计

✅ **推荐做法**
- 使用直观的手势映射（如捏合缩放）
- 提供手势教程和提示
- 支持传统鼠标/键盘操作作为备选

❌ **避免做法**
- 过度复杂的手势组合
- 容易误触的手势
- 没有视觉反馈的手势

### 2. 智能引导

✅ **推荐做法**
- 根据用户水平调整引导详细程度
- 在适当时机提供帮助（如多次错误后）
- 允许用户跳过或关闭引导

❌ **避免做法**
- 过于频繁的引导打断
- 千篇一律的引导内容
- 强制性的引导流程

### 3. 反馈设计

✅ **推荐做法**
- 提供即时、清晰的反馈
- 使用不同的反馈类型区分不同结果
- 允许用户自定义反馈强度

❌ **避免做法**
- 反馈延迟或不明显
- 过度的动画和音效干扰
- 缺少关键操作的反馈

### 4. 协作实验

✅ **推荐做法**
- 明确划分用户角色和权限
- 提供清晰的协作状态指示
- 实时同步所有重要操作

❌ **避免做法**
- 权限混乱导致冲突
- 缺少协作状态可见性
- 同步延迟影响体验

### 5. 录制回放

✅ **推荐做法**
- 记录完整的操作流程
- 提供灵活的回放控制
- 支持导出和分享

❌ **避免做法**
- 遗漏关键操作步骤
- 回放不流畅或不准确
- 文件过大难以分享

---

## 性能优化建议

### 1. 手势识别优化

```python
# 调整识别间隔
recognizer.update_interval = 50  # 毫秒

# 减少不必要的计算
recognizer.enable_detailed_tracking = False
```

### 2. 反馈系统优化

```python
# 限制并发动画数量
feedback_system.max_concurrent_animations = 5

# 使用轻量级反馈
feedback_system.use_lightweight_animations = True
```

### 3. 录制优化

```python
# 禁用截图以减小文件大小
recorder.record_screenshots = False

# 采样率控制
recorder.sampling_rate = 10  # 每秒10次
```

---

## 故障排除

### 常见问题

**Q: 手势识别不灵敏？**
A: 调整识别阈值参数，特别是 `swipe_threshold` 和 `tap_threshold`。

**Q: 引导提示不显示？**
A: 检查引导上下文是否正确更新，以及引导规则的条件是否匹配。

**Q: 反馈动画卡顿？**
A: 减少并发动画数量，或降低动画复杂度。

**Q: 协作同步延迟？**
A: 检查网络连接，考虑使用更高效的数据传输格式。

**Q: 录制文件过大？**
A: 禁用截图功能，减少采样率，或使用压缩格式。

---

## 更新日志

### v2.0.0 (2025-10-07)

- ✨ 新增手势交互系统
- ✨ 新增智能引导系统
- ✨ 新增增强反馈系统
- ✨ 新增协作式实验功能
- ✨ 新增录制与回放功能
- 📝 完善交互功能文档
- 🎨 优化用户体验

---

## 参考资源

- [手势交互 API 文档](../src/ui/gesture_controller.py)
- [智能引导 API 文档](../src/ui/smart_guide_system.py)
- [增强反馈 API 文档](../src/ui/enhanced_feedback.py)
- [协作实验 API 文档](../src/ui/collaborative_experiment.py)
- [录制回放 API 文档](../src/ui/experiment_recorder.py)
- [交互式实验模板（当前可用）](../assets/templates/titration_interactive.yaml)
- [交互式实验模板（简化版）](../assets/templates/simple_titration_interactive.yaml)

---

## 联系我们

如有问题或建议，请联系：

- GitHub Issues: https://github.com/VirtualChemLab/issues
- Email: support@virtualchemlab.com
- 文档反馈: docs@virtualchemlab.com

---

*最后更新: 2025-10-07*
