# 交互增强功能快速入门

## 🚀 5分钟上手指南

本指南将帮助你快速了解和使用 VirtualChemLab 的增强交互功能。

---

## 📦 第一步：安装和准备

### 检查依赖

```bash
# 确保已安装 PySide6
pip install PySide6>=6.5.0

# 可选：安装音效支持
pip install PySide6-Multimedia
```

### 验证安装

```bash
python -c "from src.ui.gesture_controller import GestureController; print('✅ 手势系统OK')"
python -c "from src.ui.smart_guide_system import SmartGuideSystem; print('✅ 引导系统OK')"
python -c "from src.ui.enhanced_feedback import EnhancedFeedbackSystem; print('✅ 反馈系统OK')"
```

---

## 🎮 第二步：运行演示程序

最快的体验方式是运行我们提供的演示程序：

```bash
python examples/interactive_experiment_demo.py
```

### 演示功能

点击顶部按钮体验各种功能：

1. **演示手势识别** - 查看支持的手势类型
2. **演示智能引导** - 体验上下文感知的提示
3. **演示反馈效果** - 观看各种动画效果
4. **开始录制** - 录制和回放操作
5. **演示协作功能** - 查看多用户协作

---

## 🎯 第三步：在实验中使用

### 方法1: 使用实验模板

创建或编辑你的实验模板YAML文件：

```yaml
experiment:
  id: "MY-EXP-001"
  title: "我的交互实验"
  
  # 启用交互功能
  interaction:
    enable_gesture: true        # 启用手势
    enable_smart_guide: true    # 启用智能引导
    enable_feedback: true       # 启用增强反馈
    enable_recording: true      # 启用录制
    enable_collaboration: false # 协作（可选）
  
  # 手势配置
  gestures:
    tap:
      - action: "select_equipment"
    swipe:
      - action: "switch_step"
        direction: "left"
  
  # 智能引导配置
  smart_guide:
    user_level: "beginner"
    auto_hint_threshold: 3
  
  # 反馈配置
  feedback:
    enable_sound: true
    enable_animation: true
    success_animation: "bounce"
    error_animation: "shake"

# ... 其他实验配置
```

### 方法2: 在代码中使用

```python
from PySide6.QtWidgets import QApplication, QMainWindow
from src.ui.gesture_controller import GestureController
from src.ui.smart_guide_system import SmartGuideSystem
from src.ui.enhanced_feedback import EnhancedFeedbackSystem

class MyExperimentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化交互系统
        self.gesture_controller = GestureController()
        self.guide_system = SmartGuideSystem()
        self.feedback_system = EnhancedFeedbackSystem()
        
        # 配置手势
        self.gesture_controller.register_action(
            "select_item",
            self.on_select
        )
        
        # 显示欢迎引导
        self.guide_system.update_context(
            experiment_id="MY-EXP-001",
            user_level="beginner"
        )
    
    def on_select(self, event):
        # 显示反馈
        self.feedback_system.show_success_effect(
            self,
            "选择成功！"
        )

app = QApplication([])
window = MyExperimentWindow()
window.show()
app.exec()
```

---

## 💡 常用功能速查

### 手势操作

| 想要做什么 | 手势操作 |
|-----------|---------|
| 选择器材 | 单击 (TAP) |
| 确认选择 | 双击 (DOUBLE_TAP) |
| 查看详情 | 长按 (LONG_PRESS) |
| 切换步骤 | 左/右滑动 (SWIPE) |
| 缩放场景 | 双指捏合 (PINCH) |
| 旋转物体 | 双指旋转 (ROTATE) |

### 代码示例

#### 1. 手势交互

```python
from src.ui.gesture_controller import GestureController, GestureType

# 创建控制器
gc = GestureController()

# 注册动作
def on_zoom(event):
    print(f"缩放: {event.scale}x")

gc.register_action("zoom", on_zoom)

# 绑定手势
gc.bind_gesture(GestureType.PINCH, "zoom")
```

#### 2. 智能引导

