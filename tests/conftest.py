"""
测试配置文件
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Headless safety: ensure Qt uses an offscreen backend before importing PySide6.
# This avoids common segfault/bus-error crashes in CI or sandboxed environments.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")

# Make tests deterministic and avoid background threads/timers that can crash
# in headless Qt environments.
os.environ.setdefault("VCL_TEST_MODE", "1")
os.environ.setdefault("VCL_DISABLE_BACKGROUND_THREADS", "1")
os.environ.setdefault("VCL_DISABLE_STARTUP_TIPS", "1")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
# Prefer a lightweight PySide6 stub during test collection to avoid importing the
# real Qt bindings in sandboxed/headless environments (can segfault at import time).
stub_root = Path(__file__).parent / "fixtures" / "pyside6_stub"
if stub_root.is_dir() and os.environ.get("VCL_FORCE_PYSIDE6_STUB") in {"1", "true", "yes"}:
    sys.path.insert(0, str(stub_root))
else:
    # Only fall back to the stub when PySide6 is not importable in the current env.
    try:
        import PySide6  # noqa: F401
    except Exception:
        if stub_root.is_dir():
            sys.path.insert(0, str(stub_root))


class _SignalBlocker:
    """上下文管理器，用于等待信号"""

    def __init__(self, signal, timeout: int):
        self._signal = signal
        self._timeout = timeout
        self.args: list[Any] | None = None
        self._loop: QEventLoop | None = None
        self._timer: QTimer | None = None

    def __enter__(self):
        from PySide6.QtCore import QEventLoop, QTimer

        self._loop = QEventLoop()
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._loop.quit)
        self._signal.connect(self._on_signal)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._cleanup()
            return False

        if self.args is not None:
            self._cleanup()
            return False

        assert self._loop is not None
        assert self._timer is not None
        self._timer.start(self._timeout)
        self._loop.exec()
        self._cleanup()

        if self.args is None:
            raise AssertionError("Signal was not emitted before timeout")

        return False

    def _on_signal(self, *args):
        self.args = list(args)
        if self._loop is not None:
            self._loop.quit()

    def _cleanup(self):
        try:
            self._signal.disconnect(self._on_signal)
        except (TypeError, RuntimeError):
            pass
        loop_quit = self._loop.quit if self._loop else None
        if self._timer:
            try:
                if loop_quit:
                    self._timer.timeout.disconnect(loop_quit)  # type: ignore[arg-type]
            except (TypeError, RuntimeError):
                pass
            self._timer.stop()
        self._loop = None
        self._timer = None


class SimpleQtBot:
    """简化版qtbot，提供常用辅助方法"""

    def __init__(self, app: Any):
        self._app = app
        self._widgets: list[Any] = []

    def addWidget(self, widget) -> None:
        self._widgets.append(widget)

    def wait(self, ms: int) -> None:
        # QTest.qWait processes the Qt event loop safely in the main thread.
        from PySide6.QtTest import QTest

        QTest.qWait(ms)

    def waitExposed(self, widget, timeout: int = 200) -> None:
        # In offscreen mode there is no "exposed" window; just let events settle.
        # Avoid forcing repaint on complex widgets (OpenGL) which may crash headless.
        _ = widget
        self.wait(timeout)

    def waitSignal(self, signal, timeout: int = 1000) -> _SignalBlocker:
        return _SignalBlocker(signal, timeout)

    def waitUntil(
        self, condition: Callable[[], bool], timeout: int = 1000, interval: int = 10
    ) -> None:
        end_time = time.monotonic() + timeout / 1000
        while time.monotonic() < end_time:
            self._app.processEvents()
            if condition():
                return
            time.sleep(interval / 1000)
        raise AssertionError("Condition not met before timeout")


@pytest.fixture(scope="session")
def qapp():
    """Qt应用程序fixture"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # 测试结束后不关闭应用程序，避免影响其他测试


@pytest.fixture
def qtbot(qapp):
    """提供轻量级qtbot替代实现"""
    return SimpleQtBot(qapp)


@pytest.fixture
def temp_dir(tmp_path):
    """临时目录fixture"""
    return tmp_path


@pytest.fixture
def sample_config():
    """示例配置fixture"""
    return {
        "app": {
            "name": "TestApp",
            "version": "1.0.0",
            "language": "zh_CN",
            "theme": "dark",
        },
        "ui": {"font_size": 12, "font_family": "Arial", "animation_enabled": True},
        "game": {"physics_enabled": True, "gravity_strength": 0.5, "friction": 0.9},
    }


@pytest.fixture
def sample_experiment_template():
    """示例实验模板fixture"""
    return {
        "id": "test_experiment",
        "title": "测试实验",
        "description": "这是一个测试实验",
        "category": "general",
        "steps": [
            {"id": "step1", "text": "第一步：准备器材", "type": "preparation"},
            {"id": "step2", "text": "第二步：进行实验", "type": "experiment"},
        ],
    }
