"""
事件系统

提供事件总线、消息传递和观察者模式实现
"""

import asyncio
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    TypeVar,
)

from .types import Constants, EventData, EventHandler, EventType

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EventPriority(Enum):
    """事件优先级"""

    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4


class EventPhase(Enum):
    """事件阶段"""

    CAPTURE = "capture"  # 捕获阶段
    BUBBLE = "bubble"  # 冒泡阶段


@dataclass
class Event:
    """事件对象"""

    type: EventType
    data: EventData = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str | None = None
    target: str | None = None
    phase: EventPhase = EventPhase.BUBBLE
    bubbles: bool = True
    cancelable: bool = True
    default_prevented: bool = False
    propagation_stopped: bool = False

    def prevent_default(self) -> None:
        """阻止默认行为"""
        if self.cancelable:
            self.default_prevented = True

    def stop_propagation(self) -> None:
        """停止事件传播"""
        self.propagation_stopped = True

    def stop_immediate_propagation(self) -> None:
        """立即停止事件传播"""
        self.propagation_stopped = True


@dataclass
class EventListener:
    """事件监听器"""

    handler: EventHandler
    priority: EventPriority = EventPriority.NORMAL
    once: bool = False
    async_handler: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class IEventBus(ABC):
    """事件总线接口"""

    @abstractmethod
    def on(self, event_type: EventType, handler: EventHandler, **kwargs) -> str:
        """注册事件监听器"""
        pass

    @abstractmethod
    def off(self, event_type: EventType, listener_id: str) -> bool:
        """移除事件监听器"""
        pass

    @abstractmethod
    def emit(self, event: Event | EventType, data: EventData | None = None) -> None:
        """发送事件"""
        pass

    @abstractmethod
    def emit_async(
        self, event: Event | EventType, data: EventData | None = None
    ) -> Awaitable[None]:
        """异步发送事件"""
        pass

    @abstractmethod
    def once(self, event_type: EventType, handler: EventHandler, **kwargs) -> str:
        """注册一次性事件监听器"""
        pass

    @abstractmethod
    def remove_all_listeners(self, event_type: EventType | None = None) -> None:
        """移除所有监听器"""
        pass