```python
from src.ui.smart_guide_system import SmartGuideSystem, GuideMessage, GuideType

# 创建引导系统
gs = SmartGuideSystem()

# 显示提示
guide = GuideMessage(
    id="tip_1",
    guide_type=GuideType.HINT,
    title="提示",
    content="这是一个有用的提示！"
)

gs.show_guide(guide, parent_widget)
```

#### 3. 增强反馈

```python
from src.ui.enhanced_feedback import EnhancedFeedbackSystem, FeedbackType, AnimationType

# 创建反馈系统
fs = EnhancedFeedbackSystem()

# 显示成功效果
fs.show_success_effect(widget, "操作成功！")

# 显示错误效果
fs.show_error_effect(widget, "操作失败！")

# 自定义反馈
fs.show_feedback(
    widget,
    FeedbackType.SUCCESS,
    AnimationType.BOUNCE,
    duration=400,
    with_sound=True
)
```

#### 4. 录制回放

```python
from src.ui.experiment_recorder import ExperimentRecorder, ExperimentPlayer

# 录制
recorder = ExperimentRecorder()
recorder.start_recording("EXP-001", "user_001", "我的录制")
recorder.record_action("click", "button_1", {"x": 100, "y": 200})
recording = recorder.stop_recording()

# 保存
from src.ui.experiment_recorder import save_recording
save_recording(recording, "my_recording.json")

# 加载和回放
from src.ui.experiment_recorder import load_recording
recording = load_recording("my_recording.json")

player = ExperimentPlayer()
player.load_recording(recording)
player.start_playback(speed=1.0)
```

#### 5. 协作实验

```python
from src.ui.collaborative_experiment import CollaborationManager, CollaboratorRole

# 创建管理器
cm = CollaborationManager()

# 创建会话
session_id = cm.create_session(
    owner_id="teacher_001",
    owner_name="张老师",
    experiment_id="EXP-001"
)

# 加入会话
cm.join_session(
    session_id,
    "student_001",
    "小明",
    CollaboratorRole.OPERATOR
)

# 获取会话
session = cm.get_session(session_id)

# 发送消息
session.send_chat_message("student_001", "我准备好了！")
```

---

## 🎨 界面组件使用

### 录制控制组件

```python
from src.ui.experiment_recorder import RecorderControlWidget

recorder = ExperimentRecorder()
control_widget = RecorderControlWidget(recorder)

# 添加到布局
layout.addWidget(control_widget)
```

### 回放控制组件

```python
from src.ui.experiment_recorder import PlayerControlWidget

player = ExperimentPlayer()
player_widget = PlayerControlWidget(player)

# 添加到布局
layout.addWidget(player_widget)
```

### 协作界面组件

```python
from src.ui.collaborative_experiment import CollaborativeExperimentWidget

collab_widget = CollaborativeExperimentWidget(
    session=session,
    current_user_id="user_001"
)

# 添加到布局
layout.addWidget(collab_widget)
```

---

## 🔧 配置和定制

### 手势参数调整

```python
recognizer = gesture_controller.recognizer

# 调整时间阈值（毫秒）
recognizer.tap_threshold = 200
recognizer.double_tap_threshold = 300
recognizer.long_press_threshold = 500

# 调整距离阈值（像素）
recognizer.swipe_threshold = 50
recognizer.pinch_threshold = 10
```

### 引导规则定制

```python
from src.ui.smart_guide_system import GuideMessage, GuidePriority

# 添加自定义规则
guide_system.add_rule(
    rule_id="my_rule",
    conditions={
        "user_level": "beginner",
        "step_type": "input",
        "user_mistakes": lambda x: x >= 2
    },
    guide=GuideMessage(
        id="help_input",
        guide_type=GuideType.HINT,
        priority=GuidePriority.HIGH,
        title="需要帮助吗？",
        content="看起来您在这一步遇到了困难...",
        actions=[
            {"id": "show_demo", "label": "查看演示"},
            {"id": "skip", "label": "跳过"}
        ]
    )
)
```

### 音效控制

```python
# 启用/禁用音效
feedback_system.set_sound_enabled(True)

# 设置音量 (0.0-1.0)
feedback_system.set_sound_volume(0.7)

# 播放特定音效
feedback_system.play_sound(FeedbackType.SUCCESS)
```

