"""
进度反馈系统

提供任务进度管理、用户反馈和状态跟踪功能
"""

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    TypeVar,
)

from .event_system import EventBus, emit
from .types import ProgressCallback

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 暂停
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 取消


class TaskPriority(Enum):
    """任务优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskInfo:
    """任务信息"""

    id: str
    name: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    progress: float = 0.0  # 0.0 - 1.0
    total_steps: int = 0
    current_step: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """任务持续时间"""
        if self.started_at is None:
            return None
        end_time = self.completed_at or time.time()
        return end_time - self.started_at

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == TaskStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, task_id: str, total_steps: int = 0):
        self.task_id = task_id
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self._callbacks: list[ProgressCallback] = []
        self._lock = threading.RLock()

    def add_callback(self, callback: ProgressCallback) -> None:
        """添加进度回调"""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback) -> None:
        """移除进度回调"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def update(self, step: int | None = None, progress: float | None = None) -> None:
        """更新进度"""
        with self._lock:
            if step is not None:
                self.current_step = step
            if progress is not None:
                self.current_step = int(progress * self.total_steps)

            # 计算进度百分比
            if self.total_steps > 0:
                current_progress = self.current_step / self.total_steps
            else:
                current_progress = progress or 0.0

            # 触发回调
            for callback in self._callbacks:
                try:
                    callback(current_progress)
                except Exception as e:
                    logger.error(f"进度回调执行错误: {e}")

            # 发送事件
            emit(
                "progress.updated",
                {
                    "task_id": self.task_id,
                    "progress": current_progress,
                    "current_step": self.current_step,
                    "total_steps": self.total_steps,
                    "elapsed_time": time.time() - self.start_time,
                },
            )

    def complete(self) -> None:
        """完成进度"""
        self.update(progress=1.0)
        emit(
            "progress.completed",
            {"task_id": self.task_id, "total_time": time.time() - self.start_time},
        )

    def reset(self) -> None:
        """重置进度"""
        with self._lock:
            self.current_step = 0
            self.start_time = time.time()


class ITaskManager(ABC):
    """任务管理器接口"""

    @abstractmethod
    def create_task(
        self,
        name: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        total_steps: int = 0,
    ) -> str:
        """创建任务"""
        pass

    @abstractmethod
    def start_task(self, task_id: str) -> bool:
        """开始任务"""
        pass

    @abstractmethod
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        pass

    @abstractmethod
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        pass

    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        pass

    @abstractmethod
    def complete_task(self, task_id: str, error: str | None = None) -> bool:
        """完成任务"""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> TaskInfo | None:
        """获取任务信息"""
        pass

    @abstractmethod
    def get_all_tasks(self) -> list[TaskInfo]:
        """获取所有任务"""
        pass

    @abstractmethod
    def get_tracker(self, task_id: str) -> ProgressTracker | None:
        """获取进度跟踪器"""
        pass


