"""
Qt 事件循环相关工具。

这里的目标是减少不安全的 `processEvents()` 使用：
- 如果没有 QApplication/QCoreApplication 实例，直接跳过
- 如果不在 Qt 主线程，直接跳过（避免跨线程驱动事件循环）
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QEventLoop, QThread


def process_events_safely(max_time_ms: int = 5) -> None:
    """在 Qt 主线程中以受控时间片处理事件。"""

    app = QCoreApplication.instance()
    if app is None:
        return

    if QThread.currentThread() != app.thread():
        return

    # Qt6 的 ProcessEventsFlag 没有 AllEvents；0 表示不排除任何事件类型。
    QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag(0), max_time_ms)

