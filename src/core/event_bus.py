"""
事件总线 (Event Bus)

提供完整的事件驱动架构支持：
- 发布/订阅模式
- 同步和异步事件
- 事件过滤
- 优先级处理
- 事件历史记录
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from re import Pattern
from typing import (
    Any,
    ClassVar,
    TypeVar,
    cast,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EventPriority(Enum):
    """事件优先级"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """事件基类"""

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """从字典创建事件"""
        return cls(
            name=data["name"],
            data=data.get("data", {}),
            timestamp=data.get("timestamp", datetime.now()),
            priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
            source=data.get("source"),
        )


SyncEventHandler = Callable[[Event], Any]
AsyncEventHandler = Callable[[Event], Awaitable[Any]]
EventHandler = SyncEventHandler | AsyncEventHandler
EventFilter = Callable[[Event], bool]
Middleware = Callable[[Event], Event | None]


@dataclass
class EventSubscriber:
    """事件订阅者"""

    handler: EventHandler
    event_name: str
    priority: EventPriority = EventPriority.NORMAL
    filter_func: EventFilter | None = None
    is_async: bool = False
    _pattern_cache: ClassVar[dict[str, Pattern[str]]] = {}

    def matches(self, event: Event) -> bool:
        """检查事件是否匹配"""
        # 检查事件名称（支持通配符）
        if self.event_name != "*" and not self._match_pattern(event.name):
            return False

        # 应用过滤器
        return not (self.filter_func and not self.filter_func(event))

    def _match_pattern(self, event_name: str) -> bool:
        """匹配事件名称模式（支持 * 通配符）- 优化版"""
        pattern = self.event_name

        # 完全匹配
        if pattern == event_name:
            return True

        # 通配符匹配 - 使用缓存的正则表达式
        if "*" in pattern:
            # 检查缓存
            if pattern not in self._pattern_cache:
                regex = pattern.replace(".", r"\.").replace("*", ".*")
                self._pattern_cache[pattern] = re.compile(f"^{regex}$")

            compiled_regex = self._pattern_cache[pattern]
            return bool(compiled_regex.match(event_name))

        return False

    async def invoke(self, event: Event) -> Any:
        """调用处理器"""
        if self.is_async:
            async_handler = cast(AsyncEventHandler, self.handler)
            return await async_handler(event)
        sync_handler = cast(SyncEventHandler, self.handler)
        return sync_handler(event)


class EventBus:
    """事件总线"""

    def __init__(self, max_history: int = 500) -> None:  # 减少默认大小，防止内存泄漏
        self._subscribers: list[EventSubscriber] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._middleware: list[Middleware] = []

        # 性能优化：缓存编译的正则表达式
        self._pattern_cache: dict[str, Pattern[str]] = {}
        self._lock = threading.RLock()

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler,
        priority: EventPriority = EventPriority.NORMAL,
        filter_func: EventFilter | None = None,
    ) -> EventBus:
        """
        订阅事件

        Args:
            event_name: 事件名称（支持通配符 *）
            handler: 事件处理器
            priority: 优先级
            filter_func: 过滤函数

        Returns:
            self（支持链式调用）

        Examples:
            # 订阅特定事件
            bus.subscribe("user.login", on_user_login)

            # 订阅所有事件
            bus.subscribe("*", on_any_event)

            # 订阅模式匹配
            bus.subscribe("user.*", on_user_event)

            # 带过滤器
            bus.subscribe("order.*", on_order,
                filter_func=lambda e: e.data.get('amount', 0) > 100)
        """
        is_async = asyncio.iscoroutinefunction(handler)

        subscriber = EventSubscriber(
            handler=handler,
            event_name=event_name,
            priority=priority,
            filter_func=filter_func,
            is_async=is_async,
        )

        with self._lock:
            self._subscribers.append(subscriber)

            # 按优先级排序
            self._subscribers.sort(key=lambda s: s.priority.value, reverse=True)

        return self

    def unsubscribe(self, handler: EventHandler) -> bool:
        """
        取消订阅

        Args:
            handler: 要移除的处理器

        Returns:
            是否成功移除
        """
        with self._lock:
            original_length = len(self._subscribers)
            self._subscribers = [s for s in self._subscribers if s.handler != handler]
            return len(self._subscribers) < original_length

    def publish(self, event: Event) -> list[Any]:
        """
        发布同步事件

        Args:
            event: 事件对象

        Returns:
            所有处理器的返回值列表

        Examples:
            event = Event(name="user.login", data={"user_id": 123})
            results = bus.publish(event)
        """
        with self._lock:
            # 应用中间件
            for middleware in self._middleware:
                mutated = middleware(event)
                if mutated is None:
                    return []
                event = mutated

            # 添加到历史
            self._add_to_history(event)

            # 通知订阅者
            results: list[Any] = []
            for subscriber in self._subscribers:
                if subscriber.matches(event):
                    if subscriber.is_async:
                        # 同步publish不支持异步订阅者，跳过
                        # 请使用 publish_async 来处理异步订阅者
                        continue
                    else:
                        # 直接调用同步处理器
                        sync_handler = cast(SyncEventHandler, subscriber.handler)
                        result = sync_handler(event)
                        results.append(result)

        return results

    async def publish_async(self, event: Event) -> list[Any]:
        """
        发布异步事件

        Args:
            event: 事件对象

        Returns:
            所有处理器的返回值列表

        Examples:
            event = Event(name="data.processed", data={"items": 100})
            results = await bus.publish_async(event)
        """
        with self._lock:
            current_event = event

            for middleware in self._middleware:
                mutated = middleware(current_event)
                if mutated is None:
                    return []
                current_event = mutated

            self._add_to_history(current_event)
            subscribers_snapshot = list(self._subscribers)

        tasks: list[Awaitable[Any]] = []
        for subscriber in subscribers_snapshot:
            if subscriber.matches(current_event):
                tasks.append(subscriber.invoke(current_event))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        return []

    def use_middleware(self, middleware: Middleware) -> EventBus:
        """
        添加中间件

        中间件可以修改或拦截事件

        Args:
            middleware: 中间件函数，接收事件并返回修改后的事件（或None表示拦截）

        Examples:
            # 日志中间件
            def log_middleware(event):
                logger.info(f"Event: {event.name}")
                return event

            bus.use_middleware(log_middleware)
        """
        self._middleware.append(middleware)
        return self

    def get_history(self, event_name: str | None = None, limit: int | None = None) -> list[Event]:
        """
        获取事件历史

        Args:
            event_name: 过滤事件名称
            limit: 限制数量

        Returns:
            事件列表
        """
        history = self._history

        if event_name:
            history = [e for e in history if e.name == event_name]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """清空历史记录"""
        self._history.clear()

    def _add_to_history(self, event: Event) -> None:
        """添加到历史记录"""
        self._history.append(event)

        # 限制历史记录大小
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_subscriber_count(self, event_name: str | None = None) -> int:
        """获取订阅者数量"""
        if event_name is None:
            return len(self._subscribers)
        return sum(1 for s in self._subscribers if s.event_name == event_name)

    def clear(self) -> None:
        """清空所有订阅（主要用于测试）"""
        with self._lock:
            self._subscribers.clear()
            self._history.clear()
            self._middleware.clear()
            self._pattern_cache.clear()

    def close(self) -> None:
        """关闭事件总线，清理资源"""
        self.clear()
        logger.info("事件总线已关闭")


# 全局事件总线实例（线程安全）
_global_event_bus: EventBus | None = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """获取全局事件总线实例（线程安全）"""
    global _global_event_bus
    if _global_event_bus is None:
        with _event_bus_lock:
            if _global_event_bus is None:  # 双重检查锁
                _global_event_bus = EventBus()
    return _global_event_bus


def close_event_bus() -> None:
    """关闭全局事件总线"""
    global _global_event_bus
    if _global_event_bus is not None:
        with _event_bus_lock:
            if _global_event_bus is not None:
                _global_event_bus.close()
                _global_event_bus = None


_HandlerT = TypeVar("_HandlerT", bound=EventHandler)


def on_event(
    event_name: str,
    priority: EventPriority = EventPriority.NORMAL,
    filter_func: EventFilter | None = None,
) -> Callable[[_HandlerT], _HandlerT]:
    """
    事件处理装饰器

    Examples:
        @on_event("user.login")
        def handle_login(event: Event):
            logger.info(f"User {event.data['user_id']} logged in")

        @on_event("order.*", priority=EventPriority.HIGH)
        async def handle_order(event: Event):
            await process_order(event.data)
    """

    def decorator(func: _HandlerT) -> _HandlerT:
        bus = get_event_bus()
        bus.subscribe(event_name, func, priority, filter_func)
        return func

    return decorator


# 示例用法
if __name__ == "__main__":
    # 创建事件总线
    bus = EventBus()

    # 订阅事件
    def on_user_login(event: Event) -> None:
        logger.info(f"User {event.data['user_id']} logged in at {event.timestamp}")

    def on_user_logout(event: Event) -> None:
        logger.info(f"User {event.data['user_id']} logged out")

    def on_any_user_event(event: Event) -> None:
        logger.info(f"User event: {event.name}")

    bus.subscribe("user.login", on_user_login, priority=EventPriority.HIGH)
    bus.subscribe("user.logout", on_user_logout)
    bus.subscribe("user.*", on_any_user_event, priority=EventPriority.LOW)

    # 发布事件
    login_event = Event(name="user.login", data={"user_id": 123, "username": "john"}, source="auth_service")

    results = bus.publish(login_event)

    # 使用装饰器
    @on_event("order.created", priority=EventPriority.HIGH)
    def on_order_created(event: Event) -> None:
        logger.info(f"Order {event.data['order_id']} created")

    # 异步事件示例
    async def test_async() -> None:
        @on_event("data.processed")
        async def on_data_processed(event: Event) -> None:
            await asyncio.sleep(0.1)
            logger.info(f"Processed {event.data['count']} items")

        event = Event(name="data.processed", data={"count": 100})
        await bus.publish_async(event)

    # asyncio.run(test_async())