class EventBus(IEventBus):
    """事件总线实现"""

    def __init__(self, max_listeners: int = 1000):
        self.max_listeners = max_listeners
        self._listeners: dict[EventType, list[EventListener]] = defaultdict(list)
        self._listener_ids: dict[str, EventListener] = {}
        self._lock = threading.RLock()
        self._event_queue: deque = deque()
        self._processing = False

    def on(
        self,
        event_type: EventType,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        async_handler: bool = False,
    ) -> str:
        """注册事件监听器"""
        with self._lock:
            if len(self._listeners[event_type]) >= self.max_listeners:
                logger.warning(
                    f"事件 {event_type} 的监听器数量已达到上限 {self.max_listeners}"
                )
                return ""

            listener = EventListener(
                handler=handler, priority=priority, async_handler=async_handler
            )

            self._listeners[event_type].append(listener)
            self._listener_ids[listener.id] = listener

            # 按优先级排序
            self._listeners[event_type].sort(
                key=lambda x: x.priority.value, reverse=True
            )

            logger.debug(f"注册事件监听器: {event_type} -> {listener.id}")
            return listener.id

    def off(self, event_type: EventType, listener_id: str) -> bool:
        """移除事件监听器"""
        with self._lock:
            if listener_id not in self._listener_ids:
                return False

            listener = self._listener_ids[listener_id]
            if listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
                del self._listener_ids[listener_id]

                # 清理空列表
                if not self._listeners[event_type]:
                    del self._listeners[event_type]

                logger.debug(f"移除事件监听器: {event_type} -> {listener_id}")
                return True

            return False

    def emit(self, event: Event | EventType, data: EventData | None = None) -> None:
        """发送事件"""
        if isinstance(event, str):
            event = Event(type=event, data=data or {})

        with self._lock:
            listeners = self._listeners.get(event.type, []).copy()

        # 执行监听器
        for listener in listeners:
            if event.propagation_stopped:
                break

            try:
                if listener.async_handler:
                    # 异步处理
                    asyncio.create_task(self._handle_async_listener(listener, event))
                else:
                    # 同步处理
                    listener.handler(event.data)

                # 一次性监听器
                if listener.once:
                    self.off(event.type, listener.id)

            except Exception as e:
                logger.error(f"事件监听器执行错误: {event.type} -> {listener.id}: {e}")

    async def emit_async(
        self, event: Event | EventType, data: EventData | None = None
    ) -> None:
        """异步发送事件"""
        if isinstance(event, str):
            event = Event(type=event, data=data or {})

        with self._lock:
            listeners = self._listeners.get(event.type, []).copy()

        # 执行监听器
        tasks = []
        for listener in listeners:
            if event.propagation_stopped:
                break

            try:
                if listener.async_handler:
                    task = asyncio.create_task(
                        self._handle_async_listener(listener, event)
                    )
                    tasks.append(task)
                else:
                    # 同步处理
                    listener.handler(event.data)

                # 一次性监听器
                if listener.once:
                    self.off(event.type, listener.id)

            except Exception as e:
                logger.error(f"事件监听器执行错误: {event.type} -> {listener.id}: {e}")

        # 等待所有异步任务完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_async_listener(
        self, listener: EventListener, event: Event
    ) -> None:
        """处理异步监听器"""
        try:
            if asyncio.iscoroutinefunction(listener.handler):
                await listener.handler(event.data)
            else:
                listener.handler(event.data)
        except Exception as e:
            logger.error(f"异步事件监听器执行错误: {e}")

    def once(
        self,
        event_type: EventType,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        async_handler: bool = False,
    ) -> str:
        """注册一次性事件监听器"""
        listener_id = self.on(event_type, handler, priority, async_handler)
        if listener_id:
            self._listener_ids[listener_id].once = True
        return listener_id

    def remove_all_listeners(self, event_type: EventType | None = None) -> None:
        """移除所有监听器"""
        with self._lock:
            if event_type:
                if event_type in self._listeners:
                    for listener in self._listeners[event_type]:
                        del self._listener_ids[listener.id]
                    del self._listeners[event_type]
            else:
                self._listeners.clear()
                self._listener_ids.clear()

    def get_listener_count(self, event_type: EventType) -> int:
        """获取监听器数量"""
        with self._lock:
            return len(self._listeners.get(event_type, []))

    def has_listeners(self, event_type: EventType) -> bool:
        """检查是否有监听器"""
        with self._lock:
            return (
                event_type in self._listeners and len(self._listeners[event_type]) > 0
            )


class EventEmitter:
    """事件发射器"""

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus or EventBus()
        self._local_listeners: dict[EventType, list[EventListener]] = defaultdict(list)

    def on(self, event_type: EventType, handler: EventHandler, **kwargs) -> str:
        """注册事件监听器"""
        return self.event_bus.on(event_type, handler, **kwargs)

    def off(self, event_type: EventType, listener_id: str) -> bool:
        """移除事件监听器"""
        return self.event_bus.off(event_type, listener_id)

    def emit(self, event_type: EventType, data: EventData | None = None) -> None:
        """发送事件"""
        self.event_bus.emit(event_type, data)

    async def emit_async(
        self, event_type: EventType, data: EventData | None = None
    ) -> None:
        """异步发送事件"""
        await self.event_bus.emit_async(event_type, data)

    def once(self, event_type: EventType, handler: EventHandler, **kwargs) -> str:
        """注册一次性事件监听器"""
        return self.event_bus.once(event_type, handler, **kwargs)


