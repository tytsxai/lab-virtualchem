"""
错误边界组件测试
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel, QWidget

from src.ui.error_boundary import ErrorBoundary, SafeWidget, with_error_boundary


@pytest.fixture
def error_boundary(qtbot):
    """创建错误边界实例"""
    boundary = ErrorBoundary()
    qtbot.addWidget(boundary)
    return boundary


def test_error_boundary_creation(error_boundary):
    """测试错误边界创建"""
    assert error_boundary is not None
    assert not error_boundary.has_error
    assert error_boundary.error_info == ""


def test_error_boundary_with_child(qtbot):
    """测试带子组件的错误边界"""
    child = QLabel("Test Child")
    boundary = ErrorBoundary(child_widget=child)
    qtbot.addWidget(boundary)

    assert boundary.child_widget == child
    assert not boundary.has_error


def test_catch_error(error_boundary, qtbot):
    """测试捕获错误"""
    test_error = ValueError("Test error")

    with qtbot.waitSignal(error_boundary.error_occurred, timeout=1000):
        error_boundary.catch_error(test_error, "测试上下文")

    assert error_boundary.has_error
    assert "Test error" in error_boundary.error_info
    assert "测试上下文" in error_boundary.error_info


def test_fallback_widget(qtbot):
    """测试自定义降级组件"""
    fallback = QLabel("Error Fallback")
    child = QLabel("Normal Child")
    boundary = ErrorBoundary(child_widget=child, fallback_widget=fallback)
    qtbot.addWidget(boundary)

    # 触发错误
    boundary.catch_error(ValueError("Test"), "context")

    # 验证降级组件显示
    assert boundary.has_error


def test_retry(error_boundary, qtbot):
    """测试重试功能"""
    error_boundary.catch_error(ValueError("Test"), "context")
    assert error_boundary.has_error

    error_boundary.retry()
    assert not error_boundary.has_error
    assert error_boundary.error_info == ""


def test_set_child(error_boundary, qtbot):
    """测试设置子组件"""
    child1 = QLabel("Child 1")
    child2 = QLabel("Child 2")

    error_boundary.set_child(child1)
    assert error_boundary.child_widget == child1

    error_boundary.set_child(child2)
    assert error_boundary.child_widget == child2


def test_safe_widget(qtbot):
    """测试安全组件包装器"""
    safe_widget = SafeWidget()
    qtbot.addWidget(safe_widget)

    def success_func():
        return 42

    def fail_func():
        raise ValueError("Failed")

    # 成功调用
    result = safe_widget.safe_call(success_func)
    assert result == 42

    # 失败调用
    result = safe_widget.safe_call(fail_func)
    assert result is None


def test_with_error_boundary_decorator(qtbot):
    """测试错误边界装饰器"""

    class TestWidget(QWidget):
        pass

    wrapped = with_error_boundary(TestWidget)
    instance = wrapped()
    qtbot.addWidget(instance)

    assert isinstance(instance, ErrorBoundary)


def test_with_error_boundary_failed_creation(qtbot):
    """测试装饰器处理创建失败"""

    class BrokenWidget(QWidget):
        def __init__(self):
            raise ValueError("Cannot create")

    wrapped = with_error_boundary(BrokenWidget)
    instance = wrapped()
    qtbot.addWidget(instance)

    assert isinstance(instance, ErrorBoundary)
    assert instance.has_error


def test_on_error_callback(qtbot):
    """测试错误回调"""
    callback_called = []

    def on_error(error, info):
        callback_called.append((error, info))

    boundary = ErrorBoundary(on_error=on_error)
    qtbot.addWidget(boundary)

    test_error = ValueError("Test")
    boundary.catch_error(test_error, "context")

    assert len(callback_called) == 1
    assert callback_called[0][0] == test_error
