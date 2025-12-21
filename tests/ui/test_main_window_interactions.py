"""Focused tests for MainWindow behaviors.

These tests aim to cover:
- window initialization (core widgets + title)
- menu creation
- signal/slot wiring
- error handling paths
"""

from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QMessageBox

pytest_plugins = ["tests.ui.conftest_ui"]
pytestmark = pytest.mark.ui


def _menu_titles(window) -> list[str]:
    menu_bar = window.menuBar()
    return [action.text() for action in menu_bar.actions()]


def test_window_initialization_sets_title_and_core_widgets(main_window_stubbed):
    window = main_window_stubbed

    assert window.windowTitle() == "VirtualChemLab"
    assert window.centralWidget() is not None
    assert window.statusBar() is not None

    assert window.main_stack is not None
    assert window.welcome_page is not None


def test_menu_bar_contains_expected_menus(main_window_stubbed):
    window = main_window_stubbed
    titles = _menu_titles(window)

    # Basic top-level menus created in create_menu_bar().
    assert "文件" in titles
    assert "编辑" in titles
    assert "工具" in titles
    assert "数据" in titles
    assert "窗口" in titles
    assert "帮助" in titles


def test_theme_changed_signal_is_connected_to_slot(main_window_stubbed, monkeypatch):
    window = main_window_stubbed
    called: list[str] = []

    def _fake_update():
        called.append("updated")

    monkeypatch.setattr(window, "update", _fake_update)

    window.theme_changed.emit("dark")
    assert called == ["updated"]


def test_emit_core_action_signal_unknown_does_not_emit(main_window_stubbed, qtbot):
    window = main_window_stubbed
    emitted: list[str] = []

    window.new_action_triggered.connect(lambda: emitted.append("new"))
    window.emit_core_action_signal("unknown-action")

    qtbot.wait(20)
    assert emitted == []


def test_handle_exception_keyboard_interrupt_delegates(main_window_stubbed, monkeypatch):
    window = main_window_stubbed
    called: list[tuple] = []

    def _fake_excepthook(exc_type, exc_value, exc_traceback):
        called.append((exc_type, exc_value, exc_traceback))

    monkeypatch.setattr(sys, "__excepthook__", _fake_excepthook)

    exc = KeyboardInterrupt()
    window.handle_exception(KeyboardInterrupt, exc, None)
    assert called
    assert called[0][0] is KeyboardInterrupt


def test_handle_exception_shows_critical_dialog(main_window_stubbed, monkeypatch):
    window = main_window_stubbed
    calls: list[tuple] = []

    def _fake_critical(parent, title, text):
        calls.append((parent, title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", _fake_critical)

    exc = ValueError("boom")
    window.handle_exception(ValueError, exc, None)

    assert calls
    parent, title, text = calls[0]
    assert parent is window
    assert "程序错误" in title
    assert "boom" in text