class TaskManager(ITaskManager):
    """任务管理器实现"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self.tasks: dict[str, TaskInfo] = {}
        self.trackers: dict[str, ProgressTracker] = {}
        self._lock = threading.RLock()
        self._task_counter = 0

    def create_task(
        self,
        name: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        total_steps: int = 0,
    ) -> str:
        """创建任务"""
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}_{int(time.time())}"

            task = TaskInfo(
                id=task_id,
                name=name,
                description=description,
                priority=priority,
                total_steps=total_steps,
            )

            self.tasks[task_id] = task

            # 创建进度跟踪器
            if total_steps > 0:
                self.trackers[task_id] = ProgressTracker(task_id, total_steps)

            logger.info(f"创建任务: {task_id} - {name}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit(
                    "task.created",
                    {
                        "task_id": task_id,
                        "name": name,
                        "description": description,
                        "priority": priority.value,
                        "total_steps": total_steps,
                    },
                )

            return task_id

    def start_task(self, task_id: str) -> bool:
        """开始任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status != TaskStatus.PENDING:
                return False

            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            logger.info(f"开始任务: {task_id}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit(
                    "task.started", {"task_id": task_id, "name": task.name}
                )

            return True

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status != TaskStatus.RUNNING:
                return False

            task.status = TaskStatus.PAUSED

            logger.info(f"暂停任务: {task_id}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit(
                    "task.paused", {"task_id": task_id, "name": task.name}
                )

            return True

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status != TaskStatus.PAUSED:
                return False

            task.status = TaskStatus.RUNNING

            logger.info(f"恢复任务: {task_id}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit(
                    "task.resumed", {"task_id": task_id, "name": task.name}
                )

            return True

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()

            logger.info(f"取消任务: {task_id}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit(
                    "task.cancelled", {"task_id": task_id, "name": task.name}
                )

            return True

    def complete_task(self, task_id: str, error: str | None = None) -> bool:
        """完成任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                return False

            if error:
                task.status = TaskStatus.FAILED
                task.error = error
            else:
                task.status = TaskStatus.COMPLETED
                task.progress = 1.0

            task.completed_at = time.time()

            # 完成进度跟踪器
            if task_id in self.trackers:
                self.trackers[task_id].complete()

            logger.info(f"完成任务: {task_id} - {task.status.value}")

            # 发送事件
            if self.event_bus:
                self.event_bus.emit(
                    "task.completed",
                    {
                        "task_id": task_id,
                        "name": task.name,
                        "status": task.status.value,
                        "error": error,
                        "duration": task.duration,
                    },
                )

            return True

    def get_task(self, task_id: str) -> TaskInfo | None:
        """获取任务信息"""
        with self._lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[TaskInfo]:
        """获取所有任务"""
        with self._lock:
            return list(self.tasks.values())

    def get_tracker(self, task_id: str) -> ProgressTracker | None:
        """获取进度跟踪器"""
        with self._lock:
            return self.trackers.get(task_id)

    def update_task_progress(
        self, task_id: str, step: int | None = None, progress: float | None = None
    ) -> bool:
        """更新任务进度"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status != TaskStatus.RUNNING:
                return False

            if step is not None:
                task.current_step = step
            if progress is not None:
                task.progress = progress
                if task.total_steps > 0:
                    task.current_step = int(progress * task.total_steps)

            # 更新进度跟踪器
            if task_id in self.trackers:
                self.trackers[task_id].update(step, progress)

            return True

    def cleanup_completed_tasks(self, max_age: float = 3600) -> int:
        """清理已完成的任务"""
        with self._lock:
            current_time = time.time()
            to_remove = []

            for task_id, task in self.tasks.items():
                if (
                    task.is_completed
                    and task.completed_at
                    and current_time - task.completed_at > max_age
                ):
                    to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]
                if task_id in self.trackers:
                    del self.trackers[task_id]

            if to_remove:
                logger.info(f"清理了 {len(to_remove)} 个已完成的任务")

            return len(to_remove)


class ProgressBar:
    """进度条"""

    def __init__(
        self, width: int = 50, show_percentage: bool = True, show_eta: bool = True
    ):
        self.width = width
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.start_time = time.time()
        self.last_update = time.time()

    def render(
        self, progress: float, current: int = 0, total: int = 0, prefix: str = ""
    ) -> str:
        """渲染进度条"""
        # 限制进度范围
        progress = max(0.0, min(1.0, progress))

        # 计算进度条
        filled = int(progress * self.width)
        bar = "█" * filled + "░" * (self.width - filled)

        # 构建显示文本
        parts = [prefix] if prefix else []
        parts.append(f"[{bar}]")

        if self.show_percentage:
            parts.append(f"{progress:.1%}")

        if current > 0 and total > 0:
            parts.append(f"{current}/{total}")

        if self.show_eta and progress > 0:
            elapsed = time.time() - self.start_time
            eta = (elapsed / progress) * (1 - progress)
            parts.append(f"ETA: {self._format_time(eta)}")

        return " ".join(parts)

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m"
        else:
            return f"{seconds / 3600:.0f}h"


class ProgressDialog:
    """进度对话框"""

    def __init__(self, title: str = "进度", cancelable: bool = True):
        self.title = title
        self.cancelable = cancelable
        self.is_cancelled = False
        self.callbacks: list[Callable[[], None]] = []

    def add_cancel_callback(self, callback: Callable[[], None]) -> None:
        """添加取消回调"""
        self.callbacks.append(callback)

    def cancel(self) -> None:
        """取消"""
        self.is_cancelled = True
        for callback in self.callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"取消回调执行错误: {e}")


class ProgressNotifier:
    """进度通知器"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus
        self.notifications: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def notify(
        self, message: str, level: str = "info", task_id: str | None = None
    ) -> None:
        """发送通知"""
        notification = {
            "id": f"notif_{int(time.time() * 1000)}",
            "message": message,
            "level": level,
            "task_id": task_id,
            "timestamp": time.time(),
        }

        with self._lock:
            self.notifications.append(notification)

        # 发送事件
        if self.event_bus:
            self.event_bus.emit("progress.notification", notification)

        logger.info(f"进度通知: {message}")

    def get_notifications(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取通知"""
        with self._lock:
            return self.notifications[-limit:]


