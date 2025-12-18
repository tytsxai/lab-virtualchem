"""Async task execution helpers (thread/process pools).

This module provides a thin abstraction for running CPU/IO tasks asynchronously
via thread/process executors and tracking their status.
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class AsyncTask:
    """异步任务信息"""

    task_id: str
    func: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    created_at: datetime
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Exception | None = None
    execution_time: float | None = None


class AsyncServiceManager:
    """异步服务管理器"""

    def __init__(self, max_workers: int = 4, max_processes: int = 2):
        """初始化异步服务管理器

        Args:
            max_workers: 线程池最大工作线程数
            max_processes: 进程池最大进程数
        """
        self.max_workers = max_workers
        self.max_processes = max_processes

        # 创建线程池和进程池
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=max_processes)

        # 任务管理
        self.tasks: dict[str, AsyncTask] = {}
        self.task_counter = 0
        self._lock = threading.Lock()

        logger.info(
            f"异步服务管理器已初始化 (线程池: {max_workers}, 进程池: {max_processes})"
        )

    def submit_task(
        self,
        func: Callable[..., Any],
        *args: Any,
        use_process: bool = False,
        **kwargs: Any,
    ) -> str:
        """提交异步任务

        Args:
            func: 要执行的函数
            *args: 函数参数
            use_process: 是否使用进程池
            **kwargs: 函数关键字参数

        Returns:
            任务ID
        """
        with self._lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{int(time.time())}"

        task = AsyncTask(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            created_at=datetime.now(),
        )

        self.tasks[task_id] = task

        # 选择执行器
        executor = self.process_pool if use_process else self.thread_pool

        # 提交任务
        future = executor.submit(self._execute_task, task)
        future.add_done_callback(lambda f: self._task_completed(task_id, f))

        logger.debug(f"任务已提交: {task_id}")
        return task_id

    def _execute_task(self, task: AsyncTask) -> Any:
        """执行任务"""
        task.status = "running"
        start_time = time.time()

        try:
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = "completed"
            logger.debug(f"任务执行成功: {task.task_id}")
            return result
        except Exception as e:
            task.error = e
            task.status = "failed"
            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
            raise
        finally:
            task.execution_time = time.time() - start_time

    def _task_completed(self, task_id: str, future: Any) -> None:
        """任务完成回调"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if future.exception():
                task.error = future.exception()
                task.status = "failed"
            else:
                task.result = future.result()
                task.status = "completed"

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "execution_time": task.execution_time,
            "result": task.result,
            "error": str(task.error) if task.error else None,
        }

    def wait_for_task(self, task_id: str, timeout: float | None = None) -> Any:
        """等待任务完成

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            任务结果
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        start_time = time.time()
        while task.status in ["pending", "running"]:
            if timeout and time.time() - start_time > timeout:
                raise TimeoutError(f"任务超时: {task_id}")
            time.sleep(0.1)

        if task.status == "failed" and task.error:
            raise task.error

        return task.result

    def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task or task.status not in ["pending", "running"]:
            return False

        # 注意：这里只是标记为取消，实际取消需要更复杂的实现
        task.status = "cancelled"
        logger.info(f"任务已取消: {task_id}")
        return True

    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """清理已完成的任务

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            清理的任务数量
        """
        cutoff_time = datetime.now().timestamp() - max_age_hours * 3600
        tasks_to_remove = []

        for task_id, task in self.tasks.items():
            if (
                task.status in ["completed", "failed", "cancelled"]
                and task.created_at.timestamp() < cutoff_time
            ):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.tasks[task_id]

        if tasks_to_remove:
            logger.info(f"清理了 {len(tasks_to_remove)} 个已完成的任务")

        return len(tasks_to_remove)

    def get_task_statistics(self) -> dict[str, Any]:
        """获取任务统计信息

        Returns:
            统计信息
        """
        status_counts: dict[str, int] = {}
        total_execution_time: float = 0
        completed_tasks = 0

        for task in self.tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
            if task.execution_time:
                total_execution_time += task.execution_time
                completed_tasks += 1

        return {
            "total_tasks": len(self.tasks),
            "status_counts": status_counts,
            "average_execution_time": total_execution_time / completed_tasks
            if completed_tasks > 0
            else 0,
            "total_execution_time": total_execution_time,
            "completed_tasks": completed_tasks,
        }

    def shutdown(self, wait: bool = True) -> None:
        """关闭服务管理器

        Args:
            wait: 是否等待所有任务完成
        """
        logger.info("正在关闭异步服务管理器...")

        if wait:
            # 等待所有任务完成
            while any(
                task.status in ["pending", "running"] for task in self.tasks.values()
            ):
                time.sleep(0.1)

        self.thread_pool.shutdown(wait=wait)
        self.process_pool.shutdown(wait=wait)

        logger.info("异步服务管理器已关闭")


# 全局异步服务管理器
async_service_manager = AsyncServiceManager()


def async_task(
    use_process: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., str]]:
    """异步任务装饰器

    Args:
        use_process: 是否使用进程池
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., str]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            task_id = async_service_manager.submit_task(
                func, *args, use_process=use_process, **kwargs
            )
            return task_id

        return wrapper

    return decorator


