# UI测试框架

## 概述

这是VirtualChemLab的UI自动化测试框架，基于pytest-qt构建。

## 安装依赖

```bash
pip install pytest pytest-qt
```

## 运行测试

### 运行所有UI测试

```bash
pytest tests/ui/
```

### 运行特定测试文件

```bash
pytest tests/ui/test_main_window.py
```

### 运行特定测试

```bash
pytest tests/ui/test_main_window.py::TestMainWindow::test_window_creation
```

### 详细输出

```bash
pytest tests/ui/ -v
```

### 显示print输出

```bash
pytest tests/ui/ -s
```

## 测试文件结构

```
tests/ui/
├── conftest.py                 # pytest配置和fixtures
├── test_main_window.py         # 主窗口测试
├── test_experiment_panel.py    # 实验面板测试
└── README.md                   # 本文件
```

## 编写新测试

### 基本模板

```python
"""
模块测试
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from src.ui.your_widget import YourWidget


class TestYourWidget:
    """Widget测试类"""

    @pytest.fixture
    def widget(self, qtbot):
        """创建widget fixture"""
        widget = YourWidget()
        qtbot.addWidget(widget)
        return widget

    def test_creation(self, widget):
        """测试创建"""
        assert widget is not None

    def test_button_click(self, widget, qtbot):
        """测试按钮点击"""
        button = widget.findChild(QPushButton, "myButton")
        qtbot.mouseClick(button, Qt.LeftButton)

        # 验证结果
        assert widget.some_property == expected_value
```

## 常用操作

### 鼠标操作

```python
# 左键点击
qtbot.mouseClick(button, Qt.LeftButton)

# 右键点击
qtbot.mouseClick(button, Qt.RightButton)

# 双击
qtbot.mouseDClick(button, Qt.LeftButton)

# 鼠标移动
qtbot.mouseMove(widget, pos=QPoint(100, 100))
```

### 键盘操作

```python
# 输入文本
qtbot.keyClicks(line_edit, "Hello World")

# 按键
qtbot.keyPress(widget, Qt.Key_Return)
qtbot.keyRelease(widget, Qt.Key_Return)

# 组合键
qtbot.keyPress(widget, Qt.Key_C, Qt.ControlModifier)
```

### 等待和信号

```python
# 等待指定时间（毫秒）
qtbot.wait(1000)

# 等待信号
with qtbot.waitSignal(widget.my_signal, timeout=1000):
    widget.trigger_action()

# 等待窗口显示
qtbot.waitExposed(window)
```

### 断言

```python
# 基本断言
assert widget.isVisible()
assert widget.isEnabled()
assert widget.text() == "Expected"

# 信号断言
with qtbot.assertNotEmitted(widget.error_signal):
    widget.safe_operation()
```

## 测试覆盖率

### 生成覆盖率报告

```bash
pytest tests/ui/ --cov=src/ui --cov-report=html
```

### 查看报告

打开 `htmlcov/index.html`

## 最佳实践

1. **使用fixtures**: 创建可复用的测试组件
2. **测试隔离**: 每个测试应该独立运行
3. **清晰命名**: 测试函数名应该描述测试内容
4. **最小化等待**: 只在必要时使用`qtbot.wait()`
5. **模拟数据**: 使用mock对象代替真实服务
6. **错误处理**: 测试正常和异常情况

## 调试技巧

### 显示窗口（用于调试）

```python
def test_visual_debug(widget, qtbot):
    widget.show()
    qtbot.wait(5000)  # 显示5秒
```

### 截图

```python
from PySide6.QtGui import QPixmap

def test_screenshot(widget, qtbot):
    widget.show()
    qtbot.waitExposed(widget)

    pixmap = widget.grab()
    pixmap.save("screenshot.png")
```

### 打印widget树

```python
def print_widget_tree(widget, indent=0):
    """打印widget层次结构"""
    print("  " * indent + widget.__class__.__name__)
    for child in widget.children():
        if isinstance(child, QWidget):
            print_widget_tree(child, indent + 1)
```

## 常见问题

### Q: 测试运行时出现 "QWidget: Must construct a QApplication before a QWidget"

A: 确保使用了`qapp` fixture（在conftest.py中定义）

### Q: 测试超时

A: 增加waitSignal的timeout参数，或检查信号是否正确触发

### Q: 测试在CI环境失败

A: CI环境可能没有显示器，使用xvfb-run:

```bash
xvfb-run pytest tests/ui/
```

## 参考资料

- [pytest-qt文档](https://pytest-qt.readthedocs.io/)
- [PyQt5文档](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [Qt Test Framework](https://doc.qt.io/qt-5/qtest.html)