# 全局任务管理器
_global_task_manager = TaskManager()


def get_global_task_manager() -> TaskManager:
    """获取全局任务管理器"""
    return _global_task_manager


# 便捷函数
def create_task(
    name: str,
    description: str | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    total_steps: int = 0,
) -> str:
    """创建任务"""
    return _global_task_manager.create_task(name, description, priority, total_steps)


def start_task(task_id: str) -> bool:
    """开始任务"""
    return _global_task_manager.start_task(task_id)


def complete_task(task_id: str, error: str | None = None) -> bool:
    """完成任务"""
    return _global_task_manager.complete_task(task_id, error)


def update_progress(
    task_id: str, step: int | None = None, progress: float | None = None
) -> bool:
    """更新进度"""
    return _global_task_manager.update_task_progress(task_id, step, progress)


def get_task(task_id: str) -> TaskInfo | None:
    """获取任务信息"""
    return _global_task_manager.get_task(task_id)


def get_tracker(task_id: str) -> ProgressTracker | None:
    """获取进度跟踪器"""
    return _global_task_manager.get_tracker(task_id)


# 任务装饰器
def task(
    name: str,
    description: str | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
):
    """任务装饰器"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            task_id = create_task(name, description, priority)
            tracker = get_tracker(task_id)

            try:
                start_task(task_id)

                # 如果函数支持进度回调，传递跟踪器
                if tracker and "progress_callback" in func.__code__.co_varnames:
                    kwargs["progress_callback"] = tracker.update

                result = func(*args, **kwargs)
                complete_task(task_id)
                return result

            except Exception as e:
                complete_task(task_id, str(e))
                raise

        return wrapper

    return decorator


def async_task(
    name: str,
    description: str | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
):
    """异步任务装饰器"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args, **kwargs) -> T:
            task_id = create_task(name, description, priority)
            tracker = get_tracker(task_id)

            try:
                start_task(task_id)

                # 如果函数支持进度回调，传递跟踪器
                if tracker and "progress_callback" in func.__code__.co_varnames:
                    kwargs["progress_callback"] = tracker.update

                result = await func(*args, **kwargs)
                complete_task(task_id)
                return result

            except Exception as e:
                complete_task(task_id, str(e))
                raise

        return wrapper

    return decorator


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 进度反馈系统演示 ===\n")

    # 1. 基础任务管理
    logger.info("1. 基础任务管理:")

    task_id = create_task("数据处理", "处理大量数据", TaskPriority.HIGH, 100)
    tracker = get_tracker(task_id)

    if tracker:

        def progress_callback(progress):
            logger.info(f"进度: {progress:.1%}")

        tracker.add_callback(progress_callback)

    start_task(task_id)

    # 模拟进度更新
    for i in range(0, 101, 10):
        update_progress(task_id, step=i)
        time.sleep(0.1)

    complete_task(task_id)

    logger.info("")

    # 2. 任务装饰器
    logger.info("2. 任务装饰器:")

    @task("计算任务", "执行复杂计算", TaskPriority.NORMAL)
    def complex_calculation(
        n: int, progress_callback: ProgressCallback | None = None
    ) -> int:
        result = 0
        for i in range(n):
            result += i * i
            if progress_callback:
                progress_callback(i / n)
            time.sleep(0.01)
        return result

    result = complex_calculation(50)
    logger.info(f"计算结果: {result}")

    logger.info("")

    # 3. 进度条
    logger.info("3. 进度条:")

    progress_bar = ProgressBar(width=30, show_percentage=True, show_eta=True)

    for i in range(11):
        progress = i / 10
        bar_text = progress_bar.render(progress, i, 10, "处理中")
        logger.info(bar_text)
        time.sleep(0.2)

    logger.info("")

    # 4. 异步任务
    logger.info("4. 异步任务:")

    @async_task("异步任务", "执行异步操作", TaskPriority.HIGH)
    async def async_operation(
        duration: float, progress_callback: ProgressCallback | None = None
    ) -> str:
        steps = 10
        for i in range(steps):
            await asyncio.sleep(duration / steps)
            if progress_callback:
                progress_callback(i / steps)
        return "异步操作完成"

    async def run_async_demo():
        result = await async_operation(1.0)
        logger.info(f"异步任务结果: {result}")

    asyncio.run(run_async_demo())

    logger.info("进度反馈系统演示完成！")
