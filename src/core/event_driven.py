"""Event-driven primitives (EventBus).

This module implements an in-process event bus with optional async handling.
It is designed for decoupling components within a single process, not for
distributed messaging.
"""

import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""

    # 实验相关事件
    EXPERIMENT_CREATED = "experiment.created"
    EXPERIMENT_STARTED = "experiment.started"
    EXPERIMENT_PAUSED = "experiment.paused"
    EXPERIMENT_RESUMED = "experiment.resumed"
    EXPERIMENT_COMPLETED = "experiment.completed"
    EXPERIMENT_CANCELLED = "experiment.cancelled"

    # 步骤相关事件
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    STEP_RETRY = "step.retry"

    # 用户相关事件
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"

    # 系统相关事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"

    # 缓存相关事件
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"
    CACHE_EVICTED = "cache.evicted"

    # 数据库相关事件
    DATABASE_CONNECTED = "database.connected"
    DATABASE_DISCONNECTED = "database.disconnected"
    DATABASE_QUERY = "database.query"
    DATABASE_ERROR = "database.error"


@dataclass
class Event:
    """事件基类"""

    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: f"evt_{int(time.time() * 1000)}")
    source: str = "system"
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
            "source": self.source,
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """从字典创建事件"""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_id=data["event_id"],
            source=data["source"],
            data=data["data"],
            metadata=data["metadata"],
        )


@dataclass
class EventHandler:
    """事件处理器"""

    handler_id: str
    event_types: list[EventType]
    handler_func: Callable[[Event], None]
    priority: int = 0  # 优先级，数字越小优先级越高
    async_handler: bool = False
    enabled: bool = True

    def can_handle(self, event: Event) -> bool:
        """检查是否可以处理事件"""
        return self.enabled and event.event_type in self.event_types

    def handle(self, event: Event) -> None:
        """处理事件"""
        if self.can_handle(event):
            try:
                self.handler_func(event)
            except Exception as e:
                logger.error(f"事件处理器 {self.handler_id} 处理失败: {e}")


