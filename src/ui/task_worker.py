"""
任务工作器
提供后台任务执行功能
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TaskWorker(QObject):
    """任务工作器"""

    # 信号定义
    progress = Signal(int)  # 进度信号 (0-100)
    message = Signal(str)  # 消息信号
    finished = Signal(object)  # 完成信号
    error = Signal(str)  # 错误信号

    def __init__(self, task_func, *args, **kwargs):
        """初始化任务工作器

        Args:
            task_func: 任务函数
            *args: 任务函数参数
            **kwargs: 任务函数关键字参数
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.thread = QThread()
        self.moveToThread(self.thread)

        # 连接信号
        self.thread.started.connect(self.run_task)
        self.finished.connect(self.thread.quit)
        self.error.connect(self.thread.quit)

    def run_task(self):
        """运行任务"""
        try:
            logger.info("任务开始执行")
            self.message.emit("任务开始执行")

            # 执行任务
            result = self.task_func(*self.args, **self.kwargs)

            logger.info("任务执行完成")
            self.message.emit("任务执行完成")
            self.progress.emit(100)
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"任务执行失败: {e}"
            logger.error(error_msg)
            self.error.emit(error_msg)

    def start(self):
        """启动任务"""
        self.thread.start()

    def stop(self):
        """停止任务"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def cleanup(self):
        """清理资源"""
        self.stop()
        if hasattr(self, "thread"):
            self.thread.deleteLater()
