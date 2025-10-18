"""
通用后台任务线程
用于在不阻塞UI线程的情况下执行耗时任务，并提供进度与结果信号。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    """通用后台任务线程

    使用示例:
        def do_work(arg1, progress_emit=None):
            for i in range(100):
                ...
                if progress_emit:
                    progress_emit(i + 1)
            return result

        worker = TaskWorker(func=do_work, args=(...), kwargs={})
        worker.progress.connect(lambda v: ...)
        worker.finished_with_result.connect(lambda res: ...)
        worker.error.connect(lambda msg: ...)
        worker.start()
    """

    progress = Signal(int)
    message = Signal(str)
    error = Signal(str)
    finished_with_result = Signal(object)

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:  # noqa: D401 - Qt 线程入口
        try:
            # 为目标函数注入进度/消息回调（可选）
            if "progress_emit" not in self._kwargs:
                self._kwargs["progress_emit"] = self._emit_progress
            if "message_emit" not in self._kwargs:
                self._kwargs["message_emit"] = self._emit_message

            result = self._func(*self._args, **self._kwargs)
            self.finished_with_result.emit(result)
        except Exception as e:  # 由上层处理错误展示
            self.error.emit(str(e))

    def _emit_progress(self, value: int) -> None:
        self.progress.emit(int(value))

    def _emit_message(self, text: str) -> None:
        if text:
            self.message.emit(text)
