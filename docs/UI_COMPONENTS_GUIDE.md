# VirtualChemLab UI组件使用指南

**版本**: 2.0.0  
**最后更新**: 2025-10-07

---

## 📋 目录

- [概述](#概述)
- [主窗口 MainWindow](#主窗口-mainwindow)
- [实验视图 ExperimentView](#实验视图-experimentview)
- [游戏化组件](#游戏化组件)
- [现代化控件](#现代化控件)
- [自定义对话框](#自定义对话框)
- [主题系统](#主题系统)
- [动画系统](#动画系统)
- [粒子系统](#粒子系统)

---

## 概述

VirtualChemLab提供了丰富的UI组件库，基于PySide6 (Qt6)构建，具有现代化、响应式的设计。

### 核心特性

✅ **现代化设计** - 扁平化、简洁的视觉风格  
✅ **响应式布局** - 自适应不同屏幕尺寸  
✅ **主题系统** - 支持明暗主题和自定义主题  
✅ **动画效果** - 流畅的过渡和交互反馈  
✅ **游戏化元素** - 成就、等级、粒子效果等  
✅ **无障碍支持** - 键盘导航和屏幕阅读器支持  

---

## 主窗口 MainWindow

### 基础用法

```python
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.di_container import DIContainer

# 创建应用
app = QApplication(sys.argv)

# 创建DI容器
container = DIContainer()

# 创建主窗口
main_window = MainWindow(container=container)
main_window.show()

# 运行应用
sys.exit(app.exec())
```

### 核心功能

#### 1. 实验管理

```python
# 加载实验模板
main_window.load_experiment_template("titration.yaml")

# 开始新实验
main_window.start_new_experiment()

# 暂停实验
main_window.pause_experiment()

# 恢复实验
main_window.resume_experiment()

# 完成实验
main_window.complete_experiment()
```

#### 2. 菜单系统

```python
# 自定义菜单
from PySide6.QtGui import QAction

# 添加菜单项
action = QAction("自定义功能", main_window)
action.triggered.connect(custom_function)
main_window.tools_menu.addAction(action)

# 添加子菜单
submenu = main_window.tools_menu.addMenu("高级工具")
submenu.addAction(action)
```

#### 3. 状态栏

```python
# 显示状态消息
main_window.statusBar().showMessage("正在加载实验...", 3000)

# 显示永久消息
status_label = QLabel("已连接")
main_window.statusBar().addPermanentWidget(status_label)

# 显示进度
progress_bar = QProgressBar()
main_window.statusBar().addWidget(progress_bar)
```

#### 4. 信号和槽

```python
# 连接实验信号
main_window.experiment_started.connect(on_experiment_started)
main_window.experiment_completed.connect(on_experiment_completed)
main_window.theme_changed.connect(on_theme_changed)

def on_experiment_started(experiment_id: str):
    print(f"实验开始: {experiment_id}")

def on_experiment_completed(experiment_id: str, result: dict):
    print(f"实验完成: {experiment_id}, 得分: {result['score']}")

def on_theme_changed(theme_name: str):
    print(f"主题切换到: {theme_name}")
```

---

## 实验视图 ExperimentView

### 标准实验视图

```python
from src.ui.experiment_view import ExperimentView
from src.core.experiment_controller import ExperimentController

# 创建实验控制器
controller = ExperimentController(template, user_id="user123")

# 创建实验视图
experiment_view = ExperimentView(controller=controller, parent=main_window)

# 显示视图
main_window.setCentralWidget(experiment_view)

# 开始实验
experiment_view.start_experiment()
```

### 游戏化实验视图

```python
from src.ui.game_experiment_view import GameExperimentView

# 创建游戏化实验视图
game_view = GameExperimentView(
    controller=controller,
    enable_particles=True,
    enable_physics=True,
    parent=main_window
)

# 配置游戏参数
game_view.set_physics_config({
    "gravity": 9.8,
    "friction": 0.3,
    "restitution": 0.8
})

# 显示视图
main_window.setCentralWidget(game_view)
```

### 实验步骤控制

```python
# 执行下一步
experiment_view.next_step()

# 返回上一步
experiment_view.previous_step()

# 跳转到指定步骤
experiment_view.goto_step(3)

# 获取当前步骤
current_step = experiment_view.current_step_index

# 刷新步骤显示
experiment_view.refresh_step_display()
```

### 输入验证

```python
# 获取用户输入
input_data = experiment_view.get_step_input()

# 验证输入
is_valid = experiment_view.validate_input(input_data)

if is_valid:
    # 提交步骤
    experiment_view.submit_step(input_data)
else:
    # 显示错误
    experiment_view.show_input_error("输入数据无效")
```

---

## 游戏化组件

### 游戏化面板

```python
from src.ui.gamification.gamification_panel import GamificationPanel

# 创建游戏化面板
gamification_panel = GamificationPanel(user_id="user123", parent=main_window)

# 添加到主窗口
main_window.addDockWidget(Qt.RightDockWidgetArea, gamification_panel)

# 更新用户统计
gamification_panel.update_stats({
    "level": 5,
    "exp": 1250,
    "exp_to_next": 1500,
    "achievements": 12,
    "total_score": 9500
})
```

### 成就解锁对话框

```python
from src.ui.achievement_dialog import AchievementUnlockedDialog

# 显示成就解锁
achievement = {
    "id": "first_perfect",
    "name": "完美开局",
    "description": "首次获得满分",
    "icon": "🏆",
    "rarity": "rare",
    "exp_reward": 200
}

dialog = AchievementUnlockedDialog(achievement, parent=main_window)
dialog.exec()
```

### 升级对话框

```python
from src.ui.gamification.level_up_dialog import LevelUpDialog

# 显示升级对话框
level_up_data = {
    "old_level": 4,
    "new_level": 5,
    "rewards": ["新实验模板", "高级分析工具"],
    "next_level_exp": 1500
}

dialog = LevelUpDialog(level_up_data, parent=main_window)
dialog.exec()
```

### 进度指示器

```python
from src.ui.gamification.progress_indicator import CircularProgressIndicator

# 创建圆形进度指示器
progress = CircularProgressIndicator(parent=main_window)
progress.setMaximum(100)
progress.setValue(75)
progress.setText("75%")
progress.setColor(QColor("#4CAF50"))

# 动画更新进度
progress.animateTo(90, duration=1000)
```

---

## 现代化控件

### ModernButton

```python
from src.ui.modern_widgets import ModernButton

# 创建现代化按钮
button = ModernButton("开始实验", parent=main_window)

# 设置样式
button.setStyleType("primary")  # primary, secondary, success, danger, warning

# 设置图标
button.setIcon(QIcon("assets/icons/play.svg"))

# 设置圆角
button.setRounded(True)

# 连接信号
button.clicked.connect(start_experiment)
```

### ModernCard

```python
from src.ui.modern_widgets import ModernCard

# 创建卡片
card = ModernCard(parent=main_window)
card.setTitle("实验统计")
card.setIcon("📊")

# 添加内容
content_layout = QVBoxLayout()
content_layout.addWidget(QLabel("总实验数: 25"))
content_layout.addWidget(QLabel("平均分: 85"))
card.setContentLayout(content_layout)

# 设置阴影
card.setShadow(True)

# 添加到布局
layout.addWidget(card)
```

### ModernInput

```python
from src.ui.modern_widgets import ModernInput

# 创建输入框
input_field = ModernInput(parent=main_window)
input_field.setPlaceholder("输入实验名称...")
input_field.setLabel("实验名称")

# 设置验证
input_field.setValidator(QRegExpValidator(QRegExp("[A-Za-z0-9_]+")))

# 显示错误
input_field.setError("名称不能为空")

# 清除错误
input_field.clearError()

# 获取值
value = input_field.text()
```

### ModernComboBox

```python
from src.ui.modern_widgets import ModernComboBox

# 创建下拉框
combo = ModernComboBox(parent=main_window)
combo.setLabel("选择实验类型")

# 添加选项
combo.addItems(["滴定实验", "合成实验", "分析实验"])

# 设置图标
combo.setItemIcon(0, QIcon("assets/icons/titration.svg"))

# 监听变化
combo.currentTextChanged.connect(on_type_changed)
```

---

## 自定义对话框

### 设置对话框

```python
from src.ui.settings_dialog import SettingsDialog

# 创建设置对话框
settings_dialog = SettingsDialog(parent=main_window)

# 显示对话框
if settings_dialog.exec() == QDialog.Accepted:
    # 获取设置
    settings = settings_dialog.get_settings()
    apply_settings(settings)
```

### 配置对话框

```python
from src.ui.config_dialog import ConfigDialog

# 创建配置对话框
config_dialog = ConfigDialog(
    current_config=current_config,
    parent=main_window
)

# 显示对话框
if config_dialog.exec() == QDialog.Accepted:
    # 应用配置
    new_config = config_dialog.get_config()
    config_manager.update(new_config)
```

### 确认对话框

```python
from src.ui.modern_widgets import ModernMessageBox

# 创建确认对话框
msg_box = ModernMessageBox(
    title="确认删除",
    message="确定要删除这个实验吗？",
    icon=ModernMessageBox.Warning,
    parent=main_window
)

msg_box.addButton("删除", ModernMessageBox.AcceptRole)
msg_box.addButton("取消", ModernMessageBox.RejectRole)

if msg_box.exec() == ModernMessageBox.AcceptRole:
    # 执行删除
    delete_experiment()
```

---

## 主题系统

### 应用主题

```python
from src.ui.customization.theme_manager import ThemeManager, ThemeType

# 创建主题管理器
theme_manager = ThemeManager()

# 获取可用主题
themes = theme_manager.available_themes()
print(f"可用主题: {themes}")

# 应用主题
theme_manager.apply_theme(ThemeType.DARK)

# 自定义主题
custom_theme = {
    "primary_color": "#2196F3",
    "secondary_color": "#FFC107",
    "background_color": "#FFFFFF",
    "text_color": "#212121",
    "border_radius": 8,
    "shadow_enabled": True
}

theme_manager.create_theme("custom", custom_theme)
theme_manager.apply_theme("custom")
```

### 主题变量

```python
# 获取主题变量
primary_color = theme_manager.get_color("primary")
text_color = theme_manager.get_color("text")
border_radius = theme_manager.get_value("border_radius")

# 使用主题变量
button.setStyleSheet(f"""
    QPushButton {{
        background-color: {primary_color};
        color: white;
        border-radius: {border_radius}px;
    }}
""")
```

### 动态主题切换

```python
# 监听主题变化
theme_manager.theme_changed.connect(on_theme_changed)

def on_theme_changed(theme_name: str):
    # 更新UI
    update_all_widgets()
    
    # 保存偏好
    save_preference("theme", theme_name)
```

---

## 动画系统

### 属性动画

```python
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

# 创建透明度动画
animation = QPropertyAnimation(widget, b"windowOpacity")
animation.setDuration(500)
animation.setStartValue(0.0)
animation.setEndValue(1.0)
animation.setEasingCurve(QEasingCurve.InOutQuad)
animation.start()

# 创建移动动画
move_animation = QPropertyAnimation(widget, b"pos")
move_animation.setDuration(300)
move_animation.setStartValue(QPoint(0, 0))
move_animation.setEndValue(QPoint(100, 100))
move_animation.start()
```

### 顺序动画

```python
from PySide6.QtCore import QSequentialAnimationGroup

# 创建动画组
animation_group = QSequentialAnimationGroup()

# 添加动画
animation_group.addAnimation(fade_in_animation)
animation_group.addAnimation(move_animation)
animation_group.addAnimation(scale_animation)

# 播放动画组
animation_group.start()
```

### 并行动画

```python
from PySide6.QtCore import QParallelAnimationGroup

# 创建并行动画组
parallel_group = QParallelAnimationGroup()

# 同时执行多个动画
parallel_group.addAnimation(fade_animation)
parallel_group.addAnimation(scale_animation)
parallel_group.addAnimation(rotate_animation)

parallel_group.start()
```

---

## 粒子系统

### 基础粒子效果

```python
from src.ui.particle_system import ParticleSystem, ParticleType

# 创建粒子系统
particle_system = ParticleSystem(parent=main_window)

# 发射粒子
particle_system.emit(
    particle_type=ParticleType.SPARK,
    position=QPoint(100, 100),
    count=50,
    velocity=5.0,
    spread=360
)
```

### 粒子类型

```python
# 火花效果
particle_system.emit(ParticleType.SPARK, position, count=30)

# 烟雾效果
particle_system.emit(ParticleType.SMOKE, position, count=20)

# 爆炸效果
particle_system.emit(ParticleType.EXPLOSION, position, count=100)

# 泡泡效果
particle_system.emit(ParticleType.BUBBLE, position, count=15)

# 星星效果
particle_system.emit(ParticleType.STAR, position, count=25)
```

### 自定义粒子

```python
from src.ui.particle_system import Particle

# 创建自定义粒子
class CustomParticle(Particle):
    def __init__(self, position: QPoint):
        super().__init__(position)
        self.color = QColor("#FF5722")
        self.size = 10
        self.velocity = QPoint(5, -10)
        self.lifetime = 2.0
    
    def update(self, delta_time: float):
        # 更新粒子位置
        self.position += self.velocity * delta_time
        
        # 应用重力
        self.velocity.setY(self.velocity.y() + 9.8 * delta_time)
        
        # 减少生命值
        self.lifetime -= delta_time

# 注册自定义粒子
particle_system.register_particle_type("custom", CustomParticle)

# 发射自定义粒子
particle_system.emit("custom", position, count=50)
```

---

## 布局示例

### 响应式布局

```python
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout

# 创建主布局
main_layout = QVBoxLayout()

# 顶部工具栏
toolbar = QHBoxLayout()
toolbar.addWidget(ModernButton("新建"))
toolbar.addWidget(ModernButton("打开"))
toolbar.addWidget(ModernButton("保存"))
toolbar.addStretch()
main_layout.addLayout(toolbar)

# 中间内容区（网格布局）
content_grid = QGridLayout()
content_grid.addWidget(experiment_view, 0, 0, 2, 2)
content_grid.addWidget(gamification_panel, 0, 2)
content_grid.addWidget(stats_panel, 1, 2)
main_layout.addLayout(content_grid)

# 底部状态栏
status_layout = QHBoxLayout()
status_layout.addWidget(QLabel("就绪"))
main_layout.addLayout(status_layout)

# 应用布局
central_widget = QWidget()
central_widget.setLayout(main_layout)
main_window.setCentralWidget(central_widget)
```

### 分割器布局

```python
from PySide6.QtWidgets import QSplitter

# 创建水平分割器
splitter = QSplitter(Qt.Horizontal)

# 添加组件
splitter.addWidget(experiment_list)
splitter.addWidget(experiment_view)
splitter.addWidget(properties_panel)

# 设置初始大小
splitter.setSizes([200, 600, 200])

# 设置为中心部件
main_window.setCentralWidget(splitter)
```

---

## 事件处理

### 鼠标事件

```python
from PySide6.QtCore import Qt

class CustomWidget(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            print(f"左键点击: {event.pos()}")
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            print(f"拖动: {event.pos()}")
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        print("鼠标释放")
        super().mouseReleaseEvent(event)
```

### 键盘事件

```python
class CustomWidget(QWidget):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            print("按下空格键")
        elif event.key() == Qt.Key_Return:
            print("按下回车键")
        elif event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                print("Ctrl+S: 保存")
        super().keyPressEvent(event)
```

### 自定义事件

```python
from PySide6.QtCore import QEvent

class CustomEvent(QEvent):
    EventType = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, data):
        super().__init__(CustomEvent.EventType)
        self.data = data

class CustomWidget(QWidget):
    def event(self, event):
        if event.type() == CustomEvent.EventType:
            print(f"收到自定义事件: {event.data}")
            return True
        return super().event(event)

# 发送自定义事件
event = CustomEvent({"message": "Hello"})
QApplication.postEvent(widget, event)
```

---

## 最佳实践

### 1. 内存管理

```python
# 好的做法：设置父对象
widget = QWidget(parent=main_window)  # 自动管理内存

# 避免：不设置父对象
widget = QWidget()  # 可能导致内存泄漏
```

### 2. 信号连接

```python
# 好的做法：使用弱引用
from weakref import WeakMethod

widget.signal.connect(WeakMethod(self.handler))

# 或及时断开连接
widget.signal.disconnect(self.handler)
```

### 3. 线程安全

```python
# 好的做法：在主线程更新UI
from PySide6.QtCore import QMetaObject, Qt

def update_ui():
    QMetaObject.invokeMethod(
        widget,
        "setText",
        Qt.QueuedConnection,
        Q_ARG(str, "新文本")
    )

# 或使用信号
class Worker(QThread):
    update_signal = Signal(str)
    
    def run(self):
        result = heavy_computation()
        self.update_signal.emit(result)
```

### 4. 性能优化

```python
# 批量更新
widget.setUpdatesEnabled(False)
# 进行多个更新操作
widget.setUpdatesEnabled(True)
widget.update()

# 使用虚拟列表
from src.ui.virtual_list import VirtualListWidget

virtual_list = VirtualListWidget()
virtual_list.setItemCount(10000)  # 高效处理大量数据
```

---

## 参考资料

- [PySide6 官方文档](https://doc.qt.io/qtforpython/)
- [Qt6 文档](https://doc.qt.io/)
- [API_REFERENCE.md](API_REFERENCE.md) - VirtualChemLab API参考
- [CODE_STYLE_GUIDE.md](CODE_STYLE_GUIDE.md) - 代码规范

---

**更新历史**:
- 2025-10-07: 初始版本，包含所有UI组件使用说明

---

💡 **提示**: 使用现代化组件库可以快速构建美观、一致的界面。