class EventMiddleware:
    """事件中间件"""

    def __init__(self):
        self.middlewares: list[Callable[[Event], Event]] = []

    def use(self, middleware: Callable[[Event], Event]) -> None:
        """添加中间件"""
        self.middlewares.append(middleware)

    def process(self, event: Event) -> Event:
        """处理事件"""
        for middleware in self.middlewares:
            event = middleware(event)
            if event is None:
                break
        return event


class EventStore:
    """事件存储"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.events: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def add(self, event: Event) -> None:
        """添加事件"""
        with self._lock:
            self.events.append(event)

    def get_events(
        self,
        event_type: EventType | None = None,
        since: float | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """获取事件"""
        with self._lock:
            events = list(self.events)

        # 过滤
        if event_type:
            events = [e for e in events if e.type == event_type]

        if since:
            events = [e for e in events if e.timestamp >= since]

        # 限制数量
        if limit:
            events = events[-limit:]

        return events

    def clear(self) -> None:
        """清空事件"""
        with self._lock:
            self.events.clear()


class EventReplay:
    """事件重放"""

    def __init__(self, event_bus: EventBus, event_store: EventStore):
        self.event_bus = event_bus
        self.event_store = event_store

    def replay(
        self,
        event_type: EventType | None = None,
        since: float | None = None,
        speed: float = 1.0,
    ) -> None:
        """重放事件"""
        events = self.event_store.get_events(event_type, since)

        for event in events:
            # 按速度重放
            if speed != 1.0:
                time.sleep(0.1 / speed)

            self.event_bus.emit(event)


class EventMetrics:
    """事件指标"""

    def __init__(self):
        self.event_counts: dict[EventType, int] = defaultdict(int)
        self.handler_counts: dict[EventType, int] = defaultdict(int)
        self.error_counts: dict[EventType, int] = defaultdict(int)
        self.total_events = 0
        self.total_handlers = 0
        self.total_errors = 0
        self._lock = threading.RLock()

    def record_event(self, event_type: EventType) -> None:
        """记录事件"""
        with self._lock:
            self.event_counts[event_type] += 1
            self.total_events += 1

    def record_handler(self, event_type: EventType) -> None:
        """记录处理器"""
        with self._lock:
            self.handler_counts[event_type] += 1
            self.total_handlers += 1

    def record_error(self, event_type: EventType) -> None:
        """记录错误"""
        with self._lock:
            self.error_counts[event_type] += 1
            self.total_errors += 1

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_events": self.total_events,
                "total_handlers": self.total_handlers,
                "total_errors": self.total_errors,
                "event_counts": dict(self.event_counts),
                "handler_counts": dict(self.handler_counts),
                "error_counts": dict(self.error_counts),
            }


# 全局事件总线
_global_event_bus = EventBus()


def get_global_event_bus() -> EventBus:
    """获取全局事件总线"""
    return _global_event_bus


# 便捷函数
def on(event_type: EventType, handler: EventHandler, **kwargs) -> str:
    """注册全局事件监听器"""
    return _global_event_bus.on(event_type, handler, **kwargs)


def off(event_type: EventType, listener_id: str) -> bool:
    """移除全局事件监听器"""
    return _global_event_bus.off(event_type, listener_id)


def emit(event_type: EventType, data: EventData | None = None) -> None:
    """发送全局事件"""
    _global_event_bus.emit(event_type, data)


def emit_async(event_type: EventType, data: EventData | None = None) -> Awaitable[None]:
    """异步发送全局事件"""
    return _global_event_bus.emit_async(event_type, data)


def once(event_type: EventType, handler: EventHandler, **kwargs) -> str:
    """注册全局一次性事件监听器"""
    return _global_event_bus.once(event_type, handler, **kwargs)


# 事件装饰器
def event_handler(
    event_type: EventType, priority: EventPriority = EventPriority.NORMAL
):
    """事件处理器装饰器"""

    def decorator(func: EventHandler) -> EventHandler:
        on(event_type, func, priority=priority)
        return func

    return decorator


def async_event_handler(
    event_type: EventType, priority: EventPriority = EventPriority.NORMAL
):
    """异步事件处理器装饰器"""

    def decorator(func: EventHandler) -> EventHandler:
        on(event_type, func, priority=priority, async_handler=True)
        return func

    return decorator


# 预定义事件类型
class ExperimentEvents:
    """实验相关事件"""

    STARTED = Constants.EVENT_EXPERIMENT_START
    ENDED = Constants.EVENT_EXPERIMENT_END
    STEP_STARTED = Constants.EVENT_STEP_START
    STEP_ENDED = Constants.EVENT_STEP_END
    PAUSED = "experiment.paused"
    RESUMED = "experiment.resumed"
    RESET = "experiment.reset"
    ERROR = Constants.EVENT_ERROR


class UIEvents:
    """UI相关事件"""

    WINDOW_CREATED = "ui.window.created"
    WINDOW_CLOSED = "ui.window.closed"
    WIDGET_CREATED = "ui.widget.created"
    WIDGET_DESTROYED = "ui.widget.destroyed"
    THEME_CHANGED = "ui.theme.changed"
    LAYOUT_CHANGED = "ui.layout.changed"


class SystemEvents:
    """系统相关事件"""

    STARTUP = "system.startup"
    SHUTDOWN = "system.shutdown"
    CONFIG_LOADED = "system.config.loaded"
    CONFIG_SAVED = "system.config.saved"
    PLUGIN_LOADED = "system.plugin.loaded"
    PLUGIN_UNLOADED = "system.plugin.unloaded"


if __name__ == "__main__":
    # 演示使用
    logger.info("=== 事件系统演示 ===\n")

    # 1. 基础事件
    logger.info("1. 基础事件:")

    def on_experiment_start(data):
        logger.info(f"实验开始: {data}")

    def on_experiment_end(data):
        logger.info(f"实验结束: {data}")

    # 注册监听器
    listener_id1 = on(ExperimentEvents.STARTED, on_experiment_start)
    listener_id2 = on(ExperimentEvents.ENDED, on_experiment_end)

    # 发送事件
    emit(ExperimentEvents.STARTED, {"experiment_id": "exp_001"})
    emit(ExperimentEvents.ENDED, {"experiment_id": "exp_001", "result": "success"})

    # 移除监听器
    off(ExperimentEvents.STARTED, listener_id1)

    logger.info("")

    # 2. 一次性事件
    logger.info("2. 一次性事件:")

    def on_config_loaded(data):
        logger.info(f"配置加载完成: {data}")

    once(SystemEvents.CONFIG_LOADED, on_config_loaded)

    # 发送多次事件，但只处理一次
    emit(SystemEvents.CONFIG_LOADED, {"config_file": "app.yaml"})
    emit(SystemEvents.CONFIG_LOADED, {"config_file": "app.yaml"})

    logger.info("")

    # 3. 事件装饰器
    logger.info("3. 事件装饰器:")

    @event_handler(UIEvents.THEME_CHANGED, EventPriority.HIGH)
    def on_theme_changed(data):
        logger.info(f"主题变更: {data}")

    emit(UIEvents.THEME_CHANGED, {"theme": "dark"})

    logger.info("")

    # 4. 事件总线
    logger.info("4. 事件总线:")

    bus = EventBus()
    emitter = EventEmitter(bus)

    def on_custom_event(data):
        logger.info(f"自定义事件: {data}")

    emitter.on("custom.event", on_custom_event)
    emitter.emit("custom.event", {"message": "Hello Event System!"})

    logger.info("")

    # 5. 事件存储和重放
    logger.info("5. 事件存储和重放:")

    store = EventStore(max_size=100)
    replay = EventReplay(bus, store)

    # 添加事件到存储
    event = Event(type="test.event", data={"value": 42})
    store.add(event)

    # 重放事件
    replay.replay("test.event")

    logger.info("事件系统演示完成！")
