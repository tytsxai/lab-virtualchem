"""Qt 运行时自检工具。

目标：避免在同一进程中混用多个 Qt Python 绑定（PySide6 / PyQt6 / PyQt5）。
这种混用常表现为“随机崩溃”（SIGBUS/SIGSEGV），而不是 Python 异常。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Iterable


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _first_set(values: Iterable[str]) -> str | None:
    for v in values:
        if os.environ.get(v):
            return v
    return None


def ensure_single_qt_binding(*, abort: bool = True) -> None:
    """确保进程内不混用多个 Qt 绑定。

    Args:
        abort: 若检测到混用则退出进程（更安全）；否则仅抛出 RuntimeError。
    """

    loaded = {name for name in ("PySide6", "PyQt6", "PyQt5") if name in sys.modules}
    if len(loaded) <= 1:
        return

    message = (
        "Detected multiple Qt bindings loaded in the same process: "
        f"{', '.join(sorted(loaded))}. "
        "Do NOT mix PySide6/PyQt6/PyQt5 in one process; this often causes native crashes."
    )

    if abort:
        sys.stderr.write(f"\n[QtSanity] ERROR: {message}\n\n")
        raise SystemExit(1)
    raise RuntimeError(message)


def warn_if_multiple_bindings_installed() -> str | None:
    """如果安装了多个 Qt 绑定，返回警告字符串（不做 hard fail）。

    仅“安装多个”本身不一定会崩，但更容易被误导入导致混用。
    """

    installed = {name for name in ("PySide6", "PyQt6", "PyQt5") if _is_installed(name)}
    if len(installed) <= 1:
        return None
    return (
        "Multiple Qt bindings are installed: "
        f"{', '.join(sorted(installed))}. "
        "Prefer keeping only one to avoid accidental mixed imports."
    )


def warn_if_qt_path_polluted() -> str | None:
    """检测常见的 Qt 路径污染环境变量（可能导致加载到非预期的 Qt 插件/库）。"""

    key = _first_set(
        (
            "QT_PLUGIN_PATH",
            "QT_QPA_PLATFORM_PLUGIN_PATH",
            "DYLD_LIBRARY_PATH",
            "DYLD_FRAMEWORK_PATH",
            "PYTHONPATH",
        )
    )
    if not key:
        return None
    return (
        f"Environment variable {key} is set; if you see random Qt crashes, "
        "try launching with a clean environment to avoid loading mismatched Qt libraries."
    )
