"""Compatibility wrapper for the main window module.

pytest-cov treats ``--cov=src/ui/main_window`` as a filesystem path. Historically,
the implementation lived in ``src/ui/main_window.py`` which meant the coverage
command in this repo collected no data.

We keep the public import path stable:

    from src.ui.main_window import MainWindow

by re-exporting the implementation from ``src.ui.main_window_impl``.
"""

from __future__ import annotations

from ..main_window_impl import MainWindow

__all__ = ["MainWindow"]

