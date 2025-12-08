"""Minimal PySide6 stub to satisfy test imports without GUI dependencies."""

from .QtCore import QEventLoop, QTimer
from .QtWidgets import QApplication

__all__ = ["QApplication", "QEventLoop", "QTimer"]
