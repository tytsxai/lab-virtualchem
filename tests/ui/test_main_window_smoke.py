"""Offscreen smoke tests for the modern MainWindow."""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QLabel, QPushButton

from src import __version__ as APP_VERSION

pytest_plugins = ["tests.ui.conftest_ui"]
pytestmark = pytest.mark.ui


def test_main_window_initializes_offscreen(main_window_stubbed, qtbot):
    """Window builds basic UI elements and shows version label offscreen."""
    window = main_window_stubbed
    window.show()
    qtbot.wait(50)

    assert os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    assert window.windowTitle()

    menu_bar = window.menuBar()
    assert menu_bar is not None
    assert menu_bar.actions()

    status_bar = window.statusBar()
    assert status_bar is not None

    refresh_btn = window.findChild(QPushButton, "refreshButton")
    assert refresh_btn is not None

    version_label = window.findChild(QLabel, "versionLabel")
    assert version_label is not None
    assert version_label.text() == f"v{APP_VERSION}"


def test_core_action_signals_emit(main_window_stubbed, qtbot):
    """Core action stubs emit signals even in offscreen mode."""
    window = main_window_stubbed

    action_cases = [
        (window.new_action_triggered, window.on_new_experiment),
        (window.open_action_triggered, window.on_open_experiment_stub),
        (window.save_action_triggered, lambda: window.emit_core_action_signal("save")),
        (window.run_action_triggered, window.on_run_experiment_stub),
        (window.stop_action_triggered, window.on_stop_experiment_stub),
    ]

    for signal, trigger in action_cases:
        with qtbot.waitSignal(signal, timeout=1000):
            trigger()