def async_method(
    use_process: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., str]]:
    """异步方法装饰器

    Args:
        use_process: 是否使用进程池
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., str]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> str:
            task_id = async_service_manager.submit_task(
                func, self, *args, use_process=use_process, **kwargs
            )
            return task_id

        return wrapper

    return decorator


class AsyncCache:
    """异步缓存"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """初始化异步缓存

        Args:
            max_size: 最大缓存条目数
            ttl: 生存时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

        logger.info(f"异步缓存已初始化 (最大大小: {max_size}, TTL: {ttl}秒)")

    def get(self, key: str) -> Any | None:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() - entry["timestamp"] < self.ttl:
                    return entry["value"]
                else:
                    # 过期，删除
                    del self.cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            # 检查缓存大小
            if len(self.cache) >= self.max_size:
                # 删除最旧的条目
                oldest_key = min(
                    self.cache.keys(), key=lambda k: self.cache[k]["timestamp"]
                )
                del self.cache[oldest_key]

            self.cache[key] = {"value": value, "timestamp": time.time()}

    def delete(self, key: str) -> bool:
        """删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()

    def cleanup_expired(self) -> int:
        """清理过期条目

        Returns:
            清理的条目数量
        """
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self.cache.items():
                if current_time - entry["timestamp"] >= self.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]

        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")

        return len(expired_keys)

    def get_statistics(self) -> dict[str, Any]:
        """获取缓存统计信息

        Returns:
            统计信息
        """
        with self._lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "keys": list(self.cache.keys()),
            }


# 全局异步缓存
async_cache = AsyncCache()


class AsyncRateLimiter:
    """异步速率限制器"""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

        logger.info(
            f"速率限制器已初始化 (最大请求: {max_requests}, 时间窗口: {time_window}秒)"
        )

    def is_allowed(self, key: str) -> bool:
        """检查请求是否被允许

        Args:
            key: 请求标识符

        Returns:
            是否允许请求
        """
        current_time = time.time()

        with self._lock:
            if key not in self.requests:
                self.requests[key] = []

            # 清理过期请求
            self.requests[key] = [
                req_time
                for req_time in self.requests[key]
                if current_time - req_time < self.time_window
            ]

            # 检查是否超过限制
            if len(self.requests[key]) >= self.max_requests:
                return False

            # 记录当前请求
            self.requests[key].append(current_time)
            return True

    def get_remaining_requests(self, key: str) -> int:
        """获取剩余请求数

        Args:
            key: 请求标识符

        Returns:
            剩余请求数
        """
        current_time = time.time()

        with self._lock:
            if key not in self.requests:
                return self.max_requests

            # 清理过期请求
            self.requests[key] = [
                req_time
                for req_time in self.requests[key]
                if current_time - req_time < self.time_window
            ]

            return max(0, self.max_requests - len(self.requests[key]))

    def reset(self, key: str) -> None:
        """重置请求计数

        Args:
            key: 请求标识符
        """
        with self._lock:
            if key in self.requests:
                del self.requests[key]


# 全局速率限制器
async_rate_limiter = AsyncRateLimiter()