---

## 📊 完整示例：交互式滴定实验

```python
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from src.ui.gesture_controller import GestureController, GestureType
from src.ui.smart_guide_system import SmartGuideSystem
from src.ui.enhanced_feedback import EnhancedFeedbackSystem
from src.ui.experiment_recorder import ExperimentRecorder, RecorderControlWidget

class TitrationExperiment(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("交互式滴定实验")
        
        # 初始化所有系统
        self.gesture_controller = GestureController()
        self.guide_system = SmartGuideSystem()
        self.feedback_system = EnhancedFeedbackSystem()
        self.recorder = ExperimentRecorder()
        
        # 设置UI
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # 添加录制控制
        recorder_control = RecorderControlWidget(self.recorder)
        layout.addWidget(recorder_control)
        
        self.setCentralWidget(central)
        
        # 配置手势
        self.setup_gestures()
        
        # 配置引导
        self.setup_guides()
        
        # 开始录制
        self.recorder.start_recording(
            "TITRATION-001",
            "student_001",
            "滴定实验录制"
        )
    
    def setup_gestures(self):
        # 注册动作
        self.gesture_controller.register_action(
            "add_reagent",
            self.on_add_reagent
        )
        
        # 绑定手势
        self.gesture_controller.bind_gesture(
            GestureType.TAP,
            "add_reagent"
        )
    
    def setup_guides(self):
        # 设置上下文
        self.guide_system.update_context(
            experiment_id="TITRATION-001",
            step_index=0,
            step_type="interactive",
            user_level="beginner"
        )
    
    def on_add_reagent(self, event):
        # 记录操作
        self.recorder.record_action(
            "add_reagent",
            "burette",
            {"position": (event.position.x(), event.position.y())}
        )
        
        # 显示反馈
        self.feedback_system.show_success_effect(
            self,
            "试剂已添加"
        )
        
        # 更新引导
        self.guide_system.record_user_action("add_reagent")

# 运行
app = QApplication([])
window = TitrationExperiment()
window.show()
app.exec()
```

---

## 🐛 常见问题

### Q: 手势识别不灵敏？
**A**: 调整识别阈值参数：
```python
recognizer.swipe_threshold = 30  # 降低阈值
recognizer.tap_threshold = 300   # 增加时间容忍
```

### Q: 引导提示不显示？
**A**: 检查上下文配置：
```python
# 确保上下文已更新
guide_system.update_context(
    experiment_id="YOUR-EXP",
    step_index=0,
    user_level="beginner"
)
```

### Q: 音效不播放？
**A**: 检查音效是否启用：
```python
feedback_system.set_sound_enabled(True)
feedback_system.set_sound_volume(0.7)
```

### Q: 录制文件太大？
**A**: 禁用截图功能：
```python
recorder.record_screenshots = False
```

---

## 📚 下一步

### 深入学习
- 阅读 [完整使用指南](ENHANCED_INTERACTION_GUIDE.md)
- 查看 [功能总览](INTERACTION_ENHANCEMENTS_README.md)
- 研究示例模板 `assets/templates/interactive_experiment_template.yaml`

### 实践练习
1. 修改演示程序，添加自己的手势
2. 创建自定义的引导规则
3. 设计独特的反馈效果
4. 录制一个完整的实验操作

### 高级主题
- 网络协作实现
- AI辅助引导
- VR/AR集成
- 数据分析和可视化

---

## 🎉 完成！

恭喜你完成了快速入门！现在你已经掌握了：

✅ 如何启用交互功能  
✅ 如何使用手势控制  
✅ 如何配置智能引导  
✅ 如何添加增强反馈  
✅ 如何录制和回放  
✅ 如何进行协作实验  

开始创建你的交互式化学实验吧！ 🧪✨

---

**需要帮助？**
- 查看文档: `docs/ENHANCED_INTERACTION_GUIDE.md`
- 运行演示: `python examples/interactive_experiment_demo.py`
- 联系支持: support@virtualchemlab.com