class EventBus:
    """事件总线"""

    def __init__(self, max_queue_size: int = 1000):
        """初始化事件总线

        Args:
            max_queue_size: 最大队列大小
        """
        self.max_queue_size = max_queue_size
        self.handlers: dict[str, EventHandler] = {}
        self.event_queue: queue.Queue[Event] = queue.Queue(maxsize=max_queue_size)
        self.running = False
        self.worker_thread: threading.Thread | None = None
        self._lock = threading.RLock()

        # 统计信息
        self.stats = {
            "events_published": 0,
            "events_processed": 0,
            "events_failed": 0,
            "handlers_registered": 0,
            "queue_size": 0,
        }

        logger.info("事件总线已初始化")

    def register_handler(self, handler: EventHandler) -> None:
        """注册事件处理器

        Args:
            handler: 事件处理器
        """
        with self._lock:
            self.handlers[handler.handler_id] = handler
            self.stats["handlers_registered"] += 1
            logger.info(f"注册事件处理器: {handler.handler_id}")

    def unregister_handler(self, handler_id: str) -> bool:
        """注销事件处理器

        Args:
            handler_id: 处理器ID

        Returns:
            是否成功注销
        """
        with self._lock:
            if handler_id in self.handlers:
                del self.handlers[handler_id]
                self.stats["handlers_registered"] -= 1
                logger.info(f"注销事件处理器: {handler_id}")
                return True
            return False

    def publish(self, event: Event) -> bool:
        """发布事件

        Args:
            event: 事件

        Returns:
            是否成功发布
        """
        try:
            self.event_queue.put_nowait(event)
            with self._lock:
                self.stats["events_published"] += 1
                self.stats["queue_size"] = self.event_queue.qsize()
            logger.debug(f"发布事件: {event.event_type.value} ({event.event_id})")
            return True
        except queue.Full:
            logger.warning(f"事件队列已满，丢弃事件: {event.event_type.value}")
            return False

    def publish_sync(self, event: Event) -> None:
        """同步发布事件（立即处理）

        Args:
            event: 事件
        """
        self._process_event(event)

    def _process_event(self, event: Event) -> None:
        """处理事件

        Args:
            event: 事件
        """
        # 找到可以处理此事件的处理器
        eligible_handlers = [
            handler for handler in self.handlers.values() if handler.can_handle(event)
        ]

        # 按优先级排序
        eligible_handlers.sort(key=lambda h: h.priority)

        # 执行处理器
        for handler in eligible_handlers:
            try:
                handler.handle(event)
                with self._lock:
                    self.stats["events_processed"] += 1
            except Exception as e:
                logger.error(f"事件处理器 {handler.handler_id} 处理失败: {e}")
                with self._lock:
                    self.stats["events_failed"] += 1

    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self.running:
            try:
                # 从队列获取事件
                event = self.event_queue.get(timeout=1)

                # 处理事件
                self._process_event(event)

                # 标记任务完成
                self.event_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"事件总线工作线程错误: {e}")

    def start(self) -> None:
        """启动事件总线"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        logger.info("事件总线已启动")

    def stop(self) -> None:
        """停止事件总线"""
        if not self.running:
            return

        self.running = False

        if self.worker_thread:
            self.worker_thread.join(timeout=5)

        logger.info("事件总线已停止")

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        with self._lock:
            return {
                "running": self.running,
                "queue_size": self.event_queue.qsize(),
                "max_queue_size": self.max_queue_size,
                "handlers_count": len(self.handlers),
                **self.stats,
            }

    def clear_queue(self) -> int:
        """清空事件队列

        Returns:
            清空的事件数量
        """
        cleared_count = 0
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
                cleared_count += 1
            except queue.Empty:
                break

        with self._lock:
            self.stats["queue_size"] = self.event_queue.qsize()

        logger.info(f"清空了 {cleared_count} 个事件")
        return cleared_count


class EventStore:
    """事件存储"""

    def __init__(self, max_events: int = 10000):
        """初始化事件存储

        Args:
            max_events: 最大事件数量
        """
        self.max_events = max_events
        self.events: list[Event] = []
        self._lock = threading.RLock()

        logger.info(f"事件存储已初始化 (最大事件数: {max_events})")

    def store(self, event: Event) -> None:
        """存储事件

        Args:
            event: 事件
        """
        with self._lock:
            self.events.append(event)

            # 检查是否超过最大数量
            if len(self.events) > self.max_events:
                # 移除最旧的事件
                self.events.pop(0)

    def get_events(
        self,
        event_type: EventType | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """获取事件

        Args:
            event_type: 事件类型过滤
            start_time: 开始时间过滤
            end_time: 结束时间过滤
            limit: 限制数量

        Returns:
            事件列表
        """
        with self._lock:
            filtered_events = self.events

            # 按事件类型过滤
            if event_type:
                filtered_events = [
                    e for e in filtered_events if e.event_type == event_type
                ]

            # 按时间过滤
            if start_time:
                filtered_events = [
                    e for e in filtered_events if e.timestamp >= start_time
                ]

            if end_time:
                filtered_events = [
                    e for e in filtered_events if e.timestamp <= end_time
                ]

            # 限制数量
            if limit:
                filtered_events = filtered_events[-limit:]

            return filtered_events.copy()

    def get_event_by_id(self, event_id: str) -> Event | None:
        """根据ID获取事件

        Args:
            event_id: 事件ID

        Returns:
            事件或None
        """
        with self._lock:
            for event in self.events:
                if event.event_id == event_id:
                    return event
            return None

    def clear_old_events(self, older_than: datetime) -> int:
        """清理旧事件

        Args:
            older_than: 比此时间更旧的事件将被清理

        Returns:
            清理的事件数量
        """
        with self._lock:
            original_count = len(self.events)
            self.events = [e for e in self.events if e.timestamp >= older_than]
            cleared_count = original_count - len(self.events)

            if cleared_count > 0:
                logger.info(f"清理了 {cleared_count} 个旧事件")

            return cleared_count


class EventSaga:
    """事件Saga（长事务）"""

    def __init__(self, saga_id: str, event_bus: EventBus):
        """初始化Saga

        Args:
            saga_id: Saga ID
            event_bus: 事件总线
        """
        self.saga_id = saga_id
        self.event_bus = event_bus
        self.steps: list[dict[str, Any]] = []
        self.current_step = 0
        self.status = "pending"  # pending, running, completed, failed, compensated
        self.created_at = datetime.now()
        self.completed_at: datetime | None = None

        logger.info(f"Saga已创建: {saga_id}")

    def add_step(
        self,
        event_type: EventType,
        data: dict[str, Any],
        compensation_event_type: EventType | None = None,
        compensation_data: dict[str, Any] | None = None,
    ) -> None:
        """添加Saga步骤

        Args:
            event_type: 事件类型
            data: 事件数据
            compensation_event_type: 补偿事件类型
            compensation_data: 补偿事件数据
        """
        step = {
            "event_type": event_type,
            "data": data,
            "compensation_event_type": compensation_event_type,
            "compensation_data": compensation_data,
            "status": "pending",
        }

        self.steps.append(step)
        logger.debug(f"Saga {self.saga_id} 添加步骤: {event_type.value}")

    def execute(self) -> bool:
        """执行Saga

        Returns:
            是否成功执行
        """
        self.status = "running"

        try:
            for i, step in enumerate(self.steps):
                self.current_step = i

                # 发布事件
                event = Event(
                    event_type=step["event_type"],
                    data=step["data"],
                    metadata={"saga_id": self.saga_id, "step": i},
                )

                self.event_bus.publish_sync(event)
                step["status"] = "completed"

                logger.debug(f"Saga {self.saga_id} 步骤 {i} 完成")

            self.status = "completed"
            self.completed_at = datetime.now()
            logger.info(f"Saga {self.saga_id} 执行完成")
            return True

        except Exception as e:
            logger.error(f"Saga {self.saga_id} 执行失败: {e}")
            self.status = "failed"
            return False

    def compensate(self) -> bool:
        """补偿Saga

        Returns:
            是否成功补偿
        """
        self.status = "compensating"

        try:
            # 反向执行补偿步骤
            for i in range(self.current_step, -1, -1):
                step = self.steps[i]

                if step["compensation_event_type"] and step["compensation_data"]:
                    # 发布补偿事件
                    event = Event(
                        event_type=step["compensation_event_type"],
                        data=step["compensation_data"],
                        metadata={
                            "saga_id": self.saga_id,
                            "step": i,
                            "compensation": True,
                        },
                    )

                    self.event_bus.publish_sync(event)
                    step["status"] = "compensated"

                    logger.debug(f"Saga {self.saga_id} 步骤 {i} 补偿完成")

            self.status = "compensated"
            logger.info(f"Saga {self.saga_id} 补偿完成")
            return True

        except Exception as e:
            logger.error(f"Saga {self.saga_id} 补偿失败: {e}")
            self.status = "compensation_failed"
            return False


# 全局事件总线
event_bus = EventBus()

# 全局事件存储
event_store = EventStore()


def event_handler(
    event_types: list[EventType], priority: int = 0
) -> Callable[[Callable[[Event], None]], Callable[[Event], None]]:
    """事件处理器装饰器

    Args:
        event_types: 事件类型列表
        priority: 优先级
    """

    def decorator(func: Callable[[Event], None]) -> Callable[[Event], None]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            return func(*args, **kwargs)

        # 注册处理器
        handler = EventHandler(
            handler_id=f"{func.__module__}.{func.__name__}",
            event_types=event_types,
            handler_func=func,
            priority=priority,
        )

        event_bus.register_handler(handler)
        return wrapper

    return decorator


def publish_event(
    event_type: EventType,
    data: dict[str, Any] | None = None,
    source: str = "system",
    metadata: dict[str, Any] | None = None,
) -> bool:
    """发布事件的便捷函数

    Args:
        event_type: 事件类型
        data: 事件数据
        source: 事件源
        metadata: 元数据

    Returns:
        是否成功发布
    """
    event = Event(
        event_type=event_type, data=data or {}, source=source, metadata=metadata or {}
    )

    # 存储事件
    event_store.store(event)

    # 发布事件
    return event_bus.publish(event)


def create_saga(saga_id: str) -> EventSaga:
    """创建Saga的便捷函数

    Args:
        saga_id: Saga ID

    Returns:
        Saga实例
    """
    return EventSaga(saga_id, event_bus)
