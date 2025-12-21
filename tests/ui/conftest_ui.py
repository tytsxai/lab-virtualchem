"""Supplementary fixtures for UI smoke tests running in offscreen mode."""

from __future__ import annotations

import os

import pytest
qtwidgets = pytest.importorskip("PySide6.QtWidgets")
qtgui = pytest.importorskip("PySide6.QtGui")

if not hasattr(qtgui.QPainter, "RenderHint"):
    pytest.skip(
        "Qt bindings missing QPainter.RenderHint; skipping UI tests",
        allow_module_level=True,
    )

QApplication = qtwidgets.QApplication

from src.ui.main_window import MainWindow
from tests.ui.fixtures.stub_services import build_stub_container


@pytest.fixture(scope="session", autouse=True)
def qt_offscreen_env():
    """Force Qt to use the offscreen platform for headless CI runs."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    yield


@pytest.fixture(scope="session")
def offscreen_qapp(qt_offscreen_env):
    """Session-scoped QApplication that respects the offscreen setting."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def stub_container():
    """Provide a lightweight DI container for UI components."""
    return build_stub_container()


@pytest.fixture
def main_window_stubbed(qtbot, stub_container, monkeypatch):
    """Create a MainWindow with heavy startup hooks disabled."""
    monkeypatch.setattr(MainWindow, "check_first_run", lambda self: None)
    monkeypatch.setattr(MainWindow, "show_startup_tip", lambda self: None)
    monkeypatch.setattr(MainWindow, "load_last_experiment", lambda self: None)

    window = MainWindow(container=stub_container)
    qtbot.addWidget(window)
    return window
